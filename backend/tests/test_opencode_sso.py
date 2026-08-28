from services import opencode_sso_service as sso
from types import SimpleNamespace
import asyncio

import pytest
from fastapi import HTTPException
from routers import auth


def test_ticket_and_gateway_session_are_one_time_and_revocable(monkeypatch):
    stored = {}
    sessions = {}
    monkeypatch.setattr(sso.repository, "create_ticket", lambda token_hash, user_id, target_user_id, ttl: stored.update({token_hash: {"user_id": user_id, "agent_user_id": target_user_id or user_id}}))
    monkeypatch.setattr(sso.repository, "consume_ticket", lambda token_hash: stored.pop(token_hash, None))

    ticket = sso.issue_ticket("user-1")
    assert sso.consume_ticket(ticket) == {"user_id": "user-1", "agent_user_id": "user-1"}
    assert sso.consume_ticket(ticket) is None

    monkeypatch.setattr(sso.repository, "create_session", lambda token_hash, user_id, agent_user_id, auth_role, agent_role, display_name, ttl: sessions.update({token_hash: {
        "user_id": user_id, "agent_user_id": agent_user_id, "auth_role": auth_role,
        "agent_role": agent_role, "display_name": display_name,
    }}))
    monkeypatch.setattr(sso.repository, "get_session_user", lambda token_hash: sessions.get(token_hash))
    monkeypatch.setattr(sso.repository, "revoke_user_sessions", lambda user_id: sessions.clear())

    session = sso.create_gateway_session("user-1", "user-1", "user", "user", "User")
    assert sso.verify_gateway_session(session)["agent_user_id"] == "user-1"
    assert sso.verify_gateway_session(session + "tampered") is None
    sso.revoke_gateway_sessions("user-1")
    assert sso.verify_gateway_session(session) is None


def test_normal_user_gets_own_space_but_cannot_target_another_user(monkeypatch):
    user = SimpleNamespace(id="00000000-0000-4000-8000-000000000001", app_metadata={"role": "user"})
    issued = []
    monkeypatch.setattr(auth.opencode_sso_service, "issue_ticket", lambda user_id, target: issued.append((user_id, target)) or "ticket")
    result = asyncio.run(auth.create_opencode_ticket(None, user))
    assert result["redirect_url"].endswith("ticket=ticket")
    assert issued == [(str(user.id), None)]
    with pytest.raises(HTTPException) as error:
        asyncio.run(auth.create_opencode_ticket(
            auth.AgentTicketRequest(target_user_id="00000000-0000-4000-8000-000000000002"), user,
        ))
    assert error.value.status_code == 403


def test_disabled_user_cannot_start_agent_runtime():
    user = SimpleNamespace(id="00000000-0000-4000-8000-000000000001", app_metadata={"role": "user", "status": "disabled"})
    with pytest.raises(HTTPException) as error:
        asyncio.run(auth.create_opencode_ticket(None, user))
    assert error.value.status_code == 403


def test_admin_can_target_another_agent_identity(monkeypatch):
    admin = SimpleNamespace(id="00000000-0000-4000-8000-000000000001", app_metadata={"role": "admin"})
    monkeypatch.setattr(auth.supabase.auth.admin, "get_user_by_id", lambda user_id: SimpleNamespace(user=SimpleNamespace(id=user_id)))
    monkeypatch.setattr(auth.opencode_sso_service, "issue_ticket", lambda user_id, target: f"{user_id}:{target}")
    result = asyncio.run(auth.create_opencode_ticket(
        auth.AgentTicketRequest(target_user_id="00000000-0000-4000-8000-000000000002"), admin,
    ))
    assert "00000000-0000-4000-8000-000000000002" in result["redirect_url"]


def test_admin_user_directory_exposes_no_credentials(monkeypatch):
    account = SimpleNamespace(
        id="user-1", email="user@example.com", user_metadata={"name": "User"},
        app_metadata={"role": "user"}, created_at="2026-01-01", last_sign_in_at=None,
    )
    monkeypatch.setattr(auth.supabase.auth.admin, "list_users", lambda page, per_page: [account])
    result = asyncio.run(auth.auth_users())
    assert result["users"] == [{
        "id": "user-1", "email": "user@example.com", "name": "User", "role": "user", "status": "active",
        "agent_space_status": "首次进入自动创建",
        "created_at": "2026-01-01", "last_sign_in_at": None,
    }]


def test_admin_can_disable_member_and_revoke_agent_sessions(monkeypatch):
    member = SimpleNamespace(id="00000000-0000-4000-8000-000000000002", app_metadata={"role": "user"}, user_metadata={}, email="member@example.com", created_at="2026-01-01", last_sign_in_at=None)
    admin = SimpleNamespace(id="00000000-0000-4000-8000-000000000001", app_metadata={"role": "admin"})
    monkeypatch.setattr(auth.supabase.auth.admin, "get_user_by_id", lambda _: SimpleNamespace(user=member))
    monkeypatch.setattr(auth.supabase.auth.admin, "update_user_by_id", lambda _, values: SimpleNamespace(user=SimpleNamespace(**{**member.__dict__, "app_metadata": values["app_metadata"]})))
    revoked = []
    monkeypatch.setattr(auth.opencode_sso_service, "revoke_member_gateway_sessions", revoked.append)
    result = asyncio.run(auth.update_user(member.id, auth.MemberUpdateRequest(disabled=True), admin))
    assert result["user"]["status"] == "disabled"
    assert revoked == [str(member.id)]


def test_admin_invitation_assigns_member_role(monkeypatch):
    account = SimpleNamespace(id="00000000-0000-4000-8000-000000000002", app_metadata={}, user_metadata={"name": "Member"}, email="member@example.com", created_at="2026-01-01", last_sign_in_at=None)
    monkeypatch.setattr(auth.supabase.auth.admin, "invite_user_by_email", lambda *_: SimpleNamespace(user=account))
    monkeypatch.setattr(auth.supabase.auth.admin, "update_user_by_id", lambda _, values: SimpleNamespace(user=SimpleNamespace(**{**account.__dict__, "app_metadata": values["app_metadata"]})))
    result = asyncio.run(auth.invite_user(auth.InviteRequest(email="member@example.com", name="Member", role="admin")))
    assert result["message"] == "邀请已发送"
    assert result["user"]["role"] == "admin"
