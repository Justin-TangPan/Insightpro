import os
from datetime import datetime
from services.agent.planner import Planner
from services.agent.researcher import Researcher
from services.agent.analyzer import Analyzer
from services.agent.verifier import Verifier
from services.agent.reporter import Reporter
from . import AgentContext, AgentState


class AnalysisAgent:
    def __init__(self):
        self.planner = Planner()
        self.researcher = Researcher()
        self.analyzer = Analyzer()
        self.verifier = Verifier()
        self.reporter = Reporter()

    async def run(self, query: str) -> dict:
        ctx = AgentContext(task_id=f"ana_{os.urandom(4).hex()}", query=query)
        try:
            ctx.state = AgentState.PLANNING
            ctx.plan = await self.planner.plan(query)

            ctx.state = AgentState.RESEARCHING
            steps = ctx.plan.get("research_steps", [])
            ctx.research_data = await self.researcher.research(steps)

            ctx.state = AgentState.ANALYZING
            ctx.analysis = await self.analyzer.analyze(ctx.plan, ctx.research_data)

            ctx.state = AgentState.VERIFYING
            ctx.verification = await self.verifier.verify(ctx.analysis, ctx.research_data)
            ctx.confidence = ctx.verification.get("overall_confidence", 0.0)

            ctx.state = AgentState.REPORTING
            ctx.report = await self.reporter.generate(query, ctx.plan, ctx.analysis, ctx.verification)

            ctx.state = AgentState.COMPLETED
            ctx.completed_at = datetime.now().isoformat()
            return {"task_id": ctx.task_id, "state": ctx.state.value, "query": ctx.query, "plan": ctx.plan, "analysis": ctx.analysis, "verification": ctx.verification, "report": ctx.report, "confidence": ctx.confidence, "duration": {"started_at": ctx.created_at, "completed_at": ctx.completed_at}}
        except Exception as e:
            ctx.state = AgentState.FAILED
            ctx.errors.append(str(e))
            return {"task_id": ctx.task_id, "state": AgentState.FAILED.value, "query": ctx.query, "error": str(e), "partial_results": {"plan": ctx.plan, "analysis": ctx.analysis, "verification": ctx.verification}}
