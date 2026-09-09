"""What `linkage check` does NOT catch, written as the tests it would pass if it did.

Every test here is `xfail(strict=True)`: it fails the day the gap is closed, which is
the point — a blind spot recorded as a passing test that asserts the wrong behaviour is
a blind spot nobody ever removes, and one recorded only in a ROADMAP is one nobody sees
while editing the checks.

None of these is a crash or a wrong answer on a well-formed article. They are all the
same shape: a *malformed* blueprint that the checks read as well-formed, so the guarantee
they publish (`\\leanok` means proved, the manifest is the blueprint) is weaker than it
looks. Closing one is a new rule in `docs/LINKAGE.md`, not a patch — hence a record here
rather than a fix.
"""

from __future__ import annotations

import pytest

from fixtures.article import ledger_entry, statement

pytestmark = pytest.mark.xfail(strict=True, reason="documented blind spot — see the docstring")


def findings(article) -> str:
    f = article.check()
    return "\n".join(f.fatal + f.advisory)


def test_a_cyclic_uses_graph_is_reported(article):
    r"""Recorded 2026-09-07 (hcs): a forward `\uses` from a bridge node made the
    dependency graph cyclic, and nothing said so. `uses_paths` terminates on it — the
    visited set sees to that — so the cycle is invisible rather than fatal, and the
    dependency invariant it silently weakens (rule 8) is the trust story's structure.
    """
    article.blueprint(
        statement(label="thm:a", lean="A.a", leanok=True, uses=("thm:b",))
        + statement(label="thm:b", lean="A.b", leanok=True, uses=("thm:a",))
    )
    article.lean("theorem a : True := trivial\ntheorem b : True := trivial\n")
    assert "cycle" in findings(article).lower()


def test_a_uses_edge_naming_no_blueprint_label_is_reported(article):
    r"""A typo'd `\uses{thm:kernal-smooth}` names nothing, so the walk of rule 8 crosses
    no edge there — the dependency invariant passes *because* the edge is broken. Rule 1
    checks `\lean{}` against Lean and rule 4 checks the paper's labels against the
    blueprint; the blueprint's own internal edges are checked against nothing.
    """
    article.blueprint(statement(label="thm:a", lean="A.a", leanok=True,
                                uses=("thm:no-such-node",)))
    article.lean("theorem a : True := trivial\n")
    assert "thm:no-such-node" in findings(article)


def test_two_nodes_sharing_a_label_are_reported(article):
    """`Blueprint.by_label` keeps the last, so a duplicated label silently drops a node
    from the graph and from the manifest the hub reads — while `bp.nodes` still holds
    both, which is why the checks see no contradiction."""
    article.blueprint(statement(label="thm:a", body="One thing.")
                      + statement(label="thm:a", body="A different thing."))
    assert "thm:a" in findings(article)


def test_a_ledger_reference_inside_a_comment_is_not_a_reference(article):
    r"""`ledger_refs` scans the whole document text, comments included, so a `\ledger{A9}`
    in an explanatory comment is a reference that must resolve. Real blueprints do write
    them: hcs' `04-representation.tex` and `08-examples-moments.tex` both discuss
    `\ledger{}` entries in comments, and the day one names a retired id the build fails
    on a line that is not code.
    """
    article.blueprint(statement(label="thm:x")
                      + "\n% A9 was considered here as \\ledger{A9} and rejected.\n")
    assert findings(article) == ""


def test_a_commented_out_statement_environment_is_not_a_node(article):
    """Commenting a node out is how an author parks one. The environment scan does not
    strip comments first, so the parked node keeps its label, its status and its `\\uses`
    edges — it is projected into the manifest and walked by rule 8 exactly as if it were
    live."""
    live = statement(label="thm:x")
    parked = "\n".join("% " + ln for ln in statement(label="thm:parked").splitlines())
    article.blueprint(live + parked + "\n")
    assert set(article.parse().labels) == {"thm:x"}


def test_an_A_node_may_not_carry_a_ledger_entry_that_does_not_exist(article):
    """Rule 7 is satisfied by *shape*: the Assignment clause must match `ledger_key`, not
    name an entry that exists. `\\textbf{Assignment.} A99 carries it.` passes while A99 is
    nothing — the very silent case ADR-0011 was written to remove."""
    article.blueprint(statement(label="thm:x", status="A", ledger=("A1",),
                                note=r"\textbf{Assignment.} A99 carries the tail bound."))
    article.axioms(ledger_entry("A1"))
    assert "A99" in findings(article)
