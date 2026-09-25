"""The boundary harness — the four checks the repository-wide axiom guard cannot do.

Every test states one way the harness must not be a no-op: it builds an article whose
Lean tree is *almost* right, breaks exactly one thing, and asserts the check names it.
"""

from __future__ import annotations

from conftest import run_cli, tagged
from linkage import boundary

TABLE = """\
[boundary]
guard = "Formalization/Guard.lean"
probes = "Formalization/Probes.lean"
adversarial = "Formalization/Adversarial.lean"
headline = ["Art.main"]
"""

GUARD = """\
import Art

/-- info: 'Art.main' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms Art.main
"""

PROBES = """\
import Art

/-- The headline result applied at a point: it still says something. -/
theorem probe_main_at_zero : Art.main 0 = 0 := by
  simpa using Art.main
"""

ADVERSARIAL = """\
import Art

/-- FALSE: the kernel cannot be both causal and symmetric. If this ever closes, the
development proves a contradiction. -/
theorem adversarial_symmetric_causal : False := sorry
"""

LIB = """\
theorem main : True := trivial
def other : Nat := 0
"""


def built(article, *, table=TABLE, **files):
    """The default good article, with any file replaced by keyword.

    It rewrites `linkage.toml` rather than appending to it, so a test may call it twice
    to compare a good tree against a broken one.
    """
    from fixtures.article import DEFAULT_TOML

    article.file("linkage.toml", DEFAULT_TOML + "\n" + table)
    article.lean(files.get("lib", LIB), "Art.lean")
    article.lean(files.get("guard", GUARD), "Guard.lean")
    article.lean(files.get("probes", PROBES), "Probes.lean")
    article.lean(files.get("adversarial", ADVERSARIAL), "Adversarial.lean")
    return article


def report(article, **kw):
    return boundary.run(article.cfg, **kw)


# --- the opt-in ---------------------------------------------------------------

def test_unconfigured_article_reports_nothing(article):
    rep = report(article)
    assert rep.stats == {"configured": False}
    assert not rep.fatal


def test_cli_exits_zero_when_unconfigured(article):
    rc, out, err = run_cli("--root", str(article.root), "boundary")
    assert rc == 0
    assert "not configured" in err


# --- check 1: per-declaration axiom pins --------------------------------------

def test_good_article_passes(article):
    rep = report(built(article))
    assert rep.fatal == []
    assert rep.stats["pins"] == 1


def test_headline_without_a_pin_fails(article):
    built(article, guard="import Art\n")
    assert any("headline `Art.main` has no pinned" in m
               for m in tagged(report(article).fatal, "axiom-pin"))


def test_unguarded_print_axioms_fails(article):
    """The whole point of check 1: an unpinned line is the old union-only check."""
    built(article, guard="import Art\n\n#print axioms Art.main\n")
    msgs = tagged(report(article).fatal, "axiom-pin")
    assert any("is not under a `#guard_msgs in`" in m for m in msgs)


def test_pin_on_an_undeclared_axiom_fails(article):
    """A pin edited to accept a new axiom does not pass on its own say-so."""
    built(article, guard=GUARD.replace(
        "Quot.sound]", "Quot.sound, Art.bigAssumption]"))
    msgs = tagged(report(article).fatal, "axiom-pin")
    assert any("Art.bigAssumption" in m and "does not declare" in m for m in msgs)


def test_declared_interface_axiom_is_accepted(article):
    built(article, guard=GUARD.replace("Quot.sound]", "Quot.sound, Art.interface]"))
    article.trust("Art.interface")
    article.axioms("# Ledger\n\n## A1\n\nAn interface.\n\n**Lean:** `Art.interface`\n\n"
                   "**Verbatim:** as printed.\n\n**Cite:** @a2020 — Thm 1, p. 1\n")
    assert tagged(report(article).fatal, "axiom-pin") == []


def test_sorry_in_a_pin_fails(article):
    built(article, guard=GUARD.replace("Quot.sound]", "Quot.sound, sorryAx]"))
    assert any("sorryAx" in m for m in tagged(report(article).fatal, "axiom-pin"))


def test_pin_whose_expectation_names_another_declaration_fails(article):
    built(article, guard=GUARD.replace("'Art.main' depends", "'Art.other' depends"))
    assert any("copied and not edited" in m
               for m in tagged(report(article).fatal, "axiom-pin"))


def test_stale_pin_fails(article):
    built(article, guard=GUARD.replace("Art.main", "Art.deleted"))
    assert any("declared nowhere" in m for m in tagged(report(article).fatal, "axiom-pin"))


def test_guard_msgs_without_an_expectation_fails(article):
    built(article, guard="import Art\n\n#guard_msgs in\n#print axioms Art.main\n")
    assert any("no readable expectation" in m
               for m in tagged(report(article).fatal, "axiom-pin"))


def test_each_pin_reads_its_own_expectation(article):
    """A second pin must not be read against the first one's docstring."""
    text = (
        "/-- info: 'A.one' depends on axioms: [propext] -/\n"
        "#guard_msgs in\n#print axioms A.one\n\n"
        "/-- info: 'A.two' depends on axioms: [propext, Quot.sound] -/\n"
        "#guard_msgs in\n#print axioms A.two\n")
    got = {p.decl: (p.expect_decl, p.axioms) for p in boundary.pins(text)}
    assert got == {"A.one": ("A.one", ("propext",)),
                   "A.two": ("A.two", ("propext", "Quot.sound"))}


def test_axiom_free_pin_reads_as_the_empty_set(article):
    text = ("/-- info: 'Art.main' does not depend on any axioms -/\n"
            "#guard_msgs in\n#print axioms Art.main\n")
    assert boundary.pins(text)[0].axioms == ()


# --- check 2: positive probes -------------------------------------------------

def test_headline_without_a_probe_fails(article):
    built(article, probes="import Art\n\ntheorem probe_other : True := trivial\n")
    assert any("has no positive probe" in m for m in tagged(report(article).fatal, "probe"))


def test_probe_stated_as_True_fails(article):
    """A probe degenerated to `True` builds forever and witnesses nothing."""
    built(article, probes="import Art\n\ntheorem probe_main : Art.main → True := by\n"
                          "  intro _; trivial\n")
    # Mentions the headline, so coverage is satisfied; the statement is not vacuous
    # (the arrow's head is), so this one must pass, and the bare form must not.
    assert tagged(report(article).fatal, "probe") == []
    built(article, probes="import Art\n\ntheorem probe_main : True := trivial\n")
    msgs = tagged(report(article).fatal, "probe")
    assert any("stated as `True`" in m for m in msgs)


def test_sorry_probe_fails(article):
    built(article, probes="import Art\n\ntheorem probe_main : Art.main 0 = 0 := sorry\n")
    assert any("is a `sorry`" in m for m in tagged(report(article).fatal, "probe"))


def test_probe_as_an_axiom_fails(article):
    built(article, probes="import Art\n\naxiom probe_main : Art.main 0 = 0\n")
    assert any("is an `axiom`" in m for m in tagged(report(article).fatal, "probe"))


def test_empty_probe_file_fails(article):
    built(article, probes="import Art\n")
    assert any("declares no probes" in m for m in tagged(report(article).fatal, "probe"))


def test_missing_probe_file_fails(article):
    built(article)
    (article.root / "Formalization" / "Probes.lean").unlink()
    assert any("does not exist" in m for m in tagged(report(article).fatal, "probes"))


# --- check 3: adversarial goals -----------------------------------------------

def test_adversarial_goal_that_became_provable_fails(article):
    """The load-bearing test: a known-false goal that closes means unsoundness."""
    built(article, adversarial=ADVERSARIAL.replace(
        ":= sorry", ":= by exact absurd rfl (by simp)"))
    msgs = tagged(report(article).fatal, "adversarial")
    assert any("no longer a `sorry`" in m for m in msgs)
    assert any("unsound" in m for m in msgs)


def test_adversarial_goals_stay_sorry(article):
    assert tagged(report(built(article)).fatal, "adversarial") == []
    assert report(article).stats["adversarial"] == 1


def test_importing_the_adversarial_file_fails(article):
    built(article, lib=LIB + "\nimport Adversarial\n")
    assert any("imports `Adversarial`" in m
               for m in tagged(report(article).fatal, "adversarial"))


def test_undocumented_adversarial_goal_is_an_advisory(article):
    built(article, adversarial="import Art\n\ntheorem adv : False := sorry\n")
    rep = report(article)
    assert tagged(rep.fatal, "adversarial") == []
    assert any("no comment saying why it is false" in m
               for m in tagged(rep.advisory, "adversarial"))


def test_no_adversarial_file_is_an_advisory(article):
    article.boundary(TABLE.replace('adversarial = "Formalization/Adversarial.lean"\n', ""))
    article.lean(LIB, "Art.lean")
    article.lean(GUARD, "Guard.lean")
    article.lean(PROBES, "Probes.lean")
    rep = report(article)
    assert tagged(rep.fatal, "adversarial") == []
    assert tagged(rep.advisory, "adversarial")


# --- check 4: definition scrutiny ---------------------------------------------

SHADOWING = "theorem main : True := trivial\ndef convolution (f : Nat) : Nat := f\n"


def test_shadowed_standard_notion_is_reported(article):
    built(article, lib=SHADOWING)
    rep = report(article)
    assert any("`def convolution`" in m for m in tagged(rep.advisory, "shadow"))
    assert tagged(rep.fatal, "shadow") == []
    assert rep.stats["shadows"] == 1


def test_strict_shadows_makes_it_fatal(article):
    built(article, lib=SHADOWING)
    assert tagged(report(article, strict_shadows=True).fatal, "shadow")


def test_acknowledged_shadow_is_accepted(article):
    built(article, lib=SHADOWING)
    article.boundary('[boundary.shadows]\nconvolution = "ours is the causal '
                     'half-line convolution; mathlib\'s is two-sided"\n')
    rep = report(article, strict_shadows=True)
    assert tagged(rep.fatal, "shadow") == []
    assert rep.stats["shadows"] == 0


def test_shadow_acknowledgement_needs_a_reason(article):
    built(article, lib=SHADOWING)
    article.boundary('[boundary.shadows]\nconvolution = ""\n')
    assert any("empty reason" in m for m in tagged(report(article).fatal, "shadow"))


def test_stale_shadow_acknowledgement_is_an_advisory(article):
    built(article)
    article.boundary('[boundary.shadows]\nconvolution = "long since renamed"\n')
    assert any("no longer declares" in m for m in tagged(report(article).advisory, "shadow"))


def test_article_extends_the_standard_notion_list(article):
    built(article, table=TABLE + 'standard_notions_extra = ["other"]\n')
    assert any("`def Art.other`" in m or "`def other`" in m
               for m in tagged(report(article).advisory, "shadow"))


# --- the CLI ------------------------------------------------------------------

def test_cli_reports_and_exits(article):
    built(article)
    rc, out, err = run_cli("--root", str(article.root), "boundary")
    assert rc == 0, out + err
    assert "BOUNDARY HARNESS OK" in out

    built(article, guard="import Art\n")
    rc, out, err = run_cli("--root", str(article.root), "boundary")
    assert rc == 1
    assert "BOUNDARY HARNESS FAILED" in out


# --- the readers --------------------------------------------------------------

def test_declarations_split_on_the_next_declaration():
    decls = boundary.declarations(
        "/-- why -/\ntheorem a : True := trivial\n\n-- note\nexample : True := trivial\n")
    assert [(d.kind, d.name) for d in decls] == [("theorem", "a"), ("example", None)]
    assert decls[0].doc.startswith("/--")
    assert decls[1].doc == "-- note"


def test_backticked_sorry_in_a_docstring_is_not_a_sorry():
    d = boundary.declarations("/-- `sorry`-free -/\ntheorem a : True := trivial\n")[0]
    assert not d.is_sorry
