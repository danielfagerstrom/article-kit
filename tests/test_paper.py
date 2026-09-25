r"""`linkage paper` — the deterministic paper lint.

Every check gets a positive and a negative case: the clean case holds down that the
check stays silent where it should (the failure mode of a lint nobody can keep clean),
the defect case that it still fires. On top of those, the two fixture papers under
`tests/fixtures/paper/` are run end to end — `clean` must report nothing at all, and
`seeded` must report exactly the defects its `% SEED:` comments declare, which is the
brief's "reports each seeded defect on a fixture" turned into an assertion.
"""

from __future__ import annotations

import re

from conftest import run_cli, tagged
from fixtures.papers import ABSTRACT, DECLARATIONS, FIXTURES, document, install
from linkage import paper

BIB = """\
@article{author2020kernels,
  author = {Author, A.},
  title  = {Kernels},
  year   = {2020},
  doi    = {10.1000/small.2020.1},
}
"""
NODOI_BIB = """\
@article{author2020kernels,
  author = {Author, A.},
  title  = {Kernels},
  year   = {2020},
}
"""
PROP = r"""\begin{proposition}
  \label{prop:two}
  Then
  \begin{enumerate}
    \item the first moment is finite, and
    \item it determines the kernel.
  \end{enumerate}
\end{proposition}
"""


def lint(article, body: str = "", **kw):
    """The lint over a one-file paper holding `body`."""
    article.paper(document(body, **kw))
    return paper.lint(article.cfg)


# --- the fixture pair, end to end ----------------------------------------------------


def test_the_clean_fixture_paper_reports_nothing(article):
    """A lint that cannot be satisfied gets waived, so the clean side is a real test."""
    f = install(article, "clean")
    found = paper.lint(f.cfg)
    assert found.fatal == []
    assert found.advisory == []


def test_the_clean_fixture_paper_reaches_every_check(article):
    """Silence is only worth something if the checks ran: a fixture that lost its `.bib`
    or its front matter would pass the test above by having nothing to say."""
    s = paper.lint(install(article, "clean").cfg).stats
    assert s["main"] == "paper/main.tex"
    assert s["bib_files"] == ["paper/refs.bib"] and s["cites"] == 2
    assert s["statements"] == 3 and s["refs"] == 6 and s["tags_checked"] == 1
    assert s["missing_declarations"] == []
    assert paper.ABSTRACT_MIN <= s["abstract_words"] <= paper.ABSTRACT_MAX


def seeded_tags() -> list[str]:
    """The tags the seeded fixture declares, read from its own `% SEED:` comments."""
    tags = []
    for p in sorted((FIXTURES / "seeded").iterdir()):
        tags += re.findall(r"%\s*SEED:\s*(\w+)", p.read_text(encoding="utf-8"))
    return sorted(set(tags))


def test_the_seeded_fixture_paper_reports_every_seeded_defect(article):
    f = install(article, "seeded")
    found = paper.lint(f.cfg)
    msgs = found.fatal + found.advisory
    declared = seeded_tags()
    assert declared, "the seeded fixture must mark its defects with `% SEED: <tag>`"
    assert [t for t in declared if tagged(msgs, t)] == declared
    reported = sorted({m.split("]")[0].lstrip("[") for m in msgs})
    assert reported == declared, "reported a defect the fixture does not declare"


def test_the_seeded_fixture_fails_the_command_and_the_clean_one_passes(article):
    install(article, "clean")
    rc, out, _ = run_cli("--root", str(article.root), "paper")
    assert rc == 0 and "PAPER LINT OK" in out
    install(article, "seeded", dir="paper")
    rc, out, _ = run_cli("--root", str(article.root), "paper")
    assert rc == 1 and "PAPER LINT FAILED" in out
    assert "main document paper/main.tex" in out


# --- 1. \ref integrity ----------------------------------------------------------------


def test_a_reference_to_a_label_that_exists_is_silent(article):
    f = lint(article, r"\section{S}\label{sec:s} See Section~\ref{sec:s}.")
    assert tagged(f.fatal, "ref") == []


def test_a_reference_to_no_label_is_fatal(article):
    f = lint(article, r"\section{S}\label{sec:s} See Section~\ref{sec:gone}.")
    (msg,) = tagged(f.fatal, "ref")
    assert "sec:gone" in msg and "paper/paper.tex" in msg


def test_a_label_in_a_sibling_file_resolves(article):
    """A paper is many files; a label is not required to be in the one that cites it."""
    article.paper(r"\label{lem:elsewhere} Stated here.", name="other.tex")
    f = lint(article, r"See Lemma~\ref{lem:elsewhere}.")
    assert tagged(f.fatal, "ref") == []


def test_each_label_of_a_cref_list_is_checked(article):
    f = lint(article, r"\label{eq:a} See \cref{eq:a,eq:b}.")
    (msg,) = tagged(f.fatal, "ref")
    assert "eq:b" in msg


# --- 2. orphaned numbered results -----------------------------------------------------


def test_a_referenced_result_is_not_an_orphan(article):
    f = lint(article, PROP + r"By Proposition~\ref{prop:two} we are done.")
    assert tagged(f.advisory, "orphan") == []


def test_a_numbered_result_nothing_refers_to_is_an_advisory(article):
    f = lint(article, PROP)
    (msg,) = tagged(f.advisory, "orphan")
    assert "prop:two" in msg and "proposition" in msg
    assert f.fatal == []


def test_an_unlabelled_statement_is_not_an_orphan(article):
    """Nothing can reference it, so nothing is wrong: it is simply not numbered here."""
    f = lint(article, r"\begin{lemma}A remark in disguise.\end{lemma}")
    assert tagged(f.advisory, "orphan") == []


# --- 3. \cite keys and DOIs -----------------------------------------------------------


def test_a_cite_key_in_the_bib_is_silent(article):
    article.paper(BIB, name="refs.bib")
    f = lint(article, r"Following \cite{author2020kernels}.", bib="refs")
    assert tagged(f.fatal, "cite") == [] and tagged(f.advisory, "doi") == []


def test_a_cite_key_in_no_bib_is_fatal(article):
    article.paper(BIB, name="refs.bib")
    f = lint(article, r"Following \cite{nobody2020}.", bib="refs")
    (msg,) = tagged(f.fatal, "cite")
    assert "nobody2020" in msg and "paper/refs.bib" in msg


def test_an_articles_own_cite_wrapper_is_read(article):
    r"""Paper I cites through `\sscite`; a check that only knew `\cite` would see none."""
    article.paper(BIB, name="refs.bib")
    f = lint(article, r"Following \sscite{nobody2020}.", bib="refs")
    assert tagged(f.fatal, "cite")


def test_a_citation_macros_own_definition_is_not_a_citation(article):
    r"""`\newcommand{\sscite}[1]{\cite{#1}}` is Paper I's macros.tex line 8."""
    article.paper(BIB, name="refs.bib")
    f = lint(article, r"\newcommand{\sscite}[1]{\cite{#1}}", bib="refs")
    assert tagged(f.fatal, "cite") == []


def test_with_no_bib_the_cite_check_is_skipped(article):
    """There is nothing to resolve against, so every key would be reported at once."""
    f = lint(article, r"Following \cite{author2020kernels}.")
    assert tagged(f.fatal, "cite") == []
    assert f.stats["bib_files"] == []


def test_a_cited_entry_with_no_doi_is_an_advisory(article):
    article.paper(NODOI_BIB, name="refs.bib")
    f = lint(article, r"Following \cite{author2020kernels}.", bib="refs")
    (msg,) = tagged(f.advisory, "doi")
    assert "author2020kernels" in msg and f.fatal == []


def test_an_uncited_entry_with_no_doi_is_not_reported(article):
    """The bibliography may hold more than the paper cites; only cited entries matter."""
    article.paper(NODOI_BIB + "\n@book{unused2021, title = {Unused}}\n", name="refs.bib")
    f = lint(article, r"Nothing is cited here.", bib="refs")
    assert tagged(f.advisory, "doi") == []


# --- 4. an item number past the target's item count -----------------------------------


def test_an_item_number_within_the_count_is_silent(article):
    f = lint(article, PROP + r"By Proposition~\ref{prop:two}(2) we are done.")
    assert tagged(f.fatal, "item") == []


def test_an_item_number_past_the_count_is_fatal(article):
    f = lint(article, PROP + r"By Proposition~\ref{prop:two}(3) we are done.")
    (msg,) = tagged(f.fatal, "item")
    assert "(3)" in msg and "2 item(s)" in msg


def test_a_roman_item_number_is_read_too(article):
    f = lint(article, PROP + r"By Proposition~\ref{prop:two}(iii) we are done.")
    assert tagged(f.fatal, "item")


def test_a_statement_with_no_items_is_not_counted(article):
    """An equation-numbered pointer is not an item pointer; the count is unknown."""
    f = lint(article, r"""\begin{lemma}\label{lem:x}One claim.\end{lemma}
    By Lemma~\ref{lem:x}(2) we are done.""")
    assert tagged(f.fatal, "item") == []


# --- 5. a bare pointer with no citation and no label ----------------------------------


def test_a_section_sign_beside_a_reference_is_silent(article):
    f = lint(article, r"\label{sec:s} As \S\ref{sec:s} shows, the bound is sharp.")
    assert tagged(f.advisory, "point") == []


def test_a_bare_section_sign_is_an_advisory(article):
    f = lint(article, "The argument of § 4.2 carries over " + "word " * 40)
    (msg,) = tagged(f.advisory, "point")
    assert "bare '§'" in msg


def test_an_abbreviated_result_name_beside_a_citation_is_silent(article):
    article.paper(BIB, name="refs.bib")
    f = lint(article, r"Thm. 3.1 of \cite{author2020kernels} gives the bound.", bib="refs")
    assert tagged(f.advisory, "point") == []


def test_a_bare_abbreviated_result_name_is_an_advisory(article):
    f = lint(article, "By Thm. 3.1 the bound is sharp. " + "word " * 40)
    (msg,) = tagged(f.advisory, "point")
    assert "bare 'Thm'" in msg


# --- 6. a hand-written \tag whose section number is wrong -----------------------------


def test_a_tag_matching_its_section_is_silent(article):
    f = lint(article, r"\section{One}" "\n" r"\begin{equation}x\tag{1.4}\end{equation}")
    assert tagged(f.fatal, "tag") == [] and f.stats["tags_checked"] == 1


def test_a_tag_from_another_section_is_fatal(article):
    f = lint(article, r"\section{One}" "\n" r"\section{Two}" "\n"
             r"\begin{equation}x\tag{1.4}\end{equation}")
    (msg,) = tagged(f.fatal, "tag")
    assert "1.4" in msg and "section 2" in msg


def test_an_appendix_tag_is_read_as_a_letter(article):
    f = lint(article, r"\section{One}" "\n" r"\appendix" "\n" r"\section{A}" "\n"
             r"\begin{equation}x\tag{A.2}\end{equation}"
             r"\begin{equation}y\tag{1.2}\end{equation}")
    (msg,) = tagged(f.fatal, "tag")
    assert "1.2" in msg and "appendix A" in msg


def test_a_tag_that_is_not_a_section_number_is_left_alone(article):
    f = lint(article, r"\section{One}" "\n" r"\begin{equation}x\tag{$\star$}\end{equation}")
    assert tagged(f.fatal, "tag") == [] and f.stats["tags_checked"] == 0


def test_a_tag_naming_no_section_of_this_document_is_left_alone(article):
    r"""Paper I writes `\tag{V.1}` in appendix A — a custom label, not a stale number.

    The checker cannot tell a deliberate label from a pointer into a companion paper, so
    it only speaks when `N` names a *different* section of this document.
    """
    f = lint(article, r"\section{One}" "\n" r"\appendix" "\n" r"\section{A}" "\n"
             r"\begin{equation}x\tag{V.1}\end{equation}")
    assert tagged(f.fatal, "tag") == [] and f.stats["tags_checked"] == 0


def test_the_section_number_comes_from_the_document_order(article):
    r"""The tag sits in an `\input`ed file that knows nothing of its own number."""
    article.paper(r"\begin{equation}x\tag{1.4}\end{equation}", name="body.tex")
    article.paper(document(r"\section{One}" "\n" r"\section{Two}" "\n" r"\input{body}"))
    f = paper.lint(article.cfg)
    (msg,) = tagged(f.fatal, "tag")
    assert msg.startswith("[tag]    paper/body.tex:1") and "section 2" in msg


# --- 7. the declarations and the abstract ---------------------------------------------


def test_all_four_declarations_present_is_silent(article):
    f = lint(article, "Prose.")
    assert tagged(f.advisory, "decl") == [] and f.stats["missing_declarations"] == []


def test_each_missing_declaration_is_named(article):
    f = lint(article, "Prose.", declarations=r"\section*{Funding}None.")
    assert f.stats["missing_declarations"] == [
        "author contributions", "competing interests", "data availability"]
    assert len(tagged(f.advisory, "decl")) == 3


def test_an_abstract_in_range_is_silent(article):
    f = lint(article, "Prose.")
    assert tagged(f.advisory, "abstr") == [] and f.stats["abstract_words"] == 150


def test_an_abstract_outside_the_range_is_an_advisory(article):
    f = lint(article, "Prose.", abstract="Far too short.")
    (msg,) = tagged(f.advisory, "abstr")
    assert "3 words" in msg and "150" in msg


def test_a_main_document_with_no_abstract_is_an_advisory(article):
    f = lint(article, "Prose.", abstract=None)
    (msg,) = tagged(f.advisory, "abstr")
    assert "no abstract" in msg


# --- a fragment directory: the front-matter checks do not apply -----------------------


def test_without_a_main_document_the_front_matter_checks_are_skipped(article):
    r"""A paper directory of section fragments — the scaffold smoke article's shape."""
    article.paper(r"\section{S}\label{sec:s}" "\n"
                  r"\begin{equation}x\tag{9.1}\end{equation}" "\n"
                  r"As Section~\ref{sec:s} shows, the bound is sharp.")
    f = paper.lint(article.cfg)
    assert f.fatal == [] and f.advisory == []
    assert f.stats["main"] is None and f.stats["tags_checked"] == 0


def test_the_command_says_so_on_a_fragment_directory(article):
    rc, out, _ = run_cli("--root", str(article.root), "paper")
    assert rc == 0 and "no main document" in out


# --- several paper directories --------------------------------------------------------


def test_every_paper_directory_is_read(article):
    """`paths.paper` may be a list; the lint reads them all, as `linkage check` does."""
    article.papers("paper", "paper-b")
    article.paper(r"See Lemma~\ref{lem:gone}.", dir="paper-b")
    article.paper(document("Prose."))
    f = paper.lint(article.cfg)
    (msg,) = tagged(f.fatal, "ref")
    assert msg.startswith("[ref]    paper-b/paper.tex:1")


# --- the comment stripper -------------------------------------------------------------


def test_a_defect_inside_a_comment_is_not_reported(article):
    r"""A commented-out draft holds dangling refs by construction."""
    f = lint(article, "% See Lemma~\\ref{lem:gone}, \\cite{nobody2020}.\nProse.")
    assert f.fatal == []


def test_an_escaped_percent_does_not_start_a_comment(article):
    f = lint(article, r"A 5\% gain, see Lemma~\ref{lem:gone}.")
    assert tagged(f.fatal, "ref")


def test_stripping_comments_keeps_every_line_in_place(article):
    """Every finding is located by `file:line`, so the stripper may not shorten anything.

    The builder's front matter is six lines (class, \\begin{document}, the three-line
    abstract, a blank), so the body's third line is the file's ninth.
    """
    f = lint(article, "% a comment\n% another\nSee Lemma~\\ref{lem:gone}.")
    (msg,) = tagged(f.fatal, "ref")
    assert ":9:" in msg


def test_the_declarations_and_abstract_come_from_the_fixture_builder():
    """A guard on the builder itself: its abstract is in range and it declares all four."""
    assert paper.word_count(ABSTRACT) == paper.ABSTRACT_MIN
    assert all(re.search(pat, DECLARATIONS, re.I) for _, pat in paper.DECLARATIONS)
