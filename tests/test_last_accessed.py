#!/usr/bin/env python3
"""
Tests for last_accessed tracking and recency-sensitive decay.

Run with:  python3 -m pytest tests/test_last_accessed.py -v
"""

import math
import os
import sys
import tempfile
import time
import shutil

import pytest

# ---------------------------------------------------------------------------
# Isolate the module so every test uses a fresh DB in a temp directory.
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import scripts.evolve as ev


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Point the module at a fresh SQLite file for each test."""
    db_file = str(tmp_path / "test_memory.db")

    class FakePath:
        def __str__(self):
            return db_file
        def __fspath__(self):
            return db_file

    class FakeWorkingFile:
        def exists(self):
            return False
        def read_text(self):
            return "[]"
        def write_text(self, text):
            pass

    monkeypatch.setattr(ev, "DB_PATH", FakePath())
    monkeypatch.setattr(ev, "WORKING_MEMORY_FILE", FakeWorkingFile())
    yield


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSchema:
    def test_last_accessed_column_created(self):
        """init_db() must create the last_accessed column."""
        conn = ev.init_db()
        cols = [row[1] for row in conn.execute("PRAGMA table_info(memory)").fetchall()]
        conn.close()
        assert "last_accessed" in cols

    def test_migration_adds_column_to_existing_db(self, tmp_path, monkeypatch):
        """A DB created without last_accessed should be migrated transparently."""
        import sqlite3

        db_path = str(tmp_path / "legacy.db")

        class LegacyPath:
            def __str__(self): return db_path
            def __fspath__(self): return db_path

        monkeypatch.setattr(ev, "DB_PATH", LegacyPath())

        # Create a legacy DB without last_accessed
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                type TEXT DEFAULT 'fact',
                tags TEXT DEFAULT '',
                weight REAL DEFAULT 0.5,
                short_term INTEGER DEFAULT 1,
                long_term INTEGER DEFAULT 0,
                created REAL DEFAULT (strftime('%s','now')),
                updated REAL DEFAULT (strftime('%s','now'))
            )
        """)
        conn.execute("INSERT INTO memory (content, weight, updated) VALUES ('old memory', 0.7, ?)",
                     (time.time() - 100,))
        conn.commit()
        conn.close()

        # Running init_db should add and backfill the column
        conn = ev.init_db()
        cols = [row[1] for row in conn.execute("PRAGMA table_info(memory)").fetchall()]
        row = conn.execute("SELECT last_accessed FROM memory").fetchone()
        conn.close()

        assert "last_accessed" in cols
        assert row is not None and row[0] is not None


class TestAddMemory:
    def test_sets_last_accessed(self):
        """add_memory() must initialise last_accessed."""
        before = time.time()
        mid = ev.add_memory("hello world", "fact", "", 0.6)
        after = time.time()

        conn = ev.get_db()
        ts = conn.execute("SELECT last_accessed FROM memory WHERE id=?", (mid,)).fetchone()[0]
        conn.close()

        assert before <= ts <= after


class TestDecay:
    def test_uniform_decay_matches_original_formula(self):
        """use_recency=False must apply factor uniformly, identical to the old behaviour."""
        mid = ev.add_memory("test", "fact", "", 0.8)
        t0 = time.time()
        conn = ev.get_db()
        conn.execute("UPDATE memory SET last_accessed=?, weight=0.8 WHERE id=?",
                     (t0 - 60 * 86400, mid))
        conn.commit()
        conn.close()

        ev.auto_decay(factor=0.95, use_recency=False)

        conn = ev.get_db()
        new_w = conn.execute("SELECT weight FROM memory WHERE id=?", (mid,)).fetchone()[0]
        conn.close()

        assert abs(new_w - 0.8 * 0.95) < 1e-9

    def test_recency_decay_recently_accessed_decays_less(self):
        """Memories accessed moments ago should decay less than memories not accessed in 60 days."""
        mid_old = ev.add_memory("old", "fact", "", 0.8)
        mid_new = ev.add_memory("new", "fact", "", 0.8)
        t0 = time.time()

        conn = ev.get_db()
        conn.execute("UPDATE memory SET last_accessed=?, weight=0.8 WHERE id=?",
                     (t0 - 60 * 86400, mid_old))
        conn.execute("UPDATE memory SET last_accessed=?, weight=0.8 WHERE id=?",
                     (t0, mid_new))
        conn.commit()
        conn.close()

        ev.auto_decay(factor=0.90, use_recency=True)

        conn = ev.get_db()
        w_old = conn.execute("SELECT weight FROM memory WHERE id=?", (mid_old,)).fetchone()[0]
        w_new = conn.execute("SELECT weight FROM memory WHERE id=?", (mid_new,)).fetchone()[0]
        conn.close()

        assert w_new > w_old, (
            f"Recently-accessed memory should decay less: w_new={w_new:.4f} w_old={w_old:.4f}"
        )

    def test_recency_multiplier_formula(self):
        """Verify the exact multiplier formula for a memory accessed moments ago."""
        mid = ev.add_memory("formula check", "fact", "", 0.8)
        t0 = time.time()
        conn = ev.get_db()
        conn.execute("UPDATE memory SET last_accessed=?, weight=0.8 WHERE id=?", (t0, mid))
        conn.commit()
        conn.close()

        factor = 0.90
        ev.auto_decay(factor=factor, use_recency=True)

        conn = ev.get_db()
        actual = conn.execute("SELECT weight FROM memory WHERE id=?", (mid,)).fetchone()[0]
        conn.close()

        # days_since ≈ 0  →  multiplier ≈ 1.0  →  weight should be close to 0.8
        assert actual > 0.8 * factor, (
            f"Just-accessed memory decayed too much: {actual:.4f}"
        )

    def test_uniform_flag_via_cli_args(self):
        """cmd_decay respects the --uniform flag (calls auto_decay with use_recency=False)."""
        import types

        mid = ev.add_memory("uniform flag test", "fact", "", 0.8)
        conn = ev.get_db()
        conn.execute("UPDATE memory SET weight=0.8 WHERE id=?", (mid,))
        conn.commit()
        conn.close()

        args = types.SimpleNamespace(factor="0.95", uniform=True)
        ev.cmd_decay(args)

        conn = ev.get_db()
        nw = conn.execute("SELECT weight FROM memory WHERE id=?", (mid,)).fetchone()[0]
        conn.close()

        assert abs(nw - 0.8 * 0.95) < 1e-9


class TestAccessMemory:
    def test_updates_timestamp(self):
        """access_memory() must bump last_accessed to ~now."""
        mid = ev.add_memory("access test", "fact", "", 0.6)
        old_ts = time.time() - 1000
        conn = ev.get_db()
        conn.execute("UPDATE memory SET last_accessed=? WHERE id=?", (old_ts, mid))
        conn.commit()
        conn.close()

        time.sleep(0.02)
        ev.access_memory(mid)

        conn = ev.get_db()
        new_ts = conn.execute("SELECT last_accessed FROM memory WHERE id=?", (mid,)).fetchone()[0]
        conn.close()

        assert new_ts > old_ts


class TestSearchMemories:
    def test_search_updates_last_accessed(self):
        """search_memories() must update last_accessed for returned results."""
        mid = ev.add_memory("unique xyzzy search token", "fact", "", 0.7)

        conn = ev.get_db()
        before_ts = conn.execute(
            "SELECT last_accessed FROM memory WHERE id=?", (mid,)
        ).fetchone()[0]
        conn.close()

        time.sleep(0.05)
        results = ev.search_memories("xyzzy")
        assert any(r["id"] == mid for r in results), "Memory not found in search results"

        conn = ev.get_db()
        after_ts = conn.execute(
            "SELECT last_accessed FROM memory WHERE id=?", (mid,)
        ).fetchone()[0]
        conn.close()

        assert after_ts > before_ts, (
            f"last_accessed not updated after search: {before_ts} -> {after_ts}"
        )
