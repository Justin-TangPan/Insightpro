from services.ai_service import chat_complete, extract_json
import json

VERIFIER_PROMPT = """你是一位严谨的审计分析师。请对以下商业分析结果进行严格验证。

分析结果：
{analysis}

参考数据：
{research_data}

验证要求：
1. 每个结论是否有数据支撑？
2. 数据之间有无矛盾？
3. 分析逻辑是否自洽？
4. 是否存在未经验证的假设？
5. AI 是否有编造数据的嫌疑？

输出 JSON：
{{
  "overall_confidence": 0.85,
  "verified_claims": [{{"claim": "结论文本", "supported": true, "source": "数据来源", "notes": ""}}],
  "unverified_claims": [{{"claim": "无法验证的结论", "reason": "原因", "severity": "高/中/低"}}],
  "contradictions": [{{"description": "矛盾描述", "items": ["矛盾的结论1", "矛盾的结论2"]}}],
  "uncertainties": ["不确定性1", "不确定性2"],
  "data_gaps": ["缺少的数据"],
  "overall_assessment": "一句话总体评价"
}}
"""


class Verifier:
    async def verify(self, analysis: dict, research_data: list[dict]) -> dict:
        analysis_str = json.dumps(analysis, ensure_ascii=False, indent=2)[:4000]
        research_str = json.dumps(research_data, ensure_ascii=False, indent=2)[:4000]
        prompt = VERIFIER_PROMPT.format(analysis=analysis_str, research_data=research_str)
        try:
            result = chat_complete(system_prompt="你输出结构化 JSON 验证报告。", user_prompt=prompt, temperature=0.3, max_tokens=2000)
            verification = extract_json(result)
            if verification:
                return verification
        except Exception:
            pass
        return {"overall_confidence": 0.5, "verified_claims": [], "unverified_claims": [{"claim": "验证失败", "reason": "AI 验证模块异常", "severity": "高"}], "contradictions": [], "uncertainties": ["验证模块异常"], "data_gaps": [], "overall_assessment": "验证过程异常，建议人工复核"}
