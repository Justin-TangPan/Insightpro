"""Runtime settings and AI usage record models."""
from sqlalchemy import Column, BigInteger, Text, Integer, DateTime, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID
from models.base import Base


class RuntimeSetting(Base):
    __tablename__ = "runtime_settings"

    key = Column(Text, primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")


class AiUsageRecord(Base):
    __tablename__ = "ai_usage_records"
    __table_args__ = (
        Index("idx_ai_usage_records_created", "created_at"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True))
    model = Column(Text, nullable=False)
    feature = Column(Text, nullable=False)
    input_tokens = Column(Integer, nullable=False, server_default="0")
    output_tokens = Column(Integer, nullable=False, server_default="0")
    usage_reported = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")
