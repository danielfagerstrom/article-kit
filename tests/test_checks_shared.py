"""Rule 3b: is the paper's shared statement still the blueprint's?

The four states of `docs/LINKAGE.md` § rule 4 — verbatim, tracked, stale, unpinned —
plus the two reductions that make the comparison mean anything (the blueprint-only
status region, and the environment word the paper writes before a `\\ref`).
"""

from __future__ import annotations

from conftest import run_cli, tagged
from fixtures.article import statement

BODY = "The kernel is smooth on the open half-line."


def paper_stmt(body: str, marker: str, label: str = "thm:x") -> str:
    return (f"% shared with blueprint {marker}\n"
            f"\\begin{{theorem}}\n  \\label{{{label}}}\n  {body}\n\\end{{theorem}}\n")


def shas(article) -> dict[str, str]:
    return {n.label: n.shared_sha for n in article.parse().nodes if n.label}


def test_identical_text_is_verbatim_and_needs_no_pin(article):
    article.blueprint(statement(body=BODY, label="thm:x"))
    article.paper(paper_stmt(BODY, "thm:x"))
    f = article.check()
    assert f.stats["shared_verbatim"] == 1
    assert f.stats["shared_drift"] == 0
    assert f.unpinned == []


def test_the_environment_word_before_a_ref_is_reduced_away(article):
    r"""The paper writes `Theorem~\ref{X}`; leanblueprint renders the word itself."""
    article.blueprint(statement(body=r"By \ref{thm:y}, it is smooth.", label="thm:x"))
    article.paper(paper_stmt(r"By Theorem~\ref{thm:y}, it is smooth.", "thm:x"))
    assert article.check().stats["shared_verbatim"] == 1


def test_a_free_standing_formalisation_note_is_blueprint_only(article):
    """Everything from the status tag onward is the blueprint's; the paper omits it."""
    article.blueprint(statement(body=BODY, label="thm:x", note="Lean models this as a sum."))
    article.paper(paper_stmt(BODY, "thm:x"))
    assert article.check().stats["shared_verbatim"] == 1


def test_divergent_text_is_reported_with_the_point_of_divergence(article):
    article.blueprint(statement(body=BODY, label="thm:x"))
    article.paper(paper_stmt("The kernel is continuous on the open half-line.", "thm:x"))
    f = article.check()
    assert f.fatal == []
    (msg,) = tagged(f.advisory, "shared")
    assert "drifted from the blueprint after 14 chars" in msg
    assert "paper     : continuous" in msg
    assert f.stats["shared_drift"] == 1
    assert [m.file for m in f.unpinned] == ["paper.tex"]


def test_drift_is_fatal_under_strict_shared(article):
    article.blueprint(statement(body=BODY, label="thm:x"))
    article.paper(paper_stmt("Something else entirely.", "thm:x"))
    f = article.check(strict_shared=True)
    assert len(tagged(f.fatal, "shared")) == 1
    assert tagged(f.advisory, "shared") == []


def test_a_merged_statement_pinned_to_both_nodes_is_tracked(article):
    article.blueprint(statement(body=BODY, label="thm:x")
                      + statement(body="It is also bounded.", label="thm:y"))
    s = shas(article)
    article.paper(paper_stmt("The kernel is smooth and bounded.",
                             f"thm:x@{s['thm:x']}, thm:y@{s['thm:y']}"))
    f = article.check()
    assert f.stats["shared_tracked"] == 1
    assert f.stats["shared_drift"] == 0


def test_a_pin_that_no_longer_matches_is_stale(article):
    article.blueprint(statement(body=BODY, label="thm:x")
                      + statement(body="It is also bounded.", label="thm:y"))
    s = shas(article)
    article.paper(paper_stmt("The kernel is smooth and bounded.",
                             f"thm:x@{s['thm:x']}, thm:y@{s['thm:y']}"))
    # the blueprint moves: thm:y now says something else
    article.blueprint(statement(body=BODY, label="thm:x")
                      + statement(body="It is unbounded.", label="thm:y"))
    (msg,) = tagged(article.check().advisory, "shared")
    assert "blueprint node(s) thm:y changed since this paper statement was pinned" in msg


def test_an_unpinned_merge_says_so_rather_than_diffing_two_texts(article):
    article.blueprint(statement(body=BODY, label="thm:x")
                      + statement(body="It is also bounded.", label="thm:y"))
    article.paper(paper_stmt("The kernel is smooth and bounded.", "thm:x, thm:y"))
    (msg,) = tagged(article.check().advisory, "shared")
    assert "pins neither text nor sha" in msg


def test_pin_shared_writes_the_shas_and_the_rerun_is_clean(article):
    article.blueprint(statement(body=BODY, label="thm:x")
                      + statement(body="It is also bounded.", label="thm:y"))
    article.paper(paper_stmt("The kernel is smooth and bounded.", "thm:x, thm:y"))

    rc, out, _ = run_cli("--root", str(article.root), "check", "--pin-shared")
    assert rc == 0
    assert "Pinned 1 marker(s) across 1 file(s)" in out

    s = shas(article)
    written = article.root.joinpath("paper/paper.tex").read_text(encoding="utf-8")
    assert f"thm:x@{s['thm:x']}, thm:y@{s['thm:y']}" in written
    assert article.check().stats["shared_tracked"] == 1


def test_pin_shared_leaves_a_verbatim_marker_alone(article):
    article.blueprint(statement(body=BODY, label="thm:x"))
    article.paper(paper_stmt(BODY, "thm:x"))
    before = article.root.joinpath("paper/paper.tex").read_text(encoding="utf-8")
    run_cli("--root", str(article.root), "check", "--pin-shared")
    assert article.root.joinpath("paper/paper.tex").read_text(encoding="utf-8") == before


def test_advisory_when_the_paper_statement_carries_a_different_label(article):
    article.blueprint(statement(body=BODY, label="thm:x"))
    article.paper(paper_stmt(BODY, "thm:x", label="thm:paper-name"))
    (msg,) = tagged(article.check().advisory, "paper")
    assert "shares blueprint 'thm:x'" in msg
    assert "rename to the blueprint label" in msg


def test_a_marker_on_prose_is_an_advisory_not_a_drift(article):
    article.blueprint(statement(body=BODY, label="thm:x"))
    article.paper("% shared with blueprint thm:x\nAs discussed above, the kernel is nice.\n")
    f = article.check()
    assert f.stats["shared_no_env"] == 1
    (msg,) = tagged(f.advisory, "paper")
    assert "precedes no statement environment" in msg


def test_a_marker_does_not_adopt_the_next_markers_statement(article):
    """A marker whose own statement was deleted must not report the following one."""
    article.blueprint(statement(body=BODY, label="thm:x")
                      + statement(body="It is also bounded.", label="thm:y"))
    article.paper("% shared with blueprint thm:x\n\n"
                  + paper_stmt("It is also bounded.", "thm:y", label="thm:y"))
    f = article.check()
    assert f.stats["shared_no_env"] == 1
    assert f.stats["shared_verbatim"] == 1
    assert f.stats["shared_drift"] == 0
