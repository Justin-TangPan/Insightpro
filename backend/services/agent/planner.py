from services.ai_service import chat_complete, extract_json

PLANNER_PROMPT = """你是一位资深商业分析师。用户的商业分析问题是：

{query}

请分析这个问题，输出结构化的分析规划 JSON：

{{
  "analysis_type": "技术分析 / 方案分析 / 竞品分析 / 综合",
  "title": "分析报告标题",
  "research_steps": [
    {{
      "step_id": "step_1",
      "dimension": "分析维度",
      "data_needed": "需要什么数据",
      "data_source": "数据来源类型（技术热点/解决方案/友商动态）",
      "key_question": "这个维度要回答的核心问题",
      "reason": "为什么需要这个分析"
    }}
  ],
  "expected_outline": ["章节1", "章节2", "章节3"],
  "complexity": "简单/中等/深度",
  "estimated_steps": 3
}}

要求：
1. 分析维度 3-6 个
2. data_source 必须是平台已有的数据源
3. 每个 step 的 key_question 要具体可回答
"""


class Planner:
    async def plan(self, query: str) -> dict:
        prompt = PLANNER_PROMPT.format(query=query)
        result = chat_complete(system_prompt="你输出结构化 JSON 规划。", user_prompt=prompt, temperature=0.3, max_tokens=2000)
        plan = extract_json(result)
        if not plan or "research_steps" not in plan:
            plan = {
                "analysis_type": "综合",
                "title": f"{query[:30]}...",
                "research_steps": [
                    {"step_id": "step_1", "dimension": "技术路径", "data_needed": "技术热点和项目能力", "data_source": "技术热点", "key_question": f"{query}有哪些可行技术路径", "reason": "明确实现方式和成熟度"},
                    {"step_id": "step_2", "dimension": "方案能力", "data_needed": "解决方案目录和变化", "data_source": "解决方案", "key_question": f"{query}有哪些现成方案", "reason": "评估复用与集成成本"},
                    {"step_id": "step_3", "dimension": "友商对比", "data_needed": "云厂商产品动态", "data_source": "友商动态", "key_question": f"{query}的厂商能力差异", "reason": "辅助技术选型"},
                ],
                "expected_outline": ["技术路径", "方案能力", "友商对比", "实施建议"],
                "complexity": "中等",
                "estimated_steps": 3,
            }
        return plan
