from services import knowledge_service


def test_rag_chunks_and_marks_retrieved_content_as_untrusted(monkeypatch):
    text = "甲" * 2500
    chunks = knowledge_service.chunk_text(text)
    assert len(chunks) == 3
    assert chunks[0][-150:] == chunks[1][:150]

    monkeypatch.setattr(knowledge_service, "search", lambda *_: [{"title": "项目分析", "source_type": "github_project", "source_url": "https://example.com", "content": "服务端项目"}])
    prompt = knowledge_service.augment_message("user-id", "是否值得部署？")
    assert "untrusted reference material" in prompt
    assert "[1] 项目分析" in prompt
