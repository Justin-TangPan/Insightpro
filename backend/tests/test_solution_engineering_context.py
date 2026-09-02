from services import insight_agent_runtime


def test_enabled_agent_plugin_is_loaded(monkeypatch, tmp_path):
    plugin = tmp_path / "sac"
    plugin.mkdir()
    (plugin / "manifest.json").write_text('{"enabled": true, "name": "SAC", "knowledge": "AGENT.md"}', encoding="utf-8")
    (plugin / "AGENT.md").write_text("SAC workflow", encoding="utf-8")
    monkeypatch.setattr(insight_agent_runtime, "PLUGINS_ROOT", tmp_path)
    assert "Plugin: SAC" in insight_agent_runtime.plugin_knowledge()
    assert "SAC workflow" in insight_agent_runtime.plugin_knowledge()


def test_solution_engineering_context_loads_public_rules_and_dynamic_context():
    session = {
        "task_key": "solution_analysis", "task_title": "分析解决方案",
        "default_prompt": "分析当前方案。",
        "context_snapshot": {"title": "企业 AI Gateway", "content": "方案描述"},
        "conversation": [],
    }
    system = insight_agent_runtime.messages_for(session, "请开始分析。")[0]["content"]
    assert "Solution Architect" in system
    assert "Terraform 执行成功不等于 Solution 成功" in system
    assert "Discover" in system and "Validate" in system
    assert "企业 AI Gateway" in system
    assert "当前工作阶段：Understand" in system
    assert "本轮用户消息优先于预置任务" in system


def test_prebuilt_task_is_only_a_suggestion_for_a_different_user_question():
    session = {
        "task_key": "technology_research", "task_title": "技术深度调研",
        "default_prompt": "评估成熟度和 PoC。",
        "context_snapshot": {"title": "项目 A"}, "conversation": [],
    }
    system = insight_agent_runtime.messages_for(session, "解释 OAuth 的 PKCE")[0]["content"]
    assert "仅在用户点击“开始任务”或明确要求继续时执行" in system
    assert "用户提出其他问题时，只回答该问题" in system


def test_solution_context_keeps_role_practice_and_expected_output_together():
    session = {
        "task_key": "solution_architecture", "task_title": "技术架构分析",
        "default_prompt": "输出架构、风险、验证要点和下一步。",
        "context_snapshot": {"source_type": "solution", "title": "企业 AI Gateway"},
    }
    system = insight_agent_runtime.messages_for(session, "请分析当前方案。 ")[0]["content"]
    assert "当前用户角色：Solution Architect" in system
    assert "当前工作阶段：Design" in system
    assert "企业 AI Gateway" in system
    assert "资源创建 → 应用安装 → 服务健康" in system
    assert "本轮用户消息优先于预置任务" in system
