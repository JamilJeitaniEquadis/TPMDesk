import asyncio, json
from types import SimpleNamespace
import pytest
from app.meetings import summarize as S

OK = {'overview': 'A. B. C.', 'decisions': ['XML per GLN'],
      'actionItems': [{'owner': 'Jamil', 'task': 'Send files', 'dueDate': 'Friday'}], 'openQuestions': []}


class FakeMessages:
    def __init__(self, replies): self.replies, self.calls = list(replies), []
    async def create(self, **kw):
        self.calls.append(kw)
        stop, payload = self.replies.pop(0)
        text = payload if isinstance(payload, str) else json.dumps(payload)
        return SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type='text', text=text)], _request_id='req_1')


def fake(monkeypatch, replies):
    m = FakeMessages(replies)
    monkeypatch.setattr(S, 'client', lambda: SimpleNamespace(messages=m))
    return m


def test_single_call_strict_schema(monkeypatch):
    m = fake(monkeypatch, [('end_turn', OK)])
    out = asyncio.run(S.summarize('Jamil: hi', 'Weekly'))
    assert out.actionItems[0].owner == 'Jamil'
    kw = m.calls[0]
    assert kw['output_config']['format']['type'] == 'json_schema'
    assert kw['model'] == S.settings.claude_model and '<transcript>' in kw['messages'][0]['content']


def test_chunks_then_merge(monkeypatch):
    monkeypatch.setattr(S, 'settings', SimpleNamespace(**{**S.settings.__dict__, 'chunk_chars': 30}))
    m = fake(monkeypatch, [('end_turn', OK)] * 20)
    lines = '\n'.join(f'A: line number {i}' for i in range(6))
    out = asyncio.run(S.summarize(lines))
    assert len(m.calls) == len(S.chunk_lines(lines, 30)) + 1 and 'Merge them' in m.calls[-1]['system']
    assert out.decisions == ['XML per GLN']


def test_merge_failure_falls_back_locally(monkeypatch):
    monkeypatch.setattr(S, 'settings', SimpleNamespace(**{**S.settings.__dict__, 'chunk_chars': 20}))
    lines = 'A: one two three\nB: four five six'
    n = len(S.chunk_lines(lines, 20))
    fake(monkeypatch, [('end_turn', OK)] * n + [('end_turn', 'not json')])
    out = asyncio.run(S.summarize(lines))
    assert len(out.actionItems) == 1 and out.overview.count('A. B. C.') == n


@pytest.mark.parametrize('stop,payload,code', [('refusal', OK, 'refusal'), ('max_tokens', OK, 'truncated'),
                                               ('end_turn', '{"overview": 1}', 'bad_json'), ('end_turn', 'nope', 'bad_json')])
def test_errors(monkeypatch, stop, payload, code):
    fake(monkeypatch, [(stop, payload)])
    with pytest.raises(S.SummaryError) as e:
        asyncio.run(S.summarize('A: hi'))
    assert e.value.code == code


def test_empty_transcript():
    with pytest.raises(S.SummaryError) as e:
        asyncio.run(S.summarize('  '))
    assert e.value.code == 'empty'


def test_chunk_lines_keeps_lines_and_cuts_long_ones():
    ch = S.chunk_lines('a' * 25 + '\nbb\ncc', 10)
    assert ''.join(ch).replace('\n', '') == 'a' * 25 + 'bbcc' and all(len(c) <= 10 for c in ch)
