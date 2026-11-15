"""Absent parts: a repository without a blueprint, a Lean tree or a paper, by declaration.

`linkage.toml` declares a part by naming its path, or by leaving the default in place. A
part whose anchor key it leaves out *and* whose default path does not exist is absent: a
paper-only satellite (a conference version citing the long paper's blueprint and Lean) or
an article still at its draft is not broken for lacking them. A path that IS written and
does not exist stays an error, so a typo is never read as "this repository has none".
"""

from __future__ import annotations

import pytest

from conftest import run_cli
from linkage import config

PAPER = r"""\documentclass{article}
\newtheorem{theorem}{Theorem}
\begin{document}
\begin{abstract}A paper.\end{abstract}
\begin{theorem}\label{thm:main}A statement taken from the long paper.\end{theorem}
\end{document}
"""


def _paper_only(tmp_path, toml: str = 'slug = "ppr"\n\n[paths]\npaper = "paper"\n'):
    root = tmp_path / "paper-only"
    (root / "paper").mkdir(parents=True)
    (root / "paper" / "main.tex").write_text(PAPER, encoding="utf-8", newline="\n")
    (root / "linkage.toml").write_text(toml, encoding="utf-8")
    return root


def _check(root, *extra):
    return run_cli("--root", str(root), "check", *extra)


# --- what `config.load` reads as absent ------------------------------------------------


def test_a_full_article_has_every_part(article):
    assert article.cfg.absent == frozenset()


def test_paths_left_out_of_a_paper_only_repository_are_absent_parts(tmp_path):
    cfg = config.load(_paper_only(tmp_path))
    assert cfg.absent == {"blueprint", "lean"}
    assert cfg.has("paper") and not cfg.has("blueprint")
    assert cfg.missing() == []
    assert cfg.lean_uses is None


def test_the_paper_key_may_be_left_out_too(tmp_path):
    root = _paper_only(tmp_path, 'slug = "ppr"\n')
    assert config.load(root).absent == {"blueprint", "lean"}


def test_a_repository_at_its_draft_has_no_paper_and_no_lean(article):
    import shutil
    shutil.rmtree(article.root / "paper")
    shutil.rmtree(article.root / "Formalization")
    article.file("linkage.toml", 'slug = "test"\n')   # the blueprint at its defaults
    cfg = config.load(article.root)
    assert cfg.absent == {"paper", "lean"}
    assert cfg.papers == ()


def test_a_declared_path_that_does_not_exist_is_still_an_error(tmp_path):
    root = _paper_only(
        tmp_path, 'slug = "ppr"\n\n[paths]\npaper = "paper"\nlean = "Formalisation"\n')
    with pytest.raises(config.ConfigError, match="lean = Formalisation"):
        config.load(root)


def test_a_ledger_without_a_blueprint_is_a_half_declared_part(tmp_path):
    root = _paper_only(
        tmp_path, 'slug = "ppr"\n\n[paths]\npaper = "paper"\naxioms = "AXIOMS.md"\n')
    (root / "AXIOMS.md").write_text("# ledger\n", encoding="utf-8")
    with pytest.raises(config.ConfigError, match="names axioms but no `blueprint`"):
        config.load(root)


def test_shared_lean_packages_need_a_lean_part(tmp_path):
    root = _paper_only(
        tmp_path, 'slug = "ppr"\n\n[paths]\npaper = "paper"\nlean_packages = ["Lib"]\n')
    with pytest.raises(config.ConfigError, match="no Lean part"):
        config.load(root)


def test_the_companions_of_a_present_blueprint_are_still_required(article):
    """Only a part's anchor key decides absence: a blueprint without its ledger is broken."""
    (article.root / "blueprint" / "AXIOMS.md").unlink()
    with pytest.raises(config.ConfigError, match="axioms = blueprint/AXIOMS.md"):
        config.load(article.root)


# --- `linkage check` on a repository with absent parts ---------------------------------


def test_check_passes_in_a_paper_only_repository_and_says_what_it_skipped(tmp_path):
    rc, out, err = _check(_paper_only(tmp_path))
    assert rc == 0, out + err
    assert "Parts: paper; absent: blueprint, lean" in out
    assert "Blueprint:" not in out and "Dependency closure:" not in out
    # every statement of a paper-only repository has no node here by design (rule 12)
    assert "[unshared]" not in out
    assert "LINKAGE CHECK OK" in out


def test_check_still_reads_the_paper_sources(tmp_path):
    root = _paper_only(tmp_path)
    (root / "paper" / "main.tex").write_bytes(PAPER.encode() + b"\x08oops\n")
    rc, out, _ = _check(root)
    assert rc == 1
    assert "[chars]" in out


def test_a_shared_marker_without_a_blueprint_says_why_it_fails(tmp_path):
    root = _paper_only(tmp_path)
    (root / "paper" / "main.tex").write_text(
        PAPER.replace(r"\begin{theorem}", "% shared with blueprint thm:main\n"
                                          r"\begin{theorem}"),
        encoding="utf-8", newline="\n")
    rc, out, _ = _check(root)
    assert rc == 1
    assert "this repository has no blueprint part" in out


def test_a_trust_base_subsection_without_blueprint_and_lean_is_reported_not_crashed(tmp_path):
    root = _paper_only(tmp_path)
    (root / "paper" / "main.tex").write_text(
        PAPER.replace(r"\end{document}",
                      "% trust base: begin\nRests on the long paper.\n% trust base: end\n"
                      r"\end{document}"),
        encoding="utf-8", newline="\n")
    rc, out, err = _check(root)
    assert rc == 0, out + err
    assert "[trust-base]" in out and "not checked" in out


@pytest.mark.parametrize("argv", [
    ("check", "--emit-manifest", "m.json"),
    ("manifest",),
    ("closure",),
    ("axioms",),
])
def test_a_command_that_needs_an_absent_part_stops_with_a_config_error(tmp_path, argv):
    rc, out, err = run_cli("--root", str(_paper_only(tmp_path)), *argv)
    assert rc == 2, out + err
    assert "needs the blueprint" in err


def test_check_passes_on_a_blueprint_with_no_lean_yet(article):
    """The blueprint phase: nodes stated, none formalised, no Lean tree."""
    import shutil

    from fixtures.article import statement
    shutil.rmtree(article.root / "Formalization")
    article.file("linkage.toml", 'slug = "test"\n')
    article.blueprint(statement(label="thm:x"))
    rc, out, err = _check(article.root)
    assert rc == 0, out + err
    assert "absent: lean" in out and "Blueprint: 1 statement nodes" in out
