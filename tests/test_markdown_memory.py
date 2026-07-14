from scripts.markdown_memory import reindex_markdown
from scripts.unified_memory import UnifiedMemoryStore


def write_page(root, name="decision.md", memory_id="mem_1", summary="统一结论"):
    page = root / name
    page.write_text(f"""---
id: {memory_id}
type: decision
status: active
confidence: high
importance: 0.88
clients:
  - codex
tags:
  - memory
  - decision
---

{summary}

这是证据说明。
""")
    return page


def test_reindex_is_idempotent_and_removes_deleted_pages(tmp_path):
    root = tmp_path / "vault"
    root.mkdir()
    page = write_page(root)
    store = UnifiedMemoryStore(tmp_path / "memory.db")

    first = reindex_markdown(root, store)
    second = reindex_markdown(root, store)
    assert first.indexed == 1
    assert second.indexed == 0
    assert store.count_managed() == 1

    page.unlink()
    result = reindex_markdown(root, store)
    assert result.removed == 1
    assert store.count_managed() == 0
    store.close()


def test_reindex_skips_unmanaged_markdown(tmp_path):
    root = tmp_path / "vault"
    root.mkdir()
    (root / "ordinary.md").write_text("# 普通笔记")
    store = UnifiedMemoryStore(tmp_path / "memory.db")

    result = reindex_markdown(root, store)

    assert result.scanned == 1
    assert result.skipped == 1
    assert store.count_managed() == 0
    store.close()


def test_reindex_restores_supersede_relationships_from_markdown(tmp_path):
    root = tmp_path / "vault"
    root.mkdir()
    (root / "current.md").write_text("""---
id: mem_current
type: project_state
status: active
confidence: high
importance: 0.9
supersedes:
  - mem_old
superseded_by: null
tags:
  - memory
  - project_state
---

当前结论
""")
    store = UnifiedMemoryStore(tmp_path / "memory.db")

    reindex_markdown(root, store)

    row = store.connection.execute(
        "SELECT supersedes, superseded_by FROM memory_index WHERE memory_id='mem_current'"
    ).fetchone()
    assert tuple(row) == ('["mem_old"]', None)
    store.close()
