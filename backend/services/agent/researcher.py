from deep_searcher_integration import retrieve_context
from services.bidding_service import get_bidding_opportunities
from services.demand_service import get_demand_signals


class Researcher:
    async def research(self, steps: list[dict]) -> list[dict]:
        results = []
        for step in steps:
            data = {"step_id": step["step_id"], "dimension": step["dimension"], "sources": {}}
            try:
                ctx = retrieve_context(step["key_question"], top_k=5)
                data["sources"]["vector_db"] = {"items": [{"text": r["text"][:200], "score": r["score"], "collection": r["collection"]} for r in ctx[:3]], "count": len(ctx)}
            except Exception as e:
                data["sources"]["vector_db"] = {"error": str(e), "count": 0}

            source_type = step.get("data_source", "")
            if "招标" in source_type:
                try:
                    bids, total = get_bidding_opportunities(days=30)
                    data["sources"]["bidding"] = {"items": [{"title": b["title"], "industry": b["industry"], "budget": b.get("budget", "")} for b in bids[:5]], "total": total}
                except Exception as e:
                    data["sources"]["bidding"] = {"error": str(e)}
            if "政策" in source_type or "需求" in source_type:
                try:
                    signals = get_demand_signals(days=30)
                    data["sources"]["demand"] = {"items": [{"title": s["title"], "industry": s["industry"], "tags": s.get("demand_tags", "")} for s in signals[:5]], "total": len(signals)}
                except Exception as e:
                    data["sources"]["demand"] = {"error": str(e)}
            results.append(data)
        return results
