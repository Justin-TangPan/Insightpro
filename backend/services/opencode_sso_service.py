"""Short-lived, one-time SSO tickets and gateway sessions for OpenCode."""
from __future__ import annotations

import hashlib
import secrets

from repositories import opencode_sso_repository as repository

TICKET_TTL_SECONDS = 60
SESSION_TTL_SECONDS = 300


def issue_ticket(user_id: str) -> str:
    ticket = secrets.token_urlsafe(32)
    repository.create_ticket(hashlib.sha256(ticket.encode()).hexdigest(), user_id, TICKET_TTL_SECONDS)
    return ticket


def consume_ticket(ticket: str) -> str | None:
    if not ticket or len(ticket) > 256:
        return None
    return repository.consume_ticket(hashlib.sha256(ticket.encode()).hexdigest())


def create_gateway_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    repository.create_session(hashlib.sha256(token.encode()).hexdigest(), user_id, SESSION_TTL_SECONDS)
    return token


def verify_gateway_session(token: str) -> str | None:
    if not token or len(token) > 256:
        return None
    return repository.get_session_user(hashlib.sha256(token.encode()).hexdigest())


def revoke_gateway_sessions(user_id: str) -> None:
    repository.revoke_user_sessions(user_id)
