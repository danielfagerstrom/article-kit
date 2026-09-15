r"""Check 10: the two `\leanok` flags leanblueprint colours the graph from.

The statement's flag paints a node's green *border*, the proof's its green *background*.
`linkage` modelled only the first, so a node with a formalised statement and an untagged
proof painted green-on-blue — which the generated legend reads as "ready to be
formalized", i.e. not done — while the checker counted it as proved and passed.

Requested by `hemigroup-causal-scale-space-kernels` (WISHLIST, 2026-08-15). Six nodes
were affected, every one machine-checked and sorry-free, and two of them were introduced
in the session that fixed the other four: the flag is invisible at the point of writing,
because statement and proof are separate environments.
"""

from __future__ import annotations

from conftest import run_cli, tagged
from fixtures.article import statement

PROVED = "It follows from the kernel's smoothness."
LEAN = "theorem x : True := trivial\ntheorem y : True := trivial\n"


def test_a_leanok_statement_with_an_untagged_proof_is_advised(article):
    article.lean(LEAN)
    article.blueprint(statement(label="thm:x", lean="x", leanok=True, proof=PROVED))
    f = article.check()
    assert f.fatal == []
    (msg,) = tagged(f.advisory, "leanok")
    assert msg.startswith("[leanok] thm:x:")
    assert "green-bordered on BLUE" in msg


def test_both_flags_present_is_clean(article):
    article.lean(LEAN)
    article.blueprint(statement(label="thm:x", lean="x", leanok=True,
                                proof=PROVED, proof_leanok=True))
    f = article.check()
    assert tagged(f.advisory, "leanok") == [] and f.fatal == []


def test_neither_flag_present_is_clean(article):
    """An unformalised node is not the subject of this rule — check 8 owns that."""
    article.blueprint(statement(label="thm:x", proof=PROVED))
    assert tagged(article.check().advisory, "leanok") == []


def test_a_leanok_proof_under_an_untagged_statement_is_fatal(article):
    r"""The converse is incoherent, not under-reported: a formalised proof of a
    statement that is not itself formalised, painting a combination the legend has no
    reading for."""
    article.blueprint(statement(label="thm:x", proof=PROVED, proof_leanok=True))
    f = article.check()
    (msg,) = tagged(f.fatal, "leanok")
    assert "its proof carries \\leanok but its statement does not" in msg
    assert tagged(f.advisory, "leanok") == []


# --- the three exemptions ------------------------------------------------------------


def test_a_node_with_no_proof_environment_is_exempt(article):
    """Nothing to flag: it colours from the statement flag alone."""
    article.blueprint(statement(label="thm:x", lean="x", leanok=True))
    assert tagged(article.check().advisory, "leanok") == []


def test_a_definition_is_exempt(article):
    """Vocabulary, not a claim — the same exemption check 8 gives it."""
    article.lean("def x : Nat := 0\n")
    article.blueprint(statement(env="definition", label="def:x", lean="x",
                                leanok=True, proof=PROVED))
    assert tagged(article.check().advisory, "leanok") == []


def test_a_notready_node_is_exempt(article):
    """Stated but unproved by construction."""
    article.lean(LEAN)
    article.blueprint(statement(label="thm:x", lean="x", leanok=True,
                                notready=True, proof=PROVED))
    assert tagged(article.check().advisory, "leanok") == []


# --- what the parser records ---------------------------------------------------------


def test_the_proof_flag_is_read_from_the_proof_not_the_statement(article):
    article.blueprint(statement(label="thm:x", leanok=True, proof=PROVED)
                      + statement(label="thm:y", proof=PROVED, proof_leanok=True))
    x, y = article.parse().nodes
    assert (x.leanok, x.proof_leanok) == (True, False)
    assert (y.leanok, y.proof_leanok) == (False, True)


def test_the_proof_flag_does_not_leak_into_the_statement_text(article):
    r"""`\leanok` is stripped by the same normalization on both sides, so tagging a
    proof must not move any published sha."""
    plain = statement(label="thm:x", leanok=True, proof=PROVED)
    article.blueprint(plain)
    before = article.parse().nodes[0]
    article.blueprint(statement(label="thm:x", leanok=True, proof=PROVED, proof_leanok=True))
    after = article.parse().nodes[0]
    assert (after.statement, after.proof, after.shared_sha) == \
        (before.statement, before.proof, before.shared_sha)


# --- the report ----------------------------------------------------------------------


def test_the_summary_counts_both_flags(article):
    article.lean(LEAN)
    article.blueprint(statement(label="thm:x", lean="x", leanok=True,
                                proof=PROVED, proof_leanok=True)
                      + statement(label="thm:y", lean="y", leanok=True, proof=PROVED))
    rc, out, _ = run_cli("--root", str(article.root), "check")
    assert rc == 0
    assert "2 statement nodes (2 \\leanok, 1 with a \\leanok proof)" in out
