"""The three standards as plugin skills (hub Q-0544): one source, under the cap, loadable.

`docs/WRITING.md`, `docs/RELEASE.md` and `docs/DRAFTING-GATE.md` stay the text of record; the skills
are rendered from them by `linkage.skills`. What can rot silently, and is held here:

1. a `SKILL.md` edited by hand, or a document edited without re-rendering: the two would drift,
   and a session would draft against a stale copy of the standard;
2. a body grown past the 5,000 tokens Claude Code re-attaches after a compaction, whose tail
   would then be the part silently lost;
3. the frontmatter that makes the gate a forked subagent the session waits for.
"""

from __future__ import annotations

import re
import shutil

import pytest

from conftest import REPO
from linkage import skills

NAMES = ("write", "release", "gate")


def skill_text(name):
    return (REPO / ".claude" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def frontmatter(text):
    m = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    assert m, "no frontmatter"
    return m.group(1)


@pytest.mark.parametrize("name", NAMES)
def test_each_skill_is_what_its_document_renders(name):
    assert skill_text(name) == skills.RENDER[name](), (
        f"{name}/SKILL.md differs from its document: run `uv run python -m linkage.skills`")


@pytest.mark.parametrize("name", NAMES)
def test_each_skill_fits_what_a_compaction_reattaches(name):
    """Held to the budget (chars/4), not the cap: the real tokenizer counts this markdown higher."""
    assert skills.tokens(skill_text(name)) <= skills.TOKEN_BUDGET < skills.TOKEN_CAP


@pytest.mark.parametrize("name", NAMES)
def test_each_skill_names_itself_and_says_when_to_use_it(name):
    fm = frontmatter(skill_text(name))
    assert re.search(rf"(?m)^name: {name}$", fm)
    assert re.search(r"(?m)^description:", fm)


def test_the_write_skill_is_writings_rules_verbatim_restraint_budget_first():
    text = skill_text("write")
    doc = skills.sections("WRITING.md")
    bodies = [s for h, s in doc.items() if h[:2] in ("0.", "1.", "2.", "3.", "4.")]
    assert len(bodies) == 5
    for body in bodies:
        assert body in text
    heads = [ln for ln in text.splitlines() if ln.startswith("## ")]
    assert heads[0].startswith("## 2. The restraint budget")
    assert "## 5." not in text and "## 6." not in text   # on demand, not in the body


def test_the_release_skill_carries_the_rules_and_checklist_not_the_versioning():
    text = skill_text("release")
    doc = skills.sections("RELEASE.md")
    assert doc["The rules"] in text and doc["The checklist"] in text
    assert "## Versioning the framework" not in text and "## The commands" not in text
    assert "RELEASE.md" in text and "The commands" in text   # where the commands are read


def test_the_gate_runs_forked_and_is_waited_for():
    text = skill_text("gate")
    fm = frontmatter(text)
    assert re.search(r"(?m)^context: fork$", fm)
    assert re.search(r"(?m)^background: false$", fm)
    assert "$ARGUMENTS" in text and "edit no file" in text
    assert (REPO / "docs" / "DRAFTING-GATE.md").read_text(encoding="utf-8").strip() in text


@pytest.mark.parametrize("name,doc,old", [
    ("write", "WRITING.md", "## 1. Voice"),
    ("release", "RELEASE.md", "## The checklist"),
    ("gate", "DRAFTING-GATE.md", "## The rule"),
])
def test_an_edited_document_is_caught_as_drift(tmp_path, monkeypatch, name, doc, old):
    """The drift test can fail: a changed line in each document changes its skill's rendering."""
    docs = tmp_path / "docs"
    shutil.copytree(REPO / "docs", docs)
    monkeypatch.setattr(skills, "DOCS", docs)
    before = skills.RENDER[name]()
    p = docs / doc
    text = p.read_text(encoding="utf-8")
    assert old in text
    p.write_text(text.replace(old, old + " (edited)"), encoding="utf-8")
    assert skills.RENDER[name]() != before


def test_the_gate_stops_without_a_section_and_starts_from_the_hub_tool():
    text = skill_text("gate")
    assert "stop and report that" in text and "wiki gate" in text and "this article's own" in text


def test_the_release_skill_says_where_what_it_leaves_out_is():
    head = " ".join(skill_text("release").split("## The rules")[0].split())   # unwrapped
    assert '§ "The commands"' in head and "A paper with a supplement" in head


def test_frontmatter_values_that_are_not_plain_words_are_quoted():
    fm = skills._frontmatter(a="plain", b="x: y", c="<hint>", d="#tag")
    assert "a: plain" in fm and 'b: "x: y"' in fm and 'c: "<hint>"' in fm and 'd: "#tag"' in fm


def test_wrapping_never_starts_a_line_with_markdown_structure_or_splits_a_section_sign():
    words = ("word " * 18 + "- not a bullet " + "word " * 18 + "§ B and § C ") * 3
    for line in skills._wrap(words, 40):
        assert not line.startswith(("- ", "# ", "§")) and not line.endswith("§")


def test_a_missing_section_fails_loudly(tmp_path, monkeypatch):
    docs = tmp_path / "docs"
    shutil.copytree(REPO / "docs", docs)
    monkeypatch.setattr(skills, "DOCS", docs)
    p = docs / "RELEASE.md"
    p.write_text(p.read_text(encoding="utf-8").replace("## The checklist", "## Checklist"),
                 encoding="utf-8")
    with pytest.raises(KeyError, match="The checklist"):
        skills.render_release()
