"""The scaffolded SessionStart hook that syncs the shared agents from an article session.

It finds the hub's `.claude/sync-agents.sh` and runs it, silent and never failing. The hub's
script is stubbed here (its own behaviour is the hub's to test); what is under test is the
locating, the environment it is run with, and the exit code.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from linkage import scaffold

HOOK = scaffold.scaffold_dir() / "claude" / "sync-agents-hook.sh"
STUB = '#!/usr/bin/env bash\nprintf "%s" "$CLAUDE_PROJECT_DIR" > "$HOME/ran"\n'


def find_bash() -> str | None:
    """A bash that reads `C:/…` paths: on Windows `bash` on PATH may be WSL's, so prefer Git's."""
    git_bash = Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "Git" / "bin" / "bash.exe"
    if git_bash.is_file():
        return str(git_bash)
    return shutil.which("bash")


BASH = find_bash()
pytestmark = pytest.mark.skipif(BASH is None, reason="no bash")


def make_hub(path: Path, script: str = STUB) -> Path:
    (path / ".claude").mkdir(parents=True)
    (path / ".claude" / "sync-agents.sh").write_text(script, encoding="utf-8")
    return path


@pytest.fixture
def env(tmp_path):
    """A home, an article checkout under ~/dev, and an environment that names no hub."""
    home = tmp_path / "home"
    article = home / "dev" / "my-article"
    article.mkdir(parents=True)
    e = {k: v for k, v in os.environ.items() if k not in ("WIKI_VAULT", "CLAUDE_PROJECT_DIR")}
    e.update(HOME=home.as_posix(), CLAUDE_PROJECT_DIR=article.as_posix())
    return e, home, article


def run(real_run, env):
    return real_run([BASH, HOOK.as_posix()], env=env, capture_output=True, text=True, timeout=30)


def test_the_settings_wire_the_hook_and_the_file_is_seeded():
    path = scaffold.scaffold_dir() / "claude" / "settings.json"
    settings = json.loads(path.read_text(encoding="utf-8"))
    cmds = [h["command"] for g in settings["hooks"]["SessionStart"] for h in g["hooks"]]
    assert any("sync-agents-hook.sh" in c and c.rstrip().endswith("|| true") for c in cmds)
    assert scaffold.SEEDED["claude/sync-agents-hook.sh"] == ".claude/sync-agents-hook.sh"


def test_wiki_vault_wins_and_the_hub_script_runs_as_the_hub(real_run, env, tmp_path):
    e, home, _ = env
    vault = make_hub(tmp_path / "elsewhere" / "Notes")
    make_hub(home / "dev" / "other-hub")
    e["WIKI_VAULT"] = vault.as_posix()
    r = run(real_run, e)
    assert (r.returncode, r.stdout, r.stderr) == (0, "", "")
    assert (home / "ran").read_text() == vault.as_posix()


def test_the_sweep_finds_a_hub_beside_the_article(real_run, env):
    e, home, _ = env
    hub = make_hub(home / "dev" / "Notes")
    assert run(real_run, e).returncode == 0
    assert (home / "ran").read_text() == hub.as_posix()


def test_a_stale_wiki_vault_falls_through_to_the_sweep(real_run, env, tmp_path):
    e, home, _ = env
    hub = make_hub(home / "dev" / "Notes")
    e["WIKI_VAULT"] = (tmp_path / "gone").as_posix()
    assert run(real_run, e).returncode == 0
    assert (home / "ran").read_text() == hub.as_posix()


def test_no_hub_is_silent_and_exits_zero(real_run, env):
    r = run(real_run, env[0])
    assert (r.returncode, r.stdout, r.stderr) == (0, "", "")
    assert not (env[1] / "ran").exists()


def test_a_failing_hub_script_never_fails_the_session_start(real_run, env):
    e, home, _ = env
    make_hub(home / "dev" / "Notes", "#!/usr/bin/env bash\nexit 7\n")
    assert run(real_run, e).returncode == 0
