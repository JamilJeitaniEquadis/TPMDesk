# -*- coding: utf-8 -*-
"""Claude link: lets the desk opened from this folder use your Claude account, without an API key.

    python claude_link.py            (Open desk.bat starts it for you)

The desk (tpm-desk.html opened in Edge) sends its Claude requests to this small local server,
which passes them to Claude Code, signed in with your Claude account. Only the desk file can
call it: the server listens on this laptop only (127.0.0.1), answers file:// pages only, and
requires a header that other web pages can't send without the browser asking this server
first. Claude Code runs with its tools off, in an empty folder: it only writes text back.

It also lets the desk start and stop Voice summary (voice/voice_summary.py, in its own window) and
open the recordings folder or the last report: fixed commands only, nothing typed is run as a command.
"""
import json
import re
import os
import shutil
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get('TPM_LINK_PORT', '8765'))
HEADER = 'X-TPM-Desk'
ORIGINS = {'null'}                  # a page opened from a file (file://) sends Origin: null
MAX_BODY = 2 * 1024 * 1024
# Claude Code's built-in tools, all refused: the desk only needs text back.
NO_TOOLS = ['Bash', 'Edit', 'MultiEdit', 'Write', 'Read', 'Glob', 'Grep', 'LS', 'WebFetch', 'WebSearch',
            'NotebookEdit', 'NotebookRead', 'Task', 'TodoWrite', 'KillShell', 'BashOutput', 'SlashCommand']
EMPTY = tempfile.mkdtemp(prefix='tpm-claude-')


class LinkError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def claude_cli() -> str | None:
    found = shutil.which('claude')
    if found:
        return found
    for name in ('claude.exe', 'claude'):
        p = os.path.join(os.path.expanduser('~'), '.local', 'bin', name)
        if os.path.exists(p):
            return p
    return None


def as_prompt(messages: list, want_json: bool) -> str:
    """The desk's conversation, as one text for `claude -p` (it reads it from stdin)."""
    turns = [m for m in messages if isinstance(m, dict) and m.get('content')]
    if not turns:
        raise LinkError('invalid_request', 'Nothing to send.')
    text = lambda m: m['content'] if isinstance(m['content'], str) else json.dumps(m['content'], ensure_ascii=False)
    if len(turns) == 1:
        out = text(turns[0])
    else:
        past = '\n\n'.join(f'<{m.get("role", "user")}>\n{text(m)}\n</{m.get("role", "user")}>' for m in turns[:-1])
        out = (f'Conversation so far:\n{past}\n\nAnswer the last message, written by the user:\n{text(turns[-1])}')
    if want_json:
        out += '\n\nReply with only one JSON object, no other text.'
    return out


def ask(prompt: str) -> str:
    exe = claude_cli()
    if not exe:
        raise LinkError('not_installed', 'Claude Code is not installed on this laptop (see Setup in the desk).')
    try:
        r = subprocess.run([exe, '-p', 'Answer the request in the text you received. Do not use any tool.',
                            '--output-format', 'json', '--disallowedTools', *NO_TOOLS],
                           input=prompt.encode('utf-8'), capture_output=True, timeout=1200, cwd=EMPTY)
    except subprocess.TimeoutExpired:
        raise LinkError('upstream_error', 'Claude took too long to answer.')
    except OSError as e:
        raise LinkError('upstream_error', str(e))
    try:
        res = json.loads(r.stdout.decode('utf-8', 'replace'))
    except json.JSONDecodeError:
        err = (r.stderr or r.stdout).decode('utf-8', 'replace').strip()[-300:]
        raise LinkError('session_expired' if 'login' in err.lower() else 'upstream_error', err or f'exit {r.returncode}')
    text = str(res.get('result', ''))
    if res.get('is_error'):
        low = text.lower()
        code = ('session_expired' if 'login' in low or 'api key' in low
                else 'rate_limited' if 'limit' in low else 'upstream_error')
        raise LinkError(code, text[-300:])
    return text


def first_json(text: str):
    try:
        return json.loads(text[text.index('{'):text.rindex('}') + 1])
    except ValueError:
        raise LinkError('invalid_json', 'Claude did not answer in JSON.')


# ---------- Voice summary, started and stopped from the desk ----------
# Fixed commands only: the desk can start voice_summary.py (client and project are passed as
# arguments, never through a shell), ask it to stop, and open the recordings folder or a report.

VOICE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'voice')
RECORDINGS = os.path.join(VOICE, 'recordings')
STOP_FLAG = os.path.join(RECORDINGS, '.stop')             # voice_summary.py watches for it
_voice = {'proc': None}


def _clean_arg(x) -> str:
    return re.sub(r'[\x00-\x1f"]', ' ', str(x or '')).strip()[:80]


def voice_running() -> bool:
    p = _voice['proc']
    return p is not None and p.poll() is None


def voice_start(client: str, project: str, author: str = '', kind: str = '') -> dict:
    if voice_running():
        raise LinkError('busy', 'Voice summary is already listening.')
    os.makedirs(RECORDINGS, exist_ok=True)
    if os.path.exists(STOP_FLAG):
        os.remove(STOP_FLAG)
    cmd = [sys.executable, os.path.join(VOICE, 'voice_summary.py'), '--keep-open-on-error']
    if _clean_arg(client):
        cmd += ['--client', _clean_arg(client)]
    if _clean_arg(project):
        cmd += ['--project', _clean_arg(project)]
    if _clean_arg(author):
        cmd += ['--author', _clean_arg(author)]
    if kind in ('client', 'internal', 'other'):
        cmd += ['--kind', kind]
    flags = subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0   # its own window, to see the text
    _voice['proc'] = subprocess.Popen(cmd, cwd=VOICE, creationflags=flags)
    return {'started': True}


def voice_stop() -> dict:
    if not voice_running():
        return {'stopped': False}
    open(STOP_FLAG, 'w').close()
    return {'stopped': True}


def latest_folder() -> str | None:
    if not os.path.isdir(RECORDINGS):
        return None
    dirs = [os.path.join(RECORDINGS, d) for d in os.listdir(RECORDINGS) if os.path.isdir(os.path.join(RECORDINGS, d))]
    return max(dirs, key=os.path.getmtime) if dirs else None


def voice_status() -> dict:
    last = latest_folder()
    out = {'running': voice_running(), 'folder': os.path.basename(last) if last else None, 'summary': None}
    path = os.path.join(last, 'summary.json') if last else None
    if path and os.path.exists(path):
        try:
            out['summary'] = json.load(open(path, encoding='utf-8'))
        except (OSError, ValueError):
            pass
    return out


def open_path(path: str):
    if sys.platform == 'win32':
        os.startfile(path)
    else:
        subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', path])


def voice_open(what: str) -> dict:
    if what == 'recordings':
        os.makedirs(RECORDINGS, exist_ok=True)
        open_path(RECORDINGS)
        return {'opened': 'recordings'}
    last = latest_folder()
    if not last:
        raise LinkError('not_found', 'No recording yet.')
    if what == 'report':
        docs = [f for f in os.listdir(last) if f.endswith('.docx')]
        if not docs:
            raise LinkError('not_found', 'The last recording has no report yet.')
        open_path(os.path.join(last, docs[0]))
        return {'opened': docs[0]}
    open_path(last)
    return {'opened': os.path.basename(last)}


class Handler(BaseHTTPRequestHandler):
    server_version = 'TPMDeskClaudeLink/1'

    def _allowed(self) -> bool:
        return self.headers.get('Origin') in ORIGINS

    def _send(self, status: int, body: dict | None = None):
        data = json.dumps(body or {}).encode('utf-8')
        self.send_response(status)
        if self._allowed():
            self.send_header('Access-Control-Allow-Origin', self.headers['Origin'])
            self.send_header('Access-Control-Allow-Headers', f'Content-Type, {HEADER}')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Private-Network', 'true')
            self.send_header('Vary', 'Origin')
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):                                   # browser preflight
        self._send(204 if self._allowed() else 403)

    def _checked(self) -> bool:
        if not self._allowed() or self.headers.get(HEADER) != '1':
            self._send(403, {'code': 'forbidden', 'message': 'Only the desk opened from its folder can use this link.'})
            return False
        return True

    def do_GET(self):
        if not self._checked():
            return
        if self.path == '/health':
            self._send(200, {'ok': True, 'claude_code': bool(claude_cli()), 'voice': True})
        elif self.path == '/voice/status':
            self._send(200, voice_status())
        else:
            self._send(404, {'code': 'not_found'})

    def do_POST(self):
        if not self._checked():
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if size > MAX_BODY:
                raise LinkError('prompt_too_large', 'Too much text at once.')
            req = json.loads(self.rfile.read(size) or b'{}')
            if self.path == '/voice/start':
                return self._send(200, voice_start(req.get('client'), req.get('project'), req.get('author'), req.get('kind')))
            if self.path == '/voice/stop':
                return self._send(200, voice_stop())
            if self.path == '/voice/open':
                return self._send(200, voice_open(str(req.get('what') or 'last')))
            if self.path != '/sample':
                return self._send(404, {'code': 'not_found'})
            want_json = bool(req.get('json'))
            text = ask(as_prompt(req.get('messages') or [], want_json))
            self._send(200, {'json': first_json(text)} if want_json else {'text': text})
        except LinkError as e:
            self._send(502, {'code': e.code, 'message': str(e)})
        except OSError as e:
            self._send(500, {'code': 'os_error', 'message': str(e)})
        except (ValueError, TypeError) as e:
            self._send(400, {'code': 'invalid_request', 'message': str(e)})

    def log_message(self, fmt, *args):                      # one short line per request
        sys.stdout.write('  %s %s\n' % (self.command, args[1] if len(args) > 1 else ''))


class Server(ThreadingHTTPServer):
    allow_reuse_address = False      # on Windows, reuse would let a second copy share the port


def main():
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
    try:
        srv = Server(('127.0.0.1', PORT), Handler)
    except OSError:
        print(f'The Claude link is already running (port {PORT}). You can close this window.')
        return
    print('Claude link is on: the desk opened from this folder now uses your Claude account.')
    print('Claude Code: ' + ('found' if claude_cli() else 'NOT FOUND, see Setup in the desk'))
    print('Keep this window open while you use the desk. Close it to stop.\n')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
