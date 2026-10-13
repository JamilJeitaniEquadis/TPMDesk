from fastapi.testclient import TestClient
from app.meetings import api, auth, graph
from app.meetings.summarize import Summary, ActionItem

VTT = 'WEBVTT\n\n00:00.000 --> 00:02.000\n<v Guitta>Jamil sends the XML files by Friday.</v>\n'


def client(monkeypatch):
    api.app.dependency_overrides[auth.graph_token] = lambda: 'tok'
    api.app.dependency_overrides[api.require_user] = lambda: 'u1'
    monkeypatch.setattr(auth, 'current_user_key', lambda request: 'u1')
    async def resolve(token, url): return graph.Meeting('M1', 'Marionnaud weekly', '2026-10-13T09:00:00Z', url)
    async def fetch(token, m): return [graph.Transcript('T1', None, VTT)]
    captured = {}
    async def summ(lines, title):
        captured['lines'] = lines
        return Summary(overview='Three. Sentences. Here.', decisions=['XML per GLN'],
                       actionItems=[ActionItem(owner='Jamil', task='Send XML files', dueDate='Friday')], openQuestions=['PK32 default?'])
    monkeypatch.setattr(graph, 'resolve_meeting', resolve)
    monkeypatch.setattr(graph, 'fetch_transcripts', fetch)
    monkeypatch.setattr(api, 'summarize', summ)
    return TestClient(api.app), captured


def test_full_loop(monkeypatch):
    c, captured = client(monkeypatch)
    task = c.post('/api/tasks', json={'title': 'Marionnaud migration'}).json()
    r = c.post('/api/summarize-meeting', json={'taskId': task['id'], 'joinUrl': 'https://teams.microsoft.com/l/meetup-join/x'})
    assert r.status_code == 200, r.text
    s = r.json()
    assert captured['lines'] == 'Guitta: Jamil sends the XML files by Friday.'
    assert s['meetingTitle'] == 'Marionnaud weekly' and s['actionItems'][0]['done'] is False
    item = s['actionItems'][0]['id']
    assert c.patch(f'/api/action-items/{item}', json={'done': True}).json()['done'] is True
    listed = c.get(f"/api/tasks/{task['id']}/summaries").json()
    assert len(listed) == 1 and listed[0]['actionItems'][0]['done'] is True
    assert 'Jamil sends' in c.get(f"/api/transcripts/{s['rawTranscriptRef']}").text


def test_errors_are_json(monkeypatch):
    c, _ = client(monkeypatch)
    task = c.post('/api/tasks', json={'title': 't'}).json()
    async def none(token, m): raise graph.GraphError('Transcription was not enabled for this meeting.', 404, 'no_transcript')
    monkeypatch.setattr(graph, 'fetch_transcripts', none)
    r = c.post('/api/summarize-meeting', json={'taskId': task['id'], 'joinUrl': 'https://teams.microsoft.com/l/meetup-join/x'})
    assert r.status_code == 404 and r.json()['error']['code'] == 'no_transcript'
    assert c.post('/api/summarize-meeting', json={'taskId': 'nope', 'joinUrl': 'https://teams.microsoft.com/x'}).json()['error']['code'] == 'task_not_found'


def test_not_signed_in_gets_reauth():
    api.app.dependency_overrides.clear()
    r = TestClient(api.app).post('/api/summarize-meeting', json={'taskId': 'x', 'joinUrl': 'https://teams.microsoft.com/x'})
    assert r.status_code == 401 and r.json()['error']['code'] == 'reauth'
