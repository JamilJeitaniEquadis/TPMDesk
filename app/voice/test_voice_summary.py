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


ANSWER = {'kind': 'client', 'client': None, 'project': None, 'participants': {'client': [], 'equadis': []},
          'fr': {'title': 'Point', 'objective': 'O', 'overview': 'Résumé.', 'points': [], 'decisions': [],
                 'actions': [], 'openQuestions': [], 'nextMeeting': None},
          'en': {'title': 'Sync', 'objective': 'O', 'overview': 'Summary.', 'points': [], 'decisions': [],
                 'actions': [], 'openQuestions': [], 'nextMeeting': None}}


def test_long_transcripts_are_split_then_merged(monkeypatch):
    calls = []
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    monkeypatch.setattr(v, 'ask_cli', lambda task: calls.append(task) or ANSWER)
    monkeypatch.setattr(v, 'CHUNK_BYTES', 60)
    text = ''.join(f'[00:00:{i:02d}] line number {i}\n' for i in range(10))
    data = v.summarise(text, {'client': 'MyOrigines'})
    assert len(calls) == len(v.report.chunks(text, 60)) + 1 > 2
    assert '<part n="1">' in calls[-1] and 'Client: MyOrigines' in calls[0] and '"fr"' in calls[0]
    assert data['client'] == 'MyOrigines' and data['kind'] == 'client'


def test_when_reads_the_folder_and_the_last_timestamp():
    w = v.when('recordings/2026-07-17_1000_MyOrigines', None, None, '[00:00:05] a\n[01:00:00] b\n')
    assert w == {'date': '17/07/2026', 'time': '10h – 11h (60 min)'}
