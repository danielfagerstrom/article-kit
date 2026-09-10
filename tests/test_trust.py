"""The trust boundary — `linkage axioms [--check]` on its three states.

The states are: **no declaration file** (the guard has nothing to check — fails under
`--check`), **a file declaring no axioms** (the ideal state: the headline theorems rest
on Lean core alone — passes), and **a populated file** (passes or fails per whether the
ledger reviewed each name).

The middle state is a regression test with a date. Until 2026-09-07 an existing file
that declared nothing was conflated with an absent one, and failed a freshly scaffolded
article's Lean CI; commit 32da6f6 separated them. Reintroducing that conflation must
fail this module.
"""

from __future__ import annotations

from conftest import run_cli
from linkage import trust

LEDGER = """\
# Axiom ledger

## A1

An analytic interface.

**Lean:** `Article.Interfaces.tail_bound`

**Cite:** @author2020 — Thm 3.1, p. 88
"""


def axioms(article, *names: str, header: str = "# this article's interface axioms\n") -> None:
    article.root.joinpath("blueprint/trust-boundary.txt").write_text(
        header + "".join(n + "\n" for n in names), encoding="utf-8")


# --- state 1: no file ----------------------------------------------------------------


def test_a_missing_declaration_file_fails_under_check(article):
    rc, _, err = run_cli("--root", str(article.root), "axioms", "--check")
    assert rc == 1
    assert "no trust-boundary.txt" in err


def test_a_missing_declaration_file_is_only_a_note_without_check(article):
    """Without `--check` the command is a query, not a guard — and it prints no allowlist.

    Not Lean core either: the state is "no boundary has been declared", and an empty
    allowlist fails a consumer closed (every axiom unlisted) rather than open. CI always
    passes `--check`, where the missing file is a hard failure.
    """
    rc, out, err = run_cli("--root", str(article.root), "axioms")
    assert rc == 0
    assert out == ""
    assert "no trust-boundary.txt" in err


# --- state 2: the file exists and declares nothing (2026-09-07 regression) ------------


def test_an_existing_file_declaring_no_axioms_passes(article):
    """Lean core only — the ideal state, not a missing declaration."""
    axioms(article)
    rc, out, err = run_cli("--root", str(article.root), "axioms", "--check")
    assert rc == 0, "an existing trust boundary that declares nothing must PASS (32da6f6)"
    assert "no trust-boundary.txt" not in err
    assert "trust boundary OK: 0 interface axiom(s)" in err
    assert out.split() == list(trust.LEAN_CORE)


def test_an_empty_file_is_still_an_existing_declaration(article):
    """Not even a comment in it — an empty file is a declaration of nothing."""
    article.root.joinpath("blueprint/trust-boundary.txt").write_text("", encoding="utf-8")
    rc, _, _ = run_cli("--root", str(article.root), "axioms", "--check")
    assert rc == 0


# --- state 3: populated --------------------------------------------------------------


def test_a_declared_axiom_the_ledger_reviewed_passes(article):
    article.axioms(LEDGER)
    axioms(article, "Article.Interfaces.tail_bound")
    rc, out, err = run_cli("--root", str(article.root), "axioms", "--check")
    assert rc == 0
    assert "trust boundary OK: 1 interface axiom(s)" in err
    assert out.split() == [*trust.LEAN_CORE, "Article.Interfaces.tail_bound"]


def test_a_declared_axiom_no_ledger_entry_mentions_fails(article):
    """Declared but never reviewed — the case the old inline list could not catch."""
    article.axioms(LEDGER)
    axioms(article, "Article.Interfaces.tail_bound", "Article.Sneaky.shortcut")
    rc, _, err = run_cli("--root", str(article.root), "axioms", "--check")
    assert rc == 1
    assert "1 declared axiom(s)" in err
    assert "Article.Sneaky.shortcut" in err
    assert "tail_bound" not in err.split("declared but never reviewed:")[-1]


def test_grounding_is_matched_on_the_short_name(article):
    """The ledger writes `tail_bound`; the declaration may write the full path."""
    article.axioms(LEDGER.replace("`Article.Interfaces.tail_bound`", "`tail_bound`"))
    axioms(article, "Article.Interfaces.tail_bound")
    rc, _, _ = run_cli("--root", str(article.root), "axioms", "--check")
    assert rc == 0


def test_ungrounded_is_reported_even_without_check(article):
    """The grounding verdict is not a `--check` nicety: an unreviewed axiom fails."""
    article.axioms(LEDGER)
    axioms(article, "Article.Sneaky.shortcut")
    rc, _, err = run_cli("--root", str(article.root), "axioms")
    assert rc == 1 and "Article.Sneaky.shortcut" in err


# --- the readers themselves ----------------------------------------------------------


def test_declared_skips_comments_and_blank_lines(article):
    axioms(article, "one", "", "  # indented comment", "two")
    assert trust.declared(article.cfg) == ["one", "two"]


def test_declared_is_empty_for_a_missing_file(article):
    assert trust.declared(article.cfg) == []
    assert trust.trust_file(article.cfg).name == "trust-boundary.txt"


def test_the_allowlist_is_lean_core_plus_the_declarations(article):
    axioms(article, "Article.Interfaces.tail_bound")
    assert trust.allowlist(article.cfg) == [*trust.LEAN_CORE, "Article.Interfaces.tail_bound"]


def test_only_the_lean_segment_of_an_entry_grounds_a_name(article):
    """Not the whole entry: a name mentioned in the prose is not a reviewed interface."""
    article.axioms(LEDGER.replace("**Lean:** `Article.Interfaces.tail_bound`",
                                  "The Lean side uses `Article.Interfaces.tail_bound`."))
    axioms(article, "Article.Interfaces.tail_bound")
    assert trust.ungrounded(article.cfg) == ["Article.Interfaces.tail_bound"]
