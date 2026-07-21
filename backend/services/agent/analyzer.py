from services.ai_service import chat_complete, extract_json
import json

ANALYZER_PROMPT = """你是一位资深商业分析师。请基于以下研究数据，对"{dimension}"维度进行深度分析。

研究数据：
{research_data}

分析要求：
1. 基于数据做推理，不要编造
2. 指出数据支撑的结论和不确定性
3. 有数据的地方标注数据来源
4. 给出具体的商业洞察，不是泛泛而谈

输出 JSON：
{{
  "dimension": "{dimension}",
  "key_findings": [{{"finding": "具体发现", "evidence": "支撑证据", "confidence": 0.85, "source": "数据来源"}}],
  "trends": ["趋势1", "趋势2"],
  "risks": ["风险1", "风险2"],
  "opportunities": ["机会1", "机会2"],
  "uncertainty_notes": ["需要进一步验证的点"]
}}
"""


class Analyzer:
    async def analyze(self, planning: dict, research_data: list[dict]) -> dict:
        dimension_analyses = []
        for step, data in zip(planning.get("research_steps", []), research_data):
            dimension = step["dimension"]
            research_str = json.dumps(data.get("sources", {}), ensure_ascii=False, indent=2)
            prompt = ANALYZER_PROMPT.format(dimension=dimension, research_data=research_str[:3000])
            try:
                result = chat_complete(system_prompt="你输出结构化 JSON。", user_prompt=prompt, temperature=0.5, max_tokens=2000)
                analysis = extract_json(result)
                if analysis:
                    analysis["step_id"] = step["step_id"]
                    dimension_analyses.append(analysis)
                else:
                    dimension_analyses.append({"dimension": dimension, "key_findings": [], "error": "AI 分析返回非 JSON"})
            except Exception as e:
                dimension_analyses.append({"dimension": dimension, "key_findings": [], "error": str(e)})
        return {"dimensions": dimension_analyses, "total_dimensions": len(dimension_analyses)}
