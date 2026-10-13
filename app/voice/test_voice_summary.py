import numpy as np

from app.voice import voice_summary as v


def test_cut_point_lands_in_the_quiet_part():
    loud = np.ones(v.RATE * 10, dtype='float32') * 0.5
    loud[int(v.RATE * 8.0):int(v.RATE * 8.2)] = 0
    cut = v.cut_point(loud)
    assert v.RATE * 8.0 <= cut <= v.RATE * 8.2


def test_chunker_keeps_time_offsets_and_all_audio():
    got = []
    c = v.Chunker(lambda a, off: got.append((len(a), off)), piece=2)
    for _ in range(45):                       # 4.5 s of blocks
        c.add(np.ones(v.BLOCK, dtype='float32'))
    c.flush()
    assert sum(n for n, _ in got) == 45 * v.BLOCK
    assert got[0][1] == 0 and got[1][1] == got[0][0] / v.RATE


def test_long_transcripts_are_split_then_merged(monkeypatch):
    calls = []

    def fake(system, user):
        calls.append(user)
        return {'title': 't', 'overview': 'o', 'keyPoints': [], 'actionItems': [], 'openQuestions': []}

    monkeypatch.setattr(v, 'ask_claude', fake)
    monkeypatch.setattr(v, 'CHUNK_CHARS', 50)
    text = ''.join(f'[00:00:{i:02d}] line number {i}\n' for i in range(10))
    assert len(v.pieces(text, 50)) > 1
    v.summarise(text, 'Call')
    assert len(calls) == len(v.pieces(text, 50)) + 1 and '<part n="1">' in calls[-1]


def test_markdown():
    md = v.to_markdown({'title': 'X', 'overview': 'Done.', 'keyPoints': ['A'], 'actionItems': ['Send Excel'],
                        'openQuestions': []}, '', '13/10/2026')
    assert md.startswith('# X') and '- [ ] Send Excel' in md and '## Open questions\n- none' in md
