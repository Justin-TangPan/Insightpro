"""Small, server-owned catalog for Insight-Agent business actions."""
from __future__ import annotations

from fastapi import HTTPException


TASKS = {
    "technology_research": {
        "title": "技术深度调研", "status": "ready",
        "prompt": "请基于当前技术项目，评估其解决的问题、核心能力、成熟度、适用场景、引入风险和 PoC 验证重点，并给出明确下一步建议。",
    },
    "technology_value": {
        "title": "分析技术价值", "status": "ready",
        "prompt": "请分析当前技术项目的业务价值、技术成熟度、落地依赖和风险，说明是否值得进入下一步验证。",
    },
    "solution_analysis": {
        "title": "分析解决方案", "status": "ready",
        "prompt": "请分析该方案的技术架构、适用场景、核心能力、限制和可借鉴点，并给出下一步建议。",
    },
    "solution_architecture": {
        "title": "技术架构分析", "status": "ready",
        "prompt": "请拆解当前方案的技术架构、关键组件、依赖关系、集成边界和主要风险，给出可复用的架构建议。",
    },
    "solution_practice": {
        "title": "做成解决方案实践", "status": "ready",
        "prompt": "请使用已启用的“华为云解决方案实践”插件，将当前方案实践按 sac-project、sac-architecture、sac-implementation、sac-quality、sac-documentation 的顺序整理为可审阅、可验证、可交付的实践。先给出事实、假设和待确认项；涉及拓扑、网络、数据、可用性或外部依赖时，先形成 Architecture Contract 并等待人工确认。不要声称未验证的部署已完成。",
    },
    "solution_design": {
        "title": "Solution 设计", "status": "ready",
        "prompt": "请根据当前需求和已有方案，形成可执行的 Solution 设计：目标、架构、关键组件、实施阶段、风险和验收要点。",
    },
    "requirement_analysis": {
        "title": "分析需求", "status": "ready",
        "prompt": "请分析当前 Requirement 的目标、范围、约束、遗漏信息、风险和验收标准，并给出完善建议。",
    },
    "requirement_refine": {
        "title": "完善需求", "status": "waiting_confirmation",
        "prompt": "请将当前 Requirement 完善为可执行草稿，补齐业务目标、范围、非功能要求、边界、验收标准和风险；先给出建议，等待确认后再写入 Draft。",
    },
    "poc_plan": {
        "title": "PoC 规划", "status": "ready",
        "prompt": "请为当前方案制定 PoC 计划：验证假设、环境与依赖、执行步骤、成功指标、风险和退出条件。",
    },
    "validation": {
        "title": "方案验证", "status": "ready",
        "prompt": "请依据当前方案与已有材料，列出验证范围、证据需求、测试项、通过标准、风险和后续处置建议。",
    },
    "implementation": {
        "title": "开始实现", "status": "ready",
        "prompt": "请先给出实现计划、文件变更范围、依赖、测试策略和风险；需要编辑代码或工作文件时，进入 Workspace 后继续执行。",
    },
    "materials": {
        "title": "生成技术材料", "status": "ready",
        "prompt": "请基于当前对象和已有结论生成结构清晰、可审阅的技术材料，并说明仍需人工确认的内容。",
    },
}


ACTIONS = {
    "github_project": {"deep_research": "technology_research", "analyze_value": "technology_value"},
    "cloud_solution": {"analyze": "solution_analysis", "architecture": "solution_architecture", "design": "solution_design", "poc": "poc_plan"},
    "requirement": {"analyze": "requirement_analysis", "refine": "requirement_refine", "solution_design": "solution_design"},
    "solution": {"research": "solution_practice", "architecture": "solution_practice", "poc": "poc_plan", "implement": "implementation", "validate": "validation", "materials": "materials"},
}


def resolve(context_type: str, action_key: str) -> tuple[str, dict]:
    task_key = ACTIONS.get(context_type, {}).get(action_key)
    if not task_key:
        raise HTTPException(status_code=422, detail="当前业务对象不支持该 AI Action")
    task = TASKS[task_key]
    if context_type == "solution":
        task = {**task, "prompt": "以当前方案实践中已保存的背景信息、关联背景材料和来源链接为唯一工作基线。先区分事实、假设、缺口和待确认项；不要重新生成或覆盖背景信息，除非用户明确要求。\n\n" + task["prompt"]}
    return task_key, task


def task(task_key: str) -> dict:
    item = TASKS.get(task_key)
    if not item:
        raise HTTPException(status_code=422, detail="不支持的 Agent Task")
    return item
