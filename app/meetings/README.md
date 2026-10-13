# Meeting Summary

After a Teams meeting that had transcription on: one click on a task, and the transcript Teams
produced is read through Microsoft Graph, summarised by Claude, and attached to the task as a
card (overview, decisions, action items as checkable subtasks, open questions). Nothing records
audio or reads the Teams UI.

## Setup

1. Entra ID app registration (Web platform)
   - Redirect URI: `http://localhost:8000/auth/callback` (and your production URL)
   - A client secret
   - Delegated Microsoft Graph permissions: `OnlineMeetings.Read` (find the meeting from its join
     link), `OnlineMeetingTranscript.Read.All` (transcripts, needs admin consent), and optionally
     `Calendars.Read` (auto-fill the latest meeting's join link)
2. `pip install -r app/meetings/requirements.txt`
3. Copy `app/meetings/.env.example`, fill it, export it.
4. From the repository root: `uvicorn app.meetings.api:app --reload`, open http://localhost:8000

## Flow

`POST /api/summarize-meeting {taskId, joinUrl}`
1. `GET /me/onlineMeetings?$filter=JoinWebUrl eq '<url>'` (also tries the lowercase / decoded
   spellings of the link, since the filter is an exact match)
2. `GET /me/onlineMeetings/{id}/transcripts`; none -> 404 `no_transcript`
   ("Transcription was not enabled for this meeting")
3. `GET .../transcripts/{tid}/content?$format=text/vtt` with `Accept: text/vtt`, every transcript
   in creation order
4. `vtt.py` turns the WebVTT into `Speaker: text` lines (`<v Name>` tags, merged turns)
5. `summarize.py` calls Claude with a JSON schema (structured outputs), splits long transcripts
   (`SUMMARY_CHUNK_CHARS`) and merges the parts with one more call
6. `store.py` saves the summary, its action items and the raw VTT (`rawTranscriptRef`)

Errors come back as `{"error": {"code", "message"}}` with a message the card shows as is;
`401 reauth` sends the user to Microsoft sign-in.

## Auth and tokens

`auth.py`: MSAL authorization-code flow. The browser holds only a signed session cookie; the
MSAL token cache (with the refresh token) is stored server-side, Fernet-encrypted, and every
Graph call goes through `acquire_token_silent`, which refreshes on its own. To use your own
login instead, keep `graph_token()` and replace `current_user_key()`.

## Frontend

`static/meeting-summary.js` is a web component: `<meeting-summary task-id="..."></meeting-summary>`
(`api-base` attribute if the API is on another origin). `static/index.html` is a small task page
that hosts it.

## Tests

`python -m pytest app/meetings/tests` (Graph and Claude are mocked).
