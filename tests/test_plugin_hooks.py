"""The plugin's instruction log (hub Q-0544, E-0020 part 3): `hooks/hooks.json` and
`hooks/log_load.py`.

The log exists so that compactions and the rules in force are counted, not inferred. Held here:
the hook file loads the events it names, asynchronously; the script writes exactly one line of
paths and reasons per event and never any content; and it can never fail a session, whatever it
is fed or wherever it cannot write.
"""

from __future__ import annotations

import json
import os
import sys

from conftest import REPO

HOOKS = REPO / "hooks" / "hooks.json"
SCRIPT = REPO / "hooks" / "log_load.py"


def runner(real_run):
    """The hook is a process Claude Code spawns, so it is tested as one (`real_run`)."""
    def run(event, env_data=None, raw=None):
        # The real environment (Windows needs SYSTEMROOT to start Python), minus any data dir.
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PLUGIN_DATA"}
        if env_data is not None:
            env["CLAUDE_PLUGIN_DATA"] = str(env_data)
        stdin = raw if raw is not None else json.dumps(event)
        return real_run([sys.executable, str(SCRIPT)], input=stdin, text=True,
                        capture_output=True, env=env, timeout=30)
    return run


def lines(data):
    return [json.loads(ln) for ln in (data / "instructions.jsonl").read_text("utf-8").splitlines()]


def test_the_hooks_file_logs_both_events_asynchronously():
    doc = json.loads(HOOKS.read_text(encoding="utf-8"))
    events = doc["hooks"]
    assert set(events) == {"InstructionsLoaded", "SessionStart"}
    (compact,) = events["SessionStart"]
    assert compact["matcher"] == "compact"
    for groups in events.values():
        for group in groups:
            for hook in group["hooks"]:
                assert hook["type"] == "command" and hook["async"] is True
                assert "${CLAUDE_PLUGIN_ROOT}/hooks/log_load.py" in hook["command"]
                assert hook["command"].endswith("|| true")   # never a failing exit
    assert SCRIPT.is_file()


def test_an_instructions_loaded_event_writes_one_line_of_paths_and_reasons(tmp_path, real_run):
    run = runner(real_run)
    event = {"session_id": "s1", "hook_event_name": "InstructionsLoaded", "cwd": "/a",
             "file_path": "/a/.claude/rules/article-kit/writing.md", "load_reason": "compact",
             "memory_type": "Project", "transcript_path": "/t.jsonl"}
    r = run(event, tmp_path)
    assert r.returncode == 0 and r.stdout == "" and r.stderr == ""
    (line,) = lines(tmp_path)
    assert set(line) == {"session_id", "event", "file_path", "load_reason", "cwd", "ts"}
    assert line["event"] == "InstructionsLoaded" and line["load_reason"] == "compact"
    assert line["file_path"].endswith("writing.md")


def test_a_compaction_start_is_logged_under_the_same_reason_key(tmp_path, real_run):
    run = runner(real_run)
    run({"session_id": "s1", "hook_event_name": "SessionStart", "source": "compact"}, tmp_path)
    run({"session_id": "s1", "hook_event_name": "InstructionsLoaded", "file_path": "/x",
         "load_reason": "session_start"}, tmp_path)
    first, second = lines(tmp_path)
    assert first["event"] == "SessionStart" and first["load_reason"] == "compact"
    assert first["file_path"] is None and second["load_reason"] == "session_start"


def test_nothing_it_is_fed_or_cannot_reach_makes_it_fail(tmp_path, real_run):
    run = runner(real_run)
    assert run({"hook_event_name": "InstructionsLoaded"}).returncode == 0          # no data dir
    assert run(None, tmp_path, raw="not json").returncode == 0
    assert run(None, tmp_path, raw="[1, 2]").returncode == 0
    blocked = tmp_path / "file"
    blocked.write_text("a file where the directory should be", encoding="utf-8")
    assert run({"hook_event_name": "SessionStart"}, blocked / "sub").returncode == 0
    assert not (tmp_path / "instructions.jsonl").exists()
