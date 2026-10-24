from routers import agent


def test_knowledge_answer_uses_only_retrieved_sources(monkeypatch):
    captured = {}

    def fake_complete(**kwargs):
        captured.update(kwargs)
        return "项目适合私有化部署。[1]"

    monkeypatch.setattr(agent.ai_service, "chat_complete", fake_complete)
    answer = agent._answer_from_knowledge("适合私有化吗？", [{"role": "user", "content": "此前问题"}], [
        {"title": "项目 A", "content": "支持私有化部署", "source_type": "github_project"},
    ])
    assert answer.endswith("[1]")
    assert "[1] 项目 A" in captured["messages"][0]["content"]
    assert captured["messages"][-1] == {"role": "user", "content": "适合私有化吗？"}


def test_knowledge_answer_without_sources_does_not_call_model(monkeypatch):
    monkeypatch.setattr(agent.ai_service, "chat_complete", lambda **_: 1 / 0)
    assert "没有找到相关资料" in agent._answer_from_knowledge("问题", [], [])
