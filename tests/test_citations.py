r"""`linkage citations --inventory`: one row per citation, over the forms an article uses."""

from __future__ import annotations

import json

from conftest import run_cli
from fixtures.papers import document

BODY = r"""
\newcommand{\sscite}[1]{\cite{#1}}
First, as shown \cite[Thm.~3]{alpha2020}. % \cite{commented2020}
Then \cite{beta2019,gamma2018} agree.

Also [\sscite{delta2021}, p.~12] and \sscite{epsilon2022}.
The module \prog{isotropic}{Thm.~3.6, p.~13} and \progpaper{selection}.

% shared with blueprint thm:main
\begin{theorem}\label{t:main}
  Following \cite[p.~5]{zeta2017}, the claim holds.
\end{theorem}
"""

ROWS = [
    ("alpha2020", "cite", "Thm.~3", "prose", None),
    ("beta2019", "cite", "", "prose", None),
    ("gamma2018", "cite", "", "prose", None),
    ("delta2021", "cite", "p.~12", "prose", None),
    ("epsilon2022", "cite", "", "prose", None),
    ("isotropic", "prog", "Thm.~3.6, p.~13", "prose", None),
    ("selection", "progpaper", "", "prose", None),
    ("zeta2017", "cite", "p.~5", "shared-statement", "thm:main"),
]


def inventory(article):
    article.paper(document(BODY))
    rc, out, _ = run_cli("citations", "--inventory")
    assert rc == 0
    return json.loads(out)


def test_inventory_rows_match_the_fixture(article):
    rows = inventory(article)
    got = [(r["key"], r["form"], r["locator"], r["zone"], r["node"]) for r in rows]
    assert got == ROWS
    assert [r["id"] for r in rows] == [f"C{i:03d}" for i in range(1, 9)]
    assert {r["file"] for r in rows} == {"paper/paper.tex"}


def test_inventory_lines_and_paragraphs(article):
    rows = inventory(article)
    by = {r["key"]: r for r in rows}
    text = document(BODY)
    for key, needle in (("alpha2020", r"\cite[Thm"), ("zeta2017", r"\cite[p.~5]")):
        assert by[key]["line"] == text[:text.index(needle)].count("\n") + 1
    assert by["alpha2020"]["paragraph"].startswith("\\newcommand")
    assert "commented2020" not in by["alpha2020"]["paragraph"]
    assert "agree" in by["beta2019"]["paragraph"]
    assert "agree" not in by["delta2021"]["paragraph"]
    assert "commented2020" not in by


def test_a_macro_definition_is_not_a_citation(article):
    assert "#1" not in {r["key"] for r in inventory(article)}


def test_without_the_flag_it_summarises(article):
    article.paper(document(BODY))
    rc, out, _ = run_cli("citations")
    assert rc == 0
    assert "8 in the paper sources, 4 with a locator" in out
