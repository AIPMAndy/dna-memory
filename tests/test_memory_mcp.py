import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import types

from scripts.config import load_config
from scripts.memory_service import MemoryService


class FakeFastMCP:
    def __init__(self, name):
        self.name = name
        self.tools = {}

    def tool(self):
        def register(function):
            self.tools[function.__name__] = function
            return function
        return register


def service(tmp_path):
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({
        "knowledge_root": str(tmp_path / "vault"),
        "managed_memory_dir": "00 System/Memory",
        "database_path": str(tmp_path / "memory.db"),
        "skill_root": str(tmp_path / "skills"),
        "skill_registry": str(tmp_path / "registry.json"),
    }))
    return MemoryService(load_config(profile))


def load_memory_mcp(monkeypatch):
    fastmcp = types.ModuleType("mcp.server.fastmcp")
    fastmcp.FastMCP = FakeFastMCP
    server = types.ModuleType("mcp.server")
    server.fastmcp = fastmcp
    mcp = types.ModuleType("mcp")
    mcp.server = server
    monkeypatch.setitem(sys.modules, "mcp", mcp)
    monkeypatch.setitem(sys.modules, "mcp.server", server)
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fastmcp)
    sys.modules.pop("scripts.memory_mcp", None)
    return importlib.import_module("scripts.memory_mcp")


def test_mcp_registers_seven_thin_memory_tools(tmp_path, monkeypatch):
    module = load_memory_mcp(monkeypatch)
    svc = service(tmp_path)
    mcp = module.build_server(svc)

    assert set(mcp.tools) == {
        "memory_recall", "memory_get", "memory_remember", "memory_feedback",
        "memory_close_session", "memory_status", "memory_reindex",
    }

    remembered = mcp.tools["memory_remember"](
        "preference", "MCP unique preference", source_hash="mcp-source",
        source_ref="codex://session/turn-1", client="codex",
        project_path="/tmp/project", session_id="session-1",
    )
    assert remembered["ok"] is True
    recalled = mcp.tools["memory_recall"](
        "MCP unique", client="claude", session_id="claude-session"
    )
    assert recalled["memories"][0]["memory_id"] == remembered["memory_id"]
    event = svc.store.connection.execute(
        "SELECT client, session_id FROM memory_recall_events ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert tuple(event) == ("claude", "claude-session")
    fetched = mcp.tools["memory_get"](remembered["memory_id"])
    assert fetched["memory"]["summary"] == "MCP unique preference"
    assert fetched["memory"]["source_refs"] == ["codex://session/turn-1"]
    assert fetched["memory"]["clients"] == ["codex"]
    assert fetched["memory"]["project_path"] == "/tmp/project"
    assert fetched["memory"]["session_id"] == "session-1"


def test_feedback_and_close_session_store_bounded_metadata(tmp_path, monkeypatch):
    module = load_memory_mcp(monkeypatch)
    svc = service(tmp_path)
    mcp = module.build_server(svc)
    remembered = svc.remember({"type": "fact", "summary": "feedback target"})

    feedback = mcp.tools["memory_feedback"](
        remembered["memory_id"], "useful", note="helped answer"
    )
    closed = mcp.tools["memory_close_session"](
        client="claude", session_id="session-1", project_path="/tmp/project",
        source_ref="/tmp/session.jsonl",
    )

    assert feedback == {"ok": True, "recorded": True}
    assert closed["ok"] is True
    row = svc.store.connection.execute(
        "SELECT client, session_id, project_path, source_ref, excerpt "
        "FROM candidate_events WHERE event_id=?", (closed["event_id"],)
    ).fetchone()
    assert tuple(row) == (
        "claude", "session-1", "/tmp/project", "/tmp/session.jsonl", None
    )


def test_tool_errors_have_stable_structure(tmp_path, monkeypatch):
    module = load_memory_mcp(monkeypatch)
    mcp = module.build_server(service(tmp_path))

    result = mcp.tools["memory_remember"]("invalid", "not accepted")

    assert result["ok"] is False
    assert result["error"]["code"] == "validation_error"
    assert isinstance(result["error"]["message"], str)


def test_memory_remember_exposes_supersedes_without_adding_a_tool(tmp_path, monkeypatch):
    module = load_memory_mcp(monkeypatch)
    svc = service(tmp_path)
    mcp = module.build_server(svc)
    old = svc.remember({"type": "project_state", "summary": "old MCP state"})

    remembered = mcp.tools["memory_remember"](
        "project_state", "new MCP state", supersedes=[old["memory_id"]]
    )
    invalid = mcp.tools["memory_remember"](
        "project_state", "invalid MCP state", supersedes=old["memory_id"]
    )

    assert len(mcp.tools) == 7
    assert remembered["ok"] is True
    assert remembered["superseded"] == [old["memory_id"]]
    assert svc.get(old["memory_id"])["status"] == "superseded"
    assert invalid["ok"] is False
    assert invalid["error"]["code"] == "validation_error"


def test_mcp_script_starts_outside_repository_cwd(tmp_path):
    fake_package = tmp_path / "fake/mcp/server"
    fake_package.mkdir(parents=True)
    (fake_package.parent / "__init__.py").write_text("")
    (fake_package / "__init__.py").write_text("")
    (fake_package / "fastmcp.py").write_text(
        "class FastMCP:\n"
        "    def __init__(self, name): pass\n"
        "    def tool(self): return lambda fn: fn\n"
        "    def run(self, transport=None): pass\n"
    )
    script = Path(__file__).parents[1] / "scripts/memory_mcp.py"
    env = dict(os.environ, PYTHONPATH=str(tmp_path / "fake"))

    result = subprocess.run(
        [sys.executable, str(script)], cwd=str(tmp_path), env=env,
        text=True, capture_output=True,
    )

    assert result.returncode == 0, result.stderr
