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
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, headers=h)
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


FAKE_VOICE = '''
import os, sys, json, time
rec = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'recordings')
d = os.path.join(rec, '2026-10-14_1500_' + sys.argv[sys.argv.index('--client') + 1])
os.makedirs(d, exist_ok=True)
while not os.path.exists(os.path.join(rec, '.stop')):
    time.sleep(0.1)
json.dump({'meta': {}, 'summary': {'args': sys.argv[1:]}}, open(os.path.join(d, 'summary.json'), 'w'))
'''


def test_voice_start_stop_and_status(tmp_path, monkeypatch, server):
    (tmp_path / 'voice_summary.py').write_text(FAKE_VOICE)
    monkeypatch.setattr(cl, 'VOICE', str(tmp_path))
    monkeypatch.setattr(cl, 'RECORDINGS', str(tmp_path / 'recordings'))
    monkeypatch.setattr(cl, 'STOP_FLAG', str(tmp_path / 'recordings' / '.stop'))
    opened = []
    monkeypatch.setattr(cl, 'open_path', opened.append)
    body = {'client': 'My"Origines', 'project': 'PIM', 'author': 'Jamil', 'kind': 'client'}
    assert call(server + '/voice/start', 'null', body=body)[0] == 200
    assert call(server + '/voice/start', 'null', body=body)[1]['code'] == 'busy'
    assert call(server + '/voice/status', 'null')[1]['running'] is True
    assert call(server + '/voice/stop', 'null', body={})[1] == {'stopped': True}
    cl._voice['proc'].wait(10)
    st = call(server + '/voice/status', 'null')[1]
    assert st['running'] is False and st['folder'] == '2026-10-14_1500_My Origines'
    assert st['summary']['summary']['args'][-2:] == ['--kind', 'client'] and 'My Origines' in st['summary']['summary']['args']
    assert call(server + '/voice/open', 'null', body={'what': 'recordings'})[0] == 200 and opened
    assert call(server + '/voice/start', 'https://evil.example', body=body)[0] == 403


def test_portal_settings(tmp_path, monkeypatch, server):
    (tmp_path / 'modules' / 'm1').mkdir(parents=True)
    (tmp_path / 'modules' / 'm1' / 'module.json').write_text(json.dumps({'id': 'm1', 'name': 'M1', 'version': '1'}))
    monkeypatch.setattr(cl, 'PORTAL', str(tmp_path))
    monkeypatch.setattr(cl, 'PORTAL_CONFIG', str(tmp_path / 'portal.config.json'))
    assert call(server + '/portal/config', 'null')[1] == {'exists': False}
    (tmp_path / 'portal.config.json').write_text(json.dumps({'site_title': 'T', 'publish': []}))
    st = call(server + '/portal/config', 'null')[1]
    assert st['exists'] and st['modules'][0]['id'] == 'm1'
    saved = call(server + '/portal/save', 'null', body={'config': {'publish': ['m1', 'nope'], 'public_repo': ' r ', 'block_words': ['x', ' ']}})[1]
    assert saved['config'] == {'site_title': 'T', 'publish': ['m1'], 'public_repo': 'r', 'block_words': ['x']}
    assert call(server + '/portal/config', 'https://evil.example')[0] == 403
