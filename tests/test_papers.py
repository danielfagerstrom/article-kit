"""Several paper directories in one article repository (`paths.paper` as a list).

Requested by `spatial-hemigroup-scale-space` (WISHLIST, 2026-09-15): its Paper V holds a
released line paper and two modules in one repository, each with its own release tag, and
the modules were invisible to the shared-statement check. What these tests hold down is
that a second directory is not a special case — it is read, compared, pinned and counted
exactly like the first — and that the one-directory form still reads as it always did.
"""

from __future__ import annotations

import pytest

from conftest import run_cli, tagged
from fixtures.article import statement
from linkage import artifacts, config

BODY = "The kernel is smooth on the open half-line."


def paper_stmt(body: str, marker: str, label: str = "thm:x") -> str:
    return (f"% shared with blueprint {marker}\n"
            f"\\begin{{theorem}}\n  \\label{{{label}}}\n  {body}\n\\end{{theorem}}\n")


# --- configuration -------------------------------------------------------------------


def test_a_single_directory_still_reads_as_one_element(article):
    assert article.cfg.papers == (article.root / "paper",)


def test_a_list_is_read_in_the_order_it_is_written(article):
    article.papers("paper", "paper-b").paper("", dir="paper-b")
    assert article.cfg.papers == (article.root / "paper", article.root / "paper-b")


def test_every_missing_paper_directory_is_named(article):
    article.papers("paper", "paper-b", "paper-c")
    with pytest.raises(config.ConfigError) as e:
        config.load(article.root)
    assert "paper = paper-b" in str(e.value) and "paper = paper-c" in str(e.value)


def test_an_empty_list_is_a_config_error(article):
    """It would check no paper at all, silently — the opposite of what a list is for."""
    article.papers()
    with pytest.raises(config.ConfigError, match="empty list"):
        config.load(article.root)


def test_a_repeated_directory_is_a_config_error(article):
    """Every marker in it would be read, reported and pinned twice."""
    article.papers("paper", "paper")
    with pytest.raises(config.ConfigError, match="twice"):
        config.load(article.root)


def test_a_non_string_entry_is_a_config_error(article):
    article.file("linkage.toml", 'slug = "test"\n\n[paths]\npaper = 7\n')
    with pytest.raises(config.ConfigError, match="must be a directory or a list"):
        config.load(article.root)


# --- reading -------------------------------------------------------------------------


def test_markers_are_collected_from_every_directory_in_config_order(article):
    article.papers("paper-b", "paper")
    article.paper("% shared with blueprint thm:a\n")
    article.paper("% shared with blueprint thm:b\n", dir="paper-b")
    assert [m.file for m in artifacts.paper_markers(article.cfg)] == \
        ["paper-b/paper.tex", "paper/paper.tex"]


def test_same_named_files_in_two_directories_stay_distinguishable(article):
    """The report locates a marker by repo-relative path, so `paper.tex` is not ambiguous."""
    article.papers("paper", "paper-b")
    article.paper("% shared with blueprint thm:ghost\n")
    article.paper("% shared with blueprint thm:ghost\n", dir="paper-b")
    article.blueprint(statement(body=BODY, label="thm:x"))
    files = sorted(m.split(":")[0] for m in tagged(article.check().fatal, "paper"))
    assert files == ["[paper]  paper-b/paper.tex", "[paper]  paper/paper.tex"]


def test_a_second_papers_statement_is_compared_with_the_blueprint(article):
    """The whole point of the request: module B's drift is checked, not just the line paper's."""
    article.papers("paper", "paper-b")
    article.blueprint(statement(body=BODY, label="thm:x")
                      + statement(body="It is also bounded.", label="thm:y"))
    article.paper(paper_stmt(BODY, "thm:x"))
    article.paper(paper_stmt("It is unbounded.", "thm:y", label="thm:y"), dir="paper-b")
    f = article.check(strict_shared=True)
    assert f.stats["shared_verbatim"] == 1
    (msg,) = tagged(f.fatal, "shared")
    assert msg.startswith("[shared] paper-b/paper.tex:1 thm:y:")


def test_pin_shared_reaches_the_second_directory(article):
    article.papers("paper", "paper-b")
    article.blueprint(statement(body=BODY, label="thm:x")
                      + statement(body="It is also bounded.", label="thm:y"))
    article.paper(paper_stmt(BODY, "thm:x"))
    article.paper(paper_stmt("Bounded, as it happens.", "thm:y", label="thm:y"), dir="paper-b")
    rc, out, _ = run_cli("--root", str(article.root), "check", "--pin-shared")
    assert rc == 0 and "Pinned 1 marker(s) across 1 file(s)" in out
    text = article.root.joinpath("paper-b/paper.tex").read_text(encoding="utf-8")
    assert "% shared with blueprint thm:y@" in text
    assert article.check().stats["shared_tracked"] == 1


# --- reporting -----------------------------------------------------------------------


def test_the_shared_count_is_broken_down_per_directory(article):
    article.papers("paper", "paper-b")
    article.blueprint(statement(body=BODY, label="thm:x"))
    article.paper(paper_stmt(BODY, "thm:x"))
    article.paper("% shared with blueprint thm:x\n", dir="paper-b")
    rc, out, _ = run_cli("--root", str(article.root), "check")
    assert rc == 0
    assert "2 paper shared-statements" in out
    assert "papers: paper (1), paper-b (1)" in out


def test_one_directory_prints_no_breakdown(article):
    """With a single paper the line would only repeat the count above it."""
    rc, out, _ = run_cli("--root", str(article.root), "check")
    assert rc == 0 and "papers:" not in out
