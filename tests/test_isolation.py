"""The suite's isolation, asserted rather than intended.

If these three go quiet, every other test in this repo becomes a claim about the
developer's machine — the article repos next door, the pandoc on their PATH, the git in
their checkout — instead of about the package.
"""

from __future__ import annotations

import subprocess

import pytest

from conftest import REPO
from linkage import config, render


def test_the_cwd_is_a_temporary_directory(tmp_path):
    from pathlib import Path

    assert Path.cwd() == tmp_path
    assert REPO not in Path.cwd().parents


def test_the_walk_up_cannot_reach_this_checkout():
    """`linkage.toml` is not in this repo, but a future one must not be found either."""
    with pytest.raises(config.ConfigError):
        config.find_root()


def test_shelling_out_is_blocked():
    with pytest.raises(AssertionError, match="the suite runs on source text alone"):
        subprocess.run(["git", "--version"])


def test_pandoc_is_absent_unless_a_test_asks_for_it():
    assert render.pandoc_version() is None
    assert render.check_pin("3.10") == "pandoc not found on PATH"


def test_the_pandoc_fixture_makes_the_pin_available(pandoc):
    pandoc()
    assert render.check_pin("3.10") is None


def test_real_run_is_the_unpatched_subprocess(real_run):
    assert real_run is not subprocess.run
