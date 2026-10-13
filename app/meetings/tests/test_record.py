from app.meetings.record import merge_segments, to_markdown, to_vtt
from app.meetings.summarize import ActionItem, Summary
from app.meetings.vtt import parse_vtt


def test_merge_orders_and_joins_same_speaker():
    segs = [(5.0, 7.0, 'Guitta', 'Send it Friday.'), (0.0, 2.0, 'Jamil', 'Hello.'),
            (2.5, 4.0, 'Jamil', 'All XMLs are in.')]
    out = merge_segments(segs)
    assert [(c[2], c[3]) for c in out] == [('Jamil', 'Hello. All XMLs are in.'), ('Guitta', 'Send it Friday.')]


def test_vtt_round_trips_through_parser():
    cues = [(0.0, 2.0, 'Jamil', 'Hello.'), (3661.25, 3662.0, 'Guitta', 'Bye.')]
    text = to_vtt(cues)
    assert '01:01:01.250 --> 01:01:02.000' in text
    assert parse_vtt(text) == [('Jamil', 'Hello.'), ('Guitta', 'Bye.')]


def test_markdown():
    s = Summary(overview='Done.', actionItems=[ActionItem(owner='Jamil', task='Send Excel', dueDate='Friday')])
    md = to_markdown('Sync', '13/10/2026', s)
    assert '- [ ] Send Excel (Jamil), due Friday' in md and '## Decisions\n- none' in md
