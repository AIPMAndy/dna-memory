#!/usr/bin/env python3
"""Report evidence for each supported client surface without reading transcripts."""

import json
from pathlib import Path
import sqlite3
import subprocess
import time
from urllib.parse import quote

from scripts.import_native_history import configured_paths, source_files


NATIVE_SURFACES = {
    "codex-desktop": "codex",
    "codex-cli": "codex",
    "claude-code-desktop": "claude-code",
    "claude-code-cli": "claude-code",
    "claude-cowork": "claude-desktop",
    "hermes-desktop": "hermes",
    "hermes-cli": "hermes",
    "hermes-gateway": "hermes",
}

JSONL_METADATA_BYTES = 512 * 1024
JSONL_LINE_BYTES = 256 * 1024
HERMES_LOCAL_SOURCES = {"desktop", "cli", "tui", "subagent"}


def _query_one(connection, sql, parameters=()):
    if connection is None:
        return None
    try:
        return connection.execute(sql, parameters).fetchone()
    except sqlite3.Error:
        return None


def _checkpoint_status(connection, client, spec, paths, min_age_seconds=120):
    now = time.time()
    eligible = []
    checkpointed = 0
    eligible_checkpointed = 0
    for path in paths:
        stat = path.stat()
        checkpoint = _query_one(
            connection,
            "SELECT inode, offset, source_hash FROM import_checkpoints WHERE source_ref=?",
            ("native-auto:{}:{}".format(client, path.expanduser().resolve()),),
        )
        current = bool(
            checkpoint and checkpoint[0] == stat.st_ino and checkpoint[1] == stat.st_size
        )
        if current:
            checkpointed += 1
        if now - stat.st_mtime < int(min_age_seconds):
            continue
        eligible.append(path)
        if current:
            eligible_checkpointed += 1
    row = _query_one(
        connection,
        "SELECT MAX(updated_at) FROM import_checkpoints WHERE source_ref LIKE ?",
        ("native-auto:{}:%".format(client),),
    )
    roots_exist = any(Path(root).expanduser().exists() for root in spec.roots)
    return {
        "source_exists": roots_exist,
        "source_files": len(paths),
        "eligible_files": len(eligible),
        "checkpointed_files": checkpointed,
        "eligible_checkpointed_files": eligible_checkpointed,
        "checkpoint_complete": roots_exist and eligible_checkpointed == len(eligible),
        "last_import_at": row[0] if row else None,
    }


def _jsonl_marker(path, client):
    consumed = 0
    try:
        with path.open("rb") as handle:
            while consumed < JSONL_METADATA_BYTES:
                line = handle.readline(min(JSONL_LINE_BYTES, JSONL_METADATA_BYTES - consumed))
                if not line:
                    break
                consumed += len(line)
                if not line.endswith(b"\n") and len(line) == JSONL_LINE_BYTES:
                    break
                try:
                    item = json.loads(line)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                if client == "codex" and item.get("type") == "session_meta":
                    payload = item.get("payload") or {}
                    originator = str(payload.get("originator") or "")
                    raw_source = payload.get("source")
                    if isinstance(raw_source, str):
                        source = raw_source
                    elif isinstance(raw_source, dict) and "subagent" in raw_source:
                        source = "subagent"
                    elif raw_source:
                        source = "structured"
                    else:
                        source = ""
                    if originator == "Codex Desktop":
                        return "codex-desktop", "{}/{}".format(originator, source or "unknown")
                    if originator == "codex-tui" or source == "cli":
                        return "codex-cli", "{}/{}".format(originator or "unknown", source)
                    return None, "{}/{}".format(originator or "unknown", source or "unknown")
                if client == "claude-code":
                    entrypoint = item.get("entrypoint")
                    if entrypoint == "claude-desktop-3p":
                        return "claude-code-desktop", entrypoint
                    if entrypoint == "sdk-cli":
                        return "claude-code-cli", entrypoint
                    if entrypoint:
                        return None, str(entrypoint)
    except OSError:
        pass
    return None, None


def _native_entry_evidence(files):
    surface_paths = {
        "codex-desktop": [],
        "codex-cli": [],
        "claude-code-desktop": [],
        "claude-code-cli": [],
    }
    markers = {surface: {} for surface in surface_paths}
    unclassified = {"codex": 0, "claude-code": 0}
    for client in ("codex", "claude-code"):
        for path in files.get(client, []):
            surface, marker = _jsonl_marker(path, client)
            if surface is None:
                unclassified[client] += 1
                continue
            surface_paths[surface].append(path)
            markers[surface][marker] = markers[surface].get(marker, 0) + 1
    return surface_paths, markers, unclassified


def _contains_mcp(paths):
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "dna-memory" in text and "memory_mcp.py" in text:
            return True
    return False


def _mcp_status(home):
    home = Path(home)
    application_support = home / "Library" / "Application Support"
    return {
        "codex": _contains_mcp((home / ".codex" / "config.toml",)),
        "claude-code": _contains_mcp((
            home / ".claude" / "mcp.json",
            home / ".claude" / "settings.json",
            home / ".claude.json",
        )),
        "claude-desktop": _contains_mcp(tuple(
            application_support.glob("Claude*/claude_desktop_config.json")
        )),
        "hermes": _contains_mcp((home / ".hermes" / "config.yaml",)),
    }


def _launch_agent(home, label):
    plist = Path(home) / "Library" / "LaunchAgents" / (label + ".plist")
    loaded = False
    last_exit_code = None
    if plist.is_file():
        try:
            result = subprocess.run(
                ["launchctl", "print", "gui/{}/{}".format(Path(home).stat().st_uid, label)],
                capture_output=True, text=True, check=False,
            )
        except FileNotFoundError:
            return {"installed": True, "loaded": False, "last_exit_code": None}
        loaded = result.returncode == 0
        for line in result.stdout.splitlines():
            if "last exit code =" in line:
                try:
                    last_exit_code = int(line.rsplit("=", 1)[1].strip())
                except ValueError:
                    pass
                break
    return {"installed": plist.is_file(), "loaded": loaded, "last_exit_code": last_exit_code}


def _launch_agent_by_suffix(home, suffix, fallback_label):
    directory = Path(home) / "Library" / "LaunchAgents"
    candidates = sorted(directory.glob("*{}.plist".format(suffix)))
    label = candidates[0].stem if candidates else fallback_label
    return _launch_agent(home, label)


def _hermes_state_status(config, index_connection):
    path = config.hermes_state_db
    if not path or not path.is_file():
        return {
            "exists": False, "sessions": 0, "checkpointed_sessions": 0,
            "source_counts": {},
        }
    uri = "file:{}?mode=ro".format(path.resolve())
    connection = sqlite3.connect(uri, uri=True)
    try:
        source_counts = dict(connection.execute(
            "SELECT source, COUNT(*) FROM sessions GROUP BY source"
        ).fetchall())
        sessions = sum(source_counts.values())
    finally:
        connection.close()
    row = _query_one(
        index_connection,
        "SELECT COUNT(*) FROM import_checkpoints WHERE source_ref LIKE ?",
        ("hermes:{}#%".format(path.resolve()),),
    )
    checkpointed = row[0] if row else 0
    return {
        "exists": True,
        "sessions": sessions,
        "checkpointed_sessions": checkpointed,
        "checkpoint_complete": checkpointed >= sessions,
        "source_counts": source_counts,
    }


def _file_entry_evidence(paths, markers):
    return {
        "verified": bool(paths),
        "matched_files": len(paths),
        "markers": markers,
    }


def _hermes_entry_evidence(source_counts, accepted=None, gateway=False):
    if gateway:
        markers = {
            source: count for source, count in source_counts.items()
            if source not in HERMES_LOCAL_SOURCES
        }
    else:
        markers = {
            source: source_counts[source] for source in accepted or ()
            if source_counts.get(source)
        }
    matched = sum(markers.values())
    return {"verified": matched > 0, "matched_sessions": matched, "markers": markers}


def build_coverage_report(config, home=None, paths_by_client=None, min_age_seconds=120):
    home = Path(home or Path.home())
    specs = paths_by_client or configured_paths(config)
    files = source_files(specs)
    index_connection = None
    if config.database_path.is_file():
        uri = "file:{}?mode=ro".format(quote(str(config.database_path.resolve()), safe="/"))
        index_connection = sqlite3.connect(uri, uri=True)
    try:
        native = {
            client: _checkpoint_status(
                index_connection, client, specs[client], paths, min_age_seconds
            )
            for client, paths in files.items()
        }
        surface_paths, surface_markers, unclassified = _native_entry_evidence(files)
        surface_sources = {
            surface: _checkpoint_status(
                index_connection, NATIVE_SURFACES[surface],
                specs[NATIVE_SURFACES[surface]], paths, min_age_seconds,
            )
            for surface, paths in surface_paths.items()
        }
        for client, count in unclassified.items():
            if client in native:
                native[client]["unclassified_files"] = count
        hermes_state = _hermes_state_status(config, index_connection)
    finally:
        if index_connection is not None:
            index_connection.close()
    mcp = _mcp_status(home)
    native_agent = _launch_agent_by_suffix(
        home, ".dna-memory-native-history-import",
        "io.dna-memory.native-history-import",
    )
    hermes_agent = _launch_agent_by_suffix(
        home, ".dna-memory-hermes-import", "io.dna-memory.hermes-import"
    )
    surfaces = {}
    for surface, client in NATIVE_SURFACES.items():
        source = native.get(client, {
            "source_exists": False,
            "source_files": 0, "eligible_files": 0, "checkpointed_files": 0,
            "checkpoint_complete": False, "last_import_at": None,
        })
        surfaces[surface] = {
            "capture_mode": "automatic-structured" if client == "hermes" else "automatic-native",
            "automatic_capture": True,
            "source": source,
            "structured_source": hermes_state if client == "hermes" else None,
            "mcp_configured": mcp[client],
            "launch_agent": hermes_agent if client == "hermes" else native_agent,
        }
    for surface in ("codex-desktop", "codex-cli", "claude-code-desktop", "claude-code-cli"):
        client = NATIVE_SURFACES[surface]
        paths = surface_paths[surface]
        surfaces[surface]["source"] = surface_sources[surface]
        surfaces[surface]["entry_evidence"] = _file_entry_evidence(
            paths, surface_markers[surface]
        )
    source_counts = hermes_state.get("source_counts", {})
    surfaces["hermes-desktop"]["entry_evidence"] = _hermes_entry_evidence(
        source_counts, accepted=("desktop",)
    )
    surfaces["hermes-cli"]["entry_evidence"] = _hermes_entry_evidence(
        source_counts, accepted=("cli", "tui")
    )
    surfaces["hermes-gateway"]["entry_evidence"] = _hermes_entry_evidence(
        source_counts, gateway=True
    )
    surfaces["claude-desktop-cloud"] = {
        "capture_mode": "explicit-mcp-writeback",
        "automatic_capture": False,
        "reason": "no stable local transcript source confirmed",
        "source": None,
        "structured_source": None,
        "mcp_configured": mcp["claude-desktop"],
        "launch_agent": None,
    }
    return {"surfaces": surfaces, "native_sources": native, "hermes_state": hermes_state}


def main():
    from scripts.config import load_config

    print(json.dumps(build_coverage_report(load_config()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
