# -*- coding: utf-8 -*-
"""Meeting Summary API.

    uvicorn app.meetings.api:app --reload        (from the repository root)

POST  /api/summarize-meeting        {taskId, joinUrl}  -> the saved summary card
GET   /api/meetings/latest          most recent past Teams meeting (join URL auto-fill)
GET   /api/tasks/{id}/summaries     summaries already attached to a task
PATCH /api/action-items/{id}        {done}  -> tick / untick a subtask
GET   /api/transcripts/{ref}        the raw WebVTT kept for a summary
POST  /api/tasks, GET /api/tasks    minimal task records (swap for your own task table)
"""
import logging
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

from . import auth, graph, store
from .config import settings
from .summarize import SummaryError, summarize
from .vtt import parse_vtt, to_lines

log = logging.getLogger(__name__)

if not settings.session_secret:
    raise RuntimeError('SESSION_SECRET is not set (any long random string).')

app = FastAPI(title='TPM Desk · Meeting Summary')
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret, same_site='lax',
                   https_only=settings.redirect_uri.startswith('https://'), max_age=8 * 3600)
app.include_router(auth.router)
store.init()


def _err(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({'error': {'code': code, 'message': message}}, status_code=status)


@app.exception_handler(auth.NeedsSignIn)
async def _needs_sign_in(request: Request, exc):
    return _err(401, 'reauth', 'Sign in with Microsoft to read your Teams transcripts.')


@app.exception_handler(graph.GraphError)
async def _graph_error(request: Request, exc: graph.GraphError):
    return _err(exc.status, exc.code, str(exc))


@app.exception_handler(SummaryError)
async def _summary_error(request: Request, exc: SummaryError):
    return _err(exc.status, exc.code, str(exc))


class SummarizeIn(BaseModel):
    taskId: str
    joinUrl: str = Field(min_length=10, max_length=4000)


@app.post('/api/summarize-meeting')
async def summarize_meeting(body: SummarizeIn, request: Request, token: str = Depends(auth.graph_token)):
    if not store.get_task(body.taskId):
        return _err(404, 'task_not_found', 'That task does not exist.')
    meeting = await graph.resolve_meeting(token, body.joinUrl)
    transcripts = await graph.fetch_transcripts(token, meeting)
    lines = to_lines([p for t in transcripts for p in parse_vtt(t.vtt)])
    summary = await summarize(lines, meeting.subject)
    saved = store.save_summary(body.taskId, meeting, transcripts, summary,
                               settings.claude_model, auth.current_user_key(request))
    log.info('Summary %s saved for task %s (%d transcript(s), %d chars)',
             saved['id'], body.taskId, len(transcripts), len(lines))
    return saved


@app.get('/api/meetings/latest')
async def latest_meeting(token: str = Depends(auth.graph_token)):
    if 'Calendars.Read' not in settings.scopes:
        return {'joinUrl': None}
    try:
        return await graph.latest_meeting_join_url(token) or {'joinUrl': None}
    except graph.GraphError as e:          # auto-fill is a convenience: never block the button
        log.info('No latest meeting: %s', e)
        return {'joinUrl': None}


def require_user(request: Request) -> str:
    if not (k := auth.current_user_key(request)):
        raise auth.NeedsSignIn()
    return k


@app.get('/api/tasks/{task_id}/summaries')
async def task_summaries(task_id: str, _: str = Depends(require_user)):
    if not store.get_task(task_id):
        return _err(404, 'task_not_found', 'That task does not exist.')
    return store.summaries_for_task(task_id)


class DoneIn(BaseModel):
    done: bool


@app.patch('/api/action-items/{item_id}')
async def tick(item_id: str, body: DoneIn, _: str = Depends(require_user)):
    item = store.set_action_done(item_id, body.done)
    if not item:
        return _err(404, 'not_found', 'That action item does not exist.')
    return item


@app.get('/api/transcripts/{ref}', response_class=PlainTextResponse)
async def transcript(ref: str, _: str = Depends(require_user)):
    vtt = store.get_transcript(ref)
    if vtt is None:
        raise HTTPException(404)
    return vtt


class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)


@app.post('/api/tasks')
async def new_task(body: TaskIn, _: str = Depends(require_user)):
    return store.create_task(body.title)


@app.get('/api/tasks')
async def tasks(_: str = Depends(require_user)):
    return store.list_tasks()


app.mount('/', StaticFiles(directory=Path(__file__).parent / 'static', html=True), name='static')
