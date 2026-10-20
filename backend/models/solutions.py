"""Aliyun cloud solutions model."""
from sqlalchemy import Column, Integer, Text, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from models.base import Base


class AliyunSolution(Base):
    __tablename__ = "aliyun_solutions"
    __table_args__ = (
        Index("idx_aliyun_solutions_seen", "last_seen_date"),
        Index("idx_aliyun_solutions_changed", "last_changed_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=False, unique=True)
    category = Column(Text, nullable=False)
    source_description = Column(Text)
    summary = Column(Text, nullable=False)
    content_hash = Column(Text, nullable=False)
    first_seen_date = Column(Text, nullable=False)
    last_seen_date = Column(Text, nullable=False)
    last_changed_date = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="TRUE")
    is_baseline = Column(Boolean, nullable=False, server_default="FALSE")
    vendor = Column(Text, nullable=False, server_default="'阿里云'")
    content_snapshot = Column(JSONB)
    change_summary = Column(Text, nullable=False, server_default="''")
    menu_order = Column(Integer, nullable=False, server_default="0")
    removed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default="NOW()")
    updated_at = Column(DateTime(timezone=True), server_default="NOW()")
