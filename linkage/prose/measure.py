"""Feature counts over extracted prose, and the baseline profiles they compare to.

Counts; never judges. Every feature here is something a regular expression can find
without being right about whether it should be there — which is the whole division
of labour: the floor measures, a human decides, and the agent only ever works on
families the measurement has already singled out.

**Rates are per thousand words of length >= 2.** Single-letter tokens are mostly
maths variables that survived a PDF text layer, and including them in the
denominator silently deflates every rate on exactly the sources that are already
worst. The same denominator is applied to every corpus, so the comparison holds.

**Two baselines, because they answer different questions.** The author corpus says
*is this like him*; the genre corpus (pre-LLM papers of the same field) says *is
this like a paper here*. Where they agree, a deviation is a real finding. Where
they disagree, the deviation is a matter of voice and not of register — and that
distinction is not recoverable from either one alone.

Each baseline declares which statistics it may carry (`supports`). A PDF-derived
corpus cannot support sentence-length medians: undelimited maths fragments into
short pseudo-sentences, inflating the short-sentence share and dragging the median
down. It leaves the *long*-sentence share untouched, because debris never produces
a long sentence — so that one statistic is still sound, and it is marked as such
rather than the whole corpus being thrown away.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .extract import EQ, MATH, _WORD, Block

PROSE_KINDS = {"prose", "abstract", "remark"}

# --- feature families ---------------------------------------------------------
# Tag names follow ai-prose-patterns.md §1 so counts, policy and the reviewer's
# output vocabulary all key on the same word. Families, never single words: word
# lists have aged badly and a per-word rate over 20k words is noise anyway.
FAMILIES: dict[str, re.Pattern] = {
    "BOOSTER": re.compile(
        r"\b(crucially|importantly|notably|indeed|in fact|essentially|"
        r"fundamentally|precisely|exactly what|of course|clearly)\b", re.I),
    "SALIENCE": re.compile(
        r"\b(it is worth (noting|remarking|stressing)|worth noting|note that|"
        r"notice that|observe that|it should be (noted|stressed)|"
        r"recall that|bear in mind)\b", re.I),
    "SINCERITY": re.compile(
        r"\b(to be clear|to be honest|the honest (assessment|answer)|in truth|"
        r"frankly|let us be (clear|direct)|it must be said)\b", re.I),
    "ADVERB": re.compile(
        r"\b(silently|quietly|gracefully|cleanly|faithfully|seamlessly|"
        r"elegantly|neatly|effortlessly|automatically)\b", re.I),
    "PARALADDER": re.compile(
        r"\b(in other words|that is to say|put differently|put another way|"
        r"which is to say|equivalently|or rather)\b", re.I),
    "NEGPAR": re.compile(
        r"\b(not\s+(?:\w+[\s,]+){0,5}?but(?:\s+rather)?\b|"
        r"is not\s+(?:\w+[\s,]+){0,5}?[—;]\s*it is\b|"
        r"rather than\s+(?:\w+[\s,]+){0,4}?,)", re.I),
    "REVEAL": re.compile(
        r"\b(what is really|what is actually|the real (question|issue|point)|"
        r"the point is|the key (insight|observation) is|"
        r"the whole point|what matters (here )?is)\b", re.I),
    "ATTITUDE": re.compile(
        r"\b(elegant|elegance|remarkable|remarkably|striking|strikingly|"
        r"beautiful|powerful|profound|deep(ly)? (structural|reason)|"
        r"surprising|surprisingly|natural(ly)? enough)\b", re.I),
    "SIGNPOST": re.compile(
        r"\b(having (established|shown|seen)|we now turn|we turn now|"
        r"in this (section|subsection) we|the (rest|remainder) of this|"
        r"before (proceeding|turning)|as we (shall|will) see)\b", re.I),
    "VAGUEATTR": re.compile(
        r"\b(it is well known|well known that|standard results?|"
        r"it is (classical|standard) that|one can show|it can be shown|"
        r"as is (well )?known)\b", re.I),
}

PUNCT: dict[str, re.Pattern] = {
    "emdash": re.compile("—"),
    "semicolon": re.compile(";"),
    "colon": re.compile(":"),
    "parenthesis": re.compile(r"\("),
}

# Everything countable, so the report and the drill-down key on one namespace.
ALL_FEATURES: dict[str, re.Pattern] = {**PUNCT, **FAMILIES}


@dataclass
class Features:
    words: int = 0                    # tokens of length >= 2
    sentences: int = 0
    punct: dict[str, int] = field(default_factory=dict)
    families: dict[str, int] = field(default_factory=dict)
    lens: list[int] = field(default_factory=list)

    def rate(self, key: str) -> float:
        n = self.punct.get(key, self.families.get(key, 0))
        return 1000.0 * n / self.words if self.words else 0.0

    @property
    def median(self) -> float:
        s = sorted(self.lens)
        return s[len(s) // 2] if s else 0.0

    def share(self, lo: int | None = None, hi: int | None = None) -> float:
        if not self.lens:
            return 0.0
        sel = [x for x in self.lens
               if (lo is None or x > lo) and (hi is None or x < hi)]
        return 100.0 * len(sel) / len(self.lens)


def real_words(text: str) -> list[str]:
    toks = _WORD.findall(text.replace(EQ, " ").replace(MATH, " "))
    return [t for t in toks if len(t) > 1]


def features(blocks: list[Block], kinds: set[str] | None = PROSE_KINDS) -> Features:
    f = Features(punct={k: 0 for k in PUNCT}, families={k: 0 for k in FAMILIES})
    for b in blocks:
        if kinds is not None and b.kind not in kinds:
            continue
        f.words += len(real_words(b.text))
        for k, pat in PUNCT.items():
            f.punct[k] += len(pat.findall(b.text))
        for k, pat in FAMILIES.items():
            f.families[k] += len(pat.findall(b.text))
        f.lens += [s.words for s in b.sentences if s.words > 0]
    f.sentences = len(f.lens)
    return f


# --- baselines ----------------------------------------------------------------

@dataclass
class Baseline:
    name: str
    question: str            # what a deviation from this baseline means
    sources: list[str]
    supports: list[str]      # statistic keys this corpus may legitimately carry
    features: Features

    def to_json(self) -> dict:
        d = asdict(self)
        d["features"]["lens"] = self.features.lens
        return d

    @staticmethod
    def from_json(d: dict) -> "Baseline":
        fe = Features(**d.pop("features"))
        return Baseline(features=fe, **d)


ALL_STATS = ["rates", "long_share", "median", "short_share"]


def save(baselines: list[Baseline], path: Path) -> None:
    path.write_text(json.dumps([b.to_json() for b in baselines], indent=1),
                    encoding="utf-8")


def load(path: Path) -> list[Baseline]:
    return [Baseline.from_json(d) for d in json.loads(path.read_text(encoding="utf-8"))]
