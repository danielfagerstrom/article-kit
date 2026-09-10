"""Shared fixtures, and the isolation that keeps the suite honest.

Three rules, adapted from the hub's `tests/conftest.py` (C:\\Users\\danie\\Documents\\Notes):

1. **The suite never reads a real article repository.** Every test builds one under
   `tmp_path`, and the cwd is moved there, so `config.find_root()`'s walk-up cannot
   climb out of the fixture into this checkout — a suite that reads the developer's
   own tree passes in one working state and is worth less than no suite.
2. **The suite never shells out.** `subprocess.run` is blocked outright, which covers
   the three places the package reaches for a process: `render.pandoc_version`,
   `artifacts.git_provenance` and `demand.fetch_demands`. Opt in with `real_run`.
3. **What the block would break is stubbed, not silenced.** `pandoc_version` and
   `git_provenance` both swallow `OSError` only, so an unstubbed test would fail with
   the block's AssertionError instead of its own assertion. They are pinned to their
   *absent* answers (no pandoc, no git) so every test starts from one state; the
   `pandoc` fixture supplies a deterministic fake renderer for the tests that need one.

`tests/test_isolation.py` asserts all three, so they cannot rot into good intentions.
"""

from __future__ import annotations

import contextlib
import io
import subprocess
from pathlib import Path

import pytest

from fixtures.article import Article

REPO = Path(__file__).resolve().parent.parent
_REAL_RUN = subprocess.run
NO_GIT = {"source_commit": None, "source_dirty": False}


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def _blocked(*a, **kw):
        raise AssertionError(
            f"test shelled out to {a[0] if a else kw.get('args')!r} — the suite runs on "
            "source text alone. Use the `pandoc` fixture for rendering, or `real_run` if "
            "you genuinely need a subprocess."
        )

    monkeypatch.setattr(subprocess, "run", _blocked)
    monkeypatch.setattr("linkage.render.pandoc_version", lambda: None)
    monkeypatch.setattr("linkage.manifest.git_provenance", lambda root: dict(NO_GIT))
    return tmp_path


@pytest.fixture
def real_run():
    """The unpatched `subprocess.run`, for the rare test that must spawn a process."""
    return _REAL_RUN


@pytest.fixture
def article(tmp_path) -> Article:
    """A minimal article repo under tmp_path. Overwrite what the test is about."""
    return Article(tmp_path)


@pytest.fixture
def pandoc(monkeypatch):
    """Pretend the pinned pandoc is installed, rendering deterministically.

    The fake is a marker, not an imitation: `render_markdown` is one `subprocess.run`
    around pandoc's own behaviour, so imitating it would test the imitation. What the
    manifest tests need is that rendering *happened*, that the right source reached the
    renderer, and that `rendered_sha` covers what it claims to.
    """

    def _install(pin: str = "3.10", fail_on: set[str] | None = None, residue: bool = False):
        calls: list[str] = []
        monkeypatch.setattr("linkage.render.pandoc_version", lambda: pin)

        def _render(src: str, preamble: str, target: str) -> str:
            calls.append(src)
            if fail_on and any(k in src for k in fail_on):
                raise RuntimeError("pandoc exit 1")
            return ("md(" + src + ")") + (r" \unrendered" if residue else "")

        monkeypatch.setattr("linkage.manifest.render_markdown", _render)
        return calls

    return _install


def run_cli(*argv: str) -> tuple[int, str, str]:
    """Invoke `linkage <argv>` in-process; return (exit_code, stdout, stderr).

    End-to-end on purpose: the exit code *is* the contract CI binds to. Streams are
    redirected into StringIOs, which also keeps `main()`'s `reconfigure()` shim off the
    test path (a StringIO has no such method).
    """
    from linkage.cli import main

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            rc = main(list(argv))
        except SystemExit as e:  # argparse exits on --help / usage errors
            rc = e.code if isinstance(e.code, int) else 1
    return rc, out.getvalue(), err.getvalue()


def tagged(msgs: list[str], tag: str) -> list[str]:
    """The findings of one check, selected by the `[tag]` every message opens with."""
    return [m for m in msgs if m.startswith(f"[{tag}]")]


__all__ = ["NO_GIT", "REPO", "Article", "run_cli", "tagged"]
