"""Pandoc-markdown prose -> the same classified blocks as the LaTeX extractor.

The second dialect. The baseline corpus reaches us as markdown (the librarian's
pandoc conversion of the original LaTeX), and a baseline is only comparable if
both sides are measured the same way — same sentence splitter, same placeholders,
same environment classes. So this module's only job is to reach `Block`; everything
after that is shared with `extract.py`.

Pandoc-from-LaTeX is the good case: math is delimited (`$…$`, `$$…$$`), theorem
environments survive as fenced divs (`::: theorem`), citations as `[@key]`, and
cross-references as `[text](#anchor)`. All four are recoverable exactly.

The bad case is markdown derived from a PDF text layer, where **math is not
delimited** and lands in the prose as debris (`Φ τ u ( t )`). Nothing can mask it
reliably, so instead of pretending, `residue_score()` measures how much of a
source looks like undelimited math and the caller decides whether the source is
usable. A corpus is allowed to reject a document; it is not allowed to quietly
count formula fragments as words.
"""
from __future__ import annotations

import re
from pathlib import Path

from .extract import (CITE, ENV_KIND, EQ, LIST_ENVS, MATH, REF, _WORD, Block,
                      Extraction, mask_math, measure, split_sentences)

# Fenced-div names that are grouping wrappers or non-prose, not statements.
DIV_DROP = {"thebibliography", "diagram", "figure", "table", "center", "tikzpicture"}
# Pandoc pluralises some environments when several share a div.
DIV_ALIAS = {"definitions": "definition", "examples": "example",
             "theorems": "theorem", "lemmas": "lemma", "remarks": "remark",
             "propositions": "proposition", "corollaries": "corollary"}

# Applied to the whole document before it is split into lines — pandoc display math
# routinely spans blank lines, and splitting first cuts the block in half.
MD_MATH = [
    (re.compile(r"\$\$.*?\$\$", re.S), EQ),
    (re.compile(r"\\\[.*?\\\]", re.S), EQ),
    (re.compile(r"\\begin\{([A-Za-z]+\*?)\}.*?\\end\{\1\}", re.S), EQ),
    # Inline math must be allowed to span a hard-wrapped line break — the sources are
    # wrapped mid-formula — but never a blank line. Without that bound, one formula
    # whose delimiters fail to pair lets its closing `$` reach the *next* formula's
    # opening `$` and swallow every word between them.
    (re.compile(r"(?<![\\$])\$(?:\\[\s\S]|[^$\\\n]|\n(?!\s*\n))+?\$"), MATH),
]
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_XREF = re.compile(r"\[[^\]]*\]\(#[^)]*\)")
_URL = re.compile(r"\[([^\]]*)\]\((?:https?|mailto|ftp)[^)]*\)")
_CITE_BR = re.compile(r"\[(?:[^\]]*?@[^\]]*?)\]")
_CITE_BARE = re.compile(r"(?<![\w`])@[A-Za-z][\w:.\-]*")
_ATTR = re.compile(r"\{[.#][^}]*\}")
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_DIV_OPEN = re.compile(r"^:::+\s*(?:\{([^}]*)\}|([A-Za-z][A-Za-z-]*))\s*$")
_DIV_CLOSE = re.compile(r"^:::+\s*$")
_BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_TABLE = re.compile(r"^\s*(?:\|.*\||[-+:| ]{6,})\s*$")
_BACKSLASH = re.compile(r"\\([A-Za-z]+)")


def _div_name(m: re.Match) -> str | None:
    """The environment a fenced div opens, from `::: theorem` or `::: {.theorem}`."""
    if m.group(2):
        raw = m.group(2)
    else:
        cls = re.findall(r"\.([A-Za-z][A-Za-z-]*)", m.group(1) or "")
        if not cls:
            return None
        raw = cls[0]
    raw = raw.lower()
    return DIV_ALIAS.get(raw, raw)


def _inline(text: str, unknown: dict[str, int], emph: list[str]) -> str:
    text = _IMAGE.sub(" ", text)
    text = _CITE_BR.sub(CITE, text)
    text = _CITE_BARE.sub(CITE, text)
    text = _XREF.sub(REF, text)
    text = _URL.sub(r"\1", text)
    text = _ATTR.sub(" ", text)
    for m in re.finditer(r"(?<!\*)\*([^*\n]+)\*(?!\*)", text):
        emph.append(m.group(1).strip())
    text = re.sub(r"\*\*([^*\n]+)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", text)
    text = re.sub(r"(?<![\w`])_([^_\n]+)_(?![\w`])", r"\1", text)
    text = text.replace("`", "")
    # Any surviving backslash command is LaTeX pandoc could not map. Record it and
    # keep nothing but the name's absence -- same audit rule as the LaTeX side.
    for m in _BACKSLASH.finditer(text):
        unknown[m.group(1)] = unknown.get(m.group(1), 0) + 1
    text = _BACKSLASH.sub(" ", text)
    return text


def extract_md(path: Path) -> Extraction:
    return extract_md_text(path.read_text(encoding="utf-8", errors="replace"),
                           path.name)


def extract_md_text(src: str, name: str = "<text>") -> Extraction:
    """Extract from markdown already in memory.

    The repair passes run in memory over the librarian's sources, and writing a
    repaired copy back beside the original would put an unowned second copy of
    someone else's paper in a tree this package does not write to.
    """
    masked, line_of = mask_math(src, MD_MATH)
    # Walk the masked text by line, but report the *source* line number.
    lines, srcno, at = [], [], 0
    for ln in masked.split("\n"):
        lines.append(ln)
        srcno.append(line_of[min(at, len(line_of) - 1)])
        at += len(ln) + 1

    # Heading depth is document-relative: pandoc emits `#` for \section in an
    # article and for \chapter in a book, so a fixed level would mis-rank the
    # thesis against the papers.
    levels = sorted({len(m.group(1)) for ln in lines if (m := _HEADING.match(ln))})
    top = levels[0] if levels else 1

    unknown: dict[str, int] = {}
    dropped: dict[str, int] = {}
    blocks: list[Block] = []
    section, subsection = "(front matter)", None
    div_stack: list[str] = []
    buf: list[str] = []
    buf_at = 1

    def kind_now() -> str:
        for d in reversed(div_stack):
            if d in ENV_KIND:
                return ENV_KIND[d]
            if d in LIST_ENVS:
                return "list"
        return "prose"

    def flush(is_list: bool = False) -> None:
        nonlocal buf
        text = " ".join(buf).strip()
        buf = []
        if not text:
            return
        emph: list[str] = []
        norm = _inline(text, unknown, emph)
        emdashes = norm.count("—") + norm.count("---")
        norm = re.sub(r"\s+", " ", norm.replace("---", "—")).strip()
        if not norm or not _WORD.search(norm.replace(EQ, " ").replace(MATH, " ")):
            return
        b = Block(kind="list" if is_list else kind_now(),
                  env=div_stack[-1] if div_stack else None,
                  section=section, subsection=subsection, source=name,
                  line=buf_at, text=norm, emphases=emph, emdashes=emdashes)
        b.sentences = [measure(s) for s in split_sentences(norm)]
        blocks.append(b)

    skipping = 0          # depth of a dropped div
    in_list = False
    for idx, line in enumerate(lines):
        no = srcno[idx]
        if m := _DIV_OPEN.match(line):
            flush(in_list)
            in_list = False
            div = _div_name(m)
            if skipping or (div in DIV_DROP):
                skipping += 1
                if div:
                    dropped[div] = dropped.get(div, 0) + 1
                continue
            div_stack.append(div or "div")
            buf_at = no + 1
            continue
        if _DIV_CLOSE.match(line):
            flush(in_list)
            in_list = False
            if skipping:
                skipping -= 1
            elif div_stack:
                div_stack.pop()
            continue
        if skipping:
            continue
        if m := _HEADING.match(line):
            flush(in_list)
            in_list = False
            title = re.sub(r"\s+", " ", _inline(m.group(2), unknown, [])).strip()
            title = _ATTR.sub("", title).strip()
            if len(m.group(1)) <= top:
                section, subsection = title, None
            else:
                subsection = title
            buf_at = no + 1
            continue
        if _TABLE.match(line):
            flush(in_list)
            in_list = False
            dropped["table-row"] = dropped.get("table-row", 0) + 1
            continue
        if not line.strip():
            flush(in_list)
            in_list = False
            buf_at = no + 1
            continue
        if m := _BULLET.match(line):
            flush(in_list)
            in_list = True
            buf_at = no
            buf.append(line[m.end():])
            continue
        if line.lstrip().startswith(">"):
            line = line.lstrip()[1:]
        if not buf:
            buf_at = no
        buf.append(line)
    flush(in_list)
    return Extraction(blocks=blocks, unknown=unknown, dropped_envs=dropped)


def residue_score(ex: Extraction) -> float:
    """Fraction of prose word tokens that are a single letter.

    The usable signal for undelimited math in a PDF-derived text layer: clean
    English runs ~1-3% (`a`, `I`, initials), while formula debris pushes it far
    higher because every variable becomes its own token. A screen for whether a
    source belongs in the corpus at all — not a correction, because there is no
    reliable way to put the delimiters back.
    """
    total = single = 0
    for b in ex.blocks:
        for w in _WORD.findall(b.text.replace(EQ, " ").replace(MATH, " ")):
            total += 1
            if len(w) == 1:
                single += 1
    return single / total if total else 0.0
