"""Building the two baseline profiles from the librarian's sources.

The corpus is *declared here and measured on demand* — the paper texts are the
librarian's, and this repo stores only the derived counts. That keeps the single-
writer rule (the librarian owns sources) and keeps copyrighted text out of a repo
whose job is to hold a measuring instrument.

PDF-derived sources are repaired in memory, never written back. A repaired file on
disk would be a second copy of someone else's paper with no owner and no way to
tell it from the original.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .markdown import extract_md_text, residue_score
from .measure import Baseline, Features, PROSE_KINDS, features
from .repair import repair

LIBRARY = Path("G:/My Drive/Zotero_Library")

# Pandoc-from-LaTeX: maths delimited, environments preserved. Carries every statistic.
AUTHOR_SOURCES = [
    "fagerstrom-2004-eccv-galilean-invariants",
    "fagerstrom-2005-ijcv-temporal-scale-spaces",
    "fagerstrom-2007-ssvm-spatio-temporal",
    "fagerstrom-2011-spatio-temporal-scale-space",
]

# Docling-from-PDF, all published <= 2011, none by Fagerstrom. Maths is undelimited
# and fragments into short pseudo-sentences, so this corpus may not carry medians or
# the short-sentence share. Debris never lengthens a sentence, so the long-sentence
# share and the punctuation/family rates stand.
GENRE_SOURCES = [
    "lindeberg2011generalized",
    "r.duits2004axioms",
    "alvarez1993axioms",
    "koenderink1992local",
    "guichard1998morphological",
    "koenderink1984structure",
    "florack1993cartesian",
    "florackFamiliesTunedScalespace1992",
    "a.saldenLinearScalespaceTheory1998",   # usable only after repair
]

# On genre and converted, but beyond repair: after de-hyphenation and reflow the
# median is still 9 words and half its sentences are under ten, which is debris
# rather than register. Recorded so the exclusion is a decision, not an oversight.
GENRE_REJECTED = {
    "lindebergTimeRecursiveVelocityAdaptedSpatioTemporal2002":
        "residue 18.9% after repair; median 9w, 50% of sentences under 10w",
    "koenderink1992generic": "image-only PDF, 0 text chars, needs OCR",
}


@dataclass
class SourceStat:
    key: str
    words: int
    residue: float
    repaired: dict


def _find() -> dict[str, Path]:
    return {p.stem: p for p in LIBRARY.rglob("*.md")}


def measure_sources(keys: list[str], *, do_repair: bool,
                    warn=print) -> tuple[Features, list[SourceStat]]:
    found = _find()
    blocks, stats = [], []
    for k in keys:
        p = found.get(k)
        if p is None:
            warn(f"  baseline source missing: {k}")
            continue
        raw = p.read_text(encoding="utf-8", errors="replace")
        rep = {}
        if do_repair:
            raw, rep = repair(raw)
        ex = extract_md_text(raw, p.name)
        blocks += ex.blocks
        f = features(ex.blocks)
        stats.append(SourceStat(k, f.words, residue_score(ex), rep))
        if ex.unknown:
            warn(f"  {k}: unrecognised commands {dict(list(ex.unknown.items())[:5])}")
    return features(blocks), stats


def build(warn=print) -> tuple[list[Baseline], dict[str, list[SourceStat]]]:
    af, astat = measure_sources(AUTHOR_SOURCES, do_repair=False, warn=warn)
    gf, gstat = measure_sources(GENRE_SOURCES, do_repair=True, warn=warn)
    return [
        Baseline(
            name="author",
            question="is this like him? — governs voice",
            sources=AUTHOR_SOURCES,
            supports=["rates", "long_share", "median", "short_share"],
            features=af),
        Baseline(
            name="genre",
            question="is this like a paper in this field? — governs the AI-register reading",
            sources=GENRE_SOURCES,
            supports=["rates", "long_share"],
            features=gf),
    ], {"author": astat, "genre": gstat}
