"""Rule 3d: has the blueprint's proof moved away from the one the paper prints?

The statement pin (`@<sha12>`) covers the statement only, and the paper transcribes the
proof beneath it by hand. Module C of `spatial-hemigroup-scale-space` (2026-09-27) sent
an external referee a proof the blueprint had repaired five days earlier: the converse of
a signed-data corollary, whose printed step was circular. The fixture pair below is that
case, reduced: the same paper against the blueprint before and after the repair.
"""

from __future__ import annotations

from conftest import run_cli, tagged
from fixtures.article import statement
from linkage import artifacts

CONVERSE = (r"If the signed datum $f$ has a nonnegative kernel transform, "
            r"then $f$ is nonnegative.")
# The proof of record as the paper transcribed it: its second step assumes the conclusion.
CIRCULAR = (r"By \ref{lem:transform-positive}, the transform of $f$ is nonnegative; "
            r"since $f$ is nonnegative, the kernel representation inverts it.")
# The blueprint's repair, made after the statement had last been verified and pinned.
REPAIRED = (r"By \ref{lem:transform-positive}, the transform of $f$ is nonnegative; "
            r"by \ref{lem:inversion}, the inverse transform preserves nonnegativity, "
            r"so $f$ is nonnegative.")
LEMMAS = (statement(label="lem:transform-positive", body="Transforms are positive.")
          + statement(label="lem:inversion", body="Inversion is positive."))


def blueprint(article, proof: str | None, **kw):
    return article.blueprint(LEMMAS + statement(
        body=CONVERSE, label="cor:converse", env="corollary", proof=proof, **kw))


def paper(article, marker: str, proof: str | None = CIRCULAR):
    return article.paper(
        f"% shared with blueprint {marker}\n"
        f"\\begin{{corollary}}\n  \\label{{cor:converse}}\n  {CONVERSE}\n\\end{{corollary}}\n"
        + (f"\\begin{{proof}}\n{proof}\n\\end{{proof}}\n" if proof is not None else ""))


def node(article, label: str = "cor:converse"):
    return article.parse().by_label[label]


def module_c(article, repaired: bool):
    """The paper written, verified and pinned against CIRCULAR; then, or not, the repair."""
    blueprint(article, CIRCULAR)
    n = node(article)
    paper(article, f"cor:converse@{n.shared_sha}+{n.shared_proof_sha}")
    if repaired:
        blueprint(article, REPAIRED)
    return article


# --- the fixture pair -------------------------------------------------------------

def test_a_proof_repaired_after_the_pin_is_advised(article):
    f = module_c(article, repaired=True).check()
    (msg,) = tagged(f.advisory, "proof")
    assert "paper/paper.tex:1" in msg
    assert "blueprint proof of cor:converse changed since this paper's proof was pinned" in msg
    assert f.stats["proof_drift"] == 1
    # the statement did not move, so its own check is silent
    assert f.stats["shared_verbatim"] == 1 and f.stats["shared_drift"] == 0
    assert f.ok


def test_an_unchanged_proof_is_silent(article):
    f = module_c(article, repaired=False).check()
    assert tagged(f.advisory, "proof") == []
    # verbatim takes precedence over the pin, as for statements
    assert f.stats["proof_verbatim"] == 1 and f.stats["proof_drift"] == 0


# --- advisory only ------------------------------------------------------------------

def test_the_advisory_never_fails_the_check_even_under_strict_shared(article):
    module_c(article, repaired=True)
    f = article.check(strict_shared=True)
    assert f.fatal == [] and len(tagged(f.advisory, "proof")) == 1
    rc, out, _ = run_cli("--root", str(article.root), "check", "--strict-shared")
    assert rc == 0
    assert "advisory [proof]" in out
    assert "shared proofs: 1 compared (0 verbatim, 0 tracked by sha, 1 to re-read)" in out


# --- the unpinned states --------------------------------------------------------------

def test_a_transcription_differing_only_in_bookkeeping_and_ref_style_is_verbatim(article):
    r"""`\leanok`, `\uses{}` and `\lean{}` are the blueprint's; the paper drops them, and
    writes `Lemma~\ref` or `\cref` where the blueprint writes `\ref`."""
    blueprint(article, r"\uses{lem:transform-positive,lem:inversion} " + REPAIRED,
              proof_leanok=True)
    paper(article, "cor:converse", REPAIRED
          .replace(r"By \ref{lem:transform-positive}", r"By Lemma~\ref{lem:transform-positive}")
          .replace(r"by \ref{lem:inversion}", r"by \cref{lem:inversion}"))
    f = article.check()
    assert tagged(f.advisory, "proof") == []
    assert f.stats["proof_verbatim"] == 1
    assert f.proof_unpinned == []


def test_an_unpinned_proof_that_differs_says_where(article):
    blueprint(article, REPAIRED)
    paper(article, "cor:converse", CIRCULAR)
    f = article.check()
    (msg,) = tagged(f.advisory, "proof")
    assert "drifted from the blueprint after" in msg
    assert r"paper     : since $f$ is nonnegative" in msg
    assert "pin it with `linkage check --pin-shared`" in msg
    assert [m.line for m in f.proof_unpinned] == [1]


def test_no_blueprint_proof_is_silent(article):
    """Nothing on the blueprint side to lose coverage of."""
    blueprint(article, None)
    paper(article, "cor:converse", CIRCULAR)
    f = article.check()
    assert tagged(f.advisory, "proof") == []
    assert f.stats["proof_verbatim"] + f.stats["proof_tracked"] + f.stats["proof_drift"] == 0
    assert f.stats["proof_unmatched"] == 0


def test_no_paper_proof_and_nothing_matched_is_reported_unmatched(article):
    """A blueprint proof of record with no paper proof anywhere -- not adjacent, and
    nothing elsewhere in the paper resolves to this label -- is the silent loss of
    coverage rule 4 now surfaces, rather than being indistinguishable from "proved
    elsewhere on purpose"."""
    blueprint(article, REPAIRED)
    paper(article, "cor:converse", proof=None)
    f = article.check()
    (msg,) = tagged(f.advisory, "proof")
    assert "paper/paper.tex:1 cor:converse" in msg
    assert "neither adjacent" in msg and "nor matched" in msg
    assert "% proof omitted" in msg
    assert f.stats["proof_unmatched"] == 1
    assert f.ok


def test_proof_omitted_opts_out_of_the_unmatched_advisory(article):
    blueprint(article, REPAIRED)
    article.paper(
        "% shared with blueprint cor:converse\n"
        f"\\begin{{corollary}}\n  \\label{{cor:converse}}\n  {CONVERSE}\n\\end{{corollary}}\n"
        "% proof omitted\n")
    f = article.check()
    assert tagged(f.advisory, "proof") == []
    assert f.stats["proof_unmatched"] == 0


# --- the escape hatch: --pin-shared ------------------------------------------------------

def test_pin_shared_pins_a_proof_meant_to_differ_and_keeps_the_statement_pin(article):
    blueprint(article, REPAIRED)
    stmt = node(article).shared_sha
    paper(article, f"cor:converse@{stmt}", "A shorter argument for the reader.")
    rc, out, _ = run_cli("--root", str(article.root), "check", "--pin-shared")
    assert rc == 0 and "(1 with a proof sha)" in out
    written = article.root.joinpath("paper/paper.tex").read_text(encoding="utf-8")
    assert f"cor:converse@{stmt}+{node(article).shared_proof_sha}" in written
    f = article.check()
    assert tagged(f.advisory, "proof") == []
    assert f.stats["proof_tracked"] == 1 and f.stats["shared_drift"] == 0


def test_pin_shared_repins_a_stale_proof(article):
    module_c(article, repaired=True)
    run_cli("--root", str(article.root), "check", "--pin-shared")
    assert tagged(article.check().advisory, "proof") == []


def test_statement_pinning_keeps_an_existing_proof_pin(article):
    """A merged statement pinned for the first time must not lose its proof's pin."""
    blueprint(article, REPAIRED)
    psha = node(article).shared_proof_sha
    article.paper(
        f"% shared with blueprint cor:converse+{psha}, lem:inversion\n"
        "\\begin{corollary}\n  The datum is nonnegative, and inversion is positive.\n"
        "\\end{corollary}\n")
    run_cli("--root", str(article.root), "check", "--pin-shared")
    (mk,) = artifacts.paper_markers(article.cfg)
    assert mk.proof_pinned == {"cor:converse": psha}
    assert set(mk.pinned) == {"cor:converse", "lem:inversion"}


def test_a_proof_pin_parses_in_a_list_without_eating_the_next_label(article):
    blueprint(article, REPAIRED)
    article.paper("% shared with blueprint cor:converse@0123456789ab+ba9876543210, "
                  "lem:inversion\n\\begin{corollary}\n  Text.\n\\end{corollary}\n")
    (mk,) = artifacts.paper_markers(article.cfg)
    assert mk.blueprint_labels == ["cor:converse", "lem:inversion"]
    assert mk.pinned == {"cor:converse": "0123456789ab"}
    assert mk.proof_pinned == {"cor:converse": "ba9876543210"}
