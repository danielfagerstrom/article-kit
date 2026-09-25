"""The reviewer output contract, implemented: parse flags, pool them, rank by breadth.

The spec is [`docs/REVIEWER-CONTRACT.md`](../docs/REVIEWER-CONTRACT.md); this module is
the half of it a machine can carry out. What it exists to prevent is the failure the
contract documents: fourteen blind reviews of one paper produced ~120 well-formed flags
as prose, and the pooling that made them actionable cost a day of reading essays.

Two levels of grouping, and they are not the same thing:

- **a defect** is one underlying fault in the text. Flags from different reviewers about
  it pool under one key, and the key is derived from the flags' own evidence (the labels
  they cite, else the prose they quote) — never from a name a reviewer chose, because a
  blind reviewer sees one section and cannot name a thread (contract, finding 3).
- **a thread** is a proposal that several defects across sections are one decision. It is
  a lead, not a verdict.

The sort key at both levels is the count of *independent reviews*. Severity is carried
through and is only ever the last tiebreak: the trial batch had the same defect at
`[low-med]` from one reviewer and `[high]` from another, so once flags are pooled the
per-reviewer number stops being informative and the count of discoveries starts.

Config-free, like `prose/`: it takes bare paths, because a review of a paper is checked
against the paper's sources and needs no `linkage.toml`.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# The vocabulary, and each tag's layer. A flag whose `layer` disagrees with its tag's is
# malformed: the layer is not a second opinion, it is which half of the template the tag
# belongs to (§B structure, §C voice).
STRUCTURE_TAGS = (
    "SCOPE", "HYPOTHESIS", "COUNT", "FRONTIER",
    "CONTRACT", "PROMISE", "ORPHAN", "ENVELOPE", "POINTER", "TRANSCLUSION",
    "NOTATION", "UNDEFINED",
)
VOICE_TAGS = (
    "MOTIVATION", "PICTURE", "PROSE",
    "NEGPAR", "PARTTAIL", "PARALADDER", "SALIENCE", "SINCERITY", "SIGNPOST",
    "ADVERB", "TRICOLON", "ATTITUDE",
)
LAYER_OF = dict.fromkeys(STRUCTURE_TAGS, "structure") | dict.fromkeys(VOICE_TAGS, "voice")

# `B.<n>` for template §B section n, several joined by `+` when one file discharges more
# than one contract, `B.0` for text the skeleton does not cover.
CONTRACT_RE = re.compile(r"^B\.(?:10|[0-9])(?:\+B\.(?:10|[0-9]))*$")

SKIP_DIRS = {".git", ".claude", "_build", "node_modules", ".lake", "__pycache__"}


@dataclass(frozen=True)
class Review:
    id: str
    target: str
    contract: str
    contract_why: str
    strengths: str
    maturity: str | None = None
    floor: str | None = None
    source: str = ""


@dataclass(frozen=True)
class Flag:
    review: str
    file: str
    anchor: str
    tag: str
    layer: str
    severity: int
    claim: str
    probe: str
    refs: tuple[str, ...] = ()
    elsewhere: tuple[str, ...] = ()
    shared_with_blueprint: bool = False
    line: int | None = None
    source: str = ""


@dataclass(frozen=True)
class Problem:
    source: str
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.source}:{self.line}: {self.message}"


@dataclass
class Defect:
    """One underlying fault, with every flag any reviewer raised about it."""

    key: str
    file: str
    tag: str
    layer: str
    flags: list[Flag] = field(default_factory=list)

    @property
    def reviews(self) -> list[str]:
        return sorted({f.review for f in self.flags})

    @property
    def breadth(self) -> int:
        return len(self.reviews)

    @property
    def severity(self) -> int:
        return max(f.severity for f in self.flags)

    @property
    def refs(self) -> list[str]:
        return sorted({r for f in self.flags for r in f.refs})

    @property
    def rank(self) -> tuple:
        return (-self.breadth, -len(self.flags), -self.severity, self.key)


@dataclass
class Thread:
    """A proposal that several defects are one decision. A lead, not a finding."""

    id: str
    defects: list[Defect] = field(default_factory=list)

    @property
    def reviews(self) -> list[str]:
        return sorted({r for d in self.defects for r in d.reviews})

    @property
    def files(self) -> list[str]:
        return sorted({d.file for d in self.defects})

    @property
    def refs(self) -> list[str]:
        return sorted({r for d in self.defects for r in d.refs})

    @property
    def rank(self) -> tuple:
        return (-len(self.reviews), -len(self.defects),
                -max(d.severity for d in self.defects), self.id)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().casefold()


class _Union:
    """Union-find over indices. Deterministic: the pools depend on the input set only."""

    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, i: int) -> int:
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def join(self, i: int, j: int) -> None:
        a, b = self.find(i), self.find(j)
        if a != b:
            self.parent[max(a, b)] = min(a, b)

    def groups(self) -> list[list[int]]:
        out: dict[int, list[int]] = defaultdict(list)
        for i in range(len(self.parent)):
            out[self.find(i)].append(i)
        return [out[k] for k in sorted(out)]


# ---------------------------------------------------------------- parsing


def _as_str(rec: dict, key: str) -> str | None:
    v = rec.get(key)
    return v if isinstance(v, str) and v.strip() else None


def _as_list(rec: dict, key: str) -> tuple[str, ...] | None:
    v = rec.get(key, [])
    if isinstance(v, list) and all(isinstance(x, str) for x in v):
        return tuple(v)
    return None


def parse(paths: list[Path]) -> tuple[list[Review], list[Flag], list[Problem]]:
    """Read JSONL review files. Returns (reviews, well-formed flags, problems).

    A `kind:"review"` record opens a review and every later flag belongs to it, so the
    files concatenate. The review's id is its own `id` if it declares one, else the file
    stem (`<stem>#2` for a second review in the same file), which is why one file per
    review is the shape the contract asks for.
    """
    reviews: list[Review] = []
    flags: list[Flag] = []
    problems: list[Problem] = []
    seen_ids: set[str] = set()

    for path in paths:
        src = path.name
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as e:
            problems.append(Problem(src, 0, f"cannot read: {e}"))
            continue
        current: str | None = None
        n_here = 0
        for lineno, raw in enumerate(text.splitlines(), 1):
            if not raw.strip():
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError as e:
                problems.append(Problem(src, lineno, f"not JSON: {e.msg}"))
                continue
            if not isinstance(rec, dict):
                problems.append(Problem(src, lineno, "not a JSON object"))
                continue
            kind = rec.get("kind")
            if kind == "review":
                n_here += 1
                rid = _as_str(rec, "id") or (path.stem if n_here == 1
                                             else f"{path.stem}#{n_here}")
                while rid in seen_ids:
                    rid += "'"
                seen_ids.add(rid)
                r, bad = _review(rec, rid, src, lineno)
                problems.extend(bad)
                if r is not None:
                    reviews.append(r)
                    current = rid
                else:
                    current = None
            elif kind == "flag":
                if current is None:
                    problems.append(Problem(
                        src, lineno, "flag before any well-formed review record — the "
                        "review record is what says which section contract it is under"))
                    continue
                f, bad = _flag(rec, current, src, lineno)
                problems.extend(bad)
                if f is not None:
                    flags.append(f)
            else:
                problems.append(Problem(src, lineno, f"unknown kind {kind!r}"))
        if n_here == 0:
            problems.append(Problem(src, 0, "no review record — every review declares its "
                                            "section contract before its flags"))
    return reviews, flags, problems


def _review(rec: dict, rid: str, src: str, lineno: int) -> tuple[Review | None, list[Problem]]:
    bad = [Problem(src, lineno, f"review: {k} is required")
           for k in ("target", "contract", "contract_why", "strengths")
           if _as_str(rec, k) is None]
    if bad:
        return None, bad
    contract = rec["contract"]
    if not CONTRACT_RE.match(contract):
        return None, [Problem(src, lineno, f"review: contract {contract!r} is not a "
                                           "declaration of the form B.<1-10>, joined by + "
                                           "when the section discharges several")]
    return Review(id=rid, target=rec["target"], contract=contract,
                  contract_why=rec["contract_why"], strengths=rec["strengths"],
                  maturity=_as_str(rec, "maturity"), floor=_as_str(rec, "floor"),
                  source=src), []


def _flag(rec: dict, review: str, src: str, lineno: int) -> tuple[Flag | None, list[Problem]]:
    bad: list[Problem] = []
    for k in ("file", "anchor", "tag", "layer", "claim", "probe"):
        if _as_str(rec, k) is None:
            bad.append(Problem(src, lineno, f"flag: {k} is required"))
    refs = _as_list(rec, "refs")
    if refs is None:
        bad.append(Problem(src, lineno, "flag: refs must be a list of labels"))
    elif "refs" not in rec:
        bad.append(Problem(src, lineno, "flag: refs is required — every label the flag "
                                        "implicates, which is what pools it"))
    elsewhere = _as_list(rec, "elsewhere")
    if elsewhere is None:
        bad.append(Problem(src, lineno, "flag: elsewhere must be a list of paths"))
    sev = rec.get("severity")
    if not isinstance(sev, int) or isinstance(sev, bool) or not 1 <= sev <= 3:
        bad.append(Problem(src, lineno, f"flag: severity {sev!r} is not 1, 2 or 3"))
    tag = rec.get("tag")
    if isinstance(tag, str) and tag not in LAYER_OF:
        bad.append(Problem(src, lineno, f"flag: tag {tag!r} is not in the vocabulary"))
    elif isinstance(tag, str) and rec.get("layer") != LAYER_OF[tag]:
        bad.append(Problem(src, lineno, f"flag: tag {tag} is a {LAYER_OF[tag]} tag, but "
                                        f"layer says {rec.get('layer')!r}"))
    if bad:
        return None, bad
    line = rec.get("line")
    return Flag(review=review, file=rec["file"], anchor=rec["anchor"], tag=tag,
                layer=rec["layer"], severity=sev, claim=rec["claim"], probe=rec["probe"],
                refs=refs, elsewhere=elsewhere or (),
                shared_with_blueprint=bool(rec.get("shared_with_blueprint")),
                line=line if isinstance(line, int) else None, source=src), []


# ---------------------------------------------------------------- validation against the sources


def _occurrences(hay: str, needle: str) -> int:
    """Count the anchor in the file, tolerant of where LaTeX wrapped the line.

    Verbatim first; failing that, whitespace-flexible. An anchor quoted out of a `.tex`
    source crosses a line break about as often as not, and rejecting those would make the
    rule unusable rather than strict.
    """
    n = hay.count(needle)
    if n:
        return n
    flexible = r"\s+".join(re.escape(w) for w in needle.split())
    return len(re.findall(flexible, hay)) if flexible else 0


def known_labels(base: Path) -> set[str]:
    out: set[str] = set()
    for p in base.rglob("*.tex"):
        if SKIP_DIRS & set(p.parts):
            continue
        try:
            out.update(re.findall(r"\\label\{([^}]+)\}", p.read_text(encoding="utf-8")))
        except OSError:
            continue
    return out


def validate(flags: list[Flag], base: Path) -> tuple[list[Flag], list[Problem]]:
    """Enforce the anchor rule against the sources; report refs that resolve nowhere.

    A flag whose anchor is not locatable is dropped: it is not actionable, and a finding
    too diffuse to quote uniquely is usually too diffuse to act on. An unresolved `refs`
    label is reported but the flag is kept — the label is evidence for pooling, and a
    reviewer citing a label the checkout does not have is worth knowing about, not worth
    losing the flag over.
    """
    good: list[Flag] = []
    problems: list[Problem] = []
    labels = known_labels(base)
    cache: dict[str, str | None] = {}
    for f in flags:
        if f.file not in cache:
            p = base / f.file
            try:
                cache[f.file] = p.read_text(encoding="utf-8")
            except OSError:
                cache[f.file] = None
        text = cache[f.file]
        if text is None:
            problems.append(Problem(f.source, f.line or 0,
                                    f"flag: {f.file} is not under {base}"))
            continue
        n = _occurrences(text, f.anchor)
        if n != 1:
            problems.append(Problem(
                f.source, f.line or 0,
                f"flag: anchor occurs {n} times in {f.file}, not once — "
                f"{f.anchor[:60]!r}"))
            continue
        if labels:
            for r in f.refs:
                if r not in labels:
                    problems.append(Problem(f.source, f.line or 0,
                                            f"flag: refs label {r!r} resolves nowhere "
                                            f"under {base}"))
        good.append(f)
    return good, problems


def contract_conflicts(reviews: list[Review]) -> list[Problem]:
    """Two reviews of one target that declared different section contracts.

    Worth failing over: a wrong mapping invalidates every structural flag under it, and
    the disagreement is the only mechanical signal that one of them got it wrong.
    """
    by_target: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for r in reviews:
        by_target[r.target][r.contract].append(r.id)
    out = []
    for target, decls in sorted(by_target.items()):
        if len(decls) > 1:
            parts = "; ".join(f"{c} ({', '.join(sorted(ids))})"
                              for c, ids in sorted(decls.items()))
            out.append(Problem("-", 0, f"contract conflict on {target}: {parts}"))
    return out


# ---------------------------------------------------------------- pooling and ranking


def _anchor_join(a: str, b: str) -> bool:
    x, y = _norm(a), _norm(b)
    return x == y or x in y or y in x


def pool(flags: list[Flag]) -> list[Defect]:
    """Pool flags by underlying defect, within one file and one tag.

    Two flags are the same defect when they cite a label in common — the contract's
    finding 2, that threads are detectable from shared referents — or, for flags that cite
    no label at all (most voice tags), when one's anchor contains the other's.

    The key is `<file>::<TAG>::<referent>`, where the referent is the lexicographically
    smallest label the pool cites, or `anchor:<sha1[:8]>` of its smallest normalized
    anchor when it cites none. Two pools in the same (file, tag) cannot collide: if they
    shared a label they would have been joined, and if they are anchor-keyed their anchors
    do not overlap. The key is a function of the pooled set, so it is stable across runs
    over the same reviews; it is *not* stable across paper revisions (see the contract's
    open question on revision identity).
    """
    by_group: dict[tuple[str, str], list[Flag]] = defaultdict(list)
    for f in flags:
        by_group[(f.file, f.tag)].append(f)

    defects: list[Defect] = []
    for (file, tag), group in sorted(by_group.items()):
        u = _Union(len(group))
        for i, a in enumerate(group):
            for j in range(i + 1, len(group)):
                b = group[j]
                if (set(a.refs) & set(b.refs)) or (
                        not a.refs and not b.refs and _anchor_join(a.anchor, b.anchor)):
                    u.join(i, j)
        for idxs in u.groups():
            members = [group[i] for i in idxs]
            refs = sorted({r for m in members for r in m.refs})
            if refs:
                referent = refs[0]
            else:
                anchor = sorted(_norm(m.anchor) for m in members)[0]
                referent = "anchor:" + hashlib.sha1(
                    anchor.encode("utf-8")).hexdigest()[:8]
            defects.append(Defect(key=f"{file}::{tag}::{referent}", file=file, tag=tag,
                                  layer=LAYER_OF[tag], flags=members))
    return sorted(defects, key=lambda d: d.rank)


def thread(defects: list[Defect]) -> list[Thread]:
    """Propose threads: defects that reach across sections into one decision.

    Joined by a shared label, or — same tag only — by one defect's `elsewhere` naming the
    other's file. A thread of a single defect is not a thread and is not emitted.
    """
    u = _Union(len(defects))
    for i, a in enumerate(defects):
        a_else = {e for f in a.flags for e in f.elsewhere}
        for j in range(i + 1, len(defects)):
            b = defects[j]
            b_else = {e for f in b.flags for e in f.elsewhere}
            if set(a.refs) & set(b.refs) or a.tag == b.tag and (b.file in a_else or a.file in b_else):
                u.join(i, j)
    threads = []
    for idxs in u.groups():
        members = sorted((defects[i] for i in idxs), key=lambda d: d.rank)
        if len(members) > 1 and len({m.file for m in members}) > 1:
            threads.append(Thread(id="", defects=members))
    threads.sort(key=lambda t: (-len(t.reviews), -len(t.defects),
                                -max(d.severity for d in t.defects),
                                t.defects[0].key))
    return [Thread(id=f"T{i}", defects=t.defects) for i, t in enumerate(threads, 1)]


# ---------------------------------------------------------------- output


BOUNDARY = ("correctness is Lean's, grounding is the note-evaluator's, integrity is "
            "`linkage check`'s — none of them is reviewed here")


def to_json(reviews, defects, threads, problems) -> dict:
    return {
        "reviews": [{"id": r.id, "target": r.target, "contract": r.contract,
                     "contract_why": r.contract_why, "maturity": r.maturity,
                     "strengths": r.strengths, "floor": r.floor} for r in reviews],
        "threads": [{"id": t.id, "reviews": t.reviews, "files": t.files, "refs": t.refs,
                     "defects": [d.key for d in t.defects]} for t in threads],
        "defects": [{"key": d.key, "file": d.file, "tag": d.tag, "layer": d.layer,
                     "count": d.breadth, "reviews": d.reviews, "flags": len(d.flags),
                     "severity": d.severity, "refs": d.refs,
                     "anchors": [f.anchor for f in d.flags],
                     "claims": [f.claim for f in d.flags],
                     "probes": [f.probe for f in d.flags],
                     "shared_with_blueprint": any(f.shared_with_blueprint
                                                  for f in d.flags)} for d in defects],
        "malformed": [str(p) for p in problems],
    }


def _clip(s: str, n: int = 88) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def report(reviews, defects, threads, problems, top: int = 10) -> list[str]:
    """Threads first, then defects by layer — never the raw list first.

    That ordering is the whole point of the contract: a worklist is acted on in
    proportion to how short it is, so what is handed on is the threads and the decisions
    they imply, with the flags underneath as drill-down.
    """
    out: list[str] = []
    targets = sorted({r.target for r in reviews})
    decls = sorted({r.contract for r in reviews})
    out.append(f"{len(reviews)} review(s) of {', '.join(targets) or '(nothing)'} "
               f"[contract {', '.join(decls) or 'undeclared'}]")
    for r in reviews:
        out.append(f"  {r.id}: strengths — {_clip(r.strengths)}")
    out.append(f"  boundary: {BOUNDARY}")

    out.append("")
    out.append(f"THREADS ({len(threads)} proposed — a cluster is a lead, not a finding)")
    for t in threads:
        out.append(f"  {t.id}  x{len(t.reviews)} reviews, {len(t.defects)} defects  "
                   f"{', '.join(t.files)}")
        out.append(f"      refs: {', '.join(t.refs) or '(none)'}")
        for d in t.defects:
            out.append(f"      x{d.breadth} {d.tag:<12} {d.key.split('::')[-1]}")
    if not threads:
        out.append("  (none — every defect stayed inside one section)")

    for layer in ("structure", "voice"):
        rows = [d for d in defects if d.layer == layer]
        out.append("")
        out.append(f"{layer.upper()} ({len(rows)} defect(s), ranked by how many reviews "
                   "found each)")
        shown = rows if top <= 0 else rows[:top]
        for d in shown:
            mark = "  [blueprint-side]" if any(
                f.shared_with_blueprint for f in d.flags) else ""
            out.append(f"  x{d.breadth} sev<={d.severity}  {d.tag:<12} {d.file}{mark}")
            out.append(f"      {d.key.split('::')[-1]}  ({', '.join(d.reviews)})")
            for f in d.flags:
                out.append(f"      \"{_clip(f.anchor, 70)}\"")
                out.append(f"        claim: {_clip(f.claim)}")
                out.append(f"        probe: {_clip(f.probe)}")
        if len(rows) > len(shown):
            out.append(f"  … and {len(rows) - len(shown)} more; --top 0 or --json for all")

    out.append("")
    if problems:
        out.append(f"MALFORMED ({len(problems)} — reported, never silently dropped)")
        for p in problems:
            out.append(f"  {p}")
    else:
        out.append("MALFORMED (0)")
    return out


def aggregate(paths: list[Path], base: Path, top: int = 10) -> tuple[dict, list[str], int]:
    """The whole pass: parse, validate, pool, thread, rank. Returns (json, lines, rc)."""
    reviews, flags, problems = parse(paths)
    flags, more = validate(flags, base)
    problems = problems + more + contract_conflicts(reviews)
    defects = pool(flags)
    threads = thread(defects)
    return (to_json(reviews, defects, threads, problems),
            report(reviews, defects, threads, problems, top=top),
            1 if problems else 0)
