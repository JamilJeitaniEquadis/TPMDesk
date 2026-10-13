from app.meetings.vtt import parse_vtt, to_lines

TEAMS = """WEBVTT

NOTE produced by Microsoft Teams

5a1c2f3e-1111-2222-3333-444455556666/12-0
00:00:01.120 --> 00:00:04.560
<v Jamil Jeitani>Bonjour à tous, let&apos;s start.</v>

5a1c2f3e-1111-2222-3333-444455556666/13-0
00:00:05.000 --> 00:00:07.000
<v Jamil Jeitani>Agenda is the Marionnaud import.</v>

00:00:08.000 --> 00:00:10.000 align:start position:10%
<v.loud Guitta Haddad>We decided: XML only &amp; per GLN.</v>

00:00:11.000 --> 00:00:13.000
<v Guitta Haddad>Jamil, send the files by Friday.
<v Jamil Jeitani>OK, I'll do it.</v>

00:00:14.000 --> 00:00:15.000
No speaker tag here.
"""


def test_parses_teams_vtt():
    pairs = parse_vtt(TEAMS)
    assert pairs == [
        ('Jamil Jeitani', "Bonjour à tous, let's start. Agenda is the Marionnaud import."),
        ('Guitta Haddad', 'We decided: XML only & per GLN. Jamil, send the files by Friday.'),
        ('Jamil Jeitani', "OK, I'll do it."),
        ('Unknown speaker', 'No speaker tag here.'),
    ]
    assert to_lines(pairs).splitlines()[1].startswith('Guitta Haddad: We decided')


def test_empty_and_header_only():
    assert parse_vtt('') == []
    assert parse_vtt('WEBVTT\n\nNOTE nothing') == []
    assert parse_vtt('﻿WEBVTT\r\n\r\n00:00.000 --> 00:01.000\r\n<v A>hi</v>\r\n') == [('A', 'hi')]
