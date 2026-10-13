# -*- coding: utf-8 -*-
"""Microsoft sign-in (MSAL, authorization-code flow, delegated scopes).

The browser only ever holds a signed session cookie with an opaque user key. The MSAL token
cache (access + refresh tokens) stays on the server, encrypted with Fernet, one row per user.
`graph_token()` refreshes silently through MSAL; when that is no longer possible it raises
NeedsSignIn and the API answers 401 {"code": "reauth"} so the UI sends the user to /auth/login.

PLUG-IN POINT: if your app already has auth/sessions, keep `graph_token()` and replace
`current_user_key()` with your own user id, and mount the /auth routes under your login.
"""
import secrets

import msal
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from starlette.concurrency import run_in_threadpool

from . import store
from .config import settings

router = APIRouter()


class NeedsSignIn(Exception):
    pass


def _fernet() -> Fernet:
    if not settings.token_enc_key:
        raise RuntimeError('TOKEN_ENC_KEY is not set (generate one with: python -c '
                           '"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")')
    return Fernet(settings.token_enc_key.encode())


def _load(user_key: str | None) -> msal.SerializableTokenCache:
    cache = msal.SerializableTokenCache()
    blob = store.load_cache(user_key) if user_key else None
    if blob:
        try:
            cache.deserialize(_fernet().decrypt(blob).decode())
        except InvalidToken:
            store.delete_cache(user_key)          # key rotated: force a new sign-in
    return cache


def _save(user_key: str, cache: msal.SerializableTokenCache):
    if cache.has_state_changed:
        store.save_cache(user_key, _fernet().encrypt(cache.serialize().encode()))


def _app(cache: msal.SerializableTokenCache) -> msal.ConfidentialClientApplication:
    return msal.ConfidentialClientApplication(
        settings.client_id, client_credential=settings.client_secret,
        authority=f'https://login.microsoftonline.com/{settings.tenant_id}', token_cache=cache)


def current_user_key(request: Request) -> str | None:
    return request.session.get('user_key')


def _silent(user_key: str) -> str:
    cache = _load(user_key)
    app = _app(cache)
    accounts = app.get_accounts()
    result = app.acquire_token_silent(settings.scopes, account=accounts[0]) if accounts else None
    _save(user_key, cache)
    if not result or 'access_token' not in result:
        raise NeedsSignIn()
    return result['access_token']


async def graph_token(request: Request) -> str:
    user_key = current_user_key(request)
    if not user_key:
        raise NeedsSignIn()
    return await run_in_threadpool(_silent, user_key)


@router.get('/auth/login')
async def login(request: Request, next: str = '/'):
    flow = _app(msal.SerializableTokenCache()).initiate_auth_code_flow(
        settings.scopes, redirect_uri=settings.redirect_uri, state=secrets.token_urlsafe(16))
    request.session['flow'] = flow
    request.session['next'] = next if next.startswith('/') else '/'
    return RedirectResponse(flow['auth_uri'])


@router.get('/auth/callback')
async def callback(request: Request):
    flow = request.session.pop('flow', None)
    if not flow:
        raise HTTPException(400, 'Sign-in expired, start again.')
    cache = msal.SerializableTokenCache()
    result = await run_in_threadpool(
        _app(cache).acquire_token_by_auth_code_flow, flow, dict(request.query_params))
    if 'access_token' not in result:
        raise HTTPException(401, result.get('error_description') or 'Sign-in failed.')
    claims = result.get('id_token_claims', {})
    user_key = f"{claims.get('tid', '')}.{claims.get('oid', '')}"
    _save(user_key, cache)
    request.session['user_key'] = user_key
    request.session['name'] = claims.get('name', '')
    return RedirectResponse(request.session.pop('next', '/'))


@router.post('/auth/logout')
async def logout(request: Request):
    if (k := current_user_key(request)):
        store.delete_cache(k)
    request.session.clear()
    return {'ok': True}


@router.get('/auth/me')
async def me(request: Request):
    return {'signedIn': bool(current_user_key(request)), 'name': request.session.get('name', '')}
