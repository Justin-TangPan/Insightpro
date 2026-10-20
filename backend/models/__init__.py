"""SQLAlchemy ORM models for InsightWeb.

Import all model modules here so Alembic autogenerate can detect them.
Each module defines a portion of the schema; `Base` is shared.
"""
from models.base import Base
from models.trending import GithubTrending, BaiduHotsearch, TrendingBusinessEval
from models.competitors import CompetitorNews, CloudVendorNews
from models.solutions import AliyunSolution
from models.workbench import Requirement, Solution, RequirementSolution
from models.agent import (
    AgentSession, AgentAction, AgentArtifact,
    AgentSsoTicket, AgentSsoSession, AgentAuditEvent,
)
from models.email import EmailSubscriber
from models.tasks import InsightTask
from models.config import RuntimeSetting, AiUsageRecord
from models.knowledge import KnowledgeChunk

__all__ = [
    "Base",
    "GithubTrending", "BaiduHotsearch", "TrendingBusinessEval",
    "CompetitorNews", "CloudVendorNews",
    "AliyunSolution",
    "Requirement", "Solution", "RequirementSolution",
    "AgentSession", "AgentAction", "AgentArtifact",
    "AgentSsoTicket", "AgentSsoSession", "AgentAuditEvent",
    "EmailSubscriber",
    "InsightTask",
    "RuntimeSetting", "AiUsageRecord",
    "KnowledgeChunk",
]
