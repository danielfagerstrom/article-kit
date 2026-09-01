"""A behaviour fingerprint for the prose extractor.

`prose-baseline.json` is computed by running the extractor over a corpus, so a
change to the extractor silently invalidates it: the paper is then measured one
way and compared against numbers produced another way. That happened once already
-- the display-ends-a-sentence fix moved the author baseline's median from 20 to
19 -- and it was caught only because someone thought to re-run the build.

So the baseline records what the extractor *did*, and the report checks it.

**Behaviour, not source.** Hashing the module would trip on a comment and teach
everyone to ignore it. This runs the extractor over a fixed probe and hashes the
result, so only a change that alters an extraction moves the digest -- which is
exactly the set of changes that invalidate a baseline.

The probe is deliberately in code rather than in a data file: it is part of the
check, and a data file could drift without anyone noticing.
"""
from __future__ import annotations

import hashlib

# Each stanza pins one decision the measurement depends on. Adding a case is a
# deliberate act: it changes the digest, so every baseline must be rebuilt.
PROBE = r"""
\section{Probe}

A display inside a sentence must not end it,
\[
  \Phi_{y,z}\,\Phi_{x,y} \;=\; \Phi_{x,z}, \qquad 0 \le x \le y \le z,
\]
and the sentence continues past it.

A display may also end a sentence,
\[
  T_1 \;\stackrel{d}{=}\; c\,T_1 + R_c \qquad \text{for every } c \in (0,1).
\]
A new sentence then begins here.

A colon inside a display is not a full stop,
\[
  \partial_t^n u \;=\; A^n u :
\]
so this clause belongs to the same sentence.

Abbreviations do not split: see Thm.~5.2, p.~49 and \S\ref{sec:probe} for the
detail, and cf.\ \sscite{someone2020thing}. Inline maths may span a wrapped
line, as in $\Phi_{x,y} \in
\BFz$, without swallowing the prose that follows.

An em-dash aside --- like this one --- is prose; an en-dash range 1--2 is not.

% shared with blueprint thm:probe
\begin{theorem}[a probe statement]\label{thm:probe}
Statement bodies are classified apart from \emph{connective} prose.
\end{theorem}

\begin{proof}
Proof bodies are their own kind.
\end{proof}
"""


def extractor_fingerprint() -> str:
    """A digest of what the extractor makes of `PROBE`."""
    from .extract import extract_text

    ex = extract_text(PROBE, "probe.tex")
    parts: list[str] = []
    for b in ex.blocks:
        parts.append(f"{b.kind}|{b.env or '-'}|{b.emdashes}")
        for s in b.sentences:
            parts.append(f"  {s.words}/{s.math}/{s.cites}/{s.refs}|{s.text}")
    parts.append(f"unknown={sorted(ex.unknown)}")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:12]
