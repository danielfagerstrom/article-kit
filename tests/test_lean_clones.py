"""`linkage lean clones`: declarations copied between the constellation's Lean members.

The survey this ports (hub `offices/engineer/experiments/lean_overlap.py`) indexed by name,
so the property that matters here is the one it lacked: a clone is found by its statement
text, and renaming it moves nothing except the `renamed` count. Every test builds a
constellation under `tmp_path` (a vault with a `constellation.json`, member repositories
beside it) and never reads a real checkout. `git ls-files` is how the check knows what a
member tracks, so these tests spawn it: the suite's block on `subprocess.run` is lifted for
this file, over tmp trees only.
"""

from __future__ import annotations

import json
import subprocess

import pytest

from conftest import run_cli
from linkage import leanclones

LEMMA = """\
theorem add_zero_twice (x : Nat) (h : x = 0) : x + 0 = x + 0 := by
  subst h
  rfl
"""


@pytest.fixture(autouse=True)
def unblocked(monkeypatch, real_run):
    monkeypatch.setattr(subprocess, "run", real_run)
    return real_run


class Constellation:
    """A vault and its members: `member(slug, {path: text})` makes a checkout."""

    def __init__(self, root):
        self.root = root
        self.vault = root / "vault"
        self.vault.mkdir()
        self.dev = root / "dev"
        self.dev.mkdir()
        self.slugs: list[str] = []

    def member(self, slug, files=None, *, checked_out=True, track=True):
        self.slugs.append(slug)
        if checked_out:
            repo = self.dev / slug
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            for rel, text in (files or {}).items():
                f = repo / rel
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(text, encoding="utf-8")
            if track:
                subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
        self.write_manifest()
        return self

    def write_manifest(self):
        doc = {"version": 1, "workspace": {"root": str(self.dev)},
               "members": [{"slug": s, "dir": s} for s in self.slugs]}
        (self.vault / "constellation.json").write_text(json.dumps(doc), encoding="utf-8")

    def run(self, *args):
        return run_cli("lean", "clones", "--wiki", str(self.vault), *args)

    def report(self, *args):
        rc, out, err = self.run("--json", *args)
        assert out, err
        return rc, json.loads(out)


@pytest.fixture
def world(tmp_path):
    return Constellation(tmp_path)


def _pair(world, a_text, b_text, *, a_file="A/Core.lean", b_file="B/Other.lean"):
    world.member("alpha", {a_file: a_text})
    world.member("beta", {b_file: b_text})
    return world


def _only_pair(doc):
    assert len(doc["pairs"]) == 1
    return doc["pairs"][0]


# ---------------------------------------------------------------- the planted clone

def test_a_planted_clone_is_reported_by_name_and_file(world):
    _pair(world, "namespace Alpha\n\n" + LEMMA + "\nend Alpha\n",
          "import Alpha\n\nnamespace Beta\n\n-- copied\n" + LEMMA + "\nend Beta\n",
          a_file="Alpha/Core.lean", b_file="Beta/Copied.lean")
    rc, out, _ = world.run()
    assert rc == 1
    assert "Alpha.add_zero_twice" in out
    assert "Alpha/Core.lean:3" in out
    assert "Beta/Copied.lean:6" in out
    assert "LEAN CLONE CHECK" not in out  # the verdict goes to stderr on failure


def test_the_failure_verdict_is_on_stderr_and_counts_the_clones(world):
    _pair(world, LEMMA, LEMMA)
    rc, _, err = world.run()
    assert rc == 1
    assert "LEAN CLONE CHECK FAILED: 1 clone(s)" in err


def test_a_clean_constellation_exits_zero(world):
    _pair(world, LEMMA, "theorem other (x : Nat) : x + 1 = 1 + x := Nat.add_comm x 1\n")
    rc, out, _ = world.run()
    assert rc == 0
    assert "LEAN CLONE CHECK OK: 0 clone(s)" in out


# ---------------------------------------------------------------- anchored on the statement

def test_renaming_the_declaration_and_its_variables_does_not_hide_a_clone(world):
    renamed = LEMMA.replace("add_zero_twice", "totally_different").replace("x", "y")
    _pair(world, LEMMA, renamed)
    rc, doc = world.report()
    p = _only_pair(doc)
    assert rc == 1
    assert (p["clones"], p["renamed"], p["renamed_clones"]) == (1, 1, 1)
    m = p["matches"][0]
    assert m["a"]["name"] == "add_zero_twice" and m["b"]["name"] == "totally_different"


def test_a_same_name_clone_is_not_counted_as_renamed(world):
    _pair(world, LEMMA, LEMMA)
    _, doc = world.report()
    p = _only_pair(doc)
    assert (p["clones"], p["renamed"]) == (1, 0)


def test_the_same_statement_proved_differently_is_not_a_clone(world):
    other = LEMMA.replace("subst h\n  rfl", "simp")
    _pair(world, LEMMA, other)
    rc, doc = world.report()
    p = _only_pair(doc)
    assert rc == 0
    assert (p["statement_matches"], p["clones"], p["same_statement"]) == (1, 0, 1)


def test_a_different_statement_under_the_same_name_is_no_match(world):
    other = LEMMA.replace("x + 0 = x + 0", "x + 1 = x + 1")
    _pair(world, LEMMA, other)
    _, doc = world.report()
    assert _only_pair(doc)["statement_matches"] == 0


def test_a_renamed_recursive_declaration_is_still_a_clone(world):
    rec = "def count_down (n : Nat) : Nat :=\n  match n with\n  | 0 => 0\n  | k + 1 => count_down k\n"
    _pair(world, rec, rec.replace("count_down", "tick_down"))
    _, doc = world.report()
    assert _only_pair(doc)["clones"] == 1


def test_definitions_sharing_a_signature_are_not_matched(world):
    """`: Real -> Real` says nothing about which function it is; only the whole text does."""
    _pair(world, "def profile (t : Real) : Real := t * t\n",
          "def weight (t : Real) : Real := t + 1\n")
    _, doc = world.report()
    assert _only_pair(doc)["statement_matches"] == 0


def test_a_copied_definition_is_a_clone_under_another_name(world):
    _pair(world, "def profile (t : Real) : Real := t * t\n",
          "def weight (s : Real) : Real := s * s\n")
    _, doc = world.report()
    p = _only_pair(doc)
    assert (p["clones"], p["renamed_clones"]) == (1, 1)


def test_a_statement_too_short_to_be_evidence_is_not_an_anchor(world):
    _pair(world, "theorem one : True := trivial\n", "theorem two : True := by trivial\n")
    _, doc = world.report()
    assert _only_pair(doc)["statement_matches"] == 0
    _, doc = world.report("--min-tokens", "1")
    assert _only_pair(doc)["same_statement"] == 1


def test_lemma_and_theorem_are_one_kind(world):
    _pair(world, LEMMA, LEMMA.replace("theorem", "lemma"))
    _, doc = world.report()
    assert _only_pair(doc)["statement_matches"] == 1


def test_a_commented_out_declaration_is_not_a_declaration(world):
    _pair(world, "/-\n" + LEMMA + "-/\n-- " + LEMMA.splitlines()[0] + "\n", LEMMA)
    _, doc = world.report()
    assert _only_pair(doc)["statement_matches"] == 0


def test_declarations_are_paired_one_to_one_within_a_statement(world):
    twin = LEMMA + "\n" + LEMMA.replace("add_zero_twice", "add_zero_thrice")
    _pair(world, twin, LEMMA)
    _, doc = world.report()
    p = _only_pair(doc)
    assert p["clones"] == 1
    assert p["matches"][0]["renamed"] is False  # the same-named one is the one paired


# ---------------------------------------------------------------- threshold and exceptions

def test_the_threshold_admits_that_many_clones(world):
    _pair(world, LEMMA, LEMMA)
    assert world.run("--max-clones", "1")[0] == 0
    assert world.run("--max-clones", "0")[0] == 1


def test_a_named_exception_is_not_counted_and_is_still_listed(world):
    _pair(world, LEMMA, LEMMA)
    rc, out, _ = world.run("--allow", "add_zero_twice")
    assert rc == 0
    assert "[excepted: add_zero_twice]" in out
    assert "1 named in the exception list, 0 counted" in out


def test_an_exception_may_name_the_qualified_declaration_on_either_side(world):
    _pair(world, "namespace Alpha\n" + LEMMA + "end Alpha\n", LEMMA.replace("add_zero_twice", "b"))
    assert world.run("--allow", "Alpha.add_zero_twice")[0] == 0
    assert world.run("--allow", "b")[0] == 0
    assert world.run("--allow", "add_zero_twice")[0] == 0
    assert world.run("--allow", "Gamma.add_zero_twice")[0] == 1


def test_an_exception_file_takes_names_and_comments(world, tmp_path):
    _pair(world, LEMMA, LEMMA)
    f = tmp_path / "allow.txt"
    f.write_text("# accepted until E-0009 slice 3\n\nadd_zero_twice  # deliberate\n", "utf-8")
    assert world.run("--allow-file", str(f))[0] == 0


def test_an_exception_that_names_nothing_is_an_advisory_not_a_failure(world):
    _pair(world, LEMMA, "theorem other (x : Nat) : x + 1 = 1 + x := Nat.add_comm x 1\n")
    rc, out, _ = world.run("--allow", "long_gone")
    assert rc == 0
    assert "advisory exception `long_gone` names no statement match" in out


def test_an_excepted_clone_is_marked_in_the_json(world):
    _pair(world, LEMMA, LEMMA)
    _, doc = world.report("--allow", "add_zero_twice")
    p = _only_pair(doc)
    assert (p["clones"], p["excepted"], p["counted"]) == (1, 1, 0)
    assert p["matches"][0]["excepted_by"] == "add_zero_twice"
    assert doc["ok"] is True and doc["stale_allow"] == []


# ---------------------------------------------------------------- the members

def test_every_pair_of_members_is_compared(world):
    world.member("a", {"X.lean": LEMMA})
    world.member("b", {"X.lean": LEMMA})
    world.member("c", {"X.lean": LEMMA})
    _, doc = world.report()
    assert [(p["a"], p["b"], p["clones"]) for p in doc["pairs"]] == [
        ("a", "b", 1), ("a", "c", 1), ("b", "c", 1)]
    assert doc["totals"]["clones"] == 3


def test_members_that_are_not_checked_out_or_have_no_lean_are_set_aside(world):
    world.member("a", {"X.lean": LEMMA})
    world.member("b", {"X.lean": LEMMA})
    world.member("missing", checked_out=False)
    world.member("docs", {"README.md": "no Lean here\n"})
    rc, doc = world.report()
    assert doc["skipped"] == {"not checked out": ["missing"], "no Lean": ["docs"]}
    assert [m["slug"] for m in doc["members"]] == ["a", "b"]
    _, out, _ = world.run()
    assert "set aside, not checked out: missing" in out
    assert "set aside, no Lean: docs" in out


def test_only_tracked_files_are_read(world):
    """`.lake/` packages and agent worktrees are untracked copies, and would be clones of everything."""
    world.member("a", {"X.lean": LEMMA})
    world.member("b", {"Y.lean": "theorem q (x : Nat) : x = x := rfl\n"})
    ignored = world.dev / "b" / ".lake" / "packages" / "a" / "X.lean"
    ignored.parent.mkdir(parents=True)
    ignored.write_text(LEMMA, encoding="utf-8")
    subprocess.run(["git", "add", "-A", "--", "Y.lean"], cwd=world.dev / "b", check=True)
    rc, doc = world.report()
    assert (rc, _only_pair(doc)["statement_matches"]) == (0, 0)


def test_relative_member_directories_resolve_under_the_dev_root_option(world):
    world.member("a", {"X.lean": LEMMA})
    world.member("b", {"X.lean": LEMMA})
    doc = json.loads((world.vault / "constellation.json").read_text("utf-8"))
    doc["workspace"]["root"] = "/nowhere"
    (world.vault / "constellation.json").write_text(json.dumps(doc), encoding="utf-8")
    assert world.run("--dev-root", str(world.dev))[0] == 1
    assert world.run()[0] == 2  # /nowhere holds no member: fewer than two to compare


# ---------------------------------------------------------------- could not answer: exit 2

def test_fewer_than_two_lean_members_is_exit_two_not_a_pass(world):
    world.member("only", {"X.lean": LEMMA})
    rc, _, err = world.run()
    assert rc == 2
    assert err.startswith("CONFIG ERROR") and "no pair to compare" in err


def test_no_vault_is_exit_two(monkeypatch):
    monkeypatch.delenv("WIKI_VAULT", raising=False)
    rc, _, err = run_cli("lean", "clones")
    assert rc == 2
    assert "no wiki vault" in err


def test_the_vault_is_found_through_the_environment(world, monkeypatch):
    _pair(world, LEMMA, LEMMA)
    monkeypatch.setenv("WIKI_VAULT", str(world.vault))
    rc, out, _ = run_cli("lean", "clones")
    assert rc == 1 and "add_zero_twice" in out


def test_a_vault_without_a_constellation_is_exit_two(tmp_path):
    rc, _, err = run_cli("lean", "clones", "--wiki", str(tmp_path))
    assert rc == 2
    assert "no constellation.json" in err


def test_a_malformed_constellation_is_exit_two(tmp_path):
    (tmp_path / "constellation.json").write_text('{"members": [{"name": "x"}]}', "utf-8")
    rc, _, err = run_cli("lean", "clones", "--wiki", str(tmp_path))
    assert rc == 2
    assert "not a constellation manifest" in err


# ---------------------------------------------------------------- the JSON output

def test_the_json_carries_the_counts_the_text_prints(world):
    _pair(world, LEMMA + "\n" + "theorem u (x : Nat) : x * 1 = x := Nat.mul_one x\n",
          LEMMA.replace("add_zero_twice", "renamed_twin"))
    rc, doc = world.report()
    assert rc == 1
    assert set(doc) >= {"ok", "max_clones", "min_tokens", "totals", "members", "skipped",
                        "allow", "stale_allow", "pairs"}
    assert doc["ok"] is False
    assert doc["totals"]["clones"] == 1 and doc["totals"]["renamed"] == 1
    assert [m["declarations"] for m in doc["members"]] == [2, 1]
    m = doc["pairs"][0]["matches"][0]
    assert m["a"]["file"] == "A/Core.lean" and m["b"]["file"] == "B/Other.lean"
    assert m["a"]["line"] == 1


# ---------------------------------------------------------------- the ported parser

def test_the_parser_reads_namespaces_and_spans_of_a_file(tmp_path):
    f = tmp_path / "F.lean"
    f.write_text("""\
namespace Outer
namespace Inner

/-- A docstring. -/
theorem t1 (a : Nat) : a = a := rfl

end Inner

structure S where
  x : Nat

def d (n : Nat) : Nat := n
end Outer
""", encoding="utf-8")
    recs = {r["name"]: r for r in leanclones.parse_file(f, tmp_path)}
    assert recs["t1"]["ns"] == "Outer.Inner" and recs["t1"]["line"] == 5
    assert recs["t1"]["src_lines"] == 2  # the docstring is part of the span
    assert recs["S"]["ns"] == "Outer" and recs["S"]["stmt"] == ""
    assert recs["S"]["proof"] == "x : Nat"  # a structure is cut at `where`
    assert recs["d"]["ns"] == "Outer"


def test_alpha_normalization_collapses_one_letter_variables_only():
    assert leanclones.alpha("(t : Real) (s : Real) : f t = g s") == \
        leanclones.alpha("(x : Real) (y : Real) : h x = k y")
    assert leanclones.alpha("(ε : Real)") != leanclones.alpha("(δ : Real)")
    assert leanclones.alpha("(tt : Real)") != leanclones.alpha("(t : Real)")


def test_the_command_after_a_declaration_is_not_part_of_its_proof(world):
    """The survey's parser read `end Foo` and an unattached `@[simp]` as the proof's tail."""
    _pair(world, LEMMA + "\nend Alpha\n\n@[simp]\ntheorem z (a : Nat) : a = a := rfl\n",
          LEMMA + "\nopen Beta in\ntheorem y (a : Nat) : a + 0 = a := rfl\n")
    _, doc = world.report()
    assert _only_pair(doc)["clones"] == 1
