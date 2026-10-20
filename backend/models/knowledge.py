"""Knowledge chunks model with pgvector embedding."""
from sqlalchemy import Column, BigInteger, Integer, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from models.base import Base


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        Index("idx_knowledge_access", "visibility", "owner_user_id", "updated_at"),
        # Note: the embedding column uses extensions.vector type which is not
        # natively supported by SQLAlchemy. Alembic will handle the CREATE EXTENSION
        # and the vector column via a custom migration step, not autogenerate.
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    source_type = Column(Text, nullable=False)
    source_id = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    owner_user_id = Column(UUID(as_uuid=True))
    visibility = Column(Text, nullable=False)  # 'team' or 'private'
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    source_url = Column(Text)
    metadata_ = Column("metadata", JSONB, nullable=False, server_default="'{}'::jsonb")
    content_hash = Column(Text, nullable=False)
    # embedding column added via custom migration (pgvector type)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")
