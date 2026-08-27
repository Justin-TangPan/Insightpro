from services import opencode_sso_service as sso
from types import SimpleNamespace
import asyncio

import pytest
from fastapi import HTTPException
from routers import auth


def test_ticket_and_gateway_session_are_one_time_and_revocable(monkeypatch):
    stored = {}
    sessions = {}
    monkeypatch.setattr(sso.repository, "create_ticket", lambda token_hash, user_id, ttl: stored.update({token_hash: user_id}))
    monkeypatch.setattr(sso.repository, "consume_ticket", lambda token_hash: stored.pop(token_hash, None))

    ticket = sso.issue_ticket("user-1")
    assert sso.consume_ticket(ticket) == "user-1"
    assert sso.consume_ticket(ticket) is None

    monkeypatch.setattr(sso.repository, "create_session", lambda token_hash, user_id, ttl: sessions.update({token_hash: user_id}))
    monkeypatch.setattr(sso.repository, "get_session_user", lambda token_hash: sessions.get(token_hash))
    monkeypatch.setattr(sso.repository, "revoke_user_sessions", lambda user_id: sessions.clear())

    session = sso.create_gateway_session("user-1")
    assert sso.verify_gateway_session(session) == "user-1"
    assert sso.verify_gateway_session(session + "tampered") is None
    sso.revoke_gateway_sessions("user-1")
    assert sso.verify_gateway_session(session) is None


def test_single_instance_only_allows_configured_user(monkeypatch):
    monkeypatch.setattr(auth.settings, "OPENCODE_ALLOWED_EMAIL", "admin@example.com")
    auth._require_opencode_user(SimpleNamespace(email="ADMIN@example.com"))
    with pytest.raises(HTTPException) as error:
        auth._require_opencode_user(SimpleNamespace(email="user@example.com"))
    assert error.value.status_code == 403


def test_admin_user_directory_exposes_no_credentials(monkeypatch):
    account = SimpleNamespace(
        id="user-1", email="user@example.com", user_metadata={"name": "User"},
        app_metadata={"role": "user"}, created_at="2026-01-01", last_sign_in_at=None,
    )
    monkeypatch.setattr(auth.supabase.auth.admin, "list_users", lambda page, per_page: [account])
    result = asyncio.run(auth.auth_users())
    assert result["users"] == [{
        "id": "user-1", "email": "user@example.com", "name": "User", "role": "user",
        "created_at": "2026-01-01", "last_sign_in_at": None,
    }]
