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

**The instruction budget** (hub Q-0542, from the engineer office's E-0019) is stated from how
Claude Code loads files ("What survives compaction", code.claude.com/docs/en/context-window;
code.claude.com/docs/en/memory). `CLAUDE.md` and every rule without `paths:` are *resident*:
loaded at launch and re-injected after a compaction, so they are paid on every turn and are the
only text certain to be in force late in a long session. A file a session read is not: after a
compaction Claude Code re-reads at most five of the files it read or edited, the most recently
modified first, and "a file over 5,000 tokens comes back as a path reference without its
content". Three advisories follow from that: the resident sum against its budget, a "read …
before / in full / first" pointer whose target is over 5,000 tokens, and inline dated accounts
in a resident file. Tokens are estimated as characters / 4, which is what the measurement behind
the budget used; these files run about 1.7 tokens per word.

The resident count is an approximation of what Claude Code loads, close enough for a budget:
it counts frontmatter and HTML comments, which Claude Code strips, and follows `@` imports from
rules as well as from `CLAUDE.md`.
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

# The resident layer: what Claude Code loads at launch and re-injects after a compaction.
RESIDENT_FILES = ("CLAUDE.md", ".claude/CLAUDE.md", "CLAUDE.local.md")
RESIDENT_WORDS = 2000  # summed over the resident files, framework rules included
RESIDENT_LINES = 200   # the memory docs' "target under 200 lines per CLAUDE.md file", summed
POINTER_TOKENS = 5000  # a read file over this comes back after a compaction as a path only
IMPORT_DEPTH = 4       # `@path` imports: "a maximum depth of four hops" (memory docs)

_DATED_BOLD_RE = re.compile(r"^\s*(?:>\s*)*(?:[-*+]\s+)?\*\*[^*\n]*\b\d{4}-\d{2}-\d{2}\b[^*\n]*\*\*")
_HEADING_RE = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
_RECORD_HEADING_RE = re.compile(
    r"^(?:the\s+)?(?:status|history|progress|changelog|campaign|record|session\s+"
    r"(?:log|record|report)s?|plan'?s\s+state)\b", re.I)
_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_PATHS_FM_RE = re.compile(r"\A---\s*\n(?:.*\n)*?paths\s*:", re.M)
_FM_END_RE = re.compile(r"\A---\s*\n(?:.*\n)*?---\s*(?:\n|\Z)")
_CODE_SPAN_RE = re.compile(r"`[^`\n]*`")
# `\ ` is an escaped space inside a path (`@Design\ Docs/api.md`, the memory docs' example).
_IMPORT_RE = re.compile(r"(?:^|(?<=\s))@((?:\\ |[^\s`)\]])+)")
_ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_DECISION_OF_RE = re.compile(r"\bthe author['’]s decision of\b", re.I)
# A sentence that tells the session to read something before it acts, or to read all of it.
_READ_RE = re.compile(r"\bread\b", re.I)
_BEFORE_RE = re.compile(r"\b(?:before|in full|first)\b", re.I)
_MD_TARGET_RE = re.compile(r"`([^`\s]+\.md)(?:#[^`]*)?`|\]\(([^)\s]+\.md)(?:#[^)]*)?\)")
_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")


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


def _tokens(text: str) -> int:
    return len(text) // 4


def _skipped(rel_parts: tuple[str, ...]) -> bool:
    return "worktrees" in rel_parts[:-1]


def _is_scoped(text: str) -> bool:
    """A rule with `paths:` frontmatter loads on demand, not at launch."""
    m = _FM_END_RE.match(text)
    return bool(m and _PATHS_FM_RE.match(m.group(0)))


def _imports(path: Path, text: str) -> list[Path]:
    """The files a memory file pulls in with `@path` (code spans and fences excluded)."""
    out = []
    for ln in _prose_lines(text):
        for m in _IMPORT_RE.finditer(_CODE_SPAN_RE.sub("", ln)):
            # A sentence may end on the path ("see @README.md."), and `\ ` is a space.
            raw = m.group(1).replace("\\ ", " ").rstrip(".,;:")
            try:   # `~nobody` raises, an over-long token is an OSError: neither is an import
                target = Path(raw).expanduser()
                target = target if target.is_absolute() else path.parent / target
                if target.is_file():
                    out.append(target.resolve())
            except (RuntimeError, OSError):
                continue
    return out


def resident(root: Path) -> list[Path]:
    """The files Claude Code loads at launch in `root` and re-injects after a compaction:
    `CLAUDE.md` (and its `.claude/` and `.local` siblings), what they import, and every rule
    under `.claude/rules/` without `paths:` frontmatter, the framework's own included."""
    seen: dict[Path, None] = {}
    todo = [(root / rel, 0) for rel in RESIDENT_FILES if (root / rel).is_file()]
    rules = root / ".claude" / "rules"
    if rules.is_dir():
        for path in sorted(rules.rglob("*.md")):
            if (path.is_file() and not _skipped(path.relative_to(root).parts)
                    and not _is_scoped(path.read_text(encoding="utf-8", errors="replace"))):
                todo.append((path, 0))
    while todo:
        path, depth = todo.pop(0)
        path = path.resolve()
        if path in seen:
            continue
        seen[path] = None
        if depth < IMPORT_DEPTH:
            text = path.read_text(encoding="utf-8", errors="replace")
            todo.extend((p, depth + 1) for p in _imports(path, text))
    return list(seen)


def resident_load(root: Path) -> tuple[int, int, int, int]:
    """(files, words, lines, tokens) of the resident layer: everything in it, code included,
    since all of it is in context."""
    files = resident(root)
    texts = [p.read_text(encoding="utf-8", errors="replace") for p in files]
    return (len(files), sum(len(t.split()) for t in texts),
            sum(len(t.splitlines()) for t in texts), sum(_tokens(t) for t in texts))


def resident_summary(root: Path) -> str:
    """One line for `linkage check` and `linkage shape`, printed whether or not it is over."""
    n, words, lines, tokens = resident_load(root)
    return (f"Resident instructions: {words} words, {lines} lines (~{tokens} tokens) in {n} "
            f"file(s), loaded at launch and after every compaction (budget {RESIDENT_WORDS} "
            f"words, {RESIDENT_LINES} lines).")


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def check_resident(root: Path) -> list[str]:
    """The resident sum against its budget."""
    n, words, lines, tokens = resident_load(root)
    if words <= RESIDENT_WORDS and lines <= RESIDENT_LINES:
        return []
    return [f"[shape] resident instructions: {words} words, {lines} lines (~{tokens} tokens) "
            f"in {n} file(s) (budget {RESIDENT_WORDS} words, {RESIDENT_LINES} lines) — "
            "CLAUDE.md and every rule without `paths:` are paid on every turn; move what one "
            "phase needs into a path-scoped rule or a skill, and history to adr/ and "
            "CHANGELOG.md (PROCESS.md, 'Where each kind of text lives')"]


def _paragraphs(text: str):
    """(line_of, paragraph text) for the prose outside fences and frontmatter, a paragraph being
    a run of non-blank lines joined by spaces; `line_of(i)` is the file line of character `i`."""
    m = _FM_END_RE.match(text)
    offset = m.group(0).count("\n") if m else 0
    para: list[tuple[int, str]] = []
    fenced = False

    def emit():
        starts, joined, pos = [], [], 0
        for lineno, ln in para:
            starts.append((pos, lineno))
            joined.append(ln)
            pos += len(ln) + 1
        return (lambda i: max(n for p, n in starts if p <= i)), " ".join(joined)

    for i, ln in enumerate(text.splitlines()[offset:], start=offset + 1):
        if _FENCE_RE.match(ln):
            fenced = not fenced
            continue
        if fenced:
            continue
        if ln.strip():
            para.append((i, ln.strip()))
        elif para:
            yield emit()
            para = []
    if para:
        yield emit()


def _sentences(para: str):
    """(start offset, sentence) for each sentence of a paragraph."""
    pos = 0
    for m in _SENTENCE_END_RE.finditer(para):
        yield pos, para[pos:m.start()]
        pos = m.end()
    yield pos, para[pos:]


def _resolve(root: Path, path: Path, target: str) -> Path | None:
    for base in (root, path.parent):
        cand = (base / target)
        if cand.is_file():
            return cand.resolve()
    return None


def check_pointers(root: Path) -> list[str]:
    """Each "read … before / in full / first" pointer, in a resident file or a rule, whose
    target is over POINTER_TOKENS: a sentence holding "read" and one of those words, with the
    target after the "read" (so "the first section of X is read by …" is no pointer).
    Unresolvable targets (a sibling checkout that is not there) are skipped: what cannot be
    measured is not reported."""
    files = list(resident(root))
    rules = root / ".claude" / "rules"
    if rules.is_dir():
        files += [p.resolve() for p in sorted(rules.rglob("*.md"))
                  if p.is_file() and not _skipped(p.relative_to(root).parts)]
    out, seen = [], set()
    for path in dict.fromkeys(files):
        rel = _rel(root, path)
        framework = "article-kit" in Path(rel).parts[:-1]
        for line_of, para in _paragraphs(path.read_text(encoding="utf-8", errors="replace")):
            for start, sentence in _sentences(para):
                read = _READ_RE.search(sentence)
                if not (read and _BEFORE_RE.search(sentence)):
                    continue
                for m in _MD_TARGET_RE.finditer(sentence, read.end()):
                    target = m.group(1) or m.group(2)
                    line = line_of(start + m.start())
                    found = _resolve(root, path, target)
                    if found is None or (rel, found) in seen:
                        continue
                    seen.add((rel, found))
                    tokens = _tokens(found.read_text(encoding="utf-8", errors="replace"))
                    if tokens > POINTER_TOKENS:
                        out.append(
                            f"[shape] {rel}:{line}: tells the session to read `{target}` "
                            f"before acting — ~{tokens} tokens, over the {POINTER_TOKENS} a "
                            "read file keeps after a compaction (it returns as a path only); "
                            "put its rules first and cut it to that, or make it a skill"
                            + (" (a framework rule: the fix is article-kit's)" if framework
                               else ""))
    return out


def check_inline_dates(root: Path) -> list[str]:
    """Inline dated accounts in a resident file of this repository. A dated *bold opener* is
    the record-block check's; this counts the rest. The framework's rules are article-kit's."""
    out = []
    for path in resident(root):
        rel = _rel(root, path)
        if SKIP_PARTS & set(Path(rel).parts[:-1]):
            continue
        hits = []
        text = path.read_text(encoding="utf-8", errors="replace")
        m = _FM_END_RE.match(text)
        offset = m.group(0).count("\n") if m else 0
        fenced = False
        for i, ln in enumerate(text.splitlines()[offset:], start=offset + 1):
            if _FENCE_RE.match(ln):
                fenced = not fenced
                continue
            if fenced:
                continue
            # The bold opener is the record-block check's; the rest of its line is still ours.
            # A date inside a code span is a path or a command, not an account.
            bold = _DATED_BOLD_RE.match(ln)
            rest = _CODE_SPAN_RE.sub("", ln[bold.end():] if bold else ln)
            if _ISO_DATE_RE.search(rest) or _DECISION_OF_RE.search(rest):
                hits.append(i)
        if hits:
            shown = ", ".join(map(str, hits[:6])) + (", …" if len(hits) > 6 else "")
            out.append(f"[shape] {rel}: {len(hits)} line(s) with an inline dated account "
                       f"(lines {shown}) — a resident file is re-read on every turn; keep the "
                       "rule as one sentence and move the account to adr/ (PROCESS.md, 'Where "
                       "each kind of text lives')")
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
    out.extend(check_resident(root))
    out.extend(check_inline_dates(root))
    out.extend(check_pointers(root))
    return out
