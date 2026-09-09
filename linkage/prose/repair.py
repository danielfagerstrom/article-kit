"""Repair passes for markdown derived from a PDF text layer.

Three defects make an otherwise on-genre paper unusable as a baseline, and all
three are mechanical. None of them touches an author's word choices, which is the
condition for a repair being legitimate here: it restores what the PDF extractor
broke, and stops.

The passes must run in this order — headers interrupt paragraphs, so removing them
first lets the other two see continuous text.

Every pass reports what it changed. A repair that cannot say what it did is
indistinguishable from corruption, and this corpus is a measuring instrument.
"""
from __future__ import annotations

import re
from collections import Counter

_WORDISH = re.compile(r"[A-Za-z][A-Za-z'’]+")
# `partic-\n\nular`, and the spaced variant `the- ory`
_HYPHEN_BREAK = re.compile(r"([A-Za-z]{2,})-[ \t]*\n\s*\n?[ \t]*([a-z]+)")
_HYPHEN_SPACE = re.compile(r"([A-Za-z]{2,})-[ \t]+([a-z]{2,})")


def _vocabulary(text: str) -> tuple[set[str], set[str]]:
    """Solid and hyphenated word forms attested in this document.

    The document is its own dictionary. `scale-space` breaking across a line must
    rejoin *with* its hyphen while `partic-ular` must rejoin without one, and no
    general rule distinguishes them — but a paper that hyphenates `scale-space`
    at a line end has almost certainly written it unbroken elsewhere.
    """
    solid = {w.lower() for w in _WORDISH.findall(text)}
    hyph = {m.group(0).lower() for m in
            re.finditer(r"[A-Za-z]{2,}-[a-z]{2,}", text)}
    return solid, hyph


def dehyphenate(text: str) -> tuple[str, dict]:
    solid, hyph = _vocabulary(text)
    stats = Counter()

    def join(m: re.Match) -> str:
        a, b = m.group(1), m.group(2)
        if (a + b).lower() in solid:
            stats["solid (attested)"] += 1
            return a + b
        if f"{a}-{b}".lower() in hyph:
            stats["kept hyphen (attested)"] += 1
            return f"{a}-{b}"
        stats["solid (default)"] += 1
        return a + b

    text = _HYPHEN_BREAK.sub(join, text)
    text = _HYPHEN_SPACE.sub(
        lambda m: join(m) if (m.group(1) + m.group(2)).lower() in solid
        else m.group(0), text)
    return text, dict(stats)


def strip_running_heads(text: str, min_repeats: int = 3,
                        max_words: int = 12) -> tuple[str, dict]:
    """Drop short blocks that repeat across the document — page furniture.

    Self-calibrating rather than pattern-matched: a running header is by
    definition the same short line appearing on many pages, and that is a property
    this function can see without being told the journal's layout.
    """
    blocks = text.split("\n\n")
    counts = Counter()
    for b in blocks:
        s = b.strip()
        if s and len(_WORDISH.findall(s)) <= max_words:
            counts[re.sub(r"\d+", "#", s)] += 1
    heads = {k for k, v in counts.items() if v >= min_repeats}
    kept, dropped = [], Counter()
    for b in blocks:
        s = b.strip()
        key = re.sub(r"\d+", "#", s)
        if s and key in heads and len(_WORDISH.findall(s)) <= max_words:
            dropped[key[:48]] += 1
            continue
        # bare page numbers repeat but each is unique, so catch them by shape
        if re.fullmatch(r"\d{1,4}", s):
            dropped["<page number>"] += 1
            continue
        kept.append(b)
    return "\n\n".join(kept), dict(dropped)


def reflow(text: str) -> tuple[str, dict]:
    """Rejoin blocks that a column extractor split mid-sentence.

    Left alone this is the worst of the three for stylometry: every split invents
    a sentence boundary, so the short-sentence share rises and the median falls —
    exactly the statistics the baseline exists to supply.
    """
    blocks = text.split("\n\n")
    out: list[str] = []
    joined = 0
    for b in blocks:
        s = b.strip()
        if not s:
            continue
        if out:
            prev = out[-1].rstrip()
            # a continuation: previous block does not close, this one does not open
            if (prev and not re.search(r"[.!?:;)\]]['\"”]?$", prev)
                    and not re.match(r"^[-*#|>]|^\d+[.)]\s", s)
                    and not prev.startswith("#")
                    and (s[0].islower() or s[0] in "([")):
                out[-1] = prev + " " + s
                joined += 1
                continue
        out.append(s)
    return "\n\n".join(out), {"blocks joined": joined}


def repair(text: str) -> tuple[str, dict]:
    text, heads = strip_running_heads(text)
    text, hyph = dehyphenate(text)
    text, flow = reflow(text)
    return text, {"running heads": heads, "dehyphenated": hyph, "reflow": flow}
