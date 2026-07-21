from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


class AgentState(str, Enum):
    PLANNING = "planning"
    RESEARCHING = "researching"
    ANALYZING = "analyzing"
    VERIFYING = "verifying"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentContext:
    task_id: str
    query: str
    state: AgentState = AgentState.PLANNING
    plan: Optional[dict] = None
    research_data: list = field(default_factory=list)
    analysis: Optional[dict] = None
    verification: Optional[dict] = None
    report: Optional[dict] = None
    confidence: float = 0.0
    errors: list = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
