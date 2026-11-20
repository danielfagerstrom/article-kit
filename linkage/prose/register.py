r"""Restraint-budget counts by zone: `linkage prose register`.

For each paper source file, count em-dashes (`---`), semicolons and "ask" used for a requirement,
and find runs of three or more consecutive long sentences, separately in three zones:

  prose      paper-side connective text, remarks and captions -- the text the register pass edits
  statement  the blocks under a `% shared with blueprint` marker (byte-shared, never edited here)
  proof      `\begin{proof} ... \end{proof}` blocks (the proofs of record; edited at the blueprint)

Comments, math displays and inline math are stripped before counting, so that a semicolon in a
formula or in a `\cite` key list does not count. Sentences are split on `.` `!` `?` followed by a
space; a "long" sentence has more than `--long-at` words.

The `ask` column counts `ask(s|ed)` where an axiom system or a definition *requires* something
("Burt and Adelson ask it to be separable", "(A8) asked at one dilation", "asks more than a pyramid
needs"): `WRITING.md` § 3 says "require". The question sense ("this section asks which stencils")
is not counted: a question word, `about`, `by` or "question" after the verb rules a match out, as
does a person as its object ("ask all observers to report", "ask themselves whether"), and `ask(ed)
to` counts only before `be` or a determiner ("asked to point out" is a request to a person).
Tuned against the `prose-baseline.json` sources (2026-11-20): the author's four papers have no
`ask(s|ed)?`; the genre's nine have fifteen, and the four counted are requirements ("ask that the
analysis commutes", "ask for a reverse heat equation", "asks for", "the properties asked to the
scale-space"). The tests carry each of the fifteen.

Ported from `spatial-hemigroup-scale-space`'s `scripts/count-register.py` (ADR-0001 step 5): the
paper directory it hard-coded is now the module's, read from `linkage.toml`.

Why this lives beside `linkage prose stats` rather than inside it: `stats` measures the article
against the author and genre baselines and says *which patterns* to fix; this counts two marks
and one shape per zone, which is what the writing standard's restraint budget is stated in, and
its zones are the linkage ones (a shared statement is not the paper's text to edit).
"""
from __future__ import annotations

import re
from pathlib import Path

DEFAULT_LONG = 30

_DET = r"(?:the|a|an|every|each|all|its|their|this|these|those|one|two|no)"
_QUESTION = r"(?:which|what|whether|if|how|why|when|where|who|whom|whose|about|by)"
_PERSON = (r"(?:(?:all|the|a|every|each)\s+)?(?:observers?|readers?|persons?|people|authors?|"
           r"subjects?|oneself|ourselves|themselves|himself|herself|us|you|me)")
ASK_REQUIREMENT = re.compile(
    r"\bask(?:s|ed)?\b"
    rf"(?!\s+{_QUESTION}\b)"                            # the question sense
    r"(?!\s+(?:[A-Za-z]+\s+){0,2}(?:questions?|problems?)\b)"
    rf"(?!\s+{_PERSON}\b)"                              # a request to a person
    rf"(?!\s+to\s+(?!be\b|{_DET}\b))"                   # "asked to point out"
    r"(?=\s+(?:"
    rf"to\s+(?:be|{_DET})\b"                            # "asked to be", "asked to the"
    r"|(?:for|more|less|only|much|little|nothing|that|too|at|of|on|along|between|throughout)\b"
    r"|X\b"                                             # inline maths: "asks $u(0) \le f(0)$"
    rf"|(?:it|them|{_DET})\b"                           # an object: "asks it to", "asks every"
    r"|[A-Za-z]+(?:\s+[A-Za-z]+)?\s+to\s"               # "asks the kernel to", "asks X to"
    r"))",
    re.I)

ENV_END = re.compile(r"\\end\{(definition|proposition|lemma|theorem|corollary|remark)\}")
ZONES = ("prose", "proof", "statement")


def zones(lines):
    """Yield (zone, lineno, text) for each line, zone in prose/statement/proof."""
    zone = "prose"
    pending_statement = False
    for i, raw in enumerate(lines, 1):
        line = raw.split("%")[0] if not raw.lstrip().startswith("%") else ""
        stripped = raw.strip()
        if stripped.startswith("% shared with blueprint"):
            pending_statement = True
            continue
        if pending_statement and stripped.startswith("\\begin{"):
            zone = "statement"
            pending_statement = False
        if zone == "prose" and stripped.startswith("\\begin{proof}"):
            zone = "proof"
        yield zone, i, line
        if zone == "statement" and ENV_END.search(stripped):
            zone = "prose"
        if zone == "proof" and stripped.startswith("\\end{proof}"):
            zone = "prose"


def strip_math(text: str) -> str:
    text = re.sub(r"\\\[.*?\\\]", " ", text, flags=re.S)
    text = re.sub(r"\\begin\{(equation|align|gather)\*?\}.*?\\end\{\1\*?\}", " ", text, flags=re.S)
    text = re.sub(r"\$[^$]*\$", " X ", text)
    text = re.sub(r"\\(sscite|cite|ref|label|eqref)\{[^}]*\}", " ", text)
    return text


def asks(lines) -> list[tuple[str, int, str]]:
    """(zone, line, matched text) for each "ask" of a requirement. The next line is read as
    lookahead, so a verb at the end of a line still sees its object."""
    zoned = [(zone, i, strip_math(line)) for zone, i, line in zones(lines)]
    hits = []
    for k, (zone, i, line) in enumerate(zoned):
        text = line + " " + (zoned[k + 1][2] if k + 1 < len(zoned) else "")
        for m in ASK_REQUIREMENT.finditer(text):
            if m.start() < len(line):
                hits.append((zone, i, " ".join(text[m.start():].split()[:5])))
    return hits


def analyse(path: Path, show_runs: bool = False, long_at: int = DEFAULT_LONG):
    """({zone: (em-dashes, semicolons, words, asks)}, [(first line, sentence lengths)])."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    buf: dict[str, list[tuple[int, str]]] = {z: [] for z in ZONES}
    for zone, i, line in zones(lines):
        buf[zone].append((i, line))
    ask_zones = [zone for zone, _, _ in asks(lines)]
    out = {}
    for zone, items in buf.items():
        text = strip_math("\n".join(ln for _, ln in items))
        out[zone] = (text.count("---"), text.count(";"),
                     len(re.findall(r"[A-Za-z][A-Za-z'\-]*", text)), ask_zones.count(zone))
    # long-sentence runs, prose zone only, paragraph by paragraph
    runs: list[tuple[int | None, list[int]]] = []
    if show_runs:
        para: list[str] = []
        start: int | None = None
        for i, line in [*buf["prose"], (None, "")]:
            if line.strip() == "" or i is None:
                if para:
                    text = strip_math(" ".join(para))
                    sents = [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
                    lens = [len(re.findall(r"[A-Za-z][A-Za-z'\-]*", s)) for s in sents]
                    run = 0
                    for n in lens:
                        run = run + 1 if n > long_at else 0
                        if run == 3:
                            runs.append((start, lens))
                            break
                para, start = [], None
            else:
                if start is None:
                    start = i
                para.append(line)
    return out, runs


def report(files: list[Path], show_runs: bool = False, long_at: int = DEFAULT_LONG,
           show_asks: bool = False) -> list[str]:
    out = [f"{'file':24s} {'zone':10s} {'---':>5s} {'semi':>5s} {'words':>7s} {'ask':>5s}"]
    tot = {z: [0, 0, 0, 0] for z in ZONES}
    for f in files:
        counts, runs = analyse(f, show_runs, long_at)
        for zone in ZONES:
            d, s, w, a = counts[zone]
            out.append(f"{f.name:24s} {zone:10s} {d:5d} {s:5d} {w:7d} {a:5d}")
            for k, v in enumerate((d, s, w, a)):
                tot[zone][k] += v
        for start, lens in runs:
            out.append(f"    long-run at {f.name}:{start}  sentence lengths {lens}")
        if show_asks:
            for zone, i, text in asks(Path(f).read_text(encoding="utf-8").splitlines()):
                out.append(f"    ask at {f.name}:{i} ({zone})  {text}")
    for zone in ZONES:
        d, s, w, a = tot[zone]
        out.append(f"{'TOTAL':24s} {zone:10s} {d:5d} {s:5d} {w:7d} {a:5d}")
    return out


def sources(paper: Path) -> list[Path]:
    """The paper's own section sources: every `.tex` of the directory except `main.tex`, which
    is the preamble and the `\\input` list, not prose."""
    return [f for f in sorted(paper.glob("*.tex")) if f.name != "main.tex"]
