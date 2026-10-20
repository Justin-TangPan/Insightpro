"""Requirements, Solutions, and their junction model."""
from sqlalchemy import Column, BigInteger, Text, ForeignKey, DateTime, Index
from models.base import Base


class Requirement(Base):
    __tablename__ = "requirements"
    __table_args__ = (
        Index("idx_requirements_user_status", "user_id", "status", "updated_at"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Text, nullable=False)  # UUID stored as Text for simplicity
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False, server_default="''")
    status = Column(Text, nullable=False, server_default="'draft'")
    priority = Column(Text, nullable=False, server_default="'medium'")
    source_type = Column(Text, nullable=False, server_default="'manual'")
    source_id = Column(Text)
    source_url = Column(Text)
    absorbed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")


class Solution(Base):
    __tablename__ = "solutions"
    __table_args__ = (
        Index("idx_solutions_user_status", "user_id", "status", "updated_at"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=False, server_default="''")
    category = Column(Text, nullable=False, server_default="'未分类'")
    status = Column(Text, nullable=False, server_default="'draft'")
    version = Column(Text, nullable=False, server_default="'v0.1.0'")
    reference_url = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")


class RequirementSolution(Base):
    __tablename__ = "requirement_solutions"
    __table_args__ = (
        Index("idx_requirement_solutions_solution", "solution_id"),
    )

    requirement_id = Column(
        BigInteger, ForeignKey("requirements.id", ondelete="CASCADE"),
        nullable=False, primary_key=True,
    )
    solution_id = Column(
        BigInteger, ForeignKey("solutions.id", ondelete="CASCADE"),
        nullable=False, primary_key=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")
