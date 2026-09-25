r"""Rule 11: what a `\leanok` node's declaration cites, against what it `\uses{}`.

Fixtures, not a Lean build — the audit reads source text (or an exported constant map), so
the suite can exercise both routes with a three-line `Main.lean`. The Lean here is
deliberately trivial as mathematics; what each test varies is *which names appear in which
declaration's body*, since that is the whole input to the inference.
"""

from __future__ import annotations

from conftest import run_cli, tagged
from fixtures.article import statement

# lem:a is proved, thm:x is proved and its Lean proof calls `a`. The blueprint of each test
# says something different about that edge.
LEAN_X_USES_A = """\
theorem a : True := trivial

theorem x : True := by
  exact a
"""


def bp(*nodes: str) -> str:
    return "\n".join(nodes)


def lemma(label: str, decl: str, **kw) -> str:
    return statement(env="lemma", label=label, lean=decl, leanok=True,
                     proof="Immediate.", proof_leanok=True, **kw)


def theorem(label: str, decl: str, **kw) -> str:
    return statement(env="theorem", label=label, lean=decl, leanok=True,
                     proof="From the lemma.", proof_leanok=True, **kw)


# --- the scan ----------------------------------------------------------------------------


def test_the_scan_indexes_namespaced_declarations_and_what_they_cite(article):
    article.lean("""\
namespace Kern

theorem a : True := trivial

theorem b : True := by
  exact a

end Kern

theorem c : True := Kern.b
""")
    from linkage import closure

    index = closure.scan_lean(article.cfg)
    assert set(index.module) == {"Kern.a", "Kern.b", "c"}
    assert index.direct["Kern.b"] == {"Kern.a"}
    assert index.direct["c"] == {"Kern.b"}
    assert index.closure("c") == {"Kern.b", "Kern.a"}


def test_a_name_in_a_comment_is_not_a_use(article):
    article.lean("""\
theorem a : True := trivial

/- the old proof went through a -/
theorem x : True := by
  -- exact a
  trivial
""")
    from linkage import closure

    assert closure.scan_lean(article.cfg).direct["x"] == set()


# --- direction 1: declared, not inferred -------------------------------------------------


def test_a_uses_target_the_declaration_never_cites_is_advised(article):
    """A partial mismatch: the Lean proof rests on one of the two cited nodes."""
    article.lean("""\
theorem a : True := trivial

theorem b : True := trivial

theorem x : True := b
""")
    article.blueprint(bp(lemma("lem:a", "a"), lemma("lem:b", "b"),
                         theorem("thm:x", "x", uses=("lem:a", "lem:b"))))
    (msg,) = tagged(article.closure().advisory, "declared")
    assert msg.startswith("[declared] thm:x: \\uses{lem:a}")
    assert "not in the inferred closure of x" in msg


def test_a_uses_target_reached_transitively_is_supported(article):
    """The Lean proof may reach a cited ingredient through a helper the blueprint has no
    node for; that is a route, not a finding."""
    article.lean("""\
theorem a : True := trivial

theorem helper : True := a

theorem x : True := helper
""")
    article.blueprint(bp(lemma("lem:a", "a"), theorem("thm:x", "x", uses=("lem:a",))))
    assert tagged(article.closure().advisory, "declared") == []


def test_a_uses_target_with_no_lean_tag_is_not_advised(article):
    r"""An `[A]` or untagged node has no declaration to look for — f7sweep's
    `uses-[A]/untagged` column, which this audit leaves to the reader rather than flagging."""
    article.lean("theorem x : True := trivial\n")
    article.blueprint(bp(
        statement(env="lemma", label="lem:cited", body="Cited.", status="A",
                  ledger=("A1",), note=r"\textbf{Assignment.} \ledger{A1} carries it."),
        theorem("thm:x", "x", uses=("lem:cited",))))
    assert tagged(article.closure().advisory, "declared") == []


# --- direction 2: inferred, not declared -------------------------------------------------


def test_a_declaration_citing_a_node_no_uses_path_reaches_is_advised(article):
    article.lean(LEAN_X_USES_A)
    article.blueprint(bp(lemma("lem:a", "a"), theorem("thm:x", "x")))
    (msg,) = tagged(article.closure().advisory, "inferred")
    assert msg.startswith("[inferred] thm:x: x cites a (lem:a)")
    assert "add \\uses{lem:a}" in msg


def test_an_indirect_uses_path_covers_an_inferred_dependency(article):
    r"""`\uses{}` records direct edges, so a dependency the blueprint reaches through
    another node is legitimately absent from this node's own list."""
    article.lean("""\
theorem a : True := trivial

theorem b : True := a

theorem x : True := by
  exact a
""")
    article.blueprint(bp(lemma("lem:a", "a"),
                         lemma("lem:b", "b", uses=("lem:a",)),
                         theorem("thm:x", "x", uses=("lem:b",))))
    assert tagged(article.closure().advisory, "inferred") == []


def test_a_node_that_is_not_leanok_is_not_audited(article):
    article.lean(LEAN_X_USES_A)
    article.blueprint(bp(lemma("lem:a", "a"),
                         statement(env="theorem", label="thm:x", lean="x", notready=True,
                                   proof="From the lemma.")))
    a = article.closure()
    assert tagged(a.advisory, "inferred") == [] and a.stats["audited"] == 1


# --- the two flags -----------------------------------------------------------------------


def test_a_proved_node_whose_declaration_cites_nothing_of_ours_is_flagged(article):
    article.lean("""\
theorem a : True := trivial

theorem b : True := trivial

theorem x : True := trivial
""")
    article.blueprint(bp(lemma("lem:a", "a"), lemma("lem:b", "b"),
                         theorem("thm:x", "x", uses=("lem:a", "lem:b"))))
    a = article.closure()
    (msg,) = tagged(a.advisory, "empty")
    assert "thm:x: \\leanok, but x cites no declaration of this article" in msg
    assert "\\uses 2 formalised node(s) (lem:a, lem:b)" in msg
    # one finding per node, not one per \uses target: they have a single cause
    assert tagged(a.advisory, "declared") == []
    assert a.stats["empty"] == ["thm:x"]


def test_a_leaf_lemma_that_rests_on_nothing_of_ours_is_not_flagged(article):
    """Proved from Mathlib alone, and saying so: the two accounts agree that this node
    rests on nothing of this article's."""
    article.lean("theorem a : True := trivial\n")
    article.blueprint(lemma("lem:a", "a"))
    assert tagged(article.closure().advisory, "empty") == []


def test_a_definition_citing_nothing_is_not_flagged(article):
    """Definitions are vocabulary — check 8 exempts them as targets, and a definition that
    rests on nothing is the ordinary case, not an implausible one."""
    article.lean("def d : Nat := 0\ndef e : Nat := 1\n")
    article.blueprint(bp(
        statement(env="definition", label="def:e", lean="e", leanok=True,
                  body="The other constant.", status="T"),
        statement(env="definition", label="def:d", lean="d", leanok=True,
                  uses=("def:e",), body="The constant.", status="T")))
    assert tagged(article.closure().advisory, "empty") == []


def test_a_lemma_nothing_depends_on_is_flagged(article):
    article.lean("""\
theorem orphan : True := trivial

theorem x : True := trivial
""")
    article.blueprint(bp(lemma("lem:orphan", "orphan"), theorem("thm:x", "x")))
    a = article.closure()
    (msg,) = tagged(a.advisory, "orphan")
    assert msg.startswith("[orphan]  lem:orphan: no blueprint node \\uses it")
    assert a.stats["orphans"] == ["lem:orphan"]


def test_a_lemma_cited_only_in_lean_is_not_an_orphan(article):
    """Used by nothing means by neither graph: the `\\uses` edge is missing (direction 2
    says so), but the lemma is load-bearing."""
    article.lean(LEAN_X_USES_A)
    article.blueprint(bp(lemma("lem:a", "a"), theorem("thm:x", "x")))
    assert tagged(article.closure().advisory, "orphan") == []


def test_a_theorem_nothing_depends_on_is_not_an_orphan(article):
    """The ordinary shape of a headline result."""
    article.lean("theorem x : True := trivial\n")
    article.blueprint(theorem("thm:x", "x"))
    assert tagged(article.closure().advisory, "orphan") == []


# --- the export route --------------------------------------------------------------------


def test_the_export_is_believed_over_the_source_scan(article):
    r"""The point of the export: a use through a `simp` set names nothing at the use site,
    so the scan reports a false `[declared]` gap that the elaborated map does not."""
    article.lean("""\
@[simp] theorem a : True := trivial

theorem b : True := trivial

theorem x : True := by
  simp [b]
""")
    article.blueprint(bp(lemma("lem:a", "a"), lemma("lem:b", "b"),
                         theorem("thm:x", "x", uses=("lem:a", "lem:b"))))
    assert tagged(article.closure().advisory, "declared")  # the scan's false positive
    article.lean_uses({"x": ["a", "b"], "a": [], "b": []})
    assert tagged(article.closure().advisory, "declared") == []


def test_a_malformed_export_is_a_tooling_error_not_a_finding(article):
    article.lean("theorem x : True := trivial\n")
    article.file("Formalization/lean-uses.json", '{"x": "a"}')
    rc, _out, err = run_cli("--root", str(article.root), "closure")
    assert rc == 2 and "CLOSURE INPUT ERROR" in err


# --- unlocatable declarations ------------------------------------------------------------


def test_a_declaration_the_audit_cannot_read_is_reported_not_inferred(article):
    r"""A `\lean{}` pointing into a shared Lake package: check 1 accepts it (the package is
    scanned for names), this audit cannot read its body, and says so instead of scoring the
    node as citing nothing."""
    article.lean("theorem x : True := trivial\n")
    article.blueprint(bp(theorem("thm:x", "x"),
                         theorem("thm:elsewhere", "Shared.thing")))
    a = article.closure()
    (msg,) = tagged(a.advisory, "closure")
    assert "thm:elsewhere" in msg and "Shared.thing" in msg
    assert a.stats["unlocatable"] == ["thm:elsewhere"]
    assert tagged(a.advisory, "empty") == []  # not scored as citing nothing


# --- the command -------------------------------------------------------------------------


def test_the_command_reports_a_seeded_gap_and_a_seeded_orphan_and_exits_zero(article):
    """The end-to-end shape: an article with a missing `\\uses` edge and an unused lemma."""
    article.lean("""\
theorem a : True := trivial

theorem orphan : True := trivial

theorem x : True := by
  exact a
""")
    article.blueprint(bp(lemma("lem:a", "a"),
                         lemma("lem:orphan", "orphan"),
                         theorem("thm:x", "x")))
    rc, out, _err = run_cli("--root", str(article.root), "closure")
    assert rc == 0
    assert "3 \\leanok node(s) with a \\lean{} tag audited" in out
    assert "[inferred] thm:x: x cites a (lem:a)" in out
    assert "[orphan]  lem:orphan" in out
    assert "1 inferred dependenc(ies) no \\uses path reaches" in out
    assert "1 lemma(s) used by nothing" in out


def test_the_command_speaks_json(article):
    import json

    article.lean(LEAN_X_USES_A)
    article.blueprint(bp(lemma("lem:a", "a"), theorem("thm:x", "x")))
    rc, out, _err = run_cli("--root", str(article.root), "closure", "--json")
    doc = json.loads(out)
    assert rc == 0 and doc["route"] == "source scan" and doc["inferred_gaps"] == 1


def test_an_explicit_export_path_that_does_not_exist_fails(article):
    article.lean("theorem x : True := trivial\n")
    rc, _out, err = run_cli("--root", str(article.root), "closure", "--export", "nope.json")
    assert rc == 2 and "no such file" in err
