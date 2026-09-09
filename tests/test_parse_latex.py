"""The blueprint parser — the one LaTeX-aware module.

Its normalizations are load-bearing beyond this repo: `statement` and its sha are the
hub's wire format, so a change here moves every published hash at once. These tests
pin the behaviour rather than the implementation — what survives normalization, what
is stripped, and where the three reductions (statement / render source / shared) differ.
"""

from __future__ import annotations

import pytest

from fixtures.article import statement
from linkage import parse_latex as P
from linkage.config import Config


def nodes(article, tex: str):
    article.blueprint(tex)
    return {n.label: n for n in article.parse().nodes}


# --- the environment scan -------------------------------------------------------------


def test_one_node_per_statement_environment(article):
    tex = "".join(statement(label=f"thm:{k}", env=e)
                  for k, e in enumerate(("theorem", "lemma", "proposition", "corollary")))
    tex += statement(label="def:d", env="definition")
    got = nodes(article, tex)
    assert set(got) == {"thm:0", "thm:1", "thm:2", "thm:3", "def:d"}
    assert got["thm:1"].env == "lemma"


def test_an_unconfigured_environment_is_not_a_node(article):
    article.file("linkage.toml", 'slug = "test"\n\n[blueprint]\nstatement_envs = ["theorem"]\n')
    assert set(nodes(article, statement(env="lemma", label="lem:a")
                     + statement(env="theorem", label="thm:a"))) == {"thm:a"}


def test_the_metadata_commands_are_read_off_the_body(article):
    n = nodes(article, statement(
        label="thm:x", lean="A.one, A.two", uses=("def:a", "thm:b"), leanok=True,
        notes="a-note", ledger=("A1",), status="A", note=r"\textbf{Assignment.} \ledger{A1}."
    ))["thm:x"]
    assert n.lean == ["A.one", "A.two"]
    assert n.uses == ["def:a", "thm:b"]
    assert n.leanok and not n.notready
    assert n.status == "A"
    assert n.ledger == ["A1"]              # de-duplicated: status line + Assignment clause
    assert r"\textbf{Assignment.}" in n.status_note


def test_the_environment_title_is_split_out_of_the_statement(article):
    n = nodes(article, statement(label="thm:x", title="Kernel smoothness",
                                 body="It is smooth."))["thm:x"]
    assert n.title == "Kernel smoothness"
    assert n.statement == "It is smooth."


def test_a_proof_directly_following_the_statement_is_the_nodes_proof(article):
    got = nodes(article, statement(label="thm:x", proof="  By induction.  ")
                + statement(label="thm:y"))
    assert got["thm:x"].proof == "By induction."
    assert got["thm:y"].proof is None


def test_a_proof_separated_by_prose_is_not_adopted(article):
    tex = statement(label="thm:x") + "\nSome interleaving prose.\n" + r"\begin{proof}X\end{proof}"
    assert nodes(article, tex)["thm:x"].proof is None


def test_a_comment_between_statement_and_proof_is_tolerated(article):
    tex = statement(label="thm:x") + "% a note to self\n" + r"\begin{proof}X\end{proof}"
    assert nodes(article, tex)["thm:x"].proof == "X"


# --- normalize_statement: what a sha does and does not move on ------------------------


def test_normalize_strips_comments_metadata_and_collapses_whitespace():
    body = """
      \\label{thm:x} \\lean{A.b} \\uses{def:y} \\notes{slug} \\leanok
      The kernel  is    smooth.   % an aside
      \\statusT\\quad\\emph{Lean models this with \\texttt{Foo.bar}.}
    """
    assert P.normalize_statement(body) == "The kernel is smooth."


def test_a_status_annotation_edit_does_not_move_the_statement(article):
    a = nodes(article, statement(label="thm:x", note="First note."))["thm:x"]
    b = nodes(article, statement(label="thm:x", note="A wholly rewritten note."))["thm:x"]
    assert a.statement == b.statement
    assert a.status_note != b.status_note


def test_an_escaped_percent_is_not_a_comment():
    assert P.normalize_statement(r"A rate of 5\% per unit.") == r"A rate of 5\% per unit."


def test_ledger_refs_are_deleted_from_the_statement_but_kept_for_the_renderer():
    body = r"Accepted as an interface \ledger{A2}, so the bound holds."
    assert P.normalize_statement(body) == "Accepted as an interface , so the bound holds."
    assert P.normalize_for_render(body) == "Accepted as an interface ledger A2, so the bound holds."


def test_the_render_source_still_drops_a_status_line_ledger_ref():
    body = r"It holds. \statusA\ledger{A2}\quad\emph{Assignment: \ledger{A2}.}"
    assert P.normalize_for_render(body) == "It holds."


# --- shared_statement: the comparison key for rule 3b --------------------------------


def test_shared_statement_cuts_at_the_status_tag():
    body = r"It is smooth. \statusT\quad\emph{A note.} \emph{And a free-standing one.}"
    assert P.shared_statement(body) == "It is smooth."


@pytest.mark.parametrize("word", ["Theorem", "Proposition", "Lemma", "Corollaries", "Section"])
def test_shared_statement_drops_the_environment_word_before_a_ref(word):
    assert P.shared_statement(word + r"~\ref{thm:y} applies.") == r"\ref{thm:y} applies."


def test_shared_statement_is_not_what_the_hub_publishes(article):
    """The reduction is a comparison key; `statement` (and its sha) is the wire format."""
    tex = ("\\begin{theorem}\n  \\label{thm:x}\n  It is smooth.\n"
           "  \\statusT\\quad\\emph{Assignment note.} \\emph{A free-standing note.}\n"
           "\\end{theorem}\n")
    n = nodes(article, tex)["thm:x"]
    # the annotation attached to the tag is stripped from both; a *further* \emph note
    # survives into `statement` (and its published sha) and is cut only by the reduction
    assert n.shared_statement == "It is smooth."
    assert n.statement == r"It is smooth. \emph{A free-standing note.}"


def test_split_env_title_leaves_a_bracketless_body_alone():
    assert P.split_env_title("[Name] Body") == ("Name", " Body")
    assert P.split_env_title("Body") == (None, "Body")


# --- \input expansion ----------------------------------------------------------------


def test_input_is_expanded_recursively_and_the_suffix_is_optional(article):
    article.part("parts.tex", "before\n\\input{deeper}\nafter\n")
    article.part("deeper.tex", "DEEP\n")
    article.blueprint("head\n\\input{parts.tex}\ntail\n")
    tex = P.read_blueprint(article.cfg.blueprint)
    assert tex.split() == ["head", "before", "DEEP", "after", "tail"]


def test_a_commented_input_is_not_expanded(article):
    article.part("parts.tex", "PART\n")
    article.blueprint("head\n% \\input{parts.tex}\ntail\n")
    assert "PART" not in P.read_blueprint(article.cfg.blueprint)


def test_nodes_are_found_across_inputs(article):
    article.part("one.tex", statement(label="thm:a"))
    article.part("two.tex", statement(label="thm:b"))
    got = nodes(article, "\\input{one}\n\\input{two}\n")
    assert set(got) == {"thm:a", "thm:b"}


# --- document-level scans ------------------------------------------------------------


def test_ledger_refs_collect_both_the_macro_and_the_legacy_prose_form():
    cfg = Config.__new__(Config)
    cfg.ledger_key = r"A\d+"
    tex = r"\ledger{A1} and \ledger{A1} again, plus legacy ledger~A2 and ledger A3."
    assert P.ledger_refs(tex, cfg) == {"A1", "A2", "A3"}


def test_notes_slugs_are_collected_document_wide():
    assert P.notes_slugs(r"\notes{a-note} \notes{b-note} \notes{a-note}") == {"a-note", "b-note"}
