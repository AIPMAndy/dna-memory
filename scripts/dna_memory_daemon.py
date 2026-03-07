#!/usr/bin/env python3
"""
DNA Memory 后台守护进程

用途：
- 周期性执行 reflect / decay
- 与前台 evolve.py 通过文件锁协同，避免并发写冲突
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


SCRIPT_DIR = Path(__file__).resolve().parent
EVOLVE_SCRIPT = SCRIPT_DIR / "evolve.py"
CONFIG_FILE = SCRIPT_DIR.parent / "assets" / "config.json"
DEFAULT_PID_FILE = Path(os.environ.get("DNA_MEMORY_PID_FILE", "/tmp/dna-memory-daemon.pid"))
DEFAULT_LOG_FILE = Path(os.environ.get("DNA_MEMORY_LOG_FILE", "/tmp/dna-memory-daemon.log"))

RUNNING = True


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        return {}
    return {}


def load_interval_defaults() -> tuple[float, float]:
    config = load_config()
    reflect_minutes = float(config.get("auto_reflect_interval_minutes", 15))
    decay_hours = float(config.get("auto_decay_interval_hours", 1))
    return max(reflect_minutes * 60.0, 1.0), max(decay_hours * 3600.0, 1.0)


def now_ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


def log_line(log_file: Path, message: str) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{now_ts()}] {message}\n")


def read_pid(pid_file: Path) -> Optional[int]:
    if not pid_file.exists():
        return None
    try:
        return int(pid_file.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def is_pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def handle_stop_signal(signum, frame):  # noqa: ANN001,ARG001
    global RUNNING
    RUNNING = False


def run_action(action: str, log_file: Path, memory_dir: Optional[str], timeout: float) -> int:
    env = os.environ.copy()
    if memory_dir:
        env["DNA_MEMORY_DIR"] = memory_dir

    cmd = ["python3", str(EVOLVE_SCRIPT), action]
    log_line(log_file, f"run: {' '.join(cmd)}")
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
        if proc.stdout.strip():
            for line in proc.stdout.strip().splitlines():
                log_line(log_file, f"{action} stdout: {line}")
        if proc.stderr.strip():
            for line in proc.stderr.strip().splitlines():
                log_line(log_file, f"{action} stderr: {line}")
        log_line(log_file, f"{action} exit={proc.returncode}")
        return proc.returncode
    except subprocess.TimeoutExpired:
        log_line(log_file, f"{action} timeout after {timeout}s")
        return 124


def resolve_memory_dir(raw_memory_dir: Optional[str]) -> Path:
    if raw_memory_dir:
        return Path(raw_memory_dir).expanduser().resolve()
    env_dir = os.environ.get("DNA_MEMORY_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return (Path.home() / ".openclaw" / "workspace" / "memory").resolve()


def load_memory_meta(memory_dir: Path) -> dict:
    meta_file = memory_dir / "meta.json"
    if not meta_file.exists():
        return {}
    try:
        with open(meta_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        return {}
    return {}


def to_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def should_run_reflect(memory_dir: Path) -> bool:
    meta = load_memory_meta(memory_dir)
    stats = meta.get("stats", {}) if isinstance(meta.get("stats"), dict) else {}
    remember_count = to_int(stats.get("remember", 0), 0)
    last_reflect_remember_count = to_int(meta.get("last_reflect_remember_count", -1), -1)
    return remember_count > last_reflect_remember_count


def cleanup_pid_file(pid_file: Path) -> None:
    pid = read_pid(pid_file)
    if pid == os.getpid() and pid_file.exists():
        pid_file.unlink()


def cmd_run(args: argparse.Namespace) -> int:
    global RUNNING
    RUNNING = True

    pid_file = Path(args.pid_file).expanduser().resolve()
    log_file = Path(args.log_file).expanduser().resolve()

    signal.signal(signal.SIGTERM, handle_stop_signal)
    signal.signal(signal.SIGINT, handle_stop_signal)

    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()), encoding="utf-8")
    log_line(log_file, f"daemon started pid={os.getpid()}")

    last_reflect = 0.0
    last_decay = 0.0
    memory_dir = resolve_memory_dir(args.memory_dir)
    log_line(
        log_file,
        (
            f"config reflect_interval={args.reflect_interval}s "
            f"decay_interval={args.decay_interval}s memory_dir={memory_dir}"
        ),
    )

    try:
        while RUNNING:
            now = time.monotonic()

            if last_reflect == 0.0 or now - last_reflect >= args.reflect_interval:
                if should_run_reflect(memory_dir):
                    run_action("reflect", log_file, args.memory_dir, args.action_timeout)
                else:
                    log_line(log_file, "reflect skipped: no new remember events since last reflect")
                last_reflect = now

            if last_decay == 0.0 or now - last_decay >= args.decay_interval:
                run_action("decay", log_file, args.memory_dir, args.action_timeout)
                last_decay = now

            if args.once:
                break

            time.sleep(args.poll_interval)
    finally:
        log_line(log_file, "daemon stopping")
        cleanup_pid_file(pid_file)

    return 0


def cmd_start(args: argparse.Namespace) -> int:
    pid_file = Path(args.pid_file).expanduser().resolve()
    log_file = Path(args.log_file).expanduser().resolve()
    existing_pid = read_pid(pid_file)
    if existing_pid and is_pid_running(existing_pid):
        print(f"STATUS=already_running PID={existing_pid} PID_FILE={pid_file}")
        return 0

    cmd = [
        sys.executable,
        str(Path(__file__).resolve()),
        "run",
        "--reflect-interval",
        str(args.reflect_interval),
        "--decay-interval",
        str(args.decay_interval),
        "--poll-interval",
        str(args.poll_interval),
        "--action-timeout",
        str(args.action_timeout),
        "--pid-file",
        str(pid_file),
        "--log-file",
        str(log_file),
    ]
    if args.memory_dir:
        cmd.extend(["--memory-dir", args.memory_dir])

    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as out:
        proc = subprocess.Popen(
            cmd,
            stdout=out,
            stderr=out,
            start_new_session=True,
            close_fds=True,
        )

    time.sleep(0.3)
    running = is_pid_running(proc.pid)
    print(f"STATUS={'started' if running else 'failed'} PID={proc.pid} PID_FILE={pid_file} LOG_FILE={log_file}")
    return 0 if running else 1


def cmd_stop(args: argparse.Namespace) -> int:
    pid_file = Path(args.pid_file).expanduser().resolve()
    log_file = Path(args.log_file).expanduser().resolve()
    pid = read_pid(pid_file)
    if not pid:
        print(f"STATUS=not_running PID_FILE={pid_file}")
        return 0

    if not is_pid_running(pid):
        cleanup_pid_file(pid_file)
        print(f"STATUS=stale_pid_removed PID={pid}")
        return 0

    os.kill(pid, signal.SIGTERM)
    deadline = time.time() + args.wait_timeout
    while time.time() < deadline:
        if not is_pid_running(pid):
            cleanup_pid_file(pid_file)
            log_line(log_file, f"daemon stopped pid={pid}")
            print(f"STATUS=stopped PID={pid}")
            return 0
        time.sleep(0.2)

    os.kill(pid, signal.SIGKILL)
    cleanup_pid_file(pid_file)
    log_line(log_file, f"daemon killed pid={pid}")
    print(f"STATUS=killed PID={pid}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    pid_file = Path(args.pid_file).expanduser().resolve()
    pid = read_pid(pid_file)
    if pid and is_pid_running(pid):
        print(f"STATUS=running PID={pid} PID_FILE={pid_file}")
        return 0
    print(f"STATUS=not_running PID_FILE={pid_file}")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DNA Memory daemon manager")
    sub = parser.add_subparsers(dest="cmd", required=True)
    default_reflect_interval, default_decay_interval = load_interval_defaults()

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--pid-file", default=str(DEFAULT_PID_FILE))
        p.add_argument("--log-file", default=str(DEFAULT_LOG_FILE))
        p.add_argument("--memory-dir", default="")

    p_run = sub.add_parser("run", help="Run daemon loop in foreground")
    add_common(p_run)
    p_run.add_argument("--reflect-interval", type=float, default=default_reflect_interval, help="Seconds between reflect runs")
    p_run.add_argument("--decay-interval", type=float, default=default_decay_interval, help="Seconds between decay runs")
    p_run.add_argument("--poll-interval", type=float, default=2.0, help="Loop sleep seconds")
    p_run.add_argument("--action-timeout", type=float, default=60.0, help="Timeout per action call")
    p_run.add_argument("--once", action="store_true", help="Run one cycle then exit")
    p_run.set_defaults(func=cmd_run)

    p_start = sub.add_parser("start", help="Start daemon in background")
    add_common(p_start)
    p_start.add_argument("--reflect-interval", type=float, default=default_reflect_interval)
    p_start.add_argument("--decay-interval", type=float, default=default_decay_interval)
    p_start.add_argument("--poll-interval", type=float, default=2.0)
    p_start.add_argument("--action-timeout", type=float, default=60.0)
    p_start.set_defaults(func=cmd_start)

    p_stop = sub.add_parser("stop", help="Stop daemon")
    add_common(p_stop)
    p_stop.add_argument("--wait-timeout", type=float, default=8.0, help="Wait seconds before force kill")
    p_stop.set_defaults(func=cmd_stop)

    p_status = sub.add_parser("status", help="Show daemon status")
    add_common(p_status)
    p_status.set_defaults(func=cmd_status)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
