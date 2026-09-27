r"""Rule 12: a paper statement with no blueprint node is reported (advisory)."""

from __future__ import annotations

from conftest import tagged
from fixtures.article import statement

THM = "\\begin{theorem}\n  \\label{thm:%s}\n  Body.\n\\end{theorem}\n"


def test_an_unmarked_statement_is_reported(article):
    article.blueprint(statement(label="thm:x"))
    article.paper(THM % "loose")
    f = article.check()
    (msg,) = tagged(f.advisory, "unshared")
    assert "paper.tex:1" in msg and "thm:loose" in msg
    assert f.stats["paper_unshared"] == 1
    assert f.ok


def test_a_marked_statement_is_not_reported(article):
    article.blueprint(statement(label="thm:x"))
    article.paper("% shared with blueprint thm:x\n" + THM % "x")
    assert tagged(article.check().advisory, "unshared") == []


def test_the_opt_out_comment_silences_it_and_needs_a_reason(article):
    article.blueprint(statement(label="thm:x"))
    article.paper("% no blueprint node: restates Theorem 2 of the cited paper\n" + THM % "a"
                  + "\n% no blueprint node\n" + THM % "b")
    (msg,) = tagged(article.check().advisory, "unshared")
    assert "thm:b" in msg


def test_a_marker_covers_only_the_next_statement(article):
    article.blueprint(statement(label="thm:x"))
    article.paper("% shared with blueprint thm:x\n" + THM % "x" + "\n" + THM % "y")
    (msg,) = tagged(article.check().advisory, "unshared")
    assert "thm:y" in msg


def test_a_marker_for_a_nonexistent_label_still_fails(article):
    article.blueprint(statement(label="thm:x"))
    article.paper("% shared with blueprint thm:nope\n" + THM % "nope")
    f = article.check()
    assert not f.ok
    assert tagged(f.fatal, "paper")
    assert tagged(f.advisory, "unshared") == []


def test_environments_are_read_from_the_declarations(article):
    article.blueprint(statement(label="thm:x"))
    article.paper(
        "\\theoremstyle{plain}\n\\newtheorem{conjecture}{Conjecture}\n"
        "\\theoremstyle{remark}\n\\newtheorem{note}{Note}\n"
        "\\begin{conjecture}\n  \\label{conj:a}\n  Body.\n\\end{conjecture}\n"
        "\\begin{note}\n  Body.\n\\end{note}\n"
        "\\begin{remark}\n  Body.\n\\end{remark}\n"
        "% \\begin{theorem} commented out\n")
    (msg,) = tagged(article.check().advisory, "unshared")
    assert "conjecture" in msg
