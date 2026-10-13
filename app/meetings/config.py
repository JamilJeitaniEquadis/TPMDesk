# -*- coding: utf-8 -*-
"""Settings, read from the environment (see .env.example)."""
import os
from dataclasses import dataclass, field


def _list(name, default):
    return [s.strip() for s in os.environ.get(name, default).split(',') if s.strip()]


@dataclass(frozen=True)
class Settings:
    # Entra ID app registration (confidential client, web platform)
    tenant_id: str = os.environ.get('MS_TENANT_ID', 'organizations')
    client_id: str = os.environ.get('MS_CLIENT_ID', '')
    client_secret: str = os.environ.get('MS_CLIENT_SECRET', '')
    redirect_uri: str = os.environ.get('MS_REDIRECT_URI', 'http://localhost:8000/auth/callback')
    # Delegated scopes. OnlineMeetings.Read is needed for the JoinWebUrl lookup,
    # OnlineMeetingTranscript.Read.All for the transcripts, Calendars.Read only to
    # auto-fill the latest meeting (drop it from the env if you don't want that).
    scopes: list = field(default_factory=lambda: _list(
        'MS_SCOPES', 'OnlineMeetings.Read,OnlineMeetingTranscript.Read.All,Calendars.Read'))
    graph_base: str = os.environ.get('GRAPH_BASE', 'https://graph.microsoft.com/v1.0')

    # Session cookie signing + token-cache encryption (Fernet key, 32 url-safe base64 bytes)
    session_secret: str = os.environ.get('SESSION_SECRET', '')
    token_enc_key: str = os.environ.get('TOKEN_ENC_KEY', '')

    # Anthropic. The API key is read by the SDK itself (ANTHROPIC_API_KEY).
    claude_model: str = os.environ.get('CLAUDE_MODEL', 'claude-sonnet-4-6')
    chunk_chars: int = int(os.environ.get('SUMMARY_CHUNK_CHARS', '400000'))   # ~100k tokens per chunk
    max_output_tokens: int = int(os.environ.get('SUMMARY_MAX_TOKENS', '16000'))

    db_path: str = os.environ.get('MEETINGS_DB', 'meetings.sqlite3')


settings = Settings()
