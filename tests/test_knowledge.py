from app.knowledge import KnowledgeStore


def test_ingest_and_search_chinese_text(tmp_path):
    root = tmp_path / "knowledge"
    root.mkdir()
    (root / "handbook.md").write_text(
        "# 工具调用规范\n\n工具调用失败时需要设置超时并记录审计事件。",
        encoding="utf-8",
    )

    store = KnowledgeStore(root=root, db_path=tmp_path / "knowledge.db")
    summary = store.ingest()

    assert summary["documents"] == 1
    assert summary["chunks"] == 1

    results = store.search("工具调用失败", max_results=3)
    assert results
    assert results[0]["source"] == "handbook.md"
    assert "审计事件" in results[0]["content"]


def test_empty_query_returns_no_results(tmp_path):
    store = KnowledgeStore(root=tmp_path / "knowledge", db_path=tmp_path / "knowledge.db")

    assert store.search("", max_results=3) == []
