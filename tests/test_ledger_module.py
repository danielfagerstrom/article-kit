r"""A qualified `\ledger{<package>:<id>}` reference resolves against a *required module's*
own AXIOMS.md (Q-0374), the way an `include <package> @ <revision>` line of
`trust-boundary.txt` already resolves Lean names (`tests/test_trust_include.py`). Built the
same way: a real git repository under `tmp_path`, because the resolve-at-the-pinned-commit
property is the point.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from conftest import run_cli, tagged
from fixtures.article import assignment, statement

ENV = {**os.environ, "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
       "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com"}

V_BOUNDARY = "SpatialLine.fourier_toolbox_levy_unique\n"

V_AXIOMS = """\
# Paper V's ledger

## A3

Fourier-toolbox regularity (Levy uniqueness).

**Lean:** `SpatialLine.fourier_toolbox_levy_unique`

**Cite:** @levy1925 — Thm 2.1, p. 14
"""

V_AXIOMS_NO_CITE = """\
# Paper V's ledger

## A3

Fourier-toolbox regularity (Levy uniqueness).
"""


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True,
                          text=True, env=ENV).stdout.strip()


@pytest.fixture
def unblocked(monkeypatch, real_run):
    monkeypatch.setattr(subprocess, "run", real_run)


def package(article, name: str, files: dict[str, str]) -> str:
    """A git repository at `Formalization/.lake/packages/<name>`, one commit; returns its sha."""
    repo = article.root / "Formalization/.lake/packages" / name
    repo.mkdir(parents=True)
    git(repo, "init", "-q")
    for rel, text in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "release")
    return git(repo, "rev-parse", "HEAD")


def manifest(article, *pins: tuple[str, str, str]) -> None:
    """`lake-manifest.json` pinning each `(name, inputRev, rev)` as a git package."""
    article.file("Formalization/lake-manifest.json", json.dumps({
        "version": "1.2.0", "packagesDir": ".lake/packages", "name": "Consumer",
        "packages": [{"url": f"https://example.org/{n}", "type": "git", "subDir": "Formalization",
                      "rev": rev, "name": n, "inputRev": tag, "inherited": False}
                     for n, tag, rev in pins]}, indent=1))


def boundary(article, *lines: str) -> None:
    article.file("blueprint/trust-boundary.txt", "".join(f"{line}\n" for line in lines))


@pytest.fixture
def paper_v(article, unblocked):
    """A required module, `SpatialHemigroup`, with one ledger entry `A3`."""
    sha = package(article, "SpatialHemigroup", {
        "blueprint/trust-boundary.txt": V_BOUNDARY,
        "blueprint/AXIOMS.md": V_AXIOMS,
    })
    manifest(article, ("SpatialHemigroup", "v0.1", sha))
    return sha


def qualified_node(ref: str = "SpatialHemigroup:A3") -> str:
    return statement(label="thm:x", status="A", ledger=(ref,),
                     note=assignment(f"\\ledger{{{ref}}} carries it."))


# --- resolves ---------------------------------------------------------------------------


def test_a_qualified_reference_resolves_against_the_required_modules_own_ledger(
        article, paper_v):
    boundary(article, "include SpatialHemigroup @ v0.1")
    article.blueprint(qualified_node())
    f = article.check()
    assert tagged(f.fatal, "ledger") == []
    assert f.ok


def test_own_module_refs_are_unaffected_by_an_unrelated_qualified_one(article, paper_v):
    """The own-ledger path is untouched: a bare ref still resolves against this article's
    own AXIOMS.md even while a qualified ref resolves elsewhere in the same run."""
    boundary(article, "include SpatialHemigroup @ v0.1")
    article.blueprint(
        qualified_node()
        + statement(label="thm:y", status="A", ledger=("A1",), note=assignment()))
    from fixtures.article import ledger_entry
    article.axioms(ledger_entry("A1"))
    f = article.check()
    assert tagged(f.fatal, "ledger") == []


# --- fails closed ------------------------------------------------------------------------


def test_a_reference_to_a_module_nothing_includes_fails(article, paper_v):
    """No `include` line names `SpatialHemigroup` at all."""
    article.blueprint(qualified_node())
    f = article.check()
    msgs = tagged(f.fatal, "ledger")
    assert len(msgs) == 1
    assert "SpatialHemigroup is not included by trust-boundary.txt" in msgs[0]


def test_a_reference_to_a_module_included_as_something_else_fails(article, paper_v):
    """An include line exists, but not for the package this reference names."""
    boundary(article, "include SpatialHemigroup @ v0.1")
    article.blueprint(qualified_node("OtherPackage:A3"))
    f = article.check()
    msgs = tagged(f.fatal, "ledger")
    assert len(msgs) == 1 and "OtherPackage is not included" in msgs[0]


def test_a_reference_to_an_id_the_required_modules_ledger_lacks_fails(article, paper_v):
    boundary(article, "include SpatialHemigroup @ v0.1")
    article.blueprint(qualified_node("SpatialHemigroup:A99"))
    f = article.check()
    msgs = tagged(f.fatal, "ledger")
    assert len(msgs) == 1
    assert "no '## A99' entry in SpatialHemigroup's AXIOMS.md" in msgs[0]


def test_a_required_entry_with_no_cite_line_fails(article, unblocked):
    sha = package(article, "SpatialHemigroup", {
        "blueprint/trust-boundary.txt": V_BOUNDARY,
        "blueprint/AXIOMS.md": V_AXIOMS_NO_CITE,
    })
    manifest(article, ("SpatialHemigroup", "v0.1", sha))
    boundary(article, "include SpatialHemigroup @ v0.1")
    article.blueprint(qualified_node())
    f = article.check()
    msgs = tagged(f.fatal, "ledger")
    assert len(msgs) == 1 and "**Cite:**" in msgs[0] and "SpatialHemigroup" in msgs[0]


def test_a_malformed_manifest_fails_closed_rather_than_crashing(article):
    """No `include` line resolves at all when there is no manifest to pin it against --
    `trust.resolve` already reports it as an error, which is read as 'not included'."""
    article.blueprint(qualified_node())
    boundary(article, "include SpatialHemigroup @ v0.1")
    f = article.check()
    assert tagged(f.fatal, "ledger") != []


# --- the CLI end to end, like test_trust_include.py --------------------------------------


def test_linkage_check_exits_1_on_an_unresolved_qualified_reference(article, paper_v):
    article.blueprint(qualified_node("SpatialHemigroup:A99"))
    rc, out, _err = run_cli("--root", str(article.root), "check")
    assert rc == 1
    assert "A99" in out
