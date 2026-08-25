from deep_searcher_integration import retrieve_context


class Researcher:
    async def research(self, steps: list[dict]) -> list[dict]:
        results = []
        for step in steps:
            data = {"step_id": step["step_id"], "dimension": step["dimension"], "sources": {}}
            try:
                context = retrieve_context(step["key_question"], top_k=5)
                data["sources"]["vector_db"] = {
                    "items": [{"text": item["text"][:200], "score": item["score"], "collection": item["collection"]} for item in context[:3]],
                    "count": len(context),
                }
            except Exception as error:
                data["sources"]["vector_db"] = {"error": str(error), "count": 0}
            results.append(data)
        return results
