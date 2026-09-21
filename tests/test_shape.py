"""The shape advisories: instruction files hold instructions, not the record (ADR-0001)."""

from __future__ import annotations

from linkage import scaffold, shape


def _write(root, rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_a_freshly_scaffolded_article_has_no_shape_advisory(tmp_path):
    scaffold.init(tmp_path, slug="fresh")
    assert shape.check(tmp_path) == []


def test_dated_record_blocks_in_claude_md_are_reported(tmp_path):
    body = "".join(f"**Wave {i} is merged (2026-09-1{i}).** It proved things.\n\n"
                   for i in range(4))
    _write(tmp_path, "CLAUDE.md", "# x\n\n" + body)
    found = shape.check(tmp_path)
    assert any("4 dated record blocks" in a and "CLAUDE.md" in a for a in found)


def test_three_dated_blocks_are_tolerated(tmp_path):
    body = "".join(f"**Decided 2026-09-1{i}.** A rule.\n\n" for i in range(3))
    _write(tmp_path, "CLAUDE.md", body)
    assert shape.check(tmp_path) == []


def test_a_status_heading_is_reported_and_a_state_heading_is_not(tmp_path):
    _write(tmp_path, "CLAUDE.md", "# x\n\n## Status\n\nstuff\n")
    _write(tmp_path, "README.md", "# x\n\n## State\n\nstuff\n")
    found = shape.check(tmp_path)
    assert len(found) == 1 and "'Status' names a record" in found[0]


def test_the_word_budget_ignores_fenced_code(tmp_path):
    words = " ".join(["word"] * 1400)
    _write(tmp_path, "notes/HANDOFF.md", f"{words}\n```\n{words}\n```\n")
    assert shape.check(tmp_path) == []
    _write(tmp_path, "notes/HANDOFF.md", f"{words} {words}\n")
    found = shape.check(tmp_path)
    assert len(found) == 1 and "2800 words (budget 1500)" in found[0]


def test_session_prompts_and_lessons_files_are_reported(tmp_path):
    _write(tmp_path, "notes/PROMPT-module-b.md", "Paste into a new session.\n")
    _write(tmp_path, "notes/LESSONS-for-article-kit.md", "1. a lesson\n")
    found = shape.check(tmp_path)
    assert any("PROMPT-module-b.md: a session prompt" in a for a in found)
    assert any("LESSONS-for-article-kit.md" in a for a in found)


def test_the_frameworks_own_rules_and_worktrees_are_not_checked(tmp_path):
    big = " ".join(["word"] * 5000)
    _write(tmp_path, ".claude/rules/article-kit/core.md", big)
    _write(tmp_path, ".claude/worktrees/w1/CLAUDE.md", big)
    _write(tmp_path, ".claude/rules/local.md", big)
    found = shape.check(tmp_path)
    assert len(found) == 1 and ".claude/rules/local.md" in found[0]


def test_the_framework_rules_fit_their_own_budget():
    """The rules article-kit ships must pass the check they are exempt from in an article."""
    src = scaffold.scaffold_dir() / "claude" / "rules"
    for p in src.glob("*.md"):
        assert shape.check_file(p, p.name, shape.BUDGETS[".claude/rules/**/*.md"]) == [], p.name
