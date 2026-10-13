# -*- coding: utf-8 -*-
"""Microsoft Graph calls: join URL -> onlineMeeting -> transcripts (WebVTT).

Reads only the transcripts Teams itself produced; nothing here records or scrapes.
"""
import re
from dataclasses import dataclass
from urllib.parse import quote, unquote

import httpx

from .config import settings


class GraphError(Exception):
    """An error meant for the user: `status` is the HTTP status our API returns."""
    def __init__(self, message: str, status: int = 502, code: str = 'graph_error'):
        super().__init__(message)
        self.status, self.code = status, code


@dataclass
class Meeting:
    id: str
    subject: str
    start: str | None
    join_url: str


@dataclass
class Transcript:
    id: str
    created: str | None
    vtt: str


def _client(token: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=settings.graph_base, timeout=60.0,
                             headers={'Authorization': f'Bearer {token}'})


async def _get(c: httpx.AsyncClient, path: str, **kw) -> httpx.Response:
    try:
        r = await c.get(path, **kw)
    except httpx.HTTPError as e:
        raise GraphError(f'Microsoft Graph could not be reached ({type(e).__name__}).', 503, 'graph_unreachable')
    if r.status_code == 401:
        raise GraphError('Your Microsoft session has expired. Sign in again.', 401, 'reauth')
    if r.status_code == 403:
        raise GraphError(
            'Microsoft Graph refused access to this meeting or its transcript. Check that '
            'OnlineMeetings.Read and OnlineMeetingTranscript.Read.All are consented for the app, '
            'and that you organised or attended the meeting (some tenants only expose '
            'transcripts to the organiser).', 403, 'forbidden')
    if r.status_code == 429:
        raise GraphError('Microsoft Graph is throttling requests. Try again in a minute.', 429, 'throttled')
    if r.status_code >= 400 and r.status_code != 404:
        raise GraphError(f'Microsoft Graph returned {r.status_code}: {r.text[:300]}', 502)
    return r


def _join_url_variants(url: str) -> list[str]:
    """The JoinWebUrl filter is an exact match. Teams stores join links percent-encoded with
    lowercase hex (%3a, %40, %7b); links pasted from mail or chat are sometimes decoded or
    re-encoded in uppercase. Try the link as given, then those spellings."""
    url = url.strip()
    lower = lambda u: re.sub(r'%[0-9A-Fa-f]{2}', lambda m: m.group(0).lower(), u)
    out = [url, lower(url)]
    head, sep, rest = url.partition('/meetup-join/')
    if sep:
        enc = head + sep + quote(unquote(rest), safe='/?=&')
        out += [lower(enc), enc]
    out.append(unquote(url))
    return list(dict.fromkeys(out))


async def resolve_meeting(token: str, join_url: str) -> Meeting:
    if not join_url.lower().startswith('https://'):
        raise GraphError('That is not a Teams join link (it should start with https://).', 400, 'bad_url')
    async with _client(token) as c:
        for u in _join_url_variants(join_url):
            flt = "JoinWebUrl eq '" + u.replace("'", "''") + "'"
            r = await _get(c, '/me/onlineMeetings', params={'$filter': flt})
            if r.status_code == 404:
                continue
            items = r.json().get('value', [])
            if items:
                m = items[0]
                return Meeting(m['id'], m.get('subject') or 'Teams meeting',
                               m.get('startDateTime'), m.get('joinWebUrl') or join_url)
    raise GraphError('No Teams meeting with that join link was found for your account.', 404, 'meeting_not_found')


async def list_transcripts(token: str, meeting_id: str) -> list[dict]:
    async with _client(token) as c:
        r = await _get(c, f'/me/onlineMeetings/{meeting_id}/transcripts')
        if r.status_code == 404:
            return []
        items = r.json().get('value', [])
    return sorted(items, key=lambda t: t.get('createdDateTime') or '')


async def download_transcript(token: str, meeting_id: str, transcript_id: str) -> str:
    async with _client(token) as c:
        r = await _get(c, f'/me/onlineMeetings/{meeting_id}/transcripts/{transcript_id}/content',
                       params={'$format': 'text/vtt'}, headers={'Accept': 'text/vtt'})
        if r.status_code == 404:
            return ''
        return r.text


async def fetch_transcripts(token: str, meeting: Meeting) -> list[Transcript]:
    items = await list_transcripts(token, meeting.id)
    if not items:
        raise GraphError('Transcription was not enabled for this meeting, so there is nothing to '
                         'summarise. Turn on transcription in Teams next time.', 404, 'no_transcript')
    out = []
    for t in items:            # a meeting has several transcripts when transcription was restarted
        vtt = await download_transcript(token, meeting.id, t['id'])
        if vtt.strip():
            out.append(Transcript(t['id'], t.get('createdDateTime'), vtt))
    if not out:
        raise GraphError('The transcript of this meeting is empty or not available yet. Teams can '
                         'take a few minutes after the meeting ends.', 404, 'no_transcript')
    return out


async def latest_meeting_join_url(token: str) -> dict | None:
    """Most recent past Teams meeting in the user's calendar (needs Calendars.Read)."""
    from datetime import datetime, timedelta, timezone
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=14)
    async with _client(token) as c:
        r = await _get(c, '/me/calendarView', params={
            'startDateTime': start.isoformat(), 'endDateTime': end.isoformat(),
            '$select': 'subject,start,end,isOnlineMeeting,onlineMeeting',
            '$orderby': 'start/dateTime desc', '$top': '50'})
        if r.status_code == 404:
            return None
        for e in r.json().get('value', []):
            url = (e.get('onlineMeeting') or {}).get('joinUrl')
            if e.get('isOnlineMeeting') and url and (e.get('end') or {}).get('dateTime', '') <= end.strftime('%Y-%m-%dT%H:%M:%S'):
                return {'joinUrl': url, 'subject': e.get('subject'), 'start': (e.get('start') or {}).get('dateTime')}
    return None
