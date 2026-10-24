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
    found = [a for a in shape.check(tmp_path) if "resident instructions" not in a]
    assert len(found) == 1 and ".claude/rules/local.md" in found[0]


SCOPED = '---\npaths:\n  - "paper*/**"\n---\n\n'


def test_the_resident_layer_is_claude_md_its_imports_and_the_unscoped_rules(tmp_path):
    """Loaded at launch, re-injected after a compaction (code.claude.com/docs/en/memory)."""
    _write(tmp_path, "CLAUDE.md", "# x\n\nSee @notes/extra.md for more; not `@notes/quoted.md`.\n")
    _write(tmp_path, "notes/extra.md", "imported\n")
    _write(tmp_path, "notes/quoted.md", "a path in a code span is not an import\n")
    _write(tmp_path, ".claude/rules/article-kit/core.md", "framework, unscoped\n")
    _write(tmp_path, ".claude/rules/local.md", "unscoped\n")
    _write(tmp_path, ".claude/rules/writing.md", SCOPED + "scoped: on demand\n")
    got = {p.relative_to(tmp_path.resolve()).as_posix() for p in shape.resident(tmp_path)}
    assert got == {"CLAUDE.md", "notes/extra.md", ".claude/rules/article-kit/core.md",
                   ".claude/rules/local.md"}


def test_an_at_sign_that_is_no_import_does_not_break_the_check(tmp_path):
    _write(tmp_path, "CLAUDE.md", "Mail me@example.org; ask @~no-such-user-xyz/f.md or @"
           + "a" * 300 + ".md\n")
    assert [p.name for p in shape.resident(tmp_path)] == ["CLAUDE.md"]


def test_the_resident_sum_is_reported_over_budget_and_not_under(tmp_path):
    _write(tmp_path, "CLAUDE.md", "# x\n\n" + "word " * 1200 + "\n")
    _write(tmp_path, ".claude/rules/article-kit/core.md", "word " * 700 + "\n")
    assert not [a for a in shape.check(tmp_path) if "resident instructions" in a]
    _write(tmp_path, ".claude/rules/local.md", "word " * 200 + "\n")
    found = [a for a in shape.check(tmp_path) if "resident instructions" in a]
    assert len(found) == 1 and "2102 words" in found[0] and "in 3 file(s)" in found[0]



def test_the_resident_line_budget_binds_on_its_own(tmp_path):
    _write(tmp_path, "CLAUDE.md", "w\n" * 250)   # 250 words: far under the word budget
    found = [a for a in shape.check(tmp_path) if "resident instructions" in a]
    assert len(found) == 1 and "250 words, 250 lines" in found[0]


def test_imports_stop_at_four_hops_and_take_trailing_punctuation_and_escaped_spaces(tmp_path):
    # Relative to the importing file, as the memory docs say.
    _write(tmp_path, "CLAUDE.md", "See @a1.md. Also @Design\\ Docs/api.md\n")
    for i in range(1, 7):
        _write(tmp_path, f"a{i}.md", f"next @a{i + 1}.md\n")
    _write(tmp_path, "Design Docs/api.md", "imported through an escaped space\n")
    got = {p.relative_to(tmp_path.resolve()).as_posix() for p in shape.resident(tmp_path)}
    assert {"a1.md", "a2.md", "a3.md", "a4.md"} <= got and "a5.md" not in got
    assert "Design Docs/api.md" in got


def test_a_scoped_rule_does_not_count_towards_the_resident_sum(tmp_path):
    _write(tmp_path, ".claude/rules/writing.md", SCOPED + "word " * 2500 + "\n")
    assert not [a for a in shape.check(tmp_path) if "resident instructions" in a]


def test_a_read_first_pointer_to_a_long_file_is_reported(tmp_path):
    _write(tmp_path, "docs/LONG.md", "x" * (4 * shape.POINTER_TOKENS + 400))
    _write(tmp_path, "docs/SHORT.md", "x" * 400)
    _write(tmp_path, ".claude/rules/article-kit/writing.md", SCOPED
           + "**Before drafting any prose, read `docs/LONG.md` in full**, and `docs/SHORT.md`"
           " first.\n\nThe release discipline is `docs/LONG.md`.\n")
    found = [a for a in shape.check(tmp_path) if "tells the session to read" in a]
    assert len(found) == 1
    assert ".claude/rules/article-kit/writing.md:6" in found[0] and "`docs/LONG.md`" in found[0]
    assert "the fix is article-kit's" in found[0]


def test_a_pointer_without_a_read_first_or_to_a_missing_file_is_not(tmp_path):
    _write(tmp_path, "docs/LONG.md", "x" * (4 * shape.POINTER_TOKENS + 400))
    _write(tmp_path, "CLAUDE.md", "The standard is `docs/LONG.md`.\n\n"
           "Read `../sibling/docs/GONE.md` before starting.\n\n"
           "```\nread docs/LONG.md before anything\n```\n")
    assert not [a for a in shape.check(tmp_path) if "tells the session to read" in a]


def test_a_pointer_is_reported_at_its_own_line_and_only_after_the_read(tmp_path):
    _write(tmp_path, "docs/BIG.md", "x" * (4 * shape.POINTER_TOKENS + 400))
    _write(tmp_path, "CLAUDE.md", "# x\n\n- one\n- two\n- three\n- Read `docs/BIG.md` before"
           " acting.\n\nThe first section of `docs/BIG.md` is read by reviewers.\n")
    found = [a for a in shape.check(tmp_path) if "tells the session to read" in a]
    assert len(found) == 1 and "CLAUDE.md:6:" in found[0]


def test_inline_dated_accounts_in_a_resident_file_are_reported(tmp_path):
    body = "".join(f"- A rule (the author's decision of 2026-10-0{i}, after a failure).\n"
                   for i in range(1, 7))
    _write(tmp_path, "CLAUDE.md", "# x\n\n" + body)
    found = [a for a in shape.check(tmp_path) if "inline dated account" in a]
    assert len(found) == 1 and "6 line(s)" in found[0] and "lines 3, 4, 5, 6, 7, 8" in found[0]


def test_a_clean_resident_file_and_the_cases_that_are_not_inline_dates(tmp_path):
    _write(tmp_path, "CLAUDE.md", "# x\n\n**Decided 2026-09-10.** A rule.\n\n"
           "```\ngit log --since 2026-09-01\n```\n\nThe author decides.\n")
    _write(tmp_path, ".claude/rules/article-kit/core.md", "Framework text, 2026-10-04.\n")
    _write(tmp_path, ".claude/rules/writing.md", SCOPED + "Scoped, 2026-10-04.\n")
    assert not [a for a in shape.check(tmp_path) if "inline dated account" in a]


def test_a_date_in_a_code_span_is_not_an_account_and_one_after_a_bold_opener_is(tmp_path):
    _write(tmp_path, "CLAUDE.md", "# x\n\nNotes are `offices/notes/2026-10-23-load.md`.\n\n"
           "**Decided 2026-09-10.** A rule (the author's decision of that day).\n")
    found = [a for a in shape.check(tmp_path) if "inline dated account" in a]
    assert len(found) == 1 and "1 line(s)" in found[0] and "(lines 5)" in found[0]


def test_the_frameworks_own_pointers_are_measured_against_article_kits_docs(tmp_path):
    """The scaffold's rules, installed as a sync installs them, beside a copy of this
    repository's docs at `../article-kit/docs/`, send a session to no long file before it acts:
    `writing.md`'s "read WRITING.md in full" became `/article-kit:write` (hub Q-0544). So that
    this cannot pass by the check going blind, the same setup with one rule re-pointed at
    WRITING.md must report it."""
    import shutil
    article = tmp_path / "article"
    rules = article / ".claude" / "rules" / "article-kit"
    shutil.copytree(scaffold.scaffold_dir() / "claude" / "rules", rules)
    shutil.copytree(scaffold.scaffold_dir().parent / "docs", tmp_path / "article-kit" / "docs")
    assert shape.check_pointers(article) == []
    _write(rules, "planted.md", "Read `../article-kit/docs/WRITING.md` in full before drafting.\n")
    found = shape.check_pointers(article)
    assert len(found) == 1 and "planted.md:1" in found[0] and "the fix is article-kit's" in found[0]


def test_the_framework_rules_fit_their_own_budget():
    """The rules article-kit ships must pass the check they are exempt from in an article."""
    src = scaffold.scaffold_dir() / "claude" / "rules"
    for p in src.glob("*.md"):
        assert shape.check_file(p, p.name, shape.BUDGETS[".claude/rules/**/*.md"]) == [], p.name
