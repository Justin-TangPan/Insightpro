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
    assert "期望输出：与当前任务相匹配的结论、依据、风险、验证要点和下一步" in system
