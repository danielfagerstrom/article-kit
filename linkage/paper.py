r"""`linkage paper` — the deterministic paper lint, sibling to `linkage check`.

`linkage check` verifies the *edges*: blueprint to Lean, to the ledger, to the paper's
shared statements. Nothing looked at the paper sources themselves beyond the `prose`
pattern tools, so the defects a reader hits first — a `\ref` that renders `??`, a
`\cite` key that is not in the `.bib`, a pointer to item (3) of a two-item proposition —
were caught, when they were caught at all, by the blind reviews of Paper I.

What this module reads is `docs/PUBLICATION-TEMPLATE.md` § B's *Det.* rows (the
deterministic half of the publication contract) plus the three pointer defects the blind
reviews found, which no existing check can see. It is the drafting gate's deterministic
box for the drafted prose, where `linkage check` is the box for the upstream artifacts.

  FATAL (exit 1 if any fail)
    1. every `\ref`-family target is a `\label` defined somewhere in the paper sources
       (a dangling reference typesets `??`, and LaTeX's own warning is one line in
       several thousand)
    2. every `\cite` key resolves to an entry of a `.bib` the paper bibliographies
       (silent in the PDF as `[?]`; skipped entirely when no `.bib` is found, since
       then there is nothing to resolve against)
    3. an item reference past the target's item count — `Proposition~\ref{p}(3)` where
       the labelled statement has two `\item`s. Objectively a wrong pointer, and the
       count is read from the target, so it is only raised when the target *has* items;
       nesting inflates the count, which makes the check err towards silence
    4. a hand-written `\tag{N.M}` whose `N` is not the enclosing section's number: the
       equation prints a number belonging to another section. Needs the main document,
       since the section number comes from the document order, not from the file

  ADVISORY (reported, non-fatal)
    - a missing declaration (author contributions, competing interests, data
      availability, funding — PUBLICATION-TEMPLATE § A). Advisory, not fatal: a preprint
      legitimately carries fewer than a journal submission, and the checker reads
      headings, so it cannot see a declaration written into a covering letter
    - an abstract outside the template's ~150–250 words, or a main document with no
      abstract at all
    - a numbered result nothing refers to (an orphan — PUBLICATION-TEMPLATE § B.5's
      *Det.* row). Advisory because the checker cannot tell a genuinely abandoned lemma
      from one the prose picks up as "the theorem above"
    - a cited `.bib` entry with no DOI: a resolvability risk, not a defect
    - a bare `§` or `Thm.` in prose with no `\cite` and no `\ref` nearby — a pointer the
      reader cannot resolve, into a work the sentence never names. Advisory: the
      abbreviation may be typographic rather than a pointer

Everything the declarations, the abstract and the `\tag` check need comes from the
paper's **main document** — the file carrying `\begin{document}`. A paper directory
holding only section fragments (the scaffold smoke article, a module still being
assembled) has none, so those three checks are skipped and the summary line says so,
rather than reporting a fragment collection as a paper missing its front matter.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .checks import Findings
from .config import Config

# docs/PUBLICATION-TEMPLATE.md § A: "Abstract: ~150–250 words."
ABSTRACT_MIN, ABSTRACT_MAX = 150, 250

# PUBLICATION-TEMPLATE § A, "Mandatory declarations (easy to forget — the template won't
# force them)". Matched against *headings* only: the words themselves occur in ordinary
# prose ("funding"), and a heading is where a declaration actually lives.
DECLARATIONS: tuple[tuple[str, str], ...] = (
    ("author contributions", r"author\s+contribution"),
    ("competing interests",
     r"competing\s+interest|conflicts?\s+of\s+interest|declarations?\s+of\s+interest"),
    ("data availability",
     r"data\s+availability|code\s+availability|availability\s+of\s+(?:data|code)"),
    ("funding", r"funding|financial\s+support"),
)

HEADING_RE = re.compile(
    r"\\(?:chapter|section|subsection|subsubsection|paragraph|bmhead)\*?\{([^}]*)\}")
INPUT_RE = re.compile(r"\\(?:input|include|subfile)\{([^}]+)\}")
BIB_RE = re.compile(r"\\(?:bibliography|addbibresource)\{([^}]+)\}")
ABSTRACT_RE = re.compile(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", re.S)

# A `\ref`-family command, optionally followed by an item pointer: `\ref{p}(3)`,
# `\ref{p}\,(iii)`. The comma-separated form of \cref is split by the caller.
REF_RE = re.compile(
    r"\\(?:[cC]ref|[vV]ref|autoref|eqref|ref)\*?\{([^}]*)\}"
    r"(?:\s|\\[,;:!]|~)*(?:\(\s*([0-9]+|[ivxIVX]+)\s*\))?")
# Any command whose name contains "cite" — `\cite`, `\citep`, `\citet`, and an article's
# own wrapper (`\sscite` in Paper I). Optional `[...]` pre/post-notes are skipped.
CITE_RE = re.compile(r"\\[A-Za-z]*[Cc]ite[A-Za-z]*\*?(?:\[[^\]]*\])*\{([^}]*)\}")
LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
TAG_RE = re.compile(r"\\tag\*?\{([^}]*)\}")
# `\section{...}` (numbered only — a starred heading takes no number), `\appendix`, and
# the tags, read in document order so a tag's enclosing section is known.
SECTION_EVENT_RE = re.compile(
    r"\\(section)\{|\\(appendix)\b|\\(tag)\*?\{([^}]*)\}")
# A pointer abbreviation: the section sign in either spelling, or an abbreviated result
# name with its full stop. `Sec.`/`Eq.` are included because the defect is the same one.
POINTER_RE = re.compile(r"(§)|(\\S)(?![A-Za-z])|\b(Thm|Prop|Lem|Cor|Defn?|Sec|Ch|Eqn?)\.")
POINTER_WINDOW = 120
# A `\item`, for the item-count of a statement. `\item[label]` counts too.
ITEM_RE = re.compile(r"\\item\b")
ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8,
         "ix": 9, "x": 10}


def strip_comments(text: str) -> str:
    r"""Blank out LaTeX comments, keeping every offset and line break in place.

    Position-preserving on purpose: every finding in this module is located by
    `file:line`, so a stripper that shortened the text would report the wrong line.
    """
    out = []
    for line in text.splitlines(keepends=True):
        i, n = 0, len(line)
        while i < n:
            if line[i] == "\\":
                i += 2
                continue
            if line[i] == "%":
                nl = len(line.rstrip("\r\n"))  # where the line break starts
                out.append(line[:i] + " " * (nl - i) + line[nl:])
                break
            i += 1
        else:
            out.append(line)
    return "".join(out)


def _line(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def word_count(tex: str) -> int:
    r"""Words of an abstract. Commands and braces drop out; a math group counts as one
    word, the way a reader counts it."""
    t = re.sub(r"\$\$?.*?\$\$?", " x ", tex, flags=re.S)
    t = re.sub(r"\\[A-Za-z]+\*?", " ", t)
    t = re.sub(r"[{}~\\$]", " ", t)
    return sum(1 for w in t.split() if any(c.isalnum() for c in w))


@dataclass
class Source:
    """One paper source file, comments blanked."""
    path: Path
    rel: str
    text: str


@dataclass
class Statement:
    """A numbered result: its environment, its label, and how many items it has."""
    env: str
    label: str | None
    rel: str
    line: int
    items: int


@dataclass
class Segment:
    """A slice of one file, in the order the main document reaches it."""
    src: Source
    start: int
    end: int


@dataclass
class Sources:
    cfg: Config
    files: list[Source] = field(default_factory=list)
    main: Source | None = None
    order: list[Segment] = field(default_factory=list)
    statements: list[Statement] = field(default_factory=list)
    labels: dict[str, tuple[str, int]] = field(default_factory=dict)
    bib_files: list[str] = field(default_factory=list)
    bib: dict[str, bool] = field(default_factory=dict)
    """citekey -> whether its entry carries a DOI."""


def _resolve(base: Path, arg: str) -> Path | None:
    arg = arg.strip()
    for cand in (arg, arg + ".tex"):
        p = base / cand
        if p.is_file():
            return p
    return None


def read(cfg: Config) -> Sources:
    r"""Every paper source, plus whatever they `\input`, plus the bibliographies.

    An `\input` outside the paper directories is followed too: a shared preamble or a
    figure kept elsewhere still defines labels, and missing them would turn every
    reference to one into a false dangling-reference failure.
    """
    from .artifacts import paper_files

    src = Sources(cfg=cfg)
    by_path: dict[Path, Source] = {}

    def add(p: Path) -> Source | None:
        p = p.resolve()
        if p in by_path:
            return by_path[p]
        try:
            text = strip_comments(p.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            return None
        try:
            rel = p.relative_to(cfg.root).as_posix()
        except ValueError:
            rel = p.as_posix()
        s = Source(path=p, rel=rel, text=text)
        by_path[p] = s
        src.files.append(s)
        for m in INPUT_RE.finditer(text):
            if tgt := _resolve(p.parent, m.group(1)):
                add(tgt)
        return s

    for f in paper_files(cfg):
        add(f)

    src.main = next((s for s in src.files if r"\begin{document}" in s.text), None)
    if src.main is not None:
        src.order = _document_order(src.main, by_path)

    env_re = re.compile(
        r"\\begin\{(" + "|".join(cfg.statement_envs) + r")\}(.*?)\\end\{\1\}", re.S)
    for s in src.files:
        for m in LABEL_RE.finditer(s.text):
            src.labels.setdefault(m.group(1).strip(), (s.rel, _line(s.text, m.start())))
        for m in env_re.finditer(s.text):
            lab = LABEL_RE.search(m.group(2))
            src.statements.append(Statement(
                env=m.group(1),
                label=lab.group(1).strip() if lab else None,
                rel=s.rel,
                line=_line(s.text, m.start()),
                items=len(ITEM_RE.findall(m.group(2))),
            ))

    _read_bib(src)
    return src


def _document_order(main: Source, by_path: dict[Path, Source]) -> list[Segment]:
    r"""The main document's text, with each `\input`ed file spliced in at its call site."""
    order: list[Segment] = []

    def walk(s: Source, seen: frozenset[Path]) -> None:
        pos = 0
        for m in INPUT_RE.finditer(s.text):
            order.append(Segment(src=s, start=pos, end=m.start()))
            tgt = _resolve(s.path.parent, m.group(1))
            child = by_path.get(tgt.resolve()) if tgt else None
            if child is not None and child.path not in seen:
                walk(child, seen | {child.path})
            pos = m.end()
        order.append(Segment(src=s, start=pos, end=len(s.text)))

    walk(main, frozenset({main.path}))
    return order


def _read_bib(src: Sources) -> None:
    r"""Collect `citekey -> has DOI` from every `.bib` the paper uses.

    Both ways a paper names one: `\bibliography{...}` / `\addbibresource{...}` resolved
    against the file that writes it, and any `.bib` sitting in a paper directory (the
    common layout, and the one that survives a `\bibliography` written through a macro).
    """
    cands: list[Path] = []
    for s in src.files:
        for m in BIB_RE.finditer(s.text):
            for name in m.group(1).split(","):
                name = name.strip()
                if not name:
                    continue
                for cand in (name, name + ".bib"):
                    p = s.path.parent / cand
                    if p.is_file():
                        cands.append(p)
                        break
    for d in src.cfg.papers:
        cands.extend(sorted(d.glob("*.bib")))

    seen: set[Path] = set()
    for p in cands:
        p = p.resolve()
        if p in seen:
            continue
        seen.add(p)
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            src.bib_files.append(p.relative_to(src.cfg.root).as_posix())
        except ValueError:
            src.bib_files.append(p.as_posix())
        entries = list(re.finditer(r"(?m)^\s*@(\w+)\s*\{\s*([^,\s}]+)\s*,", text))
        for i, m in enumerate(entries):
            end = entries[i + 1].start() if i + 1 < len(entries) else len(text)
            body = text[m.end():end]
            if m.group(1).lower() in ("comment", "string", "preamble"):
                continue
            has_doi = bool(re.search(r"(?mi)^\s*doi\s*=", body)
                           or re.search(r"(?i)doi\.org/", body))
            key = m.group(2).strip()
            src.bib[key] = src.bib.get(key, False) or has_doi


# --- the checks -------------------------------------------------------------------


def _refs(src: Sources, f: Findings) -> tuple[set[str], int]:
    """Check 1 — every reference resolves; return the referenced labels for the orphans."""
    referenced: set[str] = set()
    total = 0
    for s in src.files:
        for m in REF_RE.finditer(s.text):
            for lab in m.group(1).split(","):
                lab = lab.strip()
                if not lab:
                    continue
                total += 1
                referenced.add(lab)
                if lab not in src.labels:
                    f.fatal.append(
                        f"[ref]    {s.rel}:{_line(s.text, m.start())}: \\ref{{{lab}}} "
                        f"names no \\label in the paper sources — it typesets as '??'")
    return referenced, total


def _orphans(src: Sources, f: Findings, referenced: set[str]) -> int:
    """Advisory — a numbered result nothing refers to (PUBLICATION-TEMPLATE § B.5)."""
    n = 0
    for st in src.statements:
        if not st.label or st.label in referenced:
            continue
        n += 1
        f.advisory.append(
            f"[orphan] {st.rel}:{st.line}: {st.env} '{st.label}' is numbered but nothing "
            f"\\ref's it — pick it up in the text, or fold it into the result that uses it")
    return n


def _cites(src: Sources, f: Findings) -> tuple[int, int]:
    """Check 2 — every `\\cite` key is in a `.bib`; advisory on an entry with no DOI."""
    if not src.bib_files:
        return 0, 0
    used: set[str] = set()
    for s in src.files:
        for m in CITE_RE.finditer(s.text):
            for key in m.group(1).split(","):
                key = key.strip()
                # A citation *macro's definition* is not a citation: Paper I's
                # `\newcommand{\sscite}[1]{\cite{#1}}` would otherwise be reported as a
                # key named `#1` resolving in no bibliography.
                if not key or "#" in key or "\\" in key:
                    continue
                used.add(key)
                if key not in src.bib:
                    f.fatal.append(
                        f"[cite]   {s.rel}:{_line(s.text, m.start())}: \\cite{{{key}}} "
                        f"resolves in none of {', '.join(src.bib_files)} — it typesets "
                        f"as '[?]'")
    if nodoi := sorted(k for k in used if k in src.bib and not src.bib[k]):
        f.advisory.append(
            f"[doi]    {len(nodoi)} cited entr(ies) carry no DOI in "
            f"{', '.join(src.bib_files)}: {', '.join(nodoi)} — a reader cannot resolve "
            f"them mechanically (advisory: an older source may genuinely have none)")
    return len(used), len(nodoi)


def _items(src: Sources, f: Findings) -> None:
    r"""Check 3 — `Proposition~\ref{p}(3)` on a two-item statement.

    Found by a blind review of Paper I, where a reordering had left three such pointers
    behind. Nothing else in the toolchain can see it: the reference resolves, the number
    typesets, and only a reader who follows the pointer finds no item there.
    """
    by_label = {st.label: st for st in src.statements if st.label}
    for s in src.files:
        for m in REF_RE.finditer(s.text):
            if not m.group(2):
                continue
            lab = m.group(1).strip()
            st = by_label.get(lab)
            if st is None or st.items == 0:
                continue  # not a statement of ours, or it has no items to count
            raw = m.group(2)
            idx = int(raw) if raw.isdigit() else ROMAN.get(raw.lower(), 0)
            if idx and idx > st.items:
                f.fatal.append(
                    f"[item]   {s.rel}:{_line(s.text, m.start())}: \\ref{{{lab}}}({raw}) "
                    f"but {st.env} '{lab}' has {st.items} item(s) "
                    f"({st.rel}:{st.line}) — the pointer names an item that is not there")


def _tags(src: Sources, f: Findings) -> int:
    r"""Check 4 — a hand-written `\tag{N.M}` whose `N` is not the enclosing section's.

    The number is written by hand exactly where LaTeX would not supply it, so nothing
    keeps it in step when a section moves; a blind review of Paper I found a `\tag{3.7}`
    in section 4. The section number comes from the document order, which is why this
    check needs the main document.
    """
    if not src.order:
        return 0
    events = [(m, seg.src) for seg in src.order
              for m in SECTION_EVENT_RE.finditer(seg.src.text, seg.start, seg.end)]

    # Which identifiers this document's sections actually carry. A tag naming anything
    # else -- Paper I writes `\tag{V.1}` for a Volterra equation in appendix A -- is a
    # deliberate custom label or a pointer into a companion paper, not a section number
    # gone stale, and the checker cannot tell those apart, so it leaves them alone. What
    # it can say without guessing is that `N` names a DIFFERENT section of this document.
    n_main = n_app = 0
    appendix = False
    for m, _s in events:
        if m.group(1):
            if appendix:
                n_app += 1
            else:
                n_main += 1
        elif m.group(2):
            appendix = True
    ids = ({str(i) for i in range(1, n_main + 1)}
           | {chr(ord("A") + i - 1) for i in range(1, n_app + 1)})

    section, appendix, checked = 0, False, 0
    for m, s in events:
        if m.group(1):
            section += 1
        elif m.group(2):
            appendix, section = True, 0
        elif m.group(3):
            tm = re.match(r"\(?\s*(\d+|[A-Z])\s*\.\s*\d+\s*\)?$", m.group(4).strip())
            if not tm or not section or tm.group(1) not in ids:
                continue  # not an N.M tag, no numbered section yet, or not a section id
            checked += 1
            want = chr(ord("A") + section - 1) if appendix else str(section)
            if tm.group(1) != want:
                f.fatal.append(
                    f"[tag]    {s.rel}:{_line(s.text, m.start())}: \\tag{{"
                    f"{m.group(4).strip()}}} inside "
                    f"{'appendix' if appendix else 'section'} {want} — the equation "
                    f"prints a number belonging to another section")
    return checked


def _pointers(src: Sources, f: Findings) -> None:
    r"""Advisory — a bare `§` or `Thm.` with no `\cite` and no `\ref` within reach.

    The sentence points somewhere and the reader cannot follow it: neither into a cited
    work (no citation) nor inside this paper (no label). Advisory, because `Sec.` at the
    end of a sentence may be typography rather than a pointer.
    """
    for s in src.files:
        for m in POINTER_RE.finditer(s.text):
            lo = max(0, m.start() - POINTER_WINDOW)
            window = s.text[lo:m.end() + POINTER_WINDOW]
            if CITE_RE.search(window) or REF_RE.search(window):
                continue
            token = next(g for g in m.groups() if g)
            f.advisory.append(
                f"[point]  {s.rel}:{_line(s.text, m.start())}: bare '{token}' pointer "
                f"with no \\cite and no \\ref within {POINTER_WINDOW} characters — say "
                f"which work, or reference the label")


def _declarations(src: Sources, f: Findings) -> list[str]:
    """Advisory — the declarations PUBLICATION-TEMPLATE § A calls mandatory."""
    if src.main is None:
        return []
    headings = " || ".join(
        m.group(1) for s in src.files for m in HEADING_RE.finditer(s.text))
    missing = [name for name, pat in DECLARATIONS
               if not re.search(pat, headings, re.I)]
    for name in missing:
        f.advisory.append(
            f"[decl]   {src.main.rel}: no heading declares '{name}' — "
            f"PUBLICATION-TEMPLATE § A calls it mandatory and the template does not "
            f"force it")
    return missing


def _abstract(src: Sources, f: Findings) -> int | None:
    """Advisory — the abstract against the template's ~150–250 words."""
    if src.main is None:
        return None
    for s in src.files:
        if m := ABSTRACT_RE.search(s.text):
            n = word_count(m.group(1))
            if not (ABSTRACT_MIN <= n <= ABSTRACT_MAX):
                f.advisory.append(
                    f"[abstr]  {s.rel}:{_line(s.text, m.start())}: abstract is {n} words, "
                    f"outside the template's {ABSTRACT_MIN}–{ABSTRACT_MAX} "
                    f"(PUBLICATION-TEMPLATE § A)")
            return n
    f.advisory.append(
        f"[abstr]  {src.main.rel}: no abstract environment in the main document")
    return 0


def lint(cfg: Config) -> Findings:
    """Every paper check, over every paper directory `linkage.toml` names."""
    src = read(cfg)
    f = Findings()
    missing_decl = _declarations(src, f)
    abstract = _abstract(src, f)
    referenced, n_refs = _refs(src, f)
    orphans = _orphans(src, f, referenced)
    n_cites, n_nodoi = _cites(src, f)
    _items(src, f)
    n_tags = _tags(src, f)
    _pointers(src, f)
    f.stats = {
        "files": len(src.files),
        "main": src.main.rel if src.main else None,
        "statements": sum(1 for st in src.statements if st.label),
        "labels": len(src.labels),
        "refs": n_refs,
        "orphans": orphans,
        "cites": n_cites,
        "bib_files": list(src.bib_files),
        "bib_entries": len(src.bib),
        "no_doi": n_nodoi,
        "abstract_words": abstract,
        "missing_declarations": missing_decl,
        "tags_checked": n_tags,
    }
    return f
