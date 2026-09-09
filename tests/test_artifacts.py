"""The side inputs: Lean sources, the axiom ledger, the paper, lake, git.

These readers are dialect-independent — they survive a change of blueprint format — so
they are tested against their own file grammars rather than through the checks.
"""

from __future__ import annotations

import json
import subprocess

import pytest

from linkage import artifacts

# --- Lean declarations ---------------------------------------------------------------


def test_every_declaration_keyword_is_recognised(article):
    article.lean("""
theorem plain : True := trivial
lemma a_lemma : True := trivial
def a_def := 1
abbrev an_abbrev := 2
structure AStruct where
instance an_instance : Inhabited Nat := ⟨0⟩
axiom an_axiom : True
@[simp] private noncomputable def decorated := 3
""")
    assert artifacts.lean_declared_names(article.cfg) == {
        "plain", "a_lemma", "a_def", "an_abbrev", "AStruct", "an_instance", "an_axiom",
        "decorated",
    }


def test_declarations_are_collected_from_every_file_but_not_from_build_output(article):
    article.lean("theorem one : True := trivial\n", name="One.lean")
    article.lean("theorem two : True := trivial\n", name="Sub/Two.lean")
    article.lean("theorem built : True := trivial\n", name=".lake/build/Three.lean")
    assert artifacts.lean_declared_names(article.cfg) == {"one", "two"}


def test_a_named_shared_package_is_scanned(article):
    article.file("linkage.toml", article.root.joinpath("linkage.toml").read_text("utf-8")
                 + '\nlean_packages = ["shared"]\n')
    article.lean("theorem mine : True := trivial\n")
    article.lean("theorem theirs : True := trivial\n", name=".lake/packages/shared/S.lean")
    assert artifacts.lean_declared_names(article.cfg) == {"mine", "theirs"}


def test_a_missing_shared_package_fails_loudly(article):
    article.file("linkage.toml", article.root.joinpath("linkage.toml").read_text("utf-8")
                 + '\nlean_packages = ["shared"]\n')
    with pytest.raises(artifacts.MissingLeanPackage, match="lake build"):
        artifacts.lean_declared_names(article.cfg)


# --- the axiom ledger ----------------------------------------------------------------


LEDGER = """\
# Axiom ledger

## A1

An interface.

**Lean:** `Article.tail_bound`, `Article.consequence`

**Cite:** @author2020 — Thm 3.1, p. 88 · @other2019 — §4 (corroboration)

## A2

Another.

**Cite:** — pending (source not yet pinned)

## A3

A third.

Nothing else.
"""


def test_the_primary_citation_is_the_first_segment_of_the_cite_line(article):
    article.axioms(LEDGER)
    e = artifacts.ledger_entries(article.cfg)["A1"]
    assert (e.citekey, e.anchor) == ("author2020", "Thm 3.1, p. 88")
    assert e.has_cite_line


def test_a_pending_citation_is_a_line_with_no_citekey(article):
    article.axioms(LEDGER)
    e = artifacts.ledger_entries(article.cfg)["A2"]
    assert e.has_cite_line and e.citekey is None and e.anchor is None


def test_an_entry_with_no_cite_line_is_flagged_not_dropped(article):
    article.axioms(LEDGER)
    entries = artifacts.ledger_entries(article.cfg)
    assert set(entries) == {"A1", "A2", "A3"}
    assert entries["A3"].has_cite_line is False


def test_the_entry_id_shape_is_configurable(article):
    article.file("linkage.toml", 'slug = "test"\n\n[blueprint]\nledger_key = "L-[a-z]+"\n')
    article.axioms("## L-tail\n\n**Cite:** @a2020 — p. 1\n")
    assert set(artifacts.ledger_entries(article.cfg)) == {"L-tail"}


# --- render-safe commands ------------------------------------------------------------


def test_macro_definitions_and_the_vetted_allowlist_are_unioned(article):
    article.macros(r"""
\newcommand{\aa}{1}
\providecommand{\bb}{2}
\renewcommand{\cc}{3}
""")
    article.allowlist("# a comment\nfrac\n\n  int  \n")
    assert artifacts.render_safe_commands(article.cfg) == {"aa", "bb", "cc", "frac", "int"}


def test_macros_are_read_through_input(article):
    article.macros("\\input{notation}\n")
    article.file("blueprint/src/notation.tex", r"\newcommand{\zz}{0}" + "\n")
    assert "zz" in artifacts.render_safe_commands(article.cfg)


# --- paper markers -------------------------------------------------------------------


PAPER = """\
Some prose.

% shared with blueprint thm:a
\\begin{theorem}
  \\label{thm:a}
  First.
\\end{theorem}

% shared with blueprint thm:b@0123456789ab, thm:c
\\begin{proposition}
  \\label{thm:merged}
  Second.
\\end{proposition}
"""


def test_markers_carry_labels_pins_line_numbers_and_the_marked_statement(article):
    article.paper(PAPER)
    a, b = artifacts.paper_markers(article.cfg)
    assert (a.file, a.line) == ("paper.tex", 3)
    assert a.blueprint_labels == ["thm:a"] and a.pinned == {}
    assert a.statement_label == "thm:a" and a.shared_statement == "First."
    assert b.blueprint_labels == ["thm:b", "thm:c"]
    assert b.pinned == {"thm:b": "0123456789ab"}
    assert b.statement_label == "thm:merged"


def test_markers_are_collected_from_every_paper_file_in_name_order(article):
    article.paper("% shared with blueprint thm:b\n", name="02-second.tex")
    article.paper("% shared with blueprint thm:a\n", name="01-first.tex")
    article.root.joinpath("paper/paper.tex").unlink()
    assert [m.file for m in artifacts.paper_markers(article.cfg)] == \
        ["01-first.tex", "02-second.tex"]


def test_pin_shared_rewrites_only_the_requested_markers(article):
    article.paper(PAPER)
    n = artifacts.pin_shared(article.cfg, {"thm:a": "aaaaaaaaaaaa", "thm:c": "cccccccccccc"},
                             only={"paper.tex:3"})
    text = article.root.joinpath("paper/paper.tex").read_text(encoding="utf-8")
    assert n == 1
    assert "% shared with blueprint thm:a@aaaaaaaaaaaa" in text
    assert "% shared with blueprint thm:b@0123456789ab, thm:c\n" in text


def test_pin_shared_repins_a_moved_label(article):
    article.paper(PAPER)
    artifacts.pin_shared(article.cfg, {"thm:b": "bbbbbbbbbbbb", "thm:c": "cccccccccccc"},
                         only={"paper.tex:9"})
    text = article.root.joinpath("paper/paper.tex").read_text(encoding="utf-8")
    assert "thm:b@bbbbbbbbbbbb, thm:c@cccccccccccc" in text


# --- control characters --------------------------------------------------------------


def test_only_hand_written_source_suffixes_are_scanned(article):
    article.root.joinpath("paper/data.csv").write_bytes(b"a\tb\n")
    article.root.joinpath("paper/note.md").write_bytes(b"a\tb\n")
    assert [c.path for c in artifacts.control_chars(article.cfg)] == ["paper/note.md"]


def test_a_control_character_is_located_by_line(article):
    article.root.joinpath("paper/x.tex").write_bytes(b"one\ntwo\nth\x0cree\n")
    (cc,) = artifacts.control_chars(article.cfg)
    assert (cc.line, cc.char) == (3, 0x0C)
    assert "th" in cc.context


# --- lake packages and git provenance ------------------------------------------------


def test_lake_package_sources_reads_the_resolved_revision(article):
    article.file("linkage.toml", article.root.joinpath("linkage.toml").read_text("utf-8")
                 + '\nlean_packages = ["shared"]\n')
    article.file("Formalization/lake-manifest.json", json.dumps({"packages": [
        {"name": "shared", "url": "https://example.invalid/shared", "rev": "deadbeef",
         "inputRev": "main"},
    ]}))
    (row,) = artifacts.lake_package_sources(article.cfg)
    assert row["url"] == "https://example.invalid/shared"
    assert row["rev"] == "deadbeef"          # the resolved sha, never the moving tag
    assert row["present"] is False


def test_no_lake_manifest_is_not_an_error(article):
    assert artifacts.lake_package_sources(article.cfg) == []


def test_git_provenance_degrades_when_git_is_unavailable(article, monkeypatch):
    def _no_git(*a, **kw):
        raise OSError("git not found")

    monkeypatch.setattr(subprocess, "run", _no_git)
    assert artifacts.git_provenance(article.root) == {"source_commit": None,
                                                      "source_dirty": False}
