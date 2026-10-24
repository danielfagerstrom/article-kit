"""Log what instructions load, and when a session compacts (hub Q-0544, E-0020 part 3).

Run by the plugin's `hooks/hooks.json` on `InstructionsLoaded` and on `SessionStart` with the source
`compact`, asynchronously and with no decision. It reads the hook's JSON from stdin and appends one
line to `instructions.jsonl` in the plugin's data directory (`$CLAUDE_PLUGIN_DATA`):
`session_id`, `event`, `file_path`, `load_reason`, `cwd`, `ts`. Paths and reasons only, never a
file's content. Every failure is silent and exits 0: a log must not be able to disturb a session.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG = "instructions.jsonl"


def record(event: dict) -> dict:
    """The line for one hook input: InstructionsLoaded carries `load_reason`, SessionStart a
    `source` (`compact` is the one the plugin asks for), stored under the same key."""
    return {
        "session_id": event.get("session_id"),
        "event": event.get("hook_event_name"),
        "file_path": event.get("file_path"),
        "load_reason": event.get("load_reason") or event.get("source"),
        "cwd": event.get("cwd"),
        # timezone.utc, not datetime.UTC (3.11+): the hook runs on whatever python3 the
        # machine has, not this project's interpreter.
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),  # noqa: UP017
    }


def main() -> int:
    try:
        data = os.environ.get("CLAUDE_PLUGIN_DATA")
        if not data:
            return 0
        event = json.loads(sys.stdin.read() or "{}")
        if not isinstance(event, dict):
            return 0
        path = Path(data)
        path.mkdir(parents=True, exist_ok=True)
        with open(path / LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record(event), ensure_ascii=False) + "\n")
    except Exception:   # noqa: BLE001 — a logging hook never fails the session
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
