r"""Check 14: a proved node that spends a ledger entry reaches the entry's interface node.

leanblueprint paints a node fully proved when it and every `\uses` ancestor carry
`\leanok`; an axiom the Lean proof calls counts against the node only if the axiom is a
labelled node without a proof. `spatial-hemigroup-affine` (Paper VII, 2026-10-06) had no
such nodes, so all 87 proved nodes painted dark green though 41 rest on a cited fact.
Paper V's convention, now PROCESS.md section 5: each ledger entry the Lean declares gets
its own interface node (`\lean{<axiom>}\leanok`, no proof), and every node naming the
entry `\uses` it.
"""

from __future__ import annotations

from conftest import tagged
from fixtures.article import assignment, ledger_entry, statement

LEAN = """\
axiom tail_bound : True
axiom mode_bound : True
theorem spend_a1 : True := tail_bound
theorem spend_a2 : True := mode_bound
theorem deeper : True := spend_a1
"""

AXIOMS = "# Axiom ledger\n\n" + ledger_entry("A1") + ledger_entry("A2")


def interface(label: str, aid: str, lean: str) -> str:
    """The interface node: the entry's statement as used, \\leanok, no proof."""
    return statement(label=label, lean=lean, leanok=True, status="A", ledger=(aid,),
                     note=assignment(rf"\ledger{{{aid}}} carries all of it."))


def spender(label: str, aid: str, lean: str, uses: tuple[str, ...] = ()) -> str:
    """An [A] node naming the entry on its status line, with a sorry-free proof."""
    return statement(label=label, lean=lean, leanok=True, uses=uses, status="A",
                     ledger=(aid,), proof="By the cited bound.", proof_leanok=True,
                     note=assignment(rf"\ledger{{{aid}}} carries the bound; the rest is [T]."))


def check(article, tex: str):
    article.lean(LEAN)
    article.axioms(AXIOMS)
    article.blueprint(tex)
    return article.check()


def test_a_spender_that_uses_its_interface_node_is_clean(article):
    f = check(article, interface("prop:tail", "A1", "tail_bound")
              + spender("lem:a", "A1", "spend_a1", uses=("prop:tail",)))
    assert f.fatal == []
    assert tagged(f.advisory, "iface") == []


def test_an_entry_with_no_interface_node_is_advised_not_fatal(article):
    f = check(article, interface("prop:tail", "A1", "tail_bound")
              + spender("lem:a", "A1", "spend_a1", uses=("prop:tail",))
              + spender("lem:b", "A2", "spend_a2"))
    assert f.fatal == []
    (msg,) = tagged(f.advisory, "iface")
    assert msg.startswith("[iface]  lem:b:")
    assert "\\ledger{A2}" in msg
    assert "add a node stating A2" in msg


def test_an_interface_node_not_used_names_the_node_to_use(article):
    f = check(article, interface("prop:tail", "A1", "tail_bound")
              + spender("lem:a", "A1", "spend_a1"))
    (msg,) = tagged(f.advisory, "iface")
    assert msg.startswith("[iface]  lem:a:")
    assert "\\uses prop:tail" in msg


def test_the_interface_node_may_be_a_transitive_ancestor(article):
    f = check(article, interface("prop:tail", "A1", "tail_bound")
              + spender("lem:a", "A1", "spend_a1", uses=("prop:tail",))
              + spender("lem:c", "A1", "deeper", uses=("lem:a",)))
    assert tagged(f.advisory, "iface") == []


def test_a_node_with_a_proof_is_not_an_interface_node(article):
    r"""Two spenders of A1 that \uses each other: neither has no proof, so neither is it."""
    f = check(article, spender("lem:a", "A1", "spend_a1")
              + spender("lem:c", "A1", "deeper", uses=("lem:a",)))
    assert [m.split()[1] for m in tagged(f.advisory, "iface")] == ["lem:a:", "lem:c:"]


def test_a_t_node_mentioning_an_entry_in_prose_is_not_the_subject(article):
    r"""`Node.ledger` holds every \ledger{} in the body; a [T] node's are commentary
    ("cites nothing ... \ledger{A2}'s territory"), as six were on Paper VII after #82."""
    f = check(article, statement(label="lem:a", lean="spend_a1", leanok=True,
                                 proof="Direct.", proof_leanok=True,
                                 note=r"Cites nothing; \ledger{A2}'s territory."))
    assert tagged(f.advisory, "iface") == []


def test_a_t_node_without_a_proof_is_not_an_interface_node(article):
    r"""A [T] definition whose note mentions A1 does not ground A1's spenders."""
    f = check(article, statement(env="definition", label="def:d", lean="spend_a1",
                                 leanok=True, note=r"Vocabulary; read with \ledger{A1}.")
              + spender("lem:a", "A1", "deeper", uses=("def:d",)))
    (msg,) = tagged(f.advisory, "iface")
    assert msg.startswith("[iface]  lem:a:")
    assert "add a node stating A1" in msg


def test_an_unproved_spender_is_not_the_subject(article):
    r"""Not \leanok: the graph does not paint it proved, so nothing is over-reported."""
    f = check(article, statement(label="lem:a", status="A", ledger=("A2",),
                                 proof="By the cited bound.",
                                 note=assignment(r"\ledger{A2} carries all of it.")))
    assert tagged(f.advisory, "iface") == []
