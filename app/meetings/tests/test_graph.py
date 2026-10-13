import asyncio
import httpx
import pytest
from app.meetings import graph

ENC = 'https://teams.microsoft.com/l/meetup-join/19%3ameeting_abc%40thread.v2/0?context=%7b%22Tid%22%3a%22t%22%7d'


def mock(handler, monkeypatch):
    monkeypatch.setattr(graph, '_client', lambda token: httpx.AsyncClient(
        base_url='https://graph.test/v1.0', transport=httpx.MockTransport(handler)))


def test_resolve_tries_encoded_variant(monkeypatch):
    seen = []
    def h(req):
        flt = req.url.params['$filter']; seen.append(flt)
        if flt == f"JoinWebUrl eq '{ENC}'":
            return httpx.Response(200, json={'value': [{'id': 'M1', 'subject': 'Weekly', 'startDateTime': '2026-10-13T09:00:00Z', 'joinWebUrl': ENC}]})
        return httpx.Response(200, json={'value': []})
    mock(h, monkeypatch)
    m = asyncio.run(graph.resolve_meeting('t', ENC.replace('%3a', ':').replace('%40', '@').replace('%7b', '{').replace('%22', '"').replace('%7d', '}')))
    assert (m.id, m.subject) == ('M1', 'Weekly') and len(seen) == 2


def test_no_transcript_message(monkeypatch):
    mock(lambda req: httpx.Response(200, json={'value': []}), monkeypatch)
    with pytest.raises(graph.GraphError) as e:
        asyncio.run(graph.fetch_transcripts('t', graph.Meeting('M1', 'Weekly', None, ENC)))
    assert e.value.code == 'no_transcript' and 'not enabled' in str(e.value)


def test_transcripts_in_order_with_vtt_accept(monkeypatch):
    def h(req):
        if req.url.path.endswith('/transcripts'):
            return httpx.Response(200, json={'value': [{'id': 'T2', 'createdDateTime': '2026-10-13T10:00:00Z'},
                                                       {'id': 'T1', 'createdDateTime': '2026-10-13T09:00:00Z'}]})
        assert req.headers['accept'] == 'text/vtt' and req.url.params['$format'] == 'text/vtt'
        return httpx.Response(200, text=f'WEBVTT\n\n00:00.000 --> 00:01.000\n<v A>{req.url.path.split("/")[-2]}</v>\n')
    mock(h, monkeypatch)
    ts = asyncio.run(graph.fetch_transcripts('t', graph.Meeting('M1', 'Weekly', None, ENC)))
    assert [t.id for t in ts] == ['T1', 'T2'] and 'T1' in ts[0].vtt


@pytest.mark.parametrize('status,code', [(401, 'reauth'), (403, 'forbidden'), (429, 'throttled'), (500, 'graph_error')])
def test_error_mapping(monkeypatch, status, code):
    mock(lambda req: httpx.Response(status, text='x'), monkeypatch)
    with pytest.raises(graph.GraphError) as e:
        asyncio.run(graph.resolve_meeting('t', ENC))
    assert e.value.code == code


def test_rejects_non_https():
    with pytest.raises(graph.GraphError) as e:
        asyncio.run(graph.resolve_meeting('t', 'teams.microsoft.com/l/meetup-join/x'))
    assert e.value.status == 400
