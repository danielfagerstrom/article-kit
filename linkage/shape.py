"""Instruction files hold instructions, not the record (ADR-0001).

An article repository's `CLAUDE.md`, `README.md`, handoff note and session rules are read by
every later session. Written to by the same sessions, they drift into running accounts of the
work: Paper V's `CLAUDE.md` reached 6,900 words, three quarters of it dated status paragraphs,
and its handoff 14,700. The hub met the same failure on a wiki page and checks for it
(`wiki lint`, check `shape`, hub ADR-0014); this is that check for the article repositories.

Everything here is an **advisory**: a worklist and a signal, never a gate. The thresholds were
set on the repositories of 2026-09-21 so that the pilot's diary-shaped files are reported and the
healthy `CLAUDE.md` of Paper I (1,500 words, no dated blocks) is not.

Independent of the blueprint: it reads the files as text, so it also runs on a repository with
no `linkage.toml` (`linkage shape DIR`).
"""
from __future__ import annotations

import re
from pathlib import Path

# file (glob relative to the root) -> word budget
BUDGETS: dict[str, int] = {
    "CLAUDE.md": 2000,
    "README.md": 1500,
    "notes/HANDOFF*.md": 1500,
    ".claude/rules/**/*.md": 900,
}
RECORD_BLOCKS = 3      # dated bold openers tolerated in one file
# The framework's own rules are checked for drift, not shape, and their shape is article-kit's.
SKIP_PARTS = {"article-kit", "worktrees"}

_DATED_BOLD_RE = re.compile(r"^\s*(?:>\s*)*(?:[-*+]\s+)?\*\*[^*\n]*\b\d{4}-\d{2}-\d{2}\b[^*\n]*\*\*")
_HEADING_RE = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
_RECORD_HEADING_RE = re.compile(
    r"^(?:the\s+)?(?:status|history|progress|changelog|campaign|record|session\s+"
    r"(?:log|record|report)s?|plan'?s\s+state)\b", re.I)
_FENCE_RE = re.compile(r"^\s*(```|~~~)")


def _prose_lines(text: str) -> list[str]:
    """The file's lines outside fenced code blocks."""
    out, fenced = [], False
    for ln in text.splitlines():
        if _FENCE_RE.match(ln):
            fenced = not fenced
            continue
        if not fenced:
            out.append(ln)
    return out


def check_file(path: Path, rel: str, budget: int) -> list[str]:
    """Advisories for one file. A README holds the state, so a Status heading is its to have."""
    lines = _prose_lines(path.read_text(encoding="utf-8", errors="replace"))
    out = []
    words = sum(len(ln.split()) for ln in lines)
    if words > budget:
        out.append(f"[shape] {rel}: {words} words (budget {budget}) — move what is not an "
                   "instruction to its home (PROCESS.md, 'Where each kind of text lives')")
    dated = sum(1 for ln in lines if _DATED_BOLD_RE.match(ln))
    if dated > RECORD_BLOCKS:
        out.append(f"[shape] {rel}: {dated} dated record blocks — history goes to CHANGELOG.md "
                   "and git, state to README.md, the next session's needs to notes/HANDOFF.md")
    for ln in lines:
        m = _HEADING_RE.match(ln)
        if (m and ln.startswith("##") and _RECORD_HEADING_RE.match(m.group(1))
                and not (rel.endswith("README.md") and m.group(1).lower().startswith("status"))):
            out.append(f"[shape] {rel}: heading '{m.group(1)}' names a record — an instruction "
                       "file holds no status or history section")
    return out


def check(root: Path) -> list[str]:
    """Shape advisories for every instruction file under `root`."""
    out: list[str] = []
    seen: set[Path] = set()
    for pattern, budget in BUDGETS.items():
        for path in sorted(root.glob(pattern)):
            rel_parts = path.relative_to(root).parts
            if path in seen or not path.is_file() or SKIP_PARTS & set(rel_parts[:-1]):
                continue
            seen.add(path)
            out.extend(check_file(path, "/".join(rel_parts), budget))
    notes = root / "notes"
    if notes.is_dir():
        for path in sorted(notes.glob("PROMPT-*.md")):
            out.append(f"[shape] notes/{path.name}: a session prompt — a phase starts from "
                       "PROCESS.md and notes/HANDOFF.md; delete it once its session has run")
        for path in sorted(notes.glob("LESSONS*.md")):
            out.append(f"[shape] notes/{path.name}: general lessons go to article-kit's "
                       "WISHLIST.md as process items, not to a file in the repository")
    return out
