#!/usr/bin/env python3
"""Thin stdio MCP adapter for the Markdown-backed memory service."""

import dataclasses
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp.server.fastmcp import FastMCP

from scripts.config import load_config
from scripts.memory_service import MemoryService, MemoryValidationError


def _error(error):
    code = "validation_error" if isinstance(error, (MemoryValidationError, ValueError)) else "internal_error"
    if code == "internal_error":
        print("dna-memory MCP error: {}".format(error), file=sys.stderr)
    return {"ok": False, "error": {"code": code, "message": str(error)}}


def build_server(service):
    mcp = FastMCP("dna-memory")

    @mcp.tool()
    def memory_recall(
        query: str, limit: int = 20, client: str = None, session_id: str = None
    ):
        """Recall active memories whose summaries match a query."""
        try:
            return {
                "ok": True,
                "memories": service.recall(query, limit, client, session_id),
            }
        except Exception as error:
            return _error(error)

    @mcp.tool()
    def memory_get(memory_id: str):
        """Get one indexed memory by its stable ID."""
        try:
            return {"ok": True, "memory": service.get(memory_id)}
        except Exception as error:
            return _error(error)

    @mcp.tool()
    def memory_remember(
        type: str, summary: str, source_hash: str = None,
        confidence: str = "medium", importance: float = 0.5,
        source_ref: str = None, client: str = None,
        project_path: str = None, session_id: str = None,
        supersedes: list[str] = None,
    ):
        """Write a reviewed memory proposal to the Markdown truth store."""
        try:
            result = service.remember({
                "type": type, "summary": summary, "source_hash": source_hash,
                "confidence": confidence, "importance": importance,
                "source_refs": [source_ref] if source_ref else [],
                "clients": [client] if client else [],
                "project_path": project_path, "session_id": session_id,
                "supersedes": supersedes or [],
            })
            return {"ok": True, **result}
        except Exception as error:
            return _error(error)

    @mcp.tool()
    def memory_feedback(
        memory_id: str, outcome: str, note: str = None,
        client: str = None, session_id: str = None,
    ):
        """Record whether a recalled memory was useful or misleading."""
        try:
            result = service.feedback(memory_id, outcome, note, client, session_id)
            return {"ok": True, **result}
        except Exception as error:
            return _error(error)

    @mcp.tool()
    def memory_close_session(
        client: str, session_id: str, project_path: str = None,
        source_ref: str = None,
    ):
        """Queue bounded session metadata without copying the transcript."""
        try:
            result = service.close_session(client, session_id, project_path, source_ref)
            return {"ok": True, **result}
        except Exception as error:
            return _error(error)

    @mcp.tool()
    def memory_status():
        """Return current memory store status."""
        try:
            return {"ok": True, **service.status()}
        except Exception as error:
            return _error(error)

    @mcp.tool()
    def memory_reindex():
        """Rebuild the disposable SQLite index from Markdown truth."""
        try:
            result = service.reindex()
            return {"ok": True, **dataclasses.asdict(result)}
        except Exception as error:
            return _error(error)

    return mcp


def main():
    build_server(MemoryService(load_config())).run(transport="stdio")


if __name__ == "__main__":
    main()
