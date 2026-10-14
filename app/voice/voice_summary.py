# -*- coding: utf-8 -*-
"""Voice summary: transcribe whatever this laptop plays, then summarise it with Claude.

    python voice_summary.py --title "Supplier call"

It captures the sound going to the current output (speakers, headphones, Bluetooth...),
follows you when you switch device, and writes the text live while you listen. Whisper
runs on this machine: the audio never leaves it, only the text goes to Claude.
Press Enter (or Ctrl+C) when you are done. The folder recordings/<date>_<title>/ then holds
transcript.txt and summary.md (transcript.txt can also be dropped in the desk's
Voice summary tab).

    python voice_summary.py --from voice/2026-10-13_1400_Supplier-call   # summarise again
    python voice_summary.py --mic                                         # add your microphone
"""
import argparse
import datetime as dt
import importlib.util
import json
import os
import queue
import re
import shutil
import signal
import site
import subprocess
import sys
import threading
import time
import warnings

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import report                                           # noqa: E402  (shared with the desk)

RATE = 16000              # Whisper works at 16 kHz mono
BLOCK = RATE // 10        # 100 ms per read
PIECE = 30                # seconds of audio sent to Whisper at a time
MODEL = os.environ.get('CLAUDE_MODEL', 'claude-sonnet-4-6')
CHUNK_BYTES = 300_000     # transcript size per Claude call (~75k tokens)


# ---------- capture ----------
# Capture runs in the main thread (soundcard uses COM on Windows, set up for the thread that
# imported it); Whisper runs in a worker thread so the capture never falls behind.

def capture(on_block, stop: threading.Event, with_mic: bool):
    """Calls on_block with 100 ms float32 blocks of the laptop sound (plus the mic if asked)."""
    import numpy as np
    import soundcard as sc
    warnings.filterwarnings('ignore', message='data discontinuity')   # silence gaps on Windows
    mic = sc.default_microphone() if with_mic else None
    while not stop.is_set():
        spk = sc.default_speaker()
        print(f'\n[listening to: {spk.name}]', flush=True)
        loop = sc.get_microphone(id=str(spk.name), include_loopback=True)
        recs = [loop.recorder(samplerate=RATE, channels=1, blocksize=BLOCK)]
        if mic:
            recs.append(mic.recorder(samplerate=RATE, channels=1, blocksize=BLOCK))
        try:
            for r in recs:
                r.__enter__()
            checked = time.monotonic()
            while not stop.is_set():
                block = sum(np.asarray(r.record(numframes=BLOCK)).reshape(-1)[:BLOCK] for r in recs)
                on_block(np.clip(block, -1, 1).astype('float32'))
                if time.monotonic() - checked > 2:          # headphones plugged in, Bluetooth...
                    checked = time.monotonic()
                    if sc.default_speaker().id != spk.id:
                        break
        except Exception as e:                                 # device vanished mid-read
            if not stop.is_set():
                print(f'\n[audio device changed or lost: {e}]', flush=True)
                time.sleep(1)
        finally:
            for r in recs:
                try:
                    r.__exit__(None, None, None)
                except Exception:
                    pass


def cut_point(audio, look_back: int = 5 * RATE) -> int:
    """Index of the quietest 100 ms in the last seconds, so a piece doesn't split a word."""
    tail = audio[-look_back:]
    n = len(tail) // BLOCK
    if n < 2:
        return len(audio)
    energy = (tail[:n * BLOCK].reshape(n, BLOCK) ** 2).mean(axis=1)
    return len(audio) - len(tail) + int(energy.argmin()) * BLOCK + BLOCK // 2


def stamp(sec: float) -> str:
    s = int(sec)
    return f'{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}'


class Chunker:
    """Gathers blocks and hands ~PIECE-second pieces, cut at a quiet moment, to a callback."""
    def __init__(self, on_piece, piece: int = PIECE):
        self.on_piece, self.size, self.buf, self.offset = on_piece, piece * RATE, [], 0.0

    def add(self, block):
        self.buf.append(block)
        if len(self.buf) * BLOCK >= self.size:
            import numpy as np
            audio = np.concatenate(self.buf)
            cut = cut_point(audio)
            self.on_piece(audio[:cut], self.offset)
            self.offset += cut / RATE
            self.buf = [audio[cut:]]

    def flush(self):
        if self.buf:
            import numpy as np
            self.on_piece(np.concatenate(self.buf), self.offset)
            self.buf = []


def listen(folder: str, model_size: str, language: str | None, with_mic: bool, gpu: bool = False) -> str:
    """Records and transcribes until Enter or Ctrl+C. Returns the transcript path."""
    os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')   # Windows without Developer Mode: harmless
    os.environ.setdefault('HF_HUB_VERBOSITY', 'error')               # no "unauthenticated requests" notice
    warnings.filterwarnings('ignore', module='huggingface_hub')
    from faster_whisper import WhisperModel
    print(f'Loading Whisper "{model_size}" (the first run downloads it)...')
    # CPU by default: an NVIDIA card without the CUDA libraries (cublas64_12.dll...) makes 'auto' crash.
    model = [WhisperModel(model_size, device='cuda' if gpu else 'cpu', compute_type='int8')]
    path = os.path.join(folder, 'transcript.txt')
    todo, stop = queue.Queue(), threading.Event()

    def text_of(audio):
        segs, _ = model[0].transcribe(audio, language=language, vad_filter=True)
        return [(s.start, s.text.strip()) for s in segs if s.text.strip()]

    def worker():
        with open(path, 'a', encoding='utf-8') as f:
            while True:
                job = todo.get()
                if job is None:
                    return
                audio, offset = job
                try:
                    try:
                        found = text_of(audio)
                    except RuntimeError as e:
                        if not gpu:
                            raise
                        print(f'\n[graphics card unavailable ({e}); switching to the processor]', flush=True)
                        model[0] = WhisperModel(model_size, device='cpu', compute_type='int8')
                        found = text_of(audio)
                except Exception as e:                         # keep listening, lose only this piece
                    print(f'\n[could not transcribe {stamp(offset)}-{stamp(offset + len(audio) / RATE)}: {e}]', flush=True)
                    continue
                for start, text in found:
                    line = f'[{stamp(offset + start)}] {text}'
                    print(line, flush=True)
                    f.write(line + '\n')
                    f.flush()

    w = threading.Thread(target=worker)
    w.start()
    chunks = Chunker(lambda audio, offset: todo.put((audio, offset)))
    signal.signal(signal.SIGINT, lambda *_: stop.set())      # Ctrl+C ends the capture cleanly
    threading.Thread(target=lambda: (sys.stdin.readline(), stop.set()), daemon=True).start()   # so does Enter
    flag = os.path.join(os.path.dirname(os.path.abspath(folder)), '.stop')   # and the desk's Stop button

    def watch():
        while not stop.is_set():
            if os.path.exists(flag):
                try:
                    os.remove(flag)
                except OSError:
                    pass
                stop.set()
            time.sleep(0.5)
    threading.Thread(target=watch, daemon=True).start()
    print('Listening. Play anything; press Enter here (or Stop in the desk) when you are done.')
    capture(chunks.add, stop, with_mic)
    print('\nFinishing the transcript...')
    chunks.flush()
    todo.put(None)
    w.join()
    signal.signal(signal.SIGINT, signal.default_int_handler)
    return path


# ---------- summary ----------

class NoClaude(Exception):
    """Claude Code is missing, not signed in, or failed: the transcript goes to the desk instead."""


def claude_cli() -> str | None:
    """Claude Code (signed in with your Claude account): summaries without an API key."""
    found = shutil.which('claude')
    if found:
        return found
    for p in (os.path.join(os.path.expanduser('~'), '.local', 'bin', 'claude.exe'),
              os.path.join(os.path.expanduser('~'), '.local', 'bin', 'claude')):
        if os.path.exists(p):
            return p
    return None


def ask_cli(task: str) -> dict:
    # Everything goes through stdin: a long prompt with line breaks doesn't survive a Windows command line.
    try:
        r = subprocess.run([claude_cli(), '-p', 'Follow the instructions in the text you received. Do not use any tool.',
                            '--output-format', 'json'], input=task.encode('utf-8'), capture_output=True, timeout=1800)
    except (OSError, TypeError, subprocess.TimeoutExpired) as e:
        raise NoClaude(str(e))
    try:
        res = json.loads(r.stdout.decode('utf-8', 'replace'))
    except json.JSONDecodeError:
        raise NoClaude((r.stderr or r.stdout).decode('utf-8', 'replace').strip()[-300:] or f'exit code {r.returncode}')
    text = str(res.get('result', ''))
    if res.get('is_error'):
        raise NoClaude(text[-300:])
    try:
        return json.loads(text[text.index('{'):text.rindex('}') + 1])
    except ValueError:
        raise NoClaude('Claude Code did not answer with a summary')


def ask_api(task: str) -> dict:
    import anthropic
    try:
        resp = anthropic.Anthropic().messages.create(
            model=MODEL, max_tokens=32000, messages=[{'role': 'user', 'content': task}],
            output_config={'format': {'type': 'json_schema', 'schema': report.SCHEMA}})
    except anthropic.AuthenticationError:
        raise SystemExit('ANTHROPIC_API_KEY is missing or wrong.')
    except anthropic.APIError as e:
        raise SystemExit(f'Claude could not summarise ({e}). The transcript is saved: rerun with --from.')
    if resp.stop_reason == 'refusal':
        raise SystemExit('Claude declined to summarise this transcript.')
    return json.loads(next(b.text for b in resp.content if b.type == 'text'))


def summarise(text: str, meta: dict) -> dict:
    """Both languages, the report fields; long transcripts are summarised in parts, then merged."""
    api = bool(os.environ.get('ANTHROPIC_API_KEY'))
    ask = ask_api if api else ask_cli
    parts = report.chunks(text, CHUNK_BYTES)
    done = []
    for i, p in enumerate(parts, 1):
        if len(parts) > 1:
            print(f'  part {i} of {len(parts)}...')
        done.append(ask(report.prompt(p, meta, i, len(parts), schema=not api)))
    if len(done) > 1:
        print('  merging the parts...')
        done = [ask(report.merge_prompt(done, meta, schema=not api))]
    return report.clean(done[0], meta)


def settings_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.json')


def author(given: str | None) -> str:
    """Your name for "Written by", asked once and kept in settings.json next to this script."""
    try:
        conf = json.load(open(settings_path(), encoding='utf-8'))
    except (OSError, ValueError):
        conf = {}
    if given:
        conf['author'] = given
    elif not conf.get('author') and sys.stdin.isatty():
        conf['author'] = input('Your name, for "Written by" in the reports (asked once): ').strip()
    if conf.get('author'):
        json.dump(conf, open(settings_path(), 'w', encoding='utf-8'), ensure_ascii=False)
    return conf.get('author', '')


def when(folder: str, start: dt.datetime | None, end: dt.datetime | None, text: str) -> dict:
    """Date and "10h – 11h" for the report header, from the recording or the folder name."""
    if start is None:
        m = re.match(r'(\d{4})-(\d{2})-(\d{2})_(\d{2})(\d{2})', os.path.basename(os.path.normpath(folder)))
        start = dt.datetime(*map(int, m.groups())) if m else dt.datetime.now()
    if end is None:
        stamps = re.findall(r'^\[(\d+):(\d\d):(\d\d)\]', text, re.M)
        h, mi, se = map(int, stamps[-1]) if stamps else (0, 0, 0)
        end = start + dt.timedelta(hours=h, minutes=mi, seconds=se)
    hm = lambda t: t.strftime('%Hh%M').replace('h00', 'h')
    mins = max(1, round((end - start).total_seconds() / 60))
    return {'date': start.strftime('%d/%m/%Y'), 'time': f'{hm(start)} – {hm(end)} ({mins} min)'}


def ensure_packages(listening: bool):
    """Installs what requirements.txt lists the first time, for the Python running this script."""
    need = (['soundcard', 'faster_whisper'] if listening else []) + ['anthropic']
    if all(importlib.util.find_spec(m) for m in need):
        return
    print(f'Installing the voice packages for Python {sys.version.split()[0]} (first time only, a few minutes)...')
    req = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'requirements.txt')
    in_venv = sys.prefix != sys.base_prefix
    cmd = [sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check', '--no-warn-script-location', '-q', '-r', req]
    if subprocess.run(cmd + ([] if in_venv else ['--user'])).returncode:
        hint = (' This Python is too new for the speech packages: use Python 3.12 (the .bat installs it).'
                if sys.version_info >= (3, 13) else ' Send the lines above to Claude.')
        raise SystemExit('The packages could not be installed.' + hint)
    if not in_venv:
        site.addsitedir(site.getusersitepackages())         # --user folder created just now
    importlib.invalidate_caches()


DESK = 'https://claude.ai/artifact/2BWgv38SCYPQkUujebuvQy'


def copy_to_clipboard(text: str) -> bool:
    try:
        if sys.platform == 'win32':
            # clip.exe reads UTF-16 when the text starts with a BOM: keeps the accents
            subprocess.run(['clip'], input=('\ufeff' + text).encode('utf-16-le'), check=True)
        elif sys.platform == 'darwin':
            subprocess.run(['pbcopy'], input=text.encode('utf-8'), check=True)
        else:
            subprocess.run(['xclip', '-selection', 'clipboard'], input=text.encode('utf-8'), check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def to_desk(text: str):
    """No API key: the desk opened in Claude summarises it, with your Claude account."""
    import webbrowser
    copied = copy_to_clipboard(text)
    webbrowser.open(DESK)
    print('\nThe desk is opening in your browser (sign in to claude.ai if asked).')
    print('Go to Voice summary > "Or paste the transcript", press Ctrl+V, then Summarize.'
          if copied else 'Open transcript.txt, copy it, paste it in Voice summary, then Summarize.')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--title', default='', help='what you are listening to (optional)')
    ap.add_argument('--client', default='', help='client name: makes the Equadis meeting report (PV)')
    ap.add_argument('--project', default='', help='project name, for the report header')
    ap.add_argument('--kind', choices=('auto',) + report.KINDS, default='auto',
                    help='client, internal or other (default: Claude decides; --client means client)')
    ap.add_argument('--author', default=None, help='"Written by" in the report (kept for next time)')
    ap.add_argument('--lang', default=None, help='language spoken: fr, en, ar... (default: detected)')
    ap.add_argument('--model', default=os.environ.get('WHISPER_MODEL', 'small'),
                    help='Whisper size: tiny, base, small, medium, large-v3 (default small)')
    ap.add_argument('--mic', action='store_true', help='also record your microphone')
    ap.add_argument('--gpu', action='store_true', help='use the NVIDIA card (needs the CUDA 12 libraries)')
    ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'recordings'),
                    help='parent folder (default: recordings next to this script)')
    ap.add_argument('--from', dest='src', help='existing folder: summarise its transcript again')
    ap.add_argument('--no-summary', action='store_true', help='only the transcript')
    ap.add_argument('--keep-open-on-error', action='store_true', help=argparse.SUPPRESS)   # started from the desk
    a = ap.parse_args(argv)

    ensure_packages(listening=not a.src)
    start = end = None
    if a.src:
        folder = a.src
    else:
        start = dt.datetime.now()
        slug = re.sub(r'[^\w-]+', '-', a.client or a.title).strip('-')[:40]
        folder = os.path.join(a.out, start.strftime('%Y-%m-%d_%H%M') + (f'_{slug}' if slug else ''))
        os.makedirs(folder, exist_ok=True)
        listen(folder, a.model, a.lang, a.mic, a.gpu)
        end = dt.datetime.now()

    path = os.path.join(folder, 'transcript.txt')
    text = open(path, encoding='utf-8').read() if os.path.exists(path) else ''
    if not text.strip():
        raise SystemExit('Nothing was heard, so there is nothing to summarise.')
    print('\nTranscript:', path)
    if a.no_summary:
        return
    if not os.environ.get('ANTHROPIC_API_KEY') and not claude_cli():
        print('\nClaude Code is not installed: see Setup in the desk (one time, 2 minutes).')
        to_desk(text)
        return
    meta = {'kind': 'client' if a.client else (a.kind if a.kind != 'auto' else None), 'client': a.client.strip(),
            'project': a.project.strip(), 'subject': a.title.strip(), 'author': author(a.author),
            **when(folder, start, end, text)}
    print('Summarising with Claude, in French and English...')
    try:
        data = summarise(text, meta)
    except NoClaude as e:
        print(f'\nClaude Code could not summarise: {e}')
        print('If it asks you to sign in: open a terminal, type  claude  , log in, then /exit.')
        to_desk(text)
        return
    except ValueError as e:
        raise SystemExit(f'{e} The transcript is saved: rerun with --from "{folder}".')
    md = report.markdown(data, meta)
    open(os.path.join(folder, 'summary.md'), 'w', encoding='utf-8').write(md)
    doc = os.path.join(folder, report.file_name(data, meta))
    open(doc, 'wb').write(report.docx(data, meta))
    open(os.path.join(folder, 'summary.json'), 'w', encoding='utf-8').write(
        json.dumps({'meta': meta, 'summary': data}, ensure_ascii=False, indent=1))
    print('\n' + md)
    print('Summary (French + English):', os.path.join(folder, 'summary.md'))
    print('Report (Word):', doc)
    if sys.platform == 'win32':
        os.startfile(doc)                                  # opens it in Word


if __name__ == '__main__':
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')               # accents in the console
    try:
        main()
    except (SystemExit, Exception) as e:
        failed = not isinstance(e, SystemExit) or e.code not in (None, 0)
        if failed and '--keep-open-on-error' in sys.argv:    # its own window: let the user read why
            import traceback
            print(e.code if isinstance(e, SystemExit) else traceback.format_exc())
            input('\nPress Enter to close this window.')
        raise
