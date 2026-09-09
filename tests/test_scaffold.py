"""Scaffolding a new article, and the drift detection that keeps the copies honest.

Plus the integration test the proposal asks for: a *freshly scaffolded* article, filled
in with the smallest article's half that has one edge of every kind, passes
`linkage check`. CI runs the same fixture through the installed console script.
"""

from __future__ import annotations

import json

import pytest

from conftest import run_cli
from linkage import scaffold
from scaffold_smoke import build


@pytest.fixture
def fresh(tmp_path):
    """A scaffolded article, with nothing else written into it."""
    root = tmp_path / "new-article"
    root.mkdir()
    scaffold.init(root, slug="fresh")
    return root


def test_init_writes_the_framework_owned_files_and_the_templates(fresh):
    for rel in scaffold.FRAMEWORK_OWNED.values():
        assert (fresh / rel).is_file(), rel
    for rel in scaffold.SEEDED.values():
        assert (fresh / rel).is_file(), rel
    for rel in scaffold.TEMPLATES.values():
        assert (fresh / rel).is_file(), rel


def test_the_templates_are_substituted(fresh):
    toml = (fresh / "linkage.toml").read_text(encoding="utf-8")
    assert 'slug = "fresh"' in toml
    assert "@@" not in toml


def test_the_stamp_records_the_framework_owned_hashes(fresh):
    stamp = json.loads((fresh / "blueprint" / scaffold.STAMP).read_text(encoding="utf-8"))
    assert set(stamp["framework_owned"]) == set(scaffold.FRAMEWORK_OWNED.values())
    assert all(len(h) == 12 for h in stamp["framework_owned"].values())


def test_a_second_init_leaves_the_articles_own_files_alone(fresh):
    own = fresh / "blueprint" / "src" / "macros.tex"
    own.write_text("% my notation\n", encoding="utf-8")
    scaffold.init(fresh, slug="fresh")
    assert own.read_text(encoding="utf-8") == "% my notation\n"


def test_sync_refreshes_a_framework_file_but_writes_no_templates(fresh):
    owned = fresh / "blueprint" / "src" / "linkage-macros.tex"
    owned.write_text("% edited by hand\n", encoding="utf-8")
    (fresh / "linkage.toml").unlink()

    assert scaffold.drift(fresh) == ["blueprint/src/linkage-macros.tex"]
    scaffold.init(fresh, slug="fresh", sync=True)
    assert scaffold.drift(fresh) == []
    assert not (fresh / "linkage.toml").exists()   # templates are the article's


def test_drift_is_silent_on_an_untouched_scaffold(fresh):
    assert scaffold.drift(fresh) == []


def test_a_missing_framework_file_is_not_drift(fresh):
    """Only a *divergent* copy is reported; an absent one is `init`'s job to restore."""
    (fresh / "blueprint" / "src" / "latexmkrc").unlink()
    assert scaffold.drift(fresh) == []


# --- the integration test -------------------------------------------------------------


def test_a_freshly_scaffolded_article_passes_linkage_check(tmp_path):
    root = build(tmp_path / "smoke")
    rc, out, err = run_cli("--root", str(root), "check")
    assert rc == 0, out + err
    assert "LINKAGE CHECK OK" in out
    assert "3 statement nodes (1 \\leanok)" in out
    assert "1 verbatim" in out


def test_the_scaffolded_article_declares_a_grounded_trust_boundary(tmp_path):
    root = build(tmp_path / "smoke")
    rc, _, err = run_cli("--root", str(root), "axioms", "--check")
    assert rc == 0, err
    assert "1 interface axiom(s)" in err


def test_an_edited_framework_file_shows_up_in_the_check(tmp_path):
    root = build(tmp_path / "smoke")
    (root / "blueprint" / "src" / "blueprint.sty").write_text("% mine now\n", encoding="utf-8")
    rc, out, _ = run_cli("--root", str(root), "check")
    assert rc == 0
    assert "advisory [scaffold] blueprint/src/blueprint.sty differs" in out
