# -*- coding: utf-8 -*-
"""Record a meeting on this laptop, transcribe it locally, summarise it with Claude.

    python -m app.meetings.record --title "Marionnaud weekly" --name Jamil

Two tracks are recorded while the meeting runs: your microphone (labelled --name)
and what the laptop plays, i.e. the other participants (labelled --others). Stop with
Ctrl+C. Whisper turns the audio into text on this machine (the audio never leaves it),
then only the text goes to Claude. The folder gets me.wav, others.wav, transcript.vtt
(it can also be dropped in the desk's Meeting summary tab) and summary.md.

    python -m app.meetings.record --from recordings/2026-10-13_1400   # redo transcript + summary

Tell the participants you are recording before you start: --yes skips the reminder.
"""
import argparse
import asyncio
import datetime as dt
import os
import re
import threading
import wave

from .vtt import parse_vtt, to_lines

RATE = 16000                  # Whisper works at 16 kHz mono
BLOCK = RATE // 10            # 100 ms per read


# ---------- recording ----------

def _record(source, frames: list, stop: threading.Event, errors: list):
    import numpy as np
    try:
        with source.recorder(samplerate=RATE, channels=1, blocksize=BLOCK) as rec:
            while not stop.is_set():
                frames.append(np.asarray(rec.record(numframes=BLOCK)).reshape(-1))
    except Exception as e:                       # device unplugged, no permission...
        errors.append(f'{source.name}: {e}')


def _save(path: str, frames: list):
    import numpy as np
    data = np.concatenate(frames) if frames else np.zeros(0, dtype='float32')
    pcm = (np.clip(data, -1, 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())
    return len(data) / RATE


def record(folder: str) -> dict:
    """Records until Ctrl+C. Returns {track name: seconds}."""
    import soundcard as sc
    mic = sc.default_microphone()
    # Loopback of the default output = everything the laptop plays (Teams voices included).
    # Works on Windows (WASAPI) and Linux (PulseAudio). On macOS install a loopback device
    # such as BlackHole and pass it with --loopback.
    spk = sc.default_speaker()
    loop = sc.get_microphone(id=str(spk.name), include_loopback=True)
    print(f'Microphone : {mic.name}\nLaptop sound: {spk.name}')

    stop, errors = threading.Event(), []
    tracks = {'me': [], 'others': []}
    threads = [threading.Thread(target=_record, args=(src, tracks[k], stop, errors), daemon=True)
               for k, src in (('me', mic), ('others', loop))]
    for t in threads:
        t.start()
    started = dt.datetime.now()
    print('Recording... press Ctrl+C when the meeting ends.')
    try:
        while any(t.is_alive() for t in threads):
            threads[0].join(1)
            m, s = divmod(int((dt.datetime.now() - started).total_seconds()), 60)
            print(f'\r  {m:02d}:{s:02d}', end='', flush=True)
    except KeyboardInterrupt:
        pass
    stop.set()
    for t in threads:
        t.join(3)
    print()
    for e in errors:
        print('Recording problem:', e)
    return {k: _save(os.path.join(folder, f'{k}.wav'), f) for k, f in tracks.items()}


# ---------- transcription ----------

def transcribe(folder: str, names: dict, model_size: str, language: str | None) -> list:
    """Returns [(start seconds, speaker, text)] for both tracks, in time order."""
    from faster_whisper import WhisperModel
    print(f'Loading Whisper "{model_size}" (first run downloads it)...')
    model = WhisperModel(model_size, device='auto', compute_type='int8')
    segs = []
    for track, speaker in names.items():
        path = os.path.join(folder, f'{track}.wav')
        if not os.path.exists(path) or os.path.getsize(path) < 1000:
            continue
        print(f'Transcribing {track}.wav...')
        found, _ = model.transcribe(path, language=language, vad_filter=True)
        segs += [(s.start, s.end, speaker, s.text.strip()) for s in found if s.text.strip()]
    return merge_segments(segs)


def merge_segments(segs: list) -> list:
    """Time order, and back-to-back segments of the same speaker joined into one cue."""
    out = []
    for start, end, who, text in sorted(segs, key=lambda s: s[0]):
        if out and out[-1][2] == who and start - out[-1][1] < 2.0:
            out[-1] = (out[-1][0], end, who, out[-1][3] + ' ' + text)
        else:
            out.append((start, end, who, text))
    return out


def _ts(sec: float) -> str:
    ms = int(round(sec * 1000))
    return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}.{ms % 1000:03d}'


def to_vtt(cues: list) -> str:
    body = ''.join(f'\n{_ts(a)} --> {_ts(b)}\n<v {who}>{text}</v>\n' for a, b, who, text in cues)
    return 'WEBVTT\n' + body


# ---------- summary ----------

def to_markdown(title: str, when: str, s) -> str:
    md = [f'# {title or "Meeting"}', f'_{when}_', '', '## Overview', s.overview or '-', '', '## Decisions']
    md += [f'- {d}' for d in s.decisions] or ['- none']
    md += ['', '## Action items']
    md += [f'- [ ] {a.task}' + (f' ({a.owner})' if a.owner else '') + (f', due {a.dueDate}' if a.dueDate else '')
           for a in s.actionItems] or ['- none']
    md += ['', '## Open questions']
    md += [f'- {q}' for q in s.openQuestions] or ['- none']
    return '\n'.join(md) + '\n'


def summarise(folder: str, title: str, when: str) -> str:
    from .summarize import SummaryError, summarize
    lines = to_lines(parse_vtt(open(os.path.join(folder, 'transcript.vtt'), encoding='utf-8').read()))
    print('Summarising with Claude...')
    try:
        s = asyncio.run(summarize(lines, title))
    except SummaryError as e:
        raise SystemExit(f'Summary failed: {e} (the transcript is saved, rerun with --from {folder})')
    path = os.path.join(folder, 'summary.md')
    open(path, 'w', encoding='utf-8').write(to_markdown(title, when, s))
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--title', default='', help='meeting name, used in the summary')
    ap.add_argument('--name', default='Me', help='your name in the transcript')
    ap.add_argument('--others', default='Participants', help='label for the laptop sound')
    ap.add_argument('--lang', default=None, help='fr, en... (default: detected)')
    ap.add_argument('--model', default=os.environ.get('WHISPER_MODEL', 'small'),
                    help='Whisper size: tiny, base, small, medium, large-v3 (default small)')
    ap.add_argument('--out', default='recordings', help='parent folder for the recordings')
    ap.add_argument('--from', dest='src', help='existing folder: skip recording')
    ap.add_argument('--no-summary', action='store_true', help='stop after the transcript')
    ap.add_argument('--yes', action='store_true', help='skip the consent reminder')
    a = ap.parse_args(argv)

    now = dt.datetime.now()
    if a.src:
        folder = a.src
    else:
        if not a.yes and input('Did you tell everyone in the meeting that you are recording? [y/N] ').strip().lower() not in ('y', 'yes', 'o', 'oui'):
            raise SystemExit('Not recording.')
        slug = re.sub(r'[^\w-]+', '-', a.title).strip('-')[:40]
        folder = os.path.join(a.out, now.strftime('%Y-%m-%d_%H%M') + (f'_{slug}' if slug else ''))
        os.makedirs(folder, exist_ok=True)
        secs = record(folder)
        print('Saved', ', '.join(f'{k}.wav ({v / 60:.1f} min)' for k, v in secs.items()))

    cues = transcribe(folder, {'me': a.name, 'others': a.others}, a.model, a.lang)
    if not cues:
        raise SystemExit('No speech found in the recording.')
    open(os.path.join(folder, 'transcript.vtt'), 'w', encoding='utf-8').write(to_vtt(cues))
    print('Transcript:', os.path.join(folder, 'transcript.vtt'))
    if not a.no_summary:
        path = summarise(folder, a.title, now.strftime('%d/%m/%Y %H:%M'))
        print('\n' + open(path, encoding='utf-8').read())
        print('Summary:', path)


if __name__ == '__main__':
    main()
