r"""Restraint-budget counts by zone: `linkage prose register`.

For each paper source file, count em-dashes (`---`) and semicolons, and find runs of three or
more consecutive long sentences, separately in three zones:

  prose      paper-side connective text, remarks and captions -- the text the register pass edits
  statement  the blocks under a `% shared with blueprint` marker (byte-shared, never edited here)
  proof      `\begin{proof} ... \end{proof}` blocks (the proofs of record; edited at the blueprint)

Comments, math displays and inline math are stripped before counting, so that a semicolon in a
formula or in a `\cite` key list does not count. Sentences are split on `.` `!` `?` followed by a
space; a "long" sentence has more than `--long-at` words.

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


def analyse(path: Path, show_runs: bool = False, long_at: int = DEFAULT_LONG):
    """({zone: (em-dashes, semicolons, words)}, [(first line, sentence lengths)])."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    buf: dict[str, list[tuple[int, str]]] = {z: [] for z in ZONES}
    for zone, i, line in zones(lines):
        buf[zone].append((i, line))
    out = {}
    for zone, items in buf.items():
        text = strip_math("\n".join(ln for _, ln in items))
        out[zone] = (text.count("---"), text.count(";"),
                     len(re.findall(r"[A-Za-z][A-Za-z'\-]*", text)))
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


def report(files: list[Path], show_runs: bool = False, long_at: int = DEFAULT_LONG) -> list[str]:
    out = [f"{'file':24s} {'zone':10s} {'---':>5s} {'semi':>5s} {'words':>7s}"]
    tot = {z: [0, 0, 0] for z in ZONES}
    for f in files:
        counts, runs = analyse(f, show_runs, long_at)
        for zone in ZONES:
            d, s, w = counts[zone]
            out.append(f"{f.name:24s} {zone:10s} {d:5d} {s:5d} {w:7d}")
            for k, v in enumerate((d, s, w)):
                tot[zone][k] += v
        for start, lens in runs:
            out.append(f"    long-run at {f.name}:{start}  sentence lengths {lens}")
    for zone in ZONES:
        d, s, w = tot[zone]
        out.append(f"{'TOTAL':24s} {zone:10s} {d:5d} {s:5d} {w:7d}")
    return out


def sources(paper: Path) -> list[Path]:
    """The paper's own section sources: every `.tex` of the directory except `main.tex`, which
    is the preamble and the `\\input` list, not prose."""
    return [f for f in sorted(paper.glob("*.tex")) if f.name != "main.tex"]
