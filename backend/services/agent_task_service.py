"""Small, server-owned catalog for Insight-Agent business actions."""
from __future__ import annotations

from fastapi import HTTPException


TASKS = {
    "technology_research": {
        "title": "Deep Tech Research", "status": "ready",
        "prompt": "Based on the current tech project, evaluate the problem it solves, core capabilities, maturity, applicable scenarios, adoption risks, and PoC validation focus, and provide clear next-step recommendations.",
    },
    "technology_value": {
        "title": "Analyze Tech Value", "status": "ready",
        "prompt": "Analyze the business value, technical maturity, implementation dependencies, and risks of the current tech project, and explain whether it is worth proceeding to the next validation step.",
    },
    "solution_analysis": {
        "title": "Analyze Solution", "status": "ready",
        "prompt": "Analyze the solution's value, applicable scenarios, and architecture. Key verification points: whether open-source projects are used, project names and purposes, and whether open-source evidence is explicit; list each cloud service resource used and its role. Base analysis only on current official materials; when uncertain, explicitly write 'not confirmed' instead of guessing based on common knowledge. Finally, state limitations, reusable points, and next-step recommendations.",
    },
    "solution_architecture": {
        "title": "Tech Architecture Analysis", "status": "ready",
        "prompt": "Decompose the current solution's technical architecture, key components, dependencies, integration boundaries, and major risks, and provide reusable architecture recommendations.",
    },
    "solution_practice": {
        "title": "Create Solution Practice", "status": "ready",
        "prompt": "Use the enabled 'Huawei Cloud Solution Practice' plugin to organize the current solution practice into reviewable, verifiable, and deliverable form following the sac-project, sac-architecture, sac-implementation, sac-quality, sac-documentation sequence. First state facts, assumptions, and items to confirm; when topology, networking, data, availability, or external dependencies are involved, form an Architecture Contract first and wait for human confirmation. Do not claim that unverified deployments are complete.",
    },
    "solution_design": {
        "title": "Solution Design", "status": "ready",
        "prompt": "Based on current requirements and existing solutions, produce an executable Solution design: objectives, architecture, key components, implementation phases, risks, and acceptance criteria.",
    },
    "requirement_analysis": {
        "title": "Analyze Requirement", "status": "ready",
        "prompt": "Analyze the current Requirement's objectives, scope, constraints, missing information, risks, and acceptance criteria, and provide improvement suggestions.",
    },
    "requirement_refine": {
        "title": "Refine Requirement", "status": "waiting_confirmation",
        "prompt": "Refine the current Requirement into an executable draft, filling in business objectives, scope, non-functional requirements, boundaries, acceptance criteria, and risks; provide suggestions first, and wait for confirmation before writing to the Draft.",
    },
    "poc_plan": {
        "title": "PoC Planning", "status": "ready",
        "prompt": "Create a PoC plan for the current solution: validation hypotheses, environment and dependencies, execution steps, success criteria, risks, and exit conditions.",
    },
    "validation": {
        "title": "Solution Validation", "status": "ready",
        "prompt": "Based on the current solution and existing materials, list the validation scope, evidence requirements, test items, pass criteria, risks, and follow-up action recommendations.",
    },
    "implementation": {
        "title": "Start Implementation", "status": "ready",
        "prompt": "First provide an implementation plan, file change scope, dependencies, testing strategy, and risks; when code or work files need to be edited, continue execution after entering the Workspace.",
    },
    "materials": {
        "title": "Generate Tech Materials", "status": "ready",
        "prompt": "Based on the current object and existing conclusions, generate well-structured, reviewable technical materials, and indicate content that still requires human confirmation.",
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
        raise HTTPException(status_code=422, detail="Current business object does not support this AI Action")
    task = TASKS[task_key]
    if context_type == "solution":
        task = {**task, "prompt": "Use the saved background information, associated background materials, and source links of the current solution practice as the sole work baseline. First distinguish facts, assumptions, gaps, and items to confirm; do not regenerate or overwrite background information unless explicitly requested by the user.\n\n" + task["prompt"]}
    return task_key, task


def task(task_key: str) -> dict:
    item = TASKS.get(task_key)
    if not item:
        raise HTTPException(status_code=422, detail="Unsupported Agent Task")
    return item
