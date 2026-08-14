"""The prose report — statistics first, instances underneath.

Deliberately the inverse of a lint report. If the problem is *overuse* rather than
presence, then the primary artifact is a rate table against baselines, and the
located instances are what you open for the two or three families that are
actually over. A list of 300 flagged sentences is not a finding; it is a way of
never reading any of them.

Three columns, and reading across them is the point:

- over BOTH baselines  -> a register deviation. This is the AI-prose signal.
- over the AUTHOR only -> a voice deviation. Normal for the field, not for him;
  an optional edit and his call.
- over the GENRE only  -> he has a habit the field does not share. Not a defect.

A statistic is only shown for a baseline that declares it can carry it: a
PDF-derived corpus cannot supply sentence-length medians, and printing one anyway
would be inventing a number.
"""
from __future__ import annotations

from pathlib import Path

from .extract import extract
from .measure import FAMILIES, PUNCT, Baseline, Features, features

MIN_WORDS = 300     # below this a rate is noise; sections are reported but marked


def _fmt(v: float) -> str:
    return f"{v:5.1f}"


MIN_COUNT = 5       # below this, a family's rate is one or two sentences


def _ratio(x: float, b: float) -> str:
    if b <= 0:
        return "  new" if x > 0 else "    -"
    r = x / b
    return f" >99x" if r > 99 else f"{r:4.1f}x"


def _verdict(x: float, bases: dict[str, float], supported: dict[str, bool],
             count: int, factor: float = 2.0) -> str:
    # A rate computed from two occurrences is not a finding, however large the
    # ratio: the baselines are 24k and 87k words, the sections often under 700.
    if count < MIN_COUNT:
        return ""
    over = [n for n, b in bases.items()
            if supported.get(n, False) and (b <= 0 < x or (b > 0 and x / b >= factor))]
    if len(over) == 2:
        return "BOTH"
    if over == ["author"]:
        return "voice"
    if over == ["genre"]:
        return "genre"
    return ""


def compare(target: Features, baselines: list[Baseline], stat: str = "rates") -> list[str]:
    by = {b.name: b for b in baselines}
    sup = {n: stat in b.supports for n, b in by.items()}
    keys = list(PUNCT) + list(FAMILIES)
    out = [
        f"  {'feature':<12}{'n':>5}{'paper':>6}{'author':>8}{'x':>7}"
        f"{'genre':>8}{'x':>7}  verdict",
        "  " + "-" * 62,
    ]
    rows = []
    for k in keys:
        x = target.rate(k)
        n = target.punct.get(k, target.families.get(k, 0))
        ba = by["author"].features.rate(k) if "author" in by else 0.0
        bg = by["genre"].features.rate(k) if "genre" in by else 0.0
        if x == 0 and ba == 0 and bg == 0:
            continue
        v = _verdict(x, {"author": ba, "genre": bg}, sup, n)
        rows.append((0 if v == "BOTH" else 1 if v else 2, -x, k, x, n, ba, bg, v))
    for _, _, k, x, n, ba, bg, v in sorted(rows):
        out.append(f"  {k:<12}{n:>5}{_fmt(x)}{_fmt(ba):>8}{_ratio(x, ba):>7}"
                   f"{_fmt(bg):>8}{_ratio(x, bg):>7}  {v}")
    out.append(f"    (a verdict needs at least {MIN_COUNT} occurrences; "
               f"'n' is the paper's raw count)")
    return out


def sentence_shape(target: Features, baselines: list[Baseline]) -> list[str]:
    by = {b.name: b for b in baselines}
    out = ["", "  sentence shape", "  " + "-" * 62,
           f"  {'':<14}{'paper':>7}{'author':>8}{'genre':>8}"]

    def row(label, fn, key):
        cells = []
        for n in ("author", "genre"):
            b = by.get(n)
            cells.append(f"{fn(b.features):>8.0f}" if b and key in b.supports
                         else f"{'  n/a':>8}")
        out.append(f"  {label:<14}{fn(target):>7.0f}" + "".join(cells))

    row("median words", lambda f: f.median, "median")
    row("< 10 words %", lambda f: f.share(hi=10), "short_share")
    row("> 30 words %", lambda f: f.share(lo=30), "long_share")
    out.append("    (n/a: a PDF-derived corpus fragments maths into short pseudo-"
               "sentences, so it")
    out.append("     may carry the long-sentence share but not the median or the "
               "short share)")
    return out


def per_section(paths: list[Path], baselines: list[Baseline]) -> list[str]:
    by = {b.name: b for b in baselines}
    ba, bg = by["author"].features, by["genre"].features
    out = ["", "  per section (connective prose only)", "  " + "-" * 76,
           f"  {'section':<26}{'words':>6}{'em/kw':>8}{'semi/kw':>9}"
           f"{'>30w%':>7}{'families/kw':>13}"]
    for p in paths:
        ex = extract(p)
        f = features(ex.blocks)
        if f.words == 0:
            continue
        fam = sum(f.families.values())
        mark = " ·" if f.words < MIN_WORDS else "  "
        out.append(f"  {p.stem[:24]:<24}{mark}{f.words:>6}{f.rate('emdash'):>8.1f}"
                   f"{f.rate('semicolon'):>9.1f}{f.share(lo=30):>7.0f}"
                   f"{1000 * fam / f.words:>13.1f}")
    out.append(f"  · fewer than {MIN_WORDS} words — rates are noise at this size")
    out.append(f"  baseline: author em {ba.rate('emdash'):.1f} semi "
               f"{ba.rate('semicolon'):.1f} >30w {ba.share(lo=30):.0f}%  |  "
               f"genre em {bg.rate('emdash'):.1f} semi {bg.rate('semicolon'):.1f} "
               f">30w {bg.share(lo=30):.0f}%")
    return out


def instances(paths: list[Path], family: str, limit: int = 40) -> list[str]:
    """The drill-down: located occurrences of one family, for a human to triage."""
    pat = FAMILIES[family]
    out = [f"  {family} — located instances", "  " + "-" * 76]
    n = 0
    for p in paths:
        for b in extract(p).blocks:
            if b.kind not in {"prose", "abstract", "remark"}:
                continue
            for s in b.sentences:
                if not pat.search(s.text):
                    continue
                n += 1
                if n > limit:
                    continue
                out.append(f"  {p.stem}:{b.line}  [{s.words}w]")
                out.append(f"      {s.text}")
    if n > limit:
        out.append(f"  … and {n - limit} more (showing {limit})")
    out.append(f"  {n} instance(s)")
    return out
