"""The nine fatal rules of `checks.run`, each fired and each kept silent.

One test pair per rule is the point of this suite. A check that only ever runs over a
clean tree proves that it does not crash; the direction that matters — that it *fires*
on the defect it was written for, and that a correct article does not trip it — is only
established by having both fixtures side by side.

The rule numbering is `docs/LINKAGE.md` § The checker (and the module docstring of
`linkage/checks.py`); the `[tag]` opening each message is what a test selects on.
"""

from __future__ import annotations

from conftest import tagged
from fixtures.article import assignment, ledger_entry, statement


def only(f, tag: str) -> list[str]:
    return tagged(f.fatal, tag)


def test_a_clean_article_has_no_findings_at_all(article):
    """The floor every other test stands on: the default fixture fires nothing."""
    article.blueprint(statement(label="thm:x"))
    f = article.check()
    assert f.fatal == []
    assert f.advisory == []
    assert f.ok


# --- rule 1: a \leanok node's \lean{} names a real declaration ------------------------


def test_rule1_fires_when_the_lean_declaration_does_not_exist(article):
    article.blueprint(statement(label="thm:x", lean="Article.kernel_smooth", leanok=True))
    article.lean("theorem something_else : True := trivial\n")
    msgs = only(article.check(), "lean")
    assert len(msgs) == 1
    assert "kernel_smooth" in msgs[0]


def test_rule1_silent_when_the_declaration_exists(article):
    article.blueprint(statement(label="thm:x", lean="Article.kernel_smooth", leanok=True))
    article.lean("theorem kernel_smooth : True := trivial\n")
    assert only(article.check(), "lean") == []


def test_rule1_matches_on_the_final_component_only(article):
    """`\\lean{A.b.c}` resolves against `c` — namespaces are not reconstructed."""
    article.blueprint(statement(label="thm:x", lean="Whatever.Namespace.smooth", leanok=True))
    article.lean("theorem smooth : True := trivial\n")
    assert only(article.check(), "lean") == []


def test_rule1_does_not_apply_to_an_unproved_node(article):
    """A \\notready node may name a declaration that does not exist yet."""
    article.blueprint(statement(label="thm:x", lean="Article.later", notready=True))
    assert only(article.check(), "lean") == []


# --- rule 2: every \ledger{} reference resolves to an AXIOMS.md entry ------------------


def test_rule2_fires_on_an_unresolved_ledger_reference(article):
    article.blueprint(statement(label="thm:x", status="A", ledger=("A7",),
                                note=assignment(r"\ledger{A7} carries it.")))
    msgs = only(article.check(), "ledger")
    assert len(msgs) == 1
    assert "A7" in msgs[0] and "no '## A7' entry" in msgs[0]


def test_rule2_silent_when_the_entry_exists(article):
    article.blueprint(statement(label="thm:x", status="A", ledger=("A1",),
                                note=assignment()))
    article.axioms(ledger_entry("A1"))
    assert only(article.check(), "ledger") == []


def test_rule2_covers_the_legacy_prose_form(article):
    """"ledger A4" in prose is still a reference — the migration is not complete."""
    article.blueprint(statement(body="Accepted as ledger A4 for now.", label="thm:x"))
    msgs = only(article.check(), "ledger")
    assert len(msgs) == 1 and "A4" in msgs[0]


# --- rule 3: a paper marker names a real blueprint label ------------------------------


MARKED = """\
%% shared with blueprint {label}
\\begin{{theorem}}
  \\label{{{own}}}
  {body}
\\end{{theorem}}
"""


def test_rule3_fires_when_the_paper_names_a_label_the_blueprint_lacks(article):
    article.blueprint(statement(label="thm:x"))
    article.paper(MARKED.format(label="thm:ghost", own="thm:ghost",
                                body="The kernel is smooth."))
    msgs = only(article.check(), "paper")
    assert len(msgs) == 1
    assert "thm:ghost" in msgs[0] and "paper.tex:1" in msgs[0]


def test_rule3_silent_when_the_label_exists(article):
    article.blueprint(statement(label="thm:x"))
    article.paper(MARKED.format(label="thm:x", own="thm:x", body="The kernel is smooth."))
    f = article.check()
    assert only(f, "paper") == []
    assert f.stats["shared_verbatim"] == 1


def test_rule3_reports_only_the_missing_labels_of_a_list(article):
    article.blueprint(statement(label="thm:x"))
    article.paper(MARKED.format(label="thm:x, thm:ghost", own="thm:x",
                                body="The kernel is smooth."))
    msgs = only(article.check(), "paper")
    assert len(msgs) == 1
    assert "thm:ghost" in msgs[0] and "thm:x," not in msgs[0]


# --- rule 4: the clean-render gate ----------------------------------------------------


def test_rule4_fires_on_a_command_that_is_neither_defined_nor_vetted(article):
    article.blueprint(statement(body=r"The \smoothing operator is bounded.", label="thm:x"))
    msgs = only(article.check(), "render")
    assert len(msgs) == 1
    assert r"\smoothing" in msgs[0]


def test_rule4_silent_for_a_macro_defined_in_the_article_macros(article):
    article.blueprint(statement(body=r"The kernel \kernel{t} is bounded.", label="thm:x"))
    assert only(article.check(), "render") == []


def test_rule4_silent_for_a_command_vetted_in_the_allowlist(article):
    article.blueprint(statement(body=r"Take $x \in \mathbb{R}$.", label="thm:x"))
    assert only(article.check(), "render") == []


def test_rule4_covers_the_proof_as_well_as_the_statement(article):
    article.blueprint(statement(label="thm:x", proof=r"By \handwaving."))
    msgs = only(article.check(), "render")
    assert len(msgs) == 1 and "in proof" in msgs[0]


def test_rule4_ignores_the_framework_vocabulary(article):
    r"""\label, \lean, \uses, \notes, \ledger and the status tags are stripped, not vetted."""
    article.blueprint(statement(label="thm:x", lean="A.b", uses=("def:y",), notes="a-note",
                                notready=True))
    article.blueprint(article.root.joinpath("blueprint/src/content.tex")
                      .read_text(encoding="utf-8")
                      + statement(env="definition", label="def:y", body="A kernel."))
    assert only(article.check(), "render") == []


# --- rule 5: every node declares [T] or [A] ------------------------------------------


def test_rule5_fires_on_a_node_with_no_status_tag(article):
    article.blueprint(statement(label="thm:x", status=None))
    msgs = only(article.check(), "status")
    assert len(msgs) == 1 and "thm:x" in msgs[0]


def test_rule5_silent_for_either_tag(article):
    article.blueprint(
        statement(label="thm:x")
        + statement(label="thm:y", status="A", ledger=("A1",), note=assignment())
    )
    article.axioms(ledger_entry("A1"))
    assert only(article.check(), "status") == []


def test_rule5_does_not_fire_on_an_unlabelled_environment(article):
    """An unlabelled remark-like environment is not a node the hub can grade."""
    article.blueprint(statement(label=None, status=None))
    assert only(article.check(), "status") == []


# --- rule 6: a referenced ledger entry carries a **Cite:** line -----------------------


def test_rule6_fires_on_an_entry_without_a_cite_line(article):
    article.blueprint(statement(label="thm:x", status="A", ledger=("A1",), note=assignment()))
    article.axioms(ledger_entry("A1", cite=None))
    msgs = only(article.check(), "ledger")
    assert len(msgs) == 1 and "**Cite:**" in msgs[0]


def test_rule6_silent_when_the_entry_carries_one(article):
    article.blueprint(statement(label="thm:x", status="A", ledger=("A1",), note=assignment()))
    article.axioms(ledger_entry("A1"))
    assert only(article.check(), "ledger") == []


def test_rule6_accepts_a_pending_citation(article):
    """`**Cite:** — pending` is a line: it projects a null citekey, not a missing entry."""
    article.blueprint(statement(label="thm:x", status="A", ledger=("A1",), note=assignment()))
    article.axioms(ledger_entry("A1", cite="— pending (source not yet pinned)"))
    assert only(article.check(), "ledger") == []


# --- rule 7: every [A] node declares its assignment (ADR-0011) ------------------------


def test_rule7_fires_when_an_A_node_declares_no_assignment(article):
    article.blueprint(statement(label="thm:x", status="A", ledger=("A1",),
                                note="Cited from the literature."))
    article.axioms(ledger_entry("A1"))
    msgs = only(article.check(), "assign")
    assert len(msgs) == 1 and "no '\\textbf{Assignment.}' clause" in msgs[0]


def test_rule7_fires_when_the_clause_names_no_ledger_entry(article):
    article.blueprint(statement(label="thm:x", status="A", ledger=("A1",),
                                note=assignment("the analytic part is cited.")))
    article.axioms(ledger_entry("A1"))
    msgs = only(article.check(), "assign")
    assert len(msgs) == 1 and "names no ledger entry" in msgs[0]


def test_rule7_silent_when_the_clause_names_one(article):
    article.blueprint(statement(label="thm:x", status="A", ledger=("A1",), note=assignment()))
    article.axioms(ledger_entry("A1"))
    assert only(article.check(), "assign") == []


def test_rule7_accepts_a_plain_text_entry_id_in_the_clause(article):
    """The clause may name an entry in prose — `\\ledger{}` there would project a source."""
    article.blueprint(statement(label="thm:x", status="A", ledger=("A1",),
                                note=assignment("A1 carries the bound; not A2.")))
    article.axioms(ledger_entry("A1"))
    assert only(article.check(), "assign") == []


def test_rule7_does_not_apply_to_T_nodes(article):
    article.blueprint(statement(label="thm:x", note="A formalisation note."))
    assert only(article.check(), "assign") == []


# --- rule 8: the dependency invariant -------------------------------------------------


def _pair(target: str) -> str:
    """A \\leanok node depending on `target`, plus whatever `target` is."""
    return statement(label="thm:a", lean="A.a", leanok=True, uses=("thm:b",)) + target


def test_rule8_fires_when_a_proved_node_rests_on_a_statement_proved_nowhere(article):
    article.blueprint(_pair(statement(label="thm:b")))
    article.lean("theorem a : True := trivial\n")
    msgs = only(article.check(), "depend")
    assert len(msgs) == 1
    assert "thm:b is proved nowhere" in msgs[0] and "thm:a -> thm:b" in msgs[0]


def test_rule8_silent_when_the_target_carries_a_blueprint_proof_of_record(article):
    """Not \\leanok is not unproved: a written proof is a debt, reported as advisory."""
    article.blueprint(_pair(statement(label="thm:b", proof="A complete argument.")))
    article.lean("theorem a : True := trivial\n")
    f = article.check()
    assert only(f, "depend") == []
    assert len(tagged(f.advisory, "depend")) == 1


def test_rule8_silent_when_the_target_is_an_A_interface(article):
    article.blueprint(_pair(statement(label="thm:b", status="A", ledger=("A1",),
                                      note=assignment())))
    article.axioms(ledger_entry("A1"))
    article.lean("theorem a : True := trivial\n")
    assert only(article.check(), "depend") == []


def test_rule8_silent_when_the_target_is_a_definition(article):
    """Definitions are vocabulary, not claims."""
    article.blueprint(
        statement(label="thm:a", lean="A.a", leanok=True, uses=("def:b",))
        + statement(env="definition", label="def:b", body="A kernel.")
    )
    article.lean("theorem a : True := trivial\n")
    assert only(article.check(), "depend") == []


def test_rule8_fatal_walk_traverses_through_an_A_node(article):
    """An [A] node's own statement may not be phrased in terms of an unproved one."""
    article.blueprint(
        statement(label="thm:a", lean="A.a", leanok=True, uses=("thm:mid",))
        + statement(label="thm:mid", status="A", ledger=("A1",), note=assignment(),
                    uses=("thm:c",))
        + statement(label="thm:c")
    )
    article.axioms(ledger_entry("A1"))
    article.lean("theorem a : True := trivial\n")
    msgs = only(article.check(), "depend")
    assert len(msgs) == 1
    assert "thm:c is proved nowhere" in msgs[0]
    assert "thm:a -> thm:mid -> thm:c" in msgs[0]


def test_rule8_advisory_dependent_count_stops_at_the_trust_boundary(article):
    """The two walks are asymmetric on purpose — both counts are printed."""
    article.blueprint(
        statement(label="thm:a", lean="A.a", leanok=True, uses=("thm:mid",))
        + statement(label="thm:mid", status="A", ledger=("A1",), note=assignment(),
                    uses=("thm:debt",))
        + statement(label="thm:debt", proof="A complete argument.")
    )
    article.axioms(ledger_entry("A1"))
    article.lean("theorem a : True := trivial\n")
    f = article.check()
    assert only(f, "depend") == []
    (msg,) = tagged(f.advisory, "depend")
    assert "reached by no \\leanok node(s) ahead of the trust boundary" in msg
    assert "(1 counting paths through an [A] interface)" in msg


def test_rule8_reports_one_finding_per_target_naming_every_reacher(article):
    article.blueprint(
        statement(label="thm:a", lean="A.a", leanok=True, uses=("thm:bad",))
        + statement(label="thm:b", lean="A.b", leanok=True, uses=("thm:bad",))
        + statement(label="thm:bad")
    )
    article.lean("theorem a : True := trivial\ntheorem b : True := trivial\n")
    (msg,) = only(article.check(), "depend")
    assert "2 \\leanok node(s) depend on it: thm:a, thm:b" in msg


def test_rule8_terminates_on_a_cyclic_uses_graph(article):
    """The visited set makes the walk terminate whatever the edges do (checks.uses_paths)."""
    article.blueprint(
        statement(label="thm:a", lean="A.a", leanok=True, uses=("thm:b",))
        + statement(label="thm:b", lean="A.b", leanok=True, uses=("thm:a",))
    )
    article.lean("theorem a : True := trivial\ntheorem b : True := trivial\n")
    assert article.check().ok


# --- rule 9: control characters in sources -------------------------------------------


def test_rule9_fires_on_a_bare_tab(article):
    article.root.joinpath("paper/tabbed.tex").write_bytes(b"A line\twith a tab.\n")
    msgs = only(article.check(), "chars")
    assert len(msgs) == 1
    assert "U+0009" in msgs[0] and "paper/tabbed.tex:1" in msgs[0]


def test_rule9_fires_on_the_backspace_a_non_raw_string_literal_writes(article):
    r"""`"\begin{proof}"` in a non-raw literal is U+0008 — the case that prompted the rule."""
    article.root.joinpath("blueprint/src/part.tex").write_bytes(b"\x08egin{proof}\n")
    msgs = only(article.check(), "chars")
    assert len(msgs) == 1 and "U+0008" in msgs[0]


def test_rule9_silent_on_a_windows_checkout(article):
    """CR immediately before LF is a checkout, not corruption."""
    article.root.joinpath("paper/crlf.tex").write_bytes(b"A line.\r\nAnother.\r\n")
    assert only(article.check(), "chars") == []


def test_rule9_skips_build_output_and_agent_worktrees(article):
    for rel in (".lake/build/x.lean", ".claude/worktrees/a/paper/y.tex", "web/z.md"):
        p = article.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"tab\there\n")
    assert only(article.check(), "chars") == []


# --- the wiki edge (checked only when a vault is supplied) ----------------------------


def test_the_notes_edge_is_checked_only_with_a_vault(article, tmp_path):
    article.blueprint(statement(label="thm:x", notes="kernel-smoothness"))
    assert only(article.check(), "notes") == []

    vault = tmp_path / "vault"
    (vault / "wiki").mkdir(parents=True)
    msgs = only(article.check(wiki=vault), "notes")
    assert len(msgs) == 1 and "kernel-smoothness" in msgs[0]

    (vault / "wiki" / "kernel-smoothness.md").write_text("# note\n", encoding="utf-8")
    assert only(article.check(wiki=vault), "notes") == []


# --- the advisories ------------------------------------------------------------------


def test_advisory_leanok_without_a_lean_declaration(article):
    article.blueprint(statement(label="thm:x", leanok=True))
    (msg,) = tagged(article.check().advisory, "lean")
    assert "is \\leanok but has no \\lean{}" in msg


def test_advisory_leanok_and_notready_together(article):
    article.blueprint(statement(label="thm:x", lean="A.x", leanok=True, notready=True))
    article.lean("theorem x : True := trivial\n")
    (msg,) = tagged(article.check().advisory, "lean")
    assert "both \\leanok and \\notready" in msg


def test_the_stats_block_reports_what_the_cli_prints(article):
    article.blueprint(
        statement(label="thm:a", lean="A.a", leanok=True, uses=("thm:b",))
        + statement(label="thm:b", proof="An argument.")
    )
    article.lean("theorem a : True := trivial\n")
    s = article.check().stats
    assert s["nodes"] == 2
    assert s["leanok"] == 1
    assert s["reached_unproved"] == 0
    assert s["reached_on_paper"] == 1
    assert s["unproved"] == []
