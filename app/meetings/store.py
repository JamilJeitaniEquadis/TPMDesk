# -*- coding: utf-8 -*-
"""SQLite storage: tasks, meeting summaries linked to a task, action items as subtasks,
raw transcripts (kept apart, referenced by rawTranscriptRef), encrypted MSAL token caches."""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS transcripts (
  id TEXT PRIMARY KEY, meeting_id TEXT NOT NULL, graph_transcript_ids TEXT NOT NULL,
  vtt TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS meeting_summaries (
  id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  meeting_id TEXT NOT NULL, meeting_title TEXT NOT NULL, meeting_date TEXT,
  overview TEXT NOT NULL, decisions TEXT NOT NULL, open_questions TEXT NOT NULL,
  raw_transcript_ref TEXT NOT NULL REFERENCES transcripts(id), model TEXT NOT NULL,
  created_by TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS action_items (
  id TEXT PRIMARY KEY, summary_id TEXT NOT NULL REFERENCES meeting_summaries(id) ON DELETE CASCADE,
  position INTEGER NOT NULL, owner TEXT, task TEXT NOT NULL, due_date TEXT,
  done INTEGER NOT NULL DEFAULT 0, done_at TEXT);
CREATE TABLE IF NOT EXISTS token_caches (
  user_key TEXT PRIMARY KEY, blob BLOB NOT NULL, updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_summaries_task ON meeting_summaries(task_id, created_at);
"""

now = lambda: datetime.now(timezone.utc).isoformat(timespec='seconds')


@contextmanager
def db():
    con = sqlite3.connect(settings.db_path)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys = ON')
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init():
    with db() as con:
        con.executescript(SCHEMA)


# ---- tasks
def create_task(title: str) -> dict:
    t = {'id': uuid.uuid4().hex, 'title': title, 'createdAt': now()}
    with db() as con:
        con.execute('INSERT INTO tasks VALUES (?,?,?)', (t['id'], t['title'], t['createdAt']))
    return t


def get_task(task_id: str) -> dict | None:
    with db() as con:
        r = con.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
    return {'id': r['id'], 'title': r['title'], 'createdAt': r['created_at']} if r else None


def list_tasks() -> list[dict]:
    with db() as con:
        rows = con.execute('SELECT * FROM tasks ORDER BY created_at DESC').fetchall()
    return [{'id': r['id'], 'title': r['title'], 'createdAt': r['created_at']} for r in rows]


# ---- summaries
def save_summary(task_id, meeting, transcripts, summary, model, user_key) -> dict:
    sid, tid = uuid.uuid4().hex, uuid.uuid4().hex
    with db() as con:
        con.execute('INSERT INTO transcripts VALUES (?,?,?,?,?)', (
            tid, meeting.id, json.dumps([t.id for t in transcripts]),
            '\n\n'.join(t.vtt for t in transcripts), now()))
        con.execute('INSERT INTO meeting_summaries VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', (
            sid, task_id, meeting.id, meeting.subject, meeting.start, summary.overview,
            json.dumps(summary.decisions), json.dumps(summary.openQuestions), tid, model,
            user_key, now()))
        con.executemany('INSERT INTO action_items (id, summary_id, position, owner, task, due_date) '
                        'VALUES (?,?,?,?,?,?)',
                        [(uuid.uuid4().hex, sid, i, a.owner, a.task, a.dueDate)
                         for i, a in enumerate(summary.actionItems)])
    return get_summary(sid)


def _summary(con, r) -> dict:
    items = con.execute('SELECT * FROM action_items WHERE summary_id = ? ORDER BY position',
                        (r['id'],)).fetchall()
    return {
        'id': r['id'], 'taskId': r['task_id'], 'meetingTitle': r['meeting_title'],
        'date': r['meeting_date'], 'overview': r['overview'],
        'decisions': json.loads(r['decisions']), 'openQuestions': json.loads(r['open_questions']),
        'actionItems': [{'id': a['id'], 'owner': a['owner'], 'task': a['task'], 'dueDate': a['due_date'],
                         'done': bool(a['done'])} for a in items],
        'rawTranscriptRef': r['raw_transcript_ref'], 'model': r['model'], 'createdAt': r['created_at'],
    }


def get_summary(summary_id: str) -> dict | None:
    with db() as con:
        r = con.execute('SELECT * FROM meeting_summaries WHERE id = ?', (summary_id,)).fetchone()
        return _summary(con, r) if r else None


def summaries_for_task(task_id: str) -> list[dict]:
    with db() as con:
        rows = con.execute('SELECT * FROM meeting_summaries WHERE task_id = ? ORDER BY created_at DESC',
                           (task_id,)).fetchall()
        return [_summary(con, r) for r in rows]


def set_action_done(item_id: str, done: bool) -> dict | None:
    with db() as con:
        cur = con.execute('UPDATE action_items SET done = ?, done_at = ? WHERE id = ?',
                          (int(done), now() if done else None, item_id))
        if not cur.rowcount:
            return None
        a = con.execute('SELECT * FROM action_items WHERE id = ?', (item_id,)).fetchone()
    return {'id': a['id'], 'owner': a['owner'], 'task': a['task'], 'dueDate': a['due_date'], 'done': bool(a['done'])}


def get_transcript(ref: str) -> str | None:
    with db() as con:
        r = con.execute('SELECT vtt FROM transcripts WHERE id = ?', (ref,)).fetchone()
    return r['vtt'] if r else None


# ---- token caches (already encrypted by auth.py)
def load_cache(user_key: str) -> bytes | None:
    with db() as con:
        r = con.execute('SELECT blob FROM token_caches WHERE user_key = ?', (user_key,)).fetchone()
    return r['blob'] if r else None


def save_cache(user_key: str, blob: bytes):
    with db() as con:
        con.execute('INSERT INTO token_caches VALUES (?,?,?) ON CONFLICT(user_key) DO UPDATE SET '
                    'blob = excluded.blob, updated_at = excluded.updated_at', (user_key, blob, now()))


def delete_cache(user_key: str):
    with db() as con:
        con.execute('DELETE FROM token_caches WHERE user_key = ?', (user_key,))
