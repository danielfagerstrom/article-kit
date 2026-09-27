r"""The paper's account of its own checking, checked (LINKAGE.md rule 13).

A module's trust-base subsection tells a reader what is machine-checked, what is proved in
prose, which cited facts its results read and what `#print axioms` prints. Every one of those
claims is derivable from the repository, and none was checked: Paper V's module C went stale
twice in two days while a proving campaign ran beside the drafting (a section calling nothing
machine-checked when four of its seven nodes had a Lean tag, a table of fourteen boundary
names when there were sixteen, an axioms block printed before a cited fact left the boundary,
a statement listed prose-only the morning after it was checked).

The paper marks the subsection with two comment lines, and this module reads what lies
between them:

    % trust base: begin
    ...
    % trust base: end

Three comparisons, all on source text by default:

1. **Status.** The region is read in *rows* — a table row (`\\`), an `\item`, a sentence or a
   paragraph. A row that `\ref`s statements and says "machine-checked" (or "Lean-checked",
   "checked in Lean", "formalised in Lean") claims each of them `\leanok`; one that says
   "prose", "on paper", "not machine-checked" or "unformalised" claims each of them not.
   A row saying both is ambiguous and reported, never guessed at.
2. **Ledger entries.** The entries the region names (an id matching `ledger_key`, or an
   interface axiom of `trust-boundary.txt` by name) against the entries its statements read:
   for a `\leanok` node, the boundary axioms its declarations reach (the `linkage closure`
   index — the export when there is one, else the source scan) mapped to their entries
   through the ledger's `**Lean:**` segments; for any other node, the `\ledger{}` entries of
   the `[A]` nodes it rests on ahead of the trust boundary (itself included).
3. **Axiom blocks.** A verbatim block in the region carrying Lean's `#print axioms` output
   must be stamped — `% printed at <commit>` or `<YYYY-MM-DD>` on a comment line directly
   above it — may print only Lean core and declared interface axioms, must agree with the
   `#guard_msgs` pin of the same declaration when the boundary harness has one, and, under
   `--fresh-axioms`, with what Lean prints now.

A paper with no marker produces nothing at all.
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from . import trust
from .config import Config
from .model import Blueprint, PaperMarker

BEGIN_RE = re.compile(r"(?im)^[ \t]*%[ \t]*trust[ -]base:[ \t]*begin\b[^\n]*$")
END_RE = re.compile(r"(?im)^[ \t]*%[ \t]*trust[ -]base:[ \t]*end\b[^\n]*$")

# The environments a printed `#print axioms` block is typeset in.
BLOCK_RE = re.compile(
    r"\\begin\{(?P<env>verbatim\*?|Verbatim|BVerbatim|lstlisting|minted)\}"
    r"(?P<body>.*?)\\end\{(?P=env)\}", re.S)
# Lean's own output line, as the boundary harness reads it from a pin.
OUTPUT_RE = re.compile(
    r"'(?P<decl>[\w'.]+)'\s+(?:depends on axioms:\s*\[(?P<axioms>[^\]]*)\]"
    r"|(?P<none>does not depend on any axioms))", re.S)
STAMP_RE = re.compile(
    r"printed at\s+(?P<stamp>[0-9a-f]{7,40}\b|\d{4}-\d{2}-\d{2}\b)", re.I)

REF_RE = re.compile(r"\\(?:[cC]ref|autoref|vref|eqref|ref)\*?\{([^}]*)\}")
LABEL_ARG_RE = re.compile(r"\\(?:[cC]ref|autoref|vref|eqref|ref|label)\*?\{[^}]*\}")
COMMENT_RE = re.compile(r"(?<!\\)%[^\n]*")
ROW_SPLIT_RE = re.compile(r"\\\\|\\item\b|\n[ \t]*\n|(?<=[.;])\s+(?=[A-Z\\])")

# Negated forms first: they are removed before the positive forms are looked for, so
# "not machine-checked" is never also read as "machine-checked".
UNCHECKED_RE = re.compile(
    r"not\s+(?:yet\s+)?(?:machine[- ]checked|lean[- ]checked|checked in lean|"
    r"formali[sz]ed)|unformali[sz]ed|prose[- ]only|\bprose\b|on paper", re.I)
CHECKED_RE = re.compile(
    r"machine[- ]checked|lean[- ]checked|checked in lean|formali[sz]ed in lean", re.I)


@dataclass
class Result:
    fatal: list[str] = field(default_factory=list)
    advisory: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


@dataclass
class Region:
    file: str
    line: int
    text: str
    offset: int
    """Character offset of `text` in its file, for line numbers."""
    source: str

    def line_of(self, pos: int) -> int:
        return self.source.count("\n", 0, self.offset + pos) + 1


def _blank(m: re.Match) -> str:
    return re.sub(r"[^\n]", " ", m.group(0))


def regions(cfg: Config) -> tuple[list[Region], list[str]]:
    """Every marked trust-base region of the papers, and the malformed markers."""
    from .artifacts import paper_files

    out: list[Region] = []
    errors: list[str] = []
    for f in paper_files(cfg):
        t = f.read_text(encoding="utf-8")
        rel = f.relative_to(cfg.root).as_posix()
        begins, ends = list(BEGIN_RE.finditer(t)), list(END_RE.finditer(t))
        if not begins and not ends:
            continue
        # Pair each begin with the first end after it and before the next begin.
        ends_left = list(ends)
        for i, b in enumerate(begins):
            nxt = begins[i + 1].start() if i + 1 < len(begins) else len(t)
            e = next((e for e in ends_left if b.end() <= e.start() < nxt), None)
            if e is None:
                errors.append(
                    f"[trust-base] {rel}:{t.count(chr(10), 0, b.start()) + 1}: "
                    "'% trust base: begin' with no '% trust base: end' before the next begin "
                    "or the end of the file -- nothing in it is checked")
                continue
            ends_left.remove(e)
            out.append(Region(rel, t.count("\n", 0, b.start()) + 1, t[b.end():e.start()],
                              b.end(), t))
        for e in ends_left:
            errors.append(
                f"[trust-base] {rel}:{t.count(chr(10), 0, e.start()) + 1}: "
                "'% trust base: end' with no begin above it")
    return out, errors


def _label_map(bp: Blueprint, markers: list[PaperMarker]) -> dict[str, list[str]]:
    """A `\\ref`'d label -> the blueprint node(s) it stands for.

    A blueprint label stands for itself; a paper statement's own label stands for the
    node(s) its `% shared with blueprint` marker names, so a paper that has not aligned its
    labels with the blueprint's (rule 4's advisory) is still read correctly.
    """
    out = {lab: [lab] for lab in bp.labels}
    for mk in markers:
        if mk.statement_label and mk.statement_label not in out:
            out[mk.statement_label] = [lab for lab in mk.blueprint_labels if lab in bp.labels]
    return out


def _refs(text: str) -> list[str]:
    return [lab.strip() for m in REF_RE.finditer(text) for lab in m.group(1).split(",")
            if lab.strip()]


# --- 1. status -------------------------------------------------------------------------


def _check_status(reg: Region, prose: str, labels: dict[str, list[str]], bp: Blueprint,
                  res: Result) -> int:
    by_label = bp.by_label
    claims = 0
    pos = 0
    for m in [*ROW_SPLIT_RE.finditer(prose), None]:
        end = m.start() if m else len(prose)
        row, row_at = prose[pos:end], pos
        pos = m.end() if m else len(prose)
        refs = _refs(row)
        if not refs:
            continue
        bare = UNCHECKED_RE.sub(" ", LABEL_ARG_RE.sub(" ", row))
        says_unchecked = bool(UNCHECKED_RE.search(LABEL_ARG_RE.sub(" ", row)))
        says_checked = bool(CHECKED_RE.search(bare))
        where = f"{reg.file}:{reg.line_of(row_at + len(row) - len(row.lstrip()))}"
        if says_checked and says_unchecked:
            res.advisory.append(
                f"[trust-base] {where}: a row both calls {', '.join(refs)} machine-checked "
                "and not -- split it so each claim sits with its statements; not checked")
            continue
        if not (says_checked or says_unchecked):
            continue
        for ref in refs:
            nodes = labels.get(ref)
            if not nodes:
                res.advisory.append(
                    f"[trust-base] {where}: \\ref{{{ref}}} is given a status but names no "
                    "blueprint node (nor a paper statement marked 'shared with blueprint') "
                    "-- not checked")
                continue
            for lab in nodes:
                claims += 1
                n = by_label[lab]
                if says_checked and not n.leanok:
                    res.fatal.append(
                        f"[trust-base] {where}: calls {ref} machine-checked, but blueprint "
                        f"node {lab} is not \\leanok -- the paper claims a check that does "
                        "not exist")
                elif says_unchecked and n.leanok:
                    res.fatal.append(
                        f"[trust-base] {where}: calls {ref} proved in prose only, but "
                        f"blueprint node {lab} is \\leanok -- the section is behind the "
                        "development")
    return claims


# --- 2. ledger entries -----------------------------------------------------------------


def _entries_by_name(cfg: Config) -> dict[str, set[str]]:
    """Short Lean name -> the ledger entries whose `**Lean:**` segment mentions it."""
    text = cfg.axioms.read_text(encoding="utf-8")
    out: dict[str, set[str]] = {}
    for aid, body in trust._entries(text, cfg.ledger_key).items():
        for seg in re.finditer(r"\*\*Lean:\*\*(.*?)(?=\n\s*\n|\*\*Cite:\*\*|\Z)", body, re.S):
            for ident in re.findall(r"`([A-Za-z_][\w'.]*)`", seg.group(1)):
                out.setdefault(ident.split(".")[-1], set()).add(aid)
    return out


def _read_by(lab: str, bp: Blueprint, index, boundary: dict[str, str],
             by_name: dict[str, set[str]]) -> tuple[set[str], set[str], list[str]] | None:
    """(entries, boundary names, unresolved declarations) node `lab` reads."""
    from .checks import uses_paths

    n = bp.by_label[lab]
    if n.leanok and n.lean:
        entries: set[str] = set()
        names: set[str] = set()
        unresolved: list[str] = []
        for d in n.lean:
            full = index.resolve(d) if index is not None else None
            if full is None:
                unresolved.append(d)
                continue
            reach = index.closure(full) | {full}
            for bfull, short in boundary.items():
                if bfull in reach:
                    names.add(short)
                    entries |= by_name.get(short, set())
        return entries, names, unresolved
    ahead = [lab, *uses_paths(lab, bp.by_label, stop_at_axiom=True)]
    return ({a for x in ahead if (m := bp.by_label.get(x)) and m.status == "A"
             for a in m.ledger}, set(), [])


def _check_ledger(cfg: Config, reg: Region, prose: str, labels: dict[str, list[str]],
                  bp: Blueprint, index, res: Result) -> None:
    declared = trust.declared(cfg)
    by_name = _entries_by_name(cfg)
    text = LABEL_ARG_RE.sub(" ", prose).replace(r"\_", "_")
    named = {m.group(0) for m in re.finditer(rf"(?<![\w-])(?:{cfg.ledger_key})(?!\w)", text)}
    named_names = {d.split(".")[-1] for d in declared
                   if re.search(rf"(?<![\w']){re.escape(d.split('.')[-1])}(?![\w'])", text)}
    for short in named_names:
        named |= by_name.get(short, set())

    # boundary axiom (full name, as the index resolves it) -> its short name
    boundary: dict[str, str] = {}
    if index is not None:
        for d in declared:
            if (full := index.resolve(d)) is not None:
                boundary[full] = d.split(".")[-1]

    read: dict[str, list[str]] = {}
    read_names: dict[str, list[str]] = {}
    lean_nodes = 0
    for ref in dict.fromkeys(_refs(prose)):
        for lab in labels.get(ref, []):
            entries, names, unresolved = _read_by(lab, bp, index, boundary, by_name)
            if unresolved:
                res.advisory.append(
                    f"[trust-base] {reg.file}:{reg.line}: {lab}'s declaration(s) "
                    f"{', '.join(unresolved)} are not in this repository's Lean index -- "
                    "the section's ledger entries are not compared")
                return
            lean_nodes += bool(bp.by_label[lab].leanok and bp.by_label[lab].lean)
            for a in entries:
                read.setdefault(a, []).append(lab)
            for s in names:
                read_names.setdefault(s, []).append(lab)

    where = f"{reg.file}:{reg.line}"
    for a in sorted(named - set(read)):
        res.fatal.append(
            f"[trust-base] {where}: the section names ledger entry {a}, but none of the "
            "statements it \\ref's reads it -- a cited fact that has left their trust base")
    for a in sorted(set(read) - named):
        res.fatal.append(
            f"[trust-base] {where}: {', '.join(sorted(set(read[a])))} read(s) ledger entry "
            f"{a}, which the section never names")
    if named_names and lean_nodes:
        # The same comparison by boundary name, when the section lists names: two
        # names grounded by one entry would otherwise hide a missing row.
        for s in sorted(named_names - set(read_names)):
            res.fatal.append(
                f"[trust-base] {where}: the section lists interface axiom {s}, which none "
                "of its machine-checked statements reaches")
        for s in sorted(set(read_names) - named_names):
            res.fatal.append(
                f"[trust-base] {where}: {', '.join(sorted(set(read_names[s])))} reach(es) "
                f"interface axiom {s}, which the section's list of names leaves out")


# --- 3. axiom blocks -------------------------------------------------------------------


def _pinned(cfg: Config) -> dict[str, tuple[str, ...]]:
    from .boundary import pins

    g = cfg.boundary.guard
    if g is None or not g.is_file():
        return {}
    return {p.decl: p.axioms for p in pins(g.read_text(encoding="utf-8"))
            if p.guarded and p.axioms is not None}


def _axioms(m: re.Match) -> tuple[str, ...]:
    return () if m.group("none") else tuple(
        a.strip() for a in (m.group("axioms") or "").split(",") if a.strip())


def _run_lean(cfg: Config, source: str) -> str:
    """Elaborate `source` in the article's Lake project; Lean's output. Raises OSError or
    subprocess.SubprocessError when Lean is not there."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "TrustBaseAxioms.lean"
        p.write_text(source, encoding="utf-8")
        r = subprocess.run(["lake", "env", "lean", str(p)], cwd=cfg.lean,
                           capture_output=True, text=True, timeout=3600)
    return r.stdout + r.stderr


def fresh_axioms(cfg: Config, decls: list[str], index) -> tuple[dict[str, tuple], str | None]:
    """What `#print axioms` prints for each of `decls` now: `(axioms by decl, error)`."""
    mods = sorted({index.module[full] for d in decls
                   if index is not None and (full := index.resolve(d)) in index.module})
    src = "".join(f"import {m}\n" for m in mods) + "".join(
        f"#print axioms {d}\n" for d in decls)
    try:
        out = _run_lean(cfg, src)
    except (OSError, subprocess.SubprocessError) as e:
        return {}, f"could not run Lean ({e})"
    got = {m.group("decl"): _axioms(m) for m in OUTPUT_RE.finditer(out)}
    missing = [d for d in decls if d not in got]
    return got, (f"Lean printed no axioms for {', '.join(missing)}: "
                 + (out.strip().splitlines() or ["(no output)"])[-1]) if missing else None


def _check_blocks(cfg: Config, reg: Region, res: Result, *, fresh: bool, index) -> int:
    allowed = set(trust.allowlist(cfg))
    has_boundary = trust.trust_file(cfg).exists()
    pinned = _pinned(cfg)
    printed: list[tuple[str, str, tuple[str, ...]]] = []
    n = 0
    for b in BLOCK_RE.finditer(reg.text):
        outs = list(OUTPUT_RE.finditer(b.group("body")))
        if not outs:
            continue
        n += 1
        where = f"{reg.file}:{reg.line_of(b.start())}"
        # The comment lines directly above the block (the last element is the text on
        # the \begin line itself, before it).
        comments = []
        for line in reversed(reg.text[:b.start()].split("\n")[:-1]):
            if not line.lstrip().startswith("%"):
                break
            comments.append(line)
        if not any(STAMP_RE.search(c) for c in comments):
            res.fatal.append(
                f"[trust-base] {where}: a printed '#print axioms' block with no stamp -- "
                "put '% printed at <commit>' (or <YYYY-MM-DD>) on the line above it, so a "
                "reader can see when it went stale")
        for m in outs:
            decl, got = m.group("decl"), _axioms(m)
            printed.append((where, decl, got))
            if "sorryAx" in got:
                res.fatal.append(f"[trust-base] {where}: {decl} is printed depending on "
                                 "sorryAx")
            if has_boundary and (out := [a for a in got
                                         if a not in allowed and a != "sorryAx"]):
                res.fatal.append(
                    f"[trust-base] {where}: {decl} is printed depending on "
                    f"{', '.join(out)}, which {trust.trust_file(cfg).name} does not declare "
                    "-- printed before the boundary changed; re-run and re-stamp")
            pin = pinned.get(decl)
            if pin is not None and set(pin) != set(got):
                res.fatal.append(
                    f"[trust-base] {where}: {decl} is printed as {_fmt(got)}, but its "
                    f"#guard_msgs pin in {cfg.boundary.guard.name} says {_fmt(pin)}")
    if fresh and printed:
        now, err = fresh_axioms(cfg, list(dict.fromkeys(d for _, d, _ in printed)), index)
        if err:
            res.fatal.append(f"[trust-base] {reg.file}:{reg.line}: --fresh-axioms: {err}")
        for where, decl, got in printed:
            if decl in now and set(now[decl]) != set(got):
                res.fatal.append(
                    f"[trust-base] {where}: {decl} is printed as {_fmt(got)}, but Lean "
                    f"prints {_fmt(now[decl])} now")
    return n


def _fmt(axioms: tuple[str, ...]) -> str:
    return "[" + ", ".join(axioms) + "]" if axioms else "no axioms"


# --- the check -------------------------------------------------------------------------


def check(bp: Blueprint, cfg: Config, markers: list[PaperMarker], *,
          fresh: bool = False) -> Result:
    """Rule 13 over every marked region; empty when no paper carries the marker."""
    res = Result()
    regs, errors = regions(cfg)
    res.fatal.extend(errors)
    res.stats = {"regions": len(regs), "claims": 0, "blocks": 0}
    if not regs:
        return res

    from .closure import ExportError, build_index
    try:
        index, _route = build_index(cfg)
    except ExportError as e:
        index = None
        res.advisory.append(f"[trust-base] the Lean index could not be read ({e}) -- "
                            "ledger entries are compared for prose-only statements alone")
    labels = _label_map(bp, markers)
    for reg in regs:
        # Comments and printed blocks are not claims: blank them, keeping offsets.
        prose = BLOCK_RE.sub(_blank, COMMENT_RE.sub(_blank, reg.text))
        res.stats["claims"] += _check_status(reg, prose, labels, bp, res)
        _check_ledger(cfg, reg, prose, labels, bp, index, res)
        res.stats["blocks"] += _check_blocks(cfg, reg, res, fresh=fresh, index=index)
    return res
