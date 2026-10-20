"""Insight tasks model."""
from sqlalchemy import Column, Text, TIMESTAMP, Index
from sqlalchemy.dialects.postgresql import JSONB
from models.base import Base


class InsightTask(Base):
    __tablename__ = "insight_tasks"
    __table_args__ = (
        Index("idx_task_status", "status"),
        Index("idx_task_created", "created_at"),
    )

    id = Column(Text, primary_key=True)
    title = Column(Text, nullable=False)
    status = Column(Text, nullable=False, server_default="'pending'")
    data_sources = Column(JSONB)
    result = Column(JSONB)
    error = Column(Text)
    created_at = Column(TIMESTAMP, server_default="NOW()")
    updated_at = Column(TIMESTAMP, server_default="NOW()")
