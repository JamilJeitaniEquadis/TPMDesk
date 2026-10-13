# -*- coding: utf-8 -*-
"""WebVTT (as produced by Teams transcription) -> "Speaker: text" lines."""
import html
import re

_TS = re.compile(r'^\s*\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3}\s*-->\s*\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3}')
_VOICE = re.compile(r'<v(?:\.[^\s>]*)?\s+([^>]*)>(.*?)(?=</v>|<v[\s.]|$)', re.S)  # a <v> can be left open
_TAG = re.compile(r'</?[^>]+>')


def parse_vtt(text: str) -> list[tuple[str, str]]:
    """Returns [(speaker, text)], consecutive cues of the same speaker merged.

    Handles the WEBVTT header, NOTE/STYLE/REGION blocks, cue identifiers (Teams
    writes GUID-like ids), cue settings after the timestamps, several <v Name>
    spans in one cue, a <v> left open until the end of the cue, cues without a
    speaker, and HTML entities.
    """
    out: list[tuple[str, str]] = []
    blocks = re.split(r'\r?\n\s*\r?\n', text.replace('﻿', '').strip())
    for block in blocks:
        lines = [l for l in block.splitlines() if l.strip()]
        if not lines or lines[0].startswith(('WEBVTT', 'NOTE', 'STYLE', 'REGION')):
            continue
        i = next((k for k, l in enumerate(lines) if _TS.match(l)), None)
        if i is None:
            continue                                  # not a cue
        payload = '\n'.join(lines[i + 1:]).strip()
        if not payload:
            continue
        spans = _VOICE.findall(payload) or [('', payload)]
        for speaker, words in spans:
            words = html.unescape(_TAG.sub('', words))
            words = ' '.join(words.split())
            speaker = ' '.join(html.unescape(speaker).split()) or 'Unknown speaker'
            if not words:
                continue
            if out and out[-1][0] == speaker:
                out[-1] = (speaker, out[-1][1] + ' ' + words)
            else:
                out.append((speaker, words))
    return out


def to_lines(pairs: list[tuple[str, str]]) -> str:
    return '\n'.join(f'{s}: {t}' for s, t in pairs)
