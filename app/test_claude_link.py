import json
import threading
import urllib.error
import urllib.request

import pytest

from app import claude_link as cl


def test_prompt_keeps_the_conversation_and_asks_for_json():
    p = cl.as_prompt([{'role': 'user', 'content': 'Q1'}, {'role': 'assistant', 'content': 'A1'},
                      {'role': 'user', 'content': 'Q2'}], want_json=True)
    assert '<user>\nQ1\n</user>' in p and '<assistant>\nA1\n</assistant>' in p
    assert p.rstrip().endswith('no other text.') and 'Q2' in p


def test_first_json_reads_fenced_answers():
    assert cl.first_json('```json\n{"a": 1}\n```') == {'a': 1}
    with pytest.raises(cl.LinkError):
        cl.first_json('no json here')


@pytest.fixture
def server(monkeypatch):
    monkeypatch.setattr(cl, 'ask', lambda prompt: '{"ok": true}' if 'JSON' in prompt else 'hello')
    srv = cl.Server(('127.0.0.1', 0), cl.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{srv.server_address[1]}'
    srv.shutdown()


def call(url, origin, header=True, body=None):
    h = {'Origin': origin, 'Content-Type': 'application/json'}
    if header:
        h['X-TPM-Desk'] = '1'
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, headers=h)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b'{}')


def test_only_the_desk_file_can_call(server):
    assert call(server + '/health', 'https://evil.example')[0] == 403
    assert call(server + '/health', 'null', header=False)[0] == 403
    assert call(server + '/health', 'null')[0] == 200


def test_sample_text_and_json(server):
    msgs = [{'role': 'user', 'content': 'hi'}]
    assert call(server + '/sample', 'null', body={'messages': msgs}) == (200, {'text': 'hello'})
    assert call(server + '/sample', 'null', body={'messages': msgs, 'json': True}) == (200, {'json': {'ok': True}})
