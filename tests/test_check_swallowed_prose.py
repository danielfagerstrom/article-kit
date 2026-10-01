"""The scaffolded swallowed-prose gate (`scaffold/scripts/check-swallowed-prose.py`), sibling to
the control-character check.

Shells out to git (to diff against a base revision) and reads the module's own `scripts/` copy, so
the suite's `subprocess.run` block is lifted through `real_run`, over a real git repository under
`tmp_path` -- the same pattern `test_release.py` and `test_sync_agents_hook.py` use.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from linkage import scaffold

SCRIPT = scaffold.scaffold_dir() / "scripts" / "check-swallowed-prose.py"

PROPOSITION = """\
\\begin{proposition}
A kernel bounded by the interface constant together with its derivatives
is uniformly smooth throughout the real line.
\\end{proposition}
"""

# A marker that replaced the whole first line, leaving it -- and no more -- as a comment: the
# swallowed tail (everything after `% CHANGED`) plus the next, unchanged line reconstructs the
# base revision's prose.
SWALLOWED = """\
\\begin{proposition}
% CHANGED A kernel bounded by the interface constant together with its derivatives
is uniformly smooth throughout the real line.
\\end{proposition}
"""

# The session-contract fix: the marker on its own line, before the changed text.
REPAIRED = """\
\\begin{proposition}
% CHANGED
A kernel bounded by the interface constant together with its derivatives
is uniformly smooth throughout the real line.
\\end{proposition}
"""


@pytest.fixture
def unblocked(monkeypatch, real_run):
    monkeypatch.setattr(subprocess, "run", real_run)
    return real_run


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def commit(root: Path, message: str) -> None:
    env = {**os.environ, "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
          "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com"}
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=root, check=True,
                   capture_output=True, text=True, env=env)


@pytest.fixture
def repo(tmp_path: Path, unblocked) -> Path:
    """A git repo whose `linkage.toml` names a non-default paper directory, a module with one
    base commit holding `manuscript/main.tex` -- the hard-coded `paper`/`paper-b`/`paper-c` list
    the ported script replaces would miss this directory entirely."""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    (root / "linkage.toml").write_text(
        'slug = "test"\n\n[paths]\npaper = "manuscript"\n', encoding="utf-8")
    manuscript = root / "manuscript"
    manuscript.mkdir()
    (manuscript / "main.tex").write_text(PROPOSITION, encoding="utf-8")
    (root / "scripts").mkdir()
    shutil.copy(SCRIPT, root / "scripts" / "check-swallowed-prose.py")
    commit(root, "base")
    return root


def base_sha(root: Path, real_run) -> str:
    r = real_run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True)
    return r.stdout.strip()


def run_check(root: Path, base: str, real_run):
    return real_run([sys.executable, str(root / "scripts" / "check-swallowed-prose.py"), base],
                    cwd=root, capture_output=True, text=True)


def test_swallowed_prose_is_found_in_the_configured_paper_directory(repo, real_run):
    base = base_sha(repo, real_run)
    (repo / "manuscript" / "main.tex").write_text(SWALLOWED, encoding="utf-8")
    r = run_check(repo, base, real_run)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "manuscript/main.tex:2" in r.stdout


def test_the_repaired_edit_is_clean(repo, real_run):
    base = base_sha(repo, real_run)
    (repo / "manuscript" / "main.tex").write_text(REPAIRED, encoding="utf-8")
    r = run_check(repo, base, real_run)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "no swallowed prose" in r.stdout
