"""Agent sessions, actions, artifacts, and SSO models."""
from sqlalchemy import Column, Text, BigInteger, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from models.base import Base


class AgentSession(Base):
    __tablename__ = "agent_sessions"
    __table_args__ = (
        Index("idx_agent_sessions_user_updated", "user_id", "updated_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    context_type = Column(Text, nullable=False)
    context_id = Column(Text, nullable=False)
    context_title = Column(Text, nullable=False)
    context_snapshot = Column(JSONB, nullable=False)
    title = Column(Text, nullable=False, server_default="'新对话'")
    conversation = Column(JSONB, nullable=False, server_default="'[]'::jsonb")
    task_key = Column(Text, nullable=False, server_default="''")
    task_title = Column(Text, nullable=False, server_default="''")
    task_status = Column(Text, nullable=False, server_default="'ready'")
    default_prompt = Column(Text, nullable=False, server_default="''")
    hermes_session_id = Column(Text, nullable=False, server_default="''")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")


class AgentAction(Base):
    __tablename__ = "agent_actions"
    __table_args__ = (
        Index("idx_agent_actions_user_status", "user_id", "status", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True)
    session_id = Column(
        UUID(as_uuid=True), ForeignKey("agent_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False)
    status = Column(Text, nullable=False, server_default="'proposed'")
    result = Column(JSONB)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")
    confirmed_at = Column(DateTime(timezone=True))


class AgentArtifact(Base):
    __tablename__ = "agent_artifacts"
    __table_args__ = (
        Index("idx_agent_artifacts_user_updated", "user_id", "updated_at"),
        Index("idx_agent_artifacts_knowledge", "knowledge_status", "updated_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    session_id = Column(
        UUID(as_uuid=True), ForeignKey("agent_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_key = Column(Text, nullable=False, server_default="''")
    type = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    filename = Column(Text, nullable=False, server_default="''")
    mime_type = Column(Text, nullable=False, server_default="'text/markdown'")
    source_type = Column(Text)
    source_id = Column(Text)
    requirement_id = Column(BigInteger)
    solution_id = Column(BigInteger)
    knowledge_status = Column(Text, nullable=False, server_default="'private'")
    knowledge_path = Column(Text)
    reviewed_by = Column(UUID(as_uuid=True))
    reviewed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")


class AgentSsoTicket(Base):
    __tablename__ = "agent_sso_tickets"
    __table_args__ = (
        Index("idx_agent_sso_tickets_expiry", "expires_at"),
    )

    token_hash = Column(Text, primary_key=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    target_user_id = Column(UUID(as_uuid=True))
    agent_session_id = Column(UUID(as_uuid=True))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")


class AgentSsoSession(Base):
    __tablename__ = "agent_sso_sessions"
    __table_args__ = (
        Index("idx_agent_sso_sessions_user", "user_id", "expires_at"),
        Index("idx_agent_sso_sessions_agent_user", "agent_user_id", "expires_at"),
    )

    token_hash = Column(Text, primary_key=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    agent_user_id = Column(UUID(as_uuid=True), nullable=False)
    auth_role = Column(Text, nullable=False, server_default="'user'")
    agent_role = Column(Text, nullable=False, server_default="'user'")
    display_name = Column(Text, nullable=False, server_default="''")
    agent_session_id = Column(UUID(as_uuid=True))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")


class AgentAuditEvent(Base):
    __tablename__ = "agent_audit_events"
    __table_args__ = (
        Index("idx_agent_audit_events_created", "created_at"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    actor_user_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(Text, nullable=False)
    target_user_id = Column(UUID(as_uuid=True))
    detail = Column(Text, nullable=False, server_default="''")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")
