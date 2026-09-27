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


def build(article, paper: str | None = None):
    article.blueprint(BLUEPRINT).axioms(LEDGER).lean(LEAN).trust("Art.tail_bound")
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
    build(article).lean(LEAN.replace("exact tail_bound", "exact trivial"))
    fatal, _, _ = findings(article)
    assert any("names ledger entry A1, but none of the statements" in m for m in fatal)
    assert any("interface axiom tail_bound, which none" in m for m in fatal)


def test_a_boundary_name_missing_from_the_list_fails(article):
    # Sixteen names, not fourteen: `main` now reaches a second interface of the same entry.
    build(article).trust("Art.tail_bound", "Art.mode_bound")
    article.axioms(LEDGER.replace("**Lean:** `Art.tail_bound`",
                                  "**Lean:** `Art.tail_bound`, `Art.mode_bound`"))
    article.lean(LEAN.replace("exact tail_bound", "have := mode_bound\n  exact tail_bound"))
    fatal, _, _ = findings(article)
    assert fatal == ["[trust-base] paper/paper.tex:3: thm:b reach(es) interface axiom "
                     "mode_bound, which the section's list of names leaves out"]


# --- drift 3: the printed axioms blocks ------------------------------------------------


def test_an_unstamped_block_fails(article):
    (msg,) = findings(build(article, section(stamp="% printed by hand\n")))[0]
    assert "no stamp" in msg and "paper.tex:11" in msg


def test_a_date_stamp_is_enough(article):
    fatal, _, _ = findings(build(article, section(stamp="% printed at 2026-09-26\n")))
    assert fatal == []


def test_a_block_printed_before_the_boundary_moved_fails(article):
    block = BLOCK.replace("Art.tail_bound]", "Art.tail_bound, Art.old_fact]")
    (msg,) = findings(build(article, section(block=block)))[0]
    assert "Art.old_fact" in msg and "does not declare" in msg


def test_a_block_is_compared_with_its_guard_pin(article):
    build(article).boundary('[boundary]\nguard = "Formalization/Guard.lean"\n')
    article.lean("/-- info: 'Art.main' depends on axioms: [propext] -/\n"
                 "#guard_msgs in\n#print axioms Art.main\n", name="Guard.lean")
    (msg,) = findings(article)[0]
    assert "#guard_msgs pin in Guard.lean says [propext]" in msg


def test_fresh_axioms_compares_with_lean(article, monkeypatch):
    build(article)
    sources: list[str] = []

    def lean(cfg, src):
        sources.append(src)
        return "'Art.main' depends on axioms: [propext]\n"

    monkeypatch.setattr("linkage.trustbase._run_lean", lean)
    assert tagged(article.check().fatal, "trust-base") == []  # not run by default
    assert sources == []
    (msg,) = tagged(article.check(fresh_axioms=True).fatal, "trust-base")
    assert "Lean prints [propext] now" in msg
    assert sources == ["import Main\n#print axioms Art.main\n"]


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
