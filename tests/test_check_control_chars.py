"""The scaffolded control-character gate (`scaffold/scripts/check-control-chars.py`): which
directories it scans, and that a repository without some of them still passes."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from linkage import scaffold

SCRIPT = scaffold.scaffold_dir() / "scripts" / "check-control-chars.py"


@pytest.fixture(autouse=True)
def unblocked(monkeypatch, real_run):
    monkeypatch.setattr(subprocess, "run", real_run)


def run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT)], cwd=root, capture_output=True,
                          text=True, encoding="utf-8")


def write(root: Path, rel: str, data: bytes = b"clean\n") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def test_a_repository_without_the_directories_passes(tmp_path):
    rc = run(tmp_path)
    assert rc.returncode == 0, rc.stderr
    assert "0 files" in rc.stdout


@pytest.mark.parametrize("rel", [
    "paper/sections/10-locality.tex",
    "paper/refs.bib",
    "paper/README.md",
    "notes/plans/plan.md",
    "notes/plans/plan.txt",
    "records/2026/log.md",
    "records/log.txt",
    "adr/0001-x.md",
    "blueprint/src/a.tex",
    "Formalization/A.lean",
])
def test_a_cr_in_each_scanned_place_is_caught(tmp_path, rel):
    write(tmp_path, rel, b"a\rb\n")
    rc = run(tmp_path)
    assert rc.returncode == 1
    assert rel in rc.stderr.replace("\\", "/")


def test_captured_tool_output_is_not_scanned(tmp_path):
    """A freeze gate's captured log keeps the terminal's escapes (ESC[1m ... ESC[0m) and a PDF
    text dump keeps glyph codes: the program's bytes, kept as a record, not corruption."""
    write(tmp_path, "records/affine/freeze-gates-q0451-output.txt", b"\x1b[1mdone.\x1b[0m\n")
    write(tmp_path, "records/notes-output.txt", b"(\x10 h \x11)\n")
    rc = run(tmp_path)
    assert rc.returncode == 0, rc.stderr
    assert "0 files" in rc.stdout


def test_a_captured_output_file_named_on_the_command_line_is_checked(tmp_path):
    write(tmp_path, "records/x-output.txt", b"\x1b[0m\n")
    rc = subprocess.run([sys.executable, str(SCRIPT), "records/x-output.txt"], cwd=tmp_path,
                        capture_output=True, text=True, encoding="utf-8")
    assert rc.returncode == 1


def test_a_written_record_beside_it_is_still_scanned(tmp_path):
    write(tmp_path, "records/x-output.txt", b"\x1b[0m\n")
    write(tmp_path, "records/x-notes.txt", b"a\x08b\n")
    rc = run(tmp_path)
    assert rc.returncode == 1
    assert "x-notes.txt" in rc.stderr and "x-output.txt" not in rc.stderr


def test_crlf_line_endings_are_legal(tmp_path):
    write(tmp_path, "notes/a.md", b"line\r\nline\r\n")
    assert run(tmp_path).returncode == 0


def test_the_configured_paper_directories_are_scanned(tmp_path):
    (tmp_path / "linkage.toml").write_text(
        'paths.paper = ["paper", "paper-b"]\n', encoding="utf-8")
    write(tmp_path, "paper-b/deep/s.tex", b"\x08egin\n")
    rc = run(tmp_path)
    assert rc.returncode == 1
    assert "U+0008" in rc.stderr


def test_a_configured_directory_replaces_the_default(tmp_path):
    (tmp_path / "linkage.toml").write_text('[paths]\npaper = "manuscript"\n', encoding="utf-8")
    write(tmp_path, "paper/s.tex", b"\x08\n")
    assert run(tmp_path).returncode == 0
    write(tmp_path, "manuscript/s.tex", b"\x07\n")
    assert run(tmp_path).returncode == 1


def test_a_broken_config_falls_back_to_paper(tmp_path):
    (tmp_path / "linkage.toml").write_text("this is [not toml\n", encoding="utf-8")
    write(tmp_path, "paper/s.tex", b"\x07\n")
    assert run(tmp_path).returncode == 1
