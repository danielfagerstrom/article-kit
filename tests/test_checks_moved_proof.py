r"""Rule 4 / check 3d: a proof moved off its statement is still matched and compared.

Paper VII (`spatial-hemigroup-affine`, PR #45) moved most proofs of §3-§5 into
appendices, each headed "Proof of Proposition~\ref{...}" with the statement left in the
main text, as journals expect of a long paper. Before this, `linkage check` only ever
looked *right after* the marked statement, so a moved proof was silently unmatched: the
drift check's coverage dropped from 18 compared proofs to 4 and nothing said so
(WISHLIST, 2026-10-04). The fixture below is that move, reduced.
"""

from __future__ import annotations

from conftest import run_cli, tagged
from fixtures.article import statement

STMT = "The kernel transform is injective on the positive cone."
PROOF_OF_RECORD = (r"By \ref{lem:transform-positive}, the transform is positive; "
                   r"injectivity follows from \ref{lem:inversion}.")
LEMMAS = (statement(label="lem:transform-positive", body="Transforms are positive.")
          + statement(label="lem:inversion", body="Inversion is positive."))


def blueprint(article, proof: str | None = PROOF_OF_RECORD):
    return article.blueprint(LEMMAS + statement(
        body=STMT, label="prop:injective", env="proposition", proof=proof))


def main_text(marker: str = "prop:injective") -> str:
    return (
        f"% shared with blueprint {marker}\n"
        f"\\begin{{proposition}}\n  \\label{{prop:injective}}\n  {STMT}\n"
        "\\end{proposition}\n\nThe proof is in Appendix~\\ref{app:a}.\n"
    )


def moved_proof(heading: str = r"[Proof of Proposition~\ref{prop:injective}]",
               body: str = PROOF_OF_RECORD) -> str:
    return f"\\begin{{proof}}{heading}\n{body}\n\\end{{proof}}\n"


# --- matched by heading ------------------------------------------------------------

def test_a_proof_moved_to_an_appendix_is_matched_by_its_heading_ref(article):
    blueprint(article)
    article.paper(main_text(), name="05-results.tex")
    article.paper(moved_proof(), name="appendix.tex")
    f = article.check()
    assert tagged(f.advisory, "proof") == []
    assert f.stats["proof_verbatim"] == 1
    assert f.stats["proof_unmatched"] == 0


def test_a_sketch_suffix_after_the_ref_does_not_break_the_match(article):
    blueprint(article)
    article.paper(main_text(), name="05-results.tex")
    article.paper(
        moved_proof(heading=r"[Proof of Proposition~\ref{prop:injective} (sketch)]"),
        name="appendix.tex")
    f = article.check()
    assert tagged(f.advisory, "proof") == []
    assert f.stats["proof_verbatim"] == 1


def test_the_matched_proof_drops_its_heading_before_comparison(article):
    """The heading itself must not leak into the compared text -- an adjacent proof
    never carries one, so the heading would read as permanent drift otherwise."""
    blueprint(article)
    article.paper(main_text(), name="05-results.tex")
    article.paper(moved_proof(), name="appendix.tex")
    f = article.check()
    assert f.stats["proof_verbatim"] == 1  # not proof_drift


def test_a_stale_matched_proof_is_advised_like_the_adjacent_case(article):
    blueprint(article)
    n = article.parse().by_label["prop:injective"]
    article.paper(f"% shared with blueprint prop:injective@{n.shared_sha}"
                  f"+{n.shared_proof_sha}\n"
                  f"\\begin{{proposition}}\n  \\label{{prop:injective}}\n  {STMT}\n"
                  "\\end{proposition}\n", name="05-results.tex")
    article.paper(moved_proof(), name="appendix.tex")
    blueprint(article, "A repaired argument, routed differently.")
    f = article.check()
    (msg,) = tagged(f.advisory, "proof")
    assert "changed since this paper's proof was pinned" in msg
    assert f.stats["proof_drift"] == 1


# --- matched by the `% proof of <label>` marker -------------------------------------

def test_an_explicit_marker_matches_a_proof_with_no_heading(article):
    blueprint(article)
    article.paper(main_text(), name="05-results.tex")
    article.paper(f"% proof of prop:injective\n{moved_proof(heading='')}", name="appendix.tex")
    f = article.check()
    assert tagged(f.advisory, "proof") == []
    assert f.stats["proof_verbatim"] == 1


def test_the_explicit_marker_takes_priority_over_a_heading_ref(article):
    """Belt and suspenders: when both are present, they must not disagree silently --
    the marker is authoritative, mirroring every other marker in this file."""
    blueprint(article)
    article.paper(main_text(), name="05-results.tex")
    article.paper(
        "% proof of prop:injective\n"
        + moved_proof(heading=r"[Proof of Proposition~\ref{prop:injective}]"),
        name="appendix.tex")
    f = article.check()
    assert tagged(f.advisory, "proof") == []
    assert f.stats["proof_verbatim"] == 1


# --- not matched ---------------------------------------------------------------------

def test_two_refs_in_the_heading_is_not_a_match(article):
    blueprint(article)
    article.paper(main_text(), name="05-results.tex")
    article.paper(
        moved_proof(heading=r"[Proof of Proposition~\ref{prop:injective}, "
                            r"cf.~\ref{lem:inversion}]"),
        name="appendix.tex")
    f = article.check()
    (msg,) = tagged(f.advisory, "proof")
    assert "neither adjacent" in msg
    assert f.stats["proof_unmatched"] == 1


def test_a_heading_naming_a_different_label_does_not_match(article):
    blueprint(article)
    article.paper(main_text(), name="05-results.tex")
    article.paper(
        moved_proof(heading=r"[Proof of Lemma~\ref{lem:inversion}]"),
        name="appendix.tex")
    f = article.check()
    assert tagged(f.advisory, "proof")[0]
    assert f.stats["proof_unmatched"] == 1


# --- --pin-shared works for a matched proof, same as the adjacent case --------------

def test_pin_shared_pins_a_matched_proof(article):
    blueprint(article)
    stmt_sha = article.parse().by_label["prop:injective"].shared_sha
    article.paper(f"% shared with blueprint prop:injective@{stmt_sha}\n"
                  f"\\begin{{proposition}}\n  \\label{{prop:injective}}\n  {STMT}\n"
                  "\\end{proposition}\n", name="05-results.tex")
    article.paper(moved_proof(body="A shorter argument for the reader."), name="appendix.tex")
    rc, out, _ = run_cli("--root", str(article.root), "check", "--pin-shared")
    assert rc == 0 and "(1 with a proof sha)" in out
    written = article.root.joinpath("paper/05-results.tex").read_text(encoding="utf-8")
    n = article.parse().by_label["prop:injective"]
    assert f"prop:injective@{stmt_sha}+{n.shared_proof_sha}" in written
    f = article.check()
    assert tagged(f.advisory, "proof") == []
    assert f.stats["proof_tracked"] == 1
