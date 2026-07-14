import sqlite3

from scripts.unified_memory import UnifiedMemoryStore


def create_legacy_db(path, content="保留我"):
    conn = sqlite3.connect(str(path))
    conn.execute("""
        CREATE TABLE memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            type TEXT DEFAULT 'fact',
            tags TEXT DEFAULT '',
            weight REAL DEFAULT 0.5,
            short_term INTEGER DEFAULT 1,
            long_term INTEGER DEFAULT 0,
            created REAL,
            updated REAL,
            last_accessed REAL
        )
    """)
    conn.execute(
        "INSERT INTO memory (content, type, weight, created, updated) VALUES (?, 'fact', 0.7, 1, 2)",
        (content,),
    )
    conn.commit()
    conn.close()
    return path


def test_migration_preserves_legacy_rows_and_is_idempotent(tmp_path):
    db = create_legacy_db(tmp_path / "memory.db")
    store = UnifiedMemoryStore(db)
    store.migrate()
    store.migrate()

    row = store.connection.execute(
        "SELECT summary, legacy_id, source_kind FROM memory_index"
    ).fetchone()
    count = store.connection.execute("SELECT COUNT(*) FROM memory_index").fetchone()[0]

    assert tuple(row) == ("保留我", 1, "legacy_cache")
    assert count == 1
    store.close()


def test_schema_supports_source_refs_and_memory_relationships(tmp_path):
    store = UnifiedMemoryStore(tmp_path / "memory.db")
    columns = {
        row[1] for row in store.connection.execute("PRAGMA table_info(memory_index)").fetchall()
    }
    tables = {
        row[0] for row in store.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    version = store.connection.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]

    assert "source_refs" in columns
    assert {"supersedes", "superseded_by"}.issubset(columns)
    assert "memory_links" in tables
    assert "memory_feedback" in tables
    recall_columns = {
        row[1] for row in store.connection.execute(
            "PRAGMA table_info(memory_recall_events)"
        ).fetchall()
    }

    assert "recall_count" in columns
    assert "memory_recall_events" in tables
    assert {
        "query_hash", "client", "session_id", "result_count", "created_at"
    }.issubset(recall_columns)
    assert version == 5
    store.close()
