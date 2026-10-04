"""`include <package> @ <revision> [<path>]` in `trust-boundary.txt` (Q-0298).

A module that requires another brings the other's trust boundary into its own by reference:
the names are read from the required package at the commit the consumer's `lake-manifest.json`
pins, never copied and never taken from the working tree. These tests run real `git` over a
package repository built under `tmp_path`, because the commit-not-working-tree property is the
point and a stubbed reader could not show it.

The case it was built for: Paper VII (`spatial-hemigroup-affine`) requires Paper V's
`SpatialHemigroup` at `v0.1`, and its first guarded theorem through Paper V prints
`SpatialLine.fourier_toolbox_levy_unique`, a name of V's ledger and not VII's.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from conftest import run_cli
from linkage import trust

V_BOUNDARY = """\
# Paper V's interface axioms
SpatialLine.fourier_toolbox_levy_unique
SpatialLine.kernel_regularity_law
"""

ENV = {**os.environ, "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
       "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com"}


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True,
                          text=True, env=ENV).stdout.strip()


@pytest.fixture
def unblocked(monkeypatch, real_run):
    monkeypatch.setattr(subprocess, "run", real_run)


def package(article, name: str, files: dict[str, str]) -> tuple[Path, str]:
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
    return repo, git(repo, "rev-parse", "HEAD")


def manifest(article, *pins: tuple[str, str, str]) -> None:
    """`lake-manifest.json` pinning each `(name, inputRev, rev)` as a git package."""
    article.file("Formalization/lake-manifest.json", json.dumps({
        "version": "1.2.0", "packagesDir": ".lake/packages", "name": "Consumer",
        "packages": [{"url": f"https://example.org/{n}", "type": "git", "subDir": "Formalization",
                      "rev": rev, "name": n, "inputRev": tag, "inherited": False}
                     for n, tag, rev in pins]}, indent=1))


def boundary(article, *lines: str) -> None:
    article.file("blueprint/trust-boundary.txt", "# this article's\n" + "".join(
        f"{line}\n" for line in lines))


@pytest.fixture
def paper_v(article, unblocked):
    """Paper VII's situation: SpatialHemigroup required at v0.1, its boundary in the export."""
    _, sha = package(article, "SpatialHemigroup", {"blueprint/trust-boundary.txt": V_BOUNDARY})
    manifest(article, ("SpatialHemigroup", "v0.1", sha))
    return sha


# --- a matching include ---------------------------------------------------------------


def test_a_matching_include_admits_exactly_the_required_modules_names(article, paper_v):
    """And this article's AXIOMS.md is not asked to ground them: the ledger is empty here."""
    boundary(article, "include SpatialHemigroup @ v0.1 blueprint/trust-boundary.txt")
    rc, out, err = run_cli("--root", str(article.root), "axioms", "--check")
    assert rc == 0, err
    assert out.split() == [*trust.LEAN_CORE, "SpatialLine.fourier_toolbox_levy_unique",
                           "SpatialLine.kernel_regularity_law"]
    assert f"included: 2 name(s) of SpatialHemigroup @ v0.1 ({paper_v[:12]})" in err
    assert "0 interface axiom(s)" in err and "2 included from 1" in err


def test_the_path_defaults_to_the_exports_trust_boundary(article, paper_v):
    boundary(article, "include SpatialHemigroup @ v0.1")
    assert trust.resolve(article.cfg).names == ["SpatialLine.fourier_toolbox_levy_unique",
                                                "SpatialLine.kernel_regularity_law"]


def test_the_revision_may_be_the_resolved_sha_or_a_prefix_of_it(article, paper_v):
    boundary(article, f"include SpatialHemigroup @ {paper_v[:10]}")
    res = trust.resolve(article.cfg)
    assert not res.errors and len(res.names) == 2
    boundary(article, f"include SpatialHemigroup @ {paper_v[:6]}")  # too short to be a pin
    assert trust.resolve(article.cfg).errors


def test_own_names_and_included_names_sit_side_by_side(article, paper_v):
    """Own names are still grounded in this ledger; included ones are not, and not duplicated."""
    article.axioms("# Ledger\n\n## A1\n\n**Lean:** `Affine.own_interface`\n\n"
                   "**Verbatim:** \"x\" (p. 1)\n")
    boundary(article, "Affine.own_interface", "include SpatialHemigroup @ v0.1",
             "SpatialLine.kernel_regularity_law")
    assert trust.declared(article.cfg) == ["Affine.own_interface",
                                           "SpatialLine.kernel_regularity_law"]
    rc, out, err = run_cli("--root", str(article.root), "axioms", "--check")
    # the copied V name on its own line is an own name, and this ledger does not ground it
    assert rc == 1 and "SpatialLine.kernel_regularity_law" in err.split("never reviewed:")[-1]
    boundary(article, "Affine.own_interface", "include SpatialHemigroup @ v0.1")
    rc, out, err = run_cli("--root", str(article.root), "axioms", "--check")
    assert rc == 0, err
    assert out.split()[3:] == ["Affine.own_interface", "SpatialLine.fourier_toolbox_levy_unique",
                               "SpatialLine.kernel_regularity_law"]


def test_the_pinned_commit_is_read_not_the_working_tree(article, paper_v):
    """An edit under `.lake/packages` -- a junction into a shared store -- admits nothing."""
    repo = article.root / "Formalization/.lake/packages/SpatialHemigroup"
    (repo / "blueprint/trust-boundary.txt").write_text(V_BOUNDARY + "Sneaky.local_edit\n",
                                                       encoding="utf-8")
    boundary(article, "include SpatialHemigroup @ v0.1")
    assert "Sneaky.local_edit" not in trust.allowlist(article.cfg)


def test_a_later_commit_in_the_checkout_is_not_the_pin(article, paper_v):
    repo = article.root / "Formalization/.lake/packages/SpatialHemigroup"
    (repo / "blueprint/trust-boundary.txt").write_text(V_BOUNDARY + "Later.name\n",
                                                       encoding="utf-8")
    git(repo, "commit", "-qam", "after the release")
    boundary(article, "include SpatialHemigroup @ v0.1")
    assert "Later.name" not in trust.allowlist(article.cfg)


# --- refused --------------------------------------------------------------------------


def test_a_revision_the_manifest_does_not_pin_is_refused(article, paper_v):
    boundary(article, "include SpatialHemigroup @ v0.2")
    rc, out, err = run_cli("--root", str(article.root), "axioms", "--check")
    assert rc == 1 and out == ""
    assert "pins SpatialHemigroup at v0.1" in err and "not v0.2" in err
    # the guard fails closed: the allowlist other consumers read admits nothing from it
    assert trust.allowlist(article.cfg) == list(trust.LEAN_CORE)


def test_a_package_missing_from_the_manifest_is_refused(article, paper_v):
    boundary(article, "include SpatialHemigroupKernels @ v0.1")
    rc, _, err = run_cli("--root", str(article.root), "axioms")
    assert rc == 1, "refused without --check too, as an ungrounded name is"
    assert "SpatialHemigroupKernels is not a package of lake-manifest.json" in err


def test_a_pinned_package_that_is_not_fetched_is_refused(article, unblocked):
    manifest(article, ("SpatialHemigroup", "v0.1", "f" * 40))
    boundary(article, "include SpatialHemigroup @ v0.1")
    rc, _, err = run_cli("--root", str(article.root), "axioms", "--check")
    assert rc == 1 and "pinned but not fetched" in err


def test_no_manifest_is_refused(article):
    boundary(article, "include SpatialHemigroup @ v0.1")
    rc, _, err = run_cli("--root", str(article.root), "axioms", "--check")
    assert rc == 1 and "no readable Formalization/lake-manifest.json" in err


def test_a_path_the_release_does_not_ship_is_refused(article, paper_v):
    boundary(article, "include SpatialHemigroup @ v0.1 axioms/boundary.txt")
    rc, _, err = run_cli("--root", str(article.root), "axioms", "--check")
    assert rc == 1 and "cannot read axioms/boundary.txt" in err


def test_a_malformed_include_line_is_refused(article):
    boundary(article, "include SpatialHemigroup v0.1")
    rc, _, err = run_cli("--root", str(article.root), "axioms", "--check")
    assert rc == 1 and "expected `include <package> @ <revision> [<path>]`" in err


# --- nested includes ------------------------------------------------------------------


def test_a_nested_include_is_resolved_against_the_consumers_manifest(article, unblocked):
    _, core = package(article, "ScaleSpaceCore", {"blueprint/trust-boundary.txt": "Core.ax\n"})
    _, v = package(article, "SpatialHemigroup", {
        "blueprint/trust-boundary.txt": V_BOUNDARY + "include ScaleSpaceCore @ v0.2.0\n"})
    manifest(article, ("SpatialHemigroup", "v0.1", v), ("ScaleSpaceCore", "v0.2.0", core))
    boundary(article, "include SpatialHemigroup @ v0.1")
    rc, out, err = run_cli("--root", str(article.root), "axioms", "--check")
    assert rc == 0, err
    assert "Core.ax" in out.split()
    assert "of ScaleSpaceCore @ v0.2.0" in err and "included by SpatialHemigroup" in err


def test_a_nested_include_at_another_revision_than_the_one_built_is_refused(article, unblocked):
    _, core = package(article, "ScaleSpaceCore", {"blueprint/trust-boundary.txt": "Core.ax\n"})
    _, v = package(article, "SpatialHemigroup", {
        "blueprint/trust-boundary.txt": V_BOUNDARY + "include ScaleSpaceCore @ v0.1.0\n"})
    manifest(article, ("SpatialHemigroup", "v0.1", v), ("ScaleSpaceCore", "v0.2.0", core))
    boundary(article, "include SpatialHemigroup @ v0.1")
    rc, _, err = run_cli("--root", str(article.root), "axioms", "--check")
    assert rc == 1
    assert "SpatialHemigroup:blueprint/trust-boundary.txt:4: include ScaleSpaceCore" in err


def test_an_include_cycle_terminates(article, unblocked):
    a = article.root / "Formalization/.lake/packages"
    _, sa = package(article, "A", {"blueprint/trust-boundary.txt": "A.ax\ninclude B @ v1\n"})
    _, sb = package(article, "B", {"blueprint/trust-boundary.txt": "B.ax\ninclude A @ v1\n"})
    assert (a / "A").is_dir() and (a / "B").is_dir()
    manifest(article, ("A", "v1", sa), ("B", "v1", sb))
    boundary(article, "include A @ v1")
    res = trust.resolve(article.cfg)
    assert not res.errors and res.names == ["A.ax", "B.ax"]
