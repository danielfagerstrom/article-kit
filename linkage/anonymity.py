"""The mechanical half of a double-blind submission's anonymity (ADR-0002).

Run by `linkage check` on a repository whose `[article]` table says `anonymous = true`. It
scans the paper's `.tex` and `.bib` sources for what leaks identity mechanically: the
creators' names (`[release] creators`), the repository's own identifying patterns
(`[article] identity`: an account, a domain, a project subdomain), repository URLs, e-mail
addresses, the name-bearing macros, and first-person self-citation.

The identifying patterns come from the private repository's own `linkage.toml`, never from
this module: a framework that is public must not carry the list of what an anonymous paper
hides. A clean run is a floor, not a certificate; a narrative giveaway ("continuing the
programme of my 2005 paper") needs a human read before submission.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .config import Config

EXEMPT = "anonymity-ok"
"""A line carrying this marker is exempt: an anonymous/camera-ready switch legitimately
holds both branches."""

GENERIC: tuple[tuple[str, str], ...] = (
    (r"github\.com", "repository URL"),
    (r"@[A-Za-z0-9._%+-]+\.[A-Za-z]{2,}", "e-mail address"),
    (r"\\thanks\b", "\\thanks note (funding or affiliation)"),
    (r"\\email\b", "e-mail macro"),
    (r"\\institute\b", "affiliation"),
    (r"\bour (earlier|previous|prior) (work|paper|article)\b", "first-person self-citation"),
    (r"\bin our\b.*\bwe (show|prove|introduce)\b", "first-person self-citation"),
    (r"\bas we (showed|proved|argued) in\b", "first-person self-citation"),
)
NAME = "identifying name"
# A citekey never renders, and citing one's own earlier work by key is normal: the argument
# of a citation macro is blanked before the patterns run.
CITEARG = re.compile(r"(\\(?:ss|no)?cite[a-zA-Z]*\*?(?:\[[^\]]*\])*)\{[^}]*\}")


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    why: str
    text: str


def _fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def identity_patterns(cfg: Config) -> list[tuple[str, str]]:
    """The creators' family names (as written and accent-folded) and `[article] identity`."""
    pats: list[tuple[str, str]] = []
    for c in cfg.release.creators:
        family = c["name"].split(",")[0].strip()
        for form in dict.fromkeys((family, _fold(family))):
            if form:
                pats.append((re.escape(form), NAME))
    pats.extend((p, NAME) for p in cfg.article.identity)
    return pats


def scan(cfg: Config) -> list[Finding]:
    pats = [(re.compile(p, re.IGNORECASE), why)
            for p, why in (*identity_patterns(cfg), *GENERIC)]
    out: list[Finding] = []
    for d in cfg.papers:
        for f in sorted((*d.rglob("*.tex"), *d.rglob("*.bib"))):
            # A bibliography entry naming the author is a reference, not a claim of authorship.
            bib = f.suffix == ".bib"
            for n, raw in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if EXEMPT in raw:
                    continue
                target = CITEARG.sub(r"\g<1>{}", raw)
                for rx, why in pats:
                    if bib and why == NAME:
                        continue
                    if rx.search(target):
                        out.append(Finding(f.relative_to(cfg.root).as_posix(), n, why,
                                           raw.strip()))
                        break
    return out
