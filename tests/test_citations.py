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
    ("delta2021", "sscite", "p.~12", "prose", None),
    ("epsilon2022", "sscite", "", "prose", None),
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


EDGE = r"""
\input{sec}

% shared with blueprint thm:a
\begin{theorem}\label{t:a}
  First line with a long run of preceding words so the bracket is far from the start
  [\sscite{eta2015}, Lem.~2]
  and \cite{theta2016}.
\end{theorem}

Prose between. \cite[see][Ch.~4]{iota2014}

% shared with blueprint thm:b
\begin{lemma}\label{t:b}
  Uses \cite[p.~9]{kappa2013}.
\end{lemma}
"""


def test_edges_two_optionals_multiline_shared_and_inputs(article):
    article.paper(document(EDGE))
    article.file("paper/sec.tex", "A section cites \\cite[p.~1]{lambda2012}.\n")
    rc, out, _ = run_cli("citations", "--inventory")
    assert rc == 0
    got = [(r["file"], r["key"], r["form"], r["locator"], r["zone"], r["node"])
           for r in json.loads(out)]
    assert got == [
        ("paper/paper.tex", "eta2015", "sscite", "Lem.~2", "shared-statement", "thm:a"),
        ("paper/paper.tex", "theta2016", "cite", "", "shared-statement", "thm:a"),
        ("paper/paper.tex", "iota2014", "cite", "Ch.~4", "prose", None),
        ("paper/paper.tex", "kappa2013", "cite", "p.~9", "shared-statement", "thm:b"),
        ("paper/sec.tex", "lambda2012", "cite", "p.~1", "prose", None),
    ]


SHARED_AND_MODULES = r"""
\makeatletter
\@namedef{progkey@V-line v0.1}{fagerstrom2026spatial}
\makeatother
One bracket, two sources [\sscite{mu2011}, p.~448; \sscite{nu2010}, (2), p.~426].
A module \prog{V-line v0.1}{Thm.~7.3, p.~37}, its paper \progpaper{V-line v0.1},
and one the paper maps to no key \prog{cone}{Lem.~1}.
"""


def test_a_shared_bracket_and_module_citekeys(article):
    article.paper(document(SHARED_AND_MODULES))
    rc, out, _ = run_cli("citations", "--inventory")
    assert rc == 0
    got = [(r["key"], r["module"], r["form"], r["locator"]) for r in json.loads(out)]
    assert got == [
        ("mu2011", None, "sscite", "p.~448"),
        ("nu2010", None, "sscite", "(2), p.~426"),
        ("fagerstrom2026spatial", "V-line v0.1", "prog", "Thm.~7.3, p.~37"),
        ("fagerstrom2026spatial", "V-line v0.1", "progpaper", ""),
        ("cone", "cone", "prog", "Lem.~1"),
    ]
