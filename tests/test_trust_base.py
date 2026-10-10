r"""Rule 13: a paper's trust-base subsection is checked against the development.

One matching article, then each of the drifts that went unnoticed in Paper V's module C:
a status the blueprint no longer has, a ledger entry named or left out, and a printed
`#print axioms` block that is unstamped or out of date. A paper without the marker is
never read.
"""

from __future__ import annotations

from conftest import run_cli, tagged
from fixtures.article import assignment, statement

LEAN = """\
namespace Art

axiom tail_bound : True
axiom mode_bound : True

theorem a_lemma : True := trivial

theorem main : True := by
  have := a_lemma
  exact tail_bound

end Art
"""

LEDGER = """\
# Axiom ledger

## A1

The tail bound.

**Lean:** `Art.tail_bound`

**Cite:** @author2020 — Thm 3.1, p. 88

**Verbatim:** "The tail is bounded." (p. 88)

## A2

The mode bound.

**Cite:** @author2021 — Lemma 2, p. 5
"""

BLUEPRINT = (
    statement(label="lem:a", lean="Art.a_lemma", leanok=True, proof="Direct.",
              proof_leanok=True)
    + statement(label="thm:b", lean="Art.main", leanok=True, uses=("lem:a",),
                proof="By the tail bound.", proof_leanok=True)
    + statement(label="lem:d", status="A", ledger=("A2",),
                note=assignment(r"\ledger{A2} carries all of it."))
    + statement(label="prop:c", uses=("lem:d",), proof="From the mode bound.")
)

STAMP = "% printed at 1a2b3c4 (2026-09-26)\n"
BLOCK = ("\\begin{verbatim}\n"
         "'Art.main' depends on axioms: [propext, Art.tail_bound]\n"
         "\\end{verbatim}\n")

ROWS = {
    "thm:b": "Theorem~\\ref{thm:b} & machine-checked & A1 (\\texttt{tail\\_bound}) \\\\\n",
    "lem:a": "Lemma~\\ref{lem:a} & machine-checked & --- \\\\\n",
    "prop:c": "Proposition~\\ref{prop:c} & proved in prose & A2 \\\\\n",
}


def section(rows: dict[str, str] | None = None, *, stamp: str = STAMP, block: str = BLOCK,
            marker: bool = True) -> str:
    body = ("\\subsection{Trust base}\n"
            + ("% trust base: begin\n" if marker else "")
            + "\\begin{tabular}{lll}\n" + "".join((rows or ROWS).values())
            + "\\end{tabular}\n\n" + stamp + block
            + ("% trust base: end\n" if marker else ""))
    return "\\section{Results}\n" + body


# What `#print axioms` prints for LEAN's two checked declarations, as the boundary harness
# pins it: the ledger comparison reads this, not the source.
PINS = {"Art.main": ("propext", "Art.tail_bound"), "Art.a_lemma": ()}


def build(article, paper: str | None = None, pins: dict | None = None):
    article.blueprint(BLUEPRINT).axioms(LEDGER).lean(LEAN).trust("Art.tail_bound")
    article.guard(PINS if pins is None else pins)
    article.paper(section() if paper is None else paper)
    return article


def findings(article):
    f = article.check()
    return tagged(f.fatal, "trust-base"), tagged(f.advisory, "trust-base"), f


# --- a matching subsection is silent ---------------------------------------------------


def test_a_matching_subsection_is_silent(article):
    fatal, advisory, f = findings(build(article))
    assert fatal == [] and advisory == []
    assert f.ok, f.fatal
    assert f.stats["trust_base"] == {"regions": 1, "claims": 3, "blocks": 1}


def test_a_paper_without_the_marker_is_not_read(article):
    rows = {**ROWS, "lem:a": "Lemma~\\ref{lem:a} & proved in prose & --- \\\\\n"}
    fatal, advisory, f = findings(build(article, section(rows, stamp="", marker=False)))
    assert fatal == [] and advisory == []
    assert f.stats["trust_base"]["regions"] == 0


def test_the_summary_line_appears_only_with_the_marker(article):
    build(article)
    rc, out, _ = run_cli("--root", str(article.root), "check")
    assert rc == 0, out
    assert "Trust base: 1 marked subsection(s), 3 status claim(s), 1 printed" in out
    article.paper(section(marker=False))
    rc, out, _ = run_cli("--root", str(article.root), "check")
    assert rc == 0 and "Trust base" not in out


# --- drift 1: a status the blueprint does not have ---------------------------------------


def test_a_checked_statement_listed_as_prose_fails(article):
    rows = {**ROWS, "lem:a": "Lemma~\\ref{lem:a} & proved in prose & --- \\\\\n"}
    (msg,) = findings(build(article, section(rows)))[0]
    assert "lem:a" in msg and "proved in prose only" in msg and "paper.tex:6" in msg


def test_a_prose_statement_listed_as_machine_checked_fails(article):
    rows = {**ROWS, "prop:c": "Proposition~\\ref{prop:c} & machine-checked & A2 \\\\\n"}
    (msg,) = findings(build(article, section(rows)))[0]
    assert "prop:c" in msg and "is not \\leanok" in msg


def test_a_negated_claim_is_read_as_prose(article):
    rows = {**ROWS, "lem:a": "Lemma~\\ref{lem:a} is not machine-checked. \\\\\n"}
    (msg,) = findings(build(article, section(rows)))[0]
    assert "lem:a" in msg and "proved in prose only" in msg


def test_a_paper_label_is_read_through_its_shared_marker(article):
    paper = ("% shared with blueprint lem:a\n\\begin{lemma}\\label{lem:paper-a}\n"
             "The kernel is smooth.\n\\end{lemma}\n")
    rows = {**ROWS, "lem:a": "Lemma~\\ref{lem:paper-a} & proved in prose & --- \\\\\n"}
    (msg,) = findings(build(article, paper + section(rows)))[0]
    assert "lem:paper-a" in msg and "blueprint node lem:a is \\leanok" in msg


def test_a_row_claiming_both_is_reported_not_guessed(article):
    rows = {**ROWS, "lem:a": "Lemma~\\ref{lem:a} & machine-checked, prose-only & --- \\\\\n"}
    fatal, advisory, _ = findings(build(article, section(rows)))
    assert fatal == []
    (msg,) = advisory
    assert "both calls lem:a machine-checked and not" in msg


# --- drift 2: the ledger entries named against those read -------------------------------


def test_an_entry_read_but_not_named_fails(article):
    rows = {**ROWS, "prop:c": "Proposition~\\ref{prop:c} & proved in prose & --- \\\\\n"}
    (msg,) = findings(build(article, section(rows)))[0]
    assert "prop:c read(s) ledger entry A2, which the section never names" in msg


def test_an_entry_named_but_no_longer_read_fails(article):
    # The tail bound has been proved: `main` no longer reaches the axiom.
    build(article, pins={**PINS, "Art.main": ("propext",)})
    article.lean(LEAN.replace("exact tail_bound", "exact trivial"))
    fatal, _, _ = findings(article)
    assert any("names ledger entry A1, but none of the statements" in m for m in fatal)
    assert any("interface axiom tail_bound, which none" in m for m in fatal)


def test_a_boundary_name_missing_from_the_list_fails(article):
    # Sixteen names, not fourteen: `main` now reaches a second interface of the same entry.
    build(article, section(block=BLOCK.replace("Art.tail_bound]",
                                               "Art.mode_bound, Art.tail_bound]")),
          pins={**PINS, "Art.main": ("propext", "Art.mode_bound", "Art.tail_bound")})
    article.trust("Art.tail_bound", "Art.mode_bound")
    article.axioms(LEDGER.replace("**Lean:** `Art.tail_bound`",
                                  "**Lean:** `Art.tail_bound`, `Art.mode_bound`"))
    article.lean(LEAN.replace("exact tail_bound", "have := mode_bound\n  exact tail_bound"))
    fatal, _, _ = findings(article)
    assert fatal == ["[trust-base] paper/paper.tex:3: thm:b reach(es) interface axiom "
                     "mode_bound, which the section's list of names leaves out"]


# --- what a \leanok node reads is `#print axioms`, not the source scan (Q-0383) -----------

# `affine` names the axiom's short name as a binder, so the source scan resolves the token
# to `Art.tail_bound`; Lean elaborates it to the bound variable and `#print axioms` prints
# nothing. Q-0377's affine statements were reported as reading ledger A2 the same way.
AFFINE_LEAN = LEAN.replace("end Art", "theorem affine (tail_bound : True) : True := tail_bound"
                                      "\n\nend Art")
AFFINE_NODE = statement(label="thm:aff", lean="Art.affine", leanok=True, proof="Direct.",
                        proof_leanok=True)
AFFINE_ROW = {"thm:aff": "Theorem~\\ref{thm:aff} & machine-checked & --- \\\\\n"}


def affine(article, pins: dict | None = None):
    build(article, section(AFFINE_ROW, stamp="", block=""),
          pins={**PINS, "Art.affine": ()} if pins is None else pins)
    return article.blueprint(BLUEPRINT + AFFINE_NODE).lean(AFFINE_LEAN)


def test_the_source_scan_would_reach_an_axiom_the_proof_does_not_use(article):
    from linkage.closure import scan_lean

    affine(article)
    assert "Art.tail_bound" in scan_lean(article.cfg).closure("Art.affine")


def test_a_statement_is_not_read_as_reaching_what_only_its_source_mentions(article):
    fatal, advisory, f = findings(affine(article))
    assert fatal == [] and advisory == []
    assert f.ok, f.fatal


def test_an_export_does_not_change_what_a_statement_reads(article):
    # An export claiming `affine` uses the axiom (stale, or wrong) is not believed here.
    affine(article).lean_uses({"Art.affine": ["Art.tail_bound"], "Art.main": []})
    assert findings(article)[0] == []


def test_a_statement_with_no_printed_axioms_is_reported_and_not_guessed(article):
    # No pin for `affine` and no --fresh-axioms: nothing to read, so the section's named
    # entries are not compared against it -- but what *is* read is still compared.
    rows = {**AFFINE_ROW, "thm:b": ROWS["thm:b"].replace("A1 (\\texttt{tail\\_bound})", "---")}
    build(article, section(rows, stamp="", block=""))
    article.blueprint(BLUEPRINT + AFFINE_NODE).lean(AFFINE_LEAN)
    fatal, advisory, _ = findings(article)
    (msg,) = advisory
    assert "no `#print axioms` output for thm:aff's Art.affine" in msg
    assert fatal == ["[trust-base] paper/paper.tex:3: thm:b read(s) ledger entry A1, which "
                     "the section never names"]


def test_fresh_axioms_reads_lean_ahead_of_the_pins(article, monkeypatch):
    affine(article, pins=PINS)  # `affine` unpinned
    printed = {"Art.main": "[propext, Art.tail_bound]", "Art.a_lemma": "[]",
               "Art.affine": "[Art.tail_bound]"}
    sources: list[str] = []

    def lean(cfg, src):
        sources.append(src)
        return "".join(f"'{d}' depends on axioms: {ax}\n" for d, ax in printed.items())

    monkeypatch.setattr("linkage.trustbase._run_lean", lean)
    (msg,) = tagged(article.check(fresh_axioms=True).fatal, "trust-base")
    assert "thm:aff read(s) ledger entry A1, which the section never names" in msg
    assert sources == ["import Main\n#print axioms Art.affine\n"]
    printed["Art.affine"] = "[]"
    assert tagged(article.check(fresh_axioms=True).fatal, "trust-base") == []


# --- a committed export older than the Lean it was generated from ----------------------


def test_a_stale_unstamped_export_fails_the_check(article):
    import os

    build(article).lean_uses({"Art.main": ["Art.tail_bound"]})
    export = article.cfg.lean_uses
    assert tagged(article.check().fatal, "lean-uses") == []
    lean = article.root / "Formalization" / "Main.lean"
    t = export.stat().st_mtime_ns
    os.utime(lean, ns=(t + 10**9, t + 10**9))
    (msg,) = tagged(article.check().fatal, "lean-uses")
    assert "lean-uses.json is older than Main.lean" in msg


def test_a_stamped_export_is_compared_by_digest(article):
    import os

    build(article).lean_uses({"Art.main": ["Art.tail_bound"]})
    rc, out, _ = run_cli("--root", str(article.root), "closure", "--stamp-export")
    assert rc == 0 and "Stamped lean-uses.json" in out
    # Touched but unchanged: the digest still matches, whatever the timestamps say.
    lean = article.root / "Formalization" / "Main.lean"
    t = article.cfg.lean_uses.stat().st_mtime_ns
    os.utime(lean, ns=(t + 10**9, t + 10**9))
    assert tagged(article.check().fatal, "lean-uses") == []
    # The stamp is not read as a declaration.
    from linkage.closure import SOURCES_KEY, build_index
    assert SOURCES_KEY not in build_index(article.cfg)[0].direct
    article.lean(LEAN.replace("exact tail_bound", "exact trivial"))
    (msg,) = tagged(article.check().fatal, "lean-uses")
    assert "generated from Lean sources (sha256:" in msg and "have changed since" in msg


# --- drift 3: the printed axioms blocks ------------------------------------------------


def test_an_unstamped_block_fails(article):
    (msg,) = findings(build(article, section(stamp="% printed by hand\n")))[0]
    assert "no stamp" in msg and "paper.tex:11" in msg


def test_a_date_stamp_is_enough(article):
    fatal, _, _ = findings(build(article, section(stamp="% printed at 2026-09-26\n")))
    assert fatal == []


def test_a_block_printed_before_the_boundary_moved_fails(article):
    block = BLOCK.replace("Art.tail_bound]", "Art.tail_bound, Art.old_fact]")
    fatal = findings(build(article, section(block=block)))[0]
    assert any("Art.old_fact" in m and "does not declare" in m for m in fatal)


def test_a_block_is_compared_with_its_guard_pin(article):
    build(article, pins={**PINS, "Art.main": ("propext",)})
    fatal = findings(article)[0]
    assert any("#guard_msgs pin in Guard.lean says [propext]" in m for m in fatal)


def test_fresh_axioms_compares_with_lean(article, monkeypatch):
    build(article)
    sources: list[str] = []

    def lean(cfg, src):
        sources.append(src)
        return "'Art.main' depends on axioms: [propext]\n"

    monkeypatch.setattr("linkage.trustbase._run_lean", lean)
    assert tagged(article.check().fatal, "trust-base") == []  # not run by default
    assert sources == []
    fatal = tagged(article.check(fresh_axioms=True).fatal, "trust-base")
    assert any("Lean prints [propext] now" in m for m in fatal)
    # ... and the ledger comparison reads the same run: `main` no longer reaches A1.
    assert any("names ledger entry A1, but none of the statements" in m for m in fatal)
    # One run for the printed block and every \leanok node the section refs.
    assert sources == ["import Main\n#print axioms Art.main\n#print axioms Art.a_lemma\n"]


def test_fresh_axioms_without_lean_fails_saying_so(article, monkeypatch):
    build(article)

    def no_lean(cfg, src):
        raise FileNotFoundError("lake")

    monkeypatch.setattr("linkage.trustbase._run_lean", no_lean)
    (msg,) = tagged(article.check(fresh_axioms=True).fatal, "trust-base")
    assert "could not run Lean" in msg


# --- the marker itself -----------------------------------------------------------------


def test_an_unclosed_marker_fails(article):
    paper = section().replace("% trust base: end\n", "")
    (msg,) = findings(build(article, paper))[0]
    assert "no '% trust base: end'" in msg
