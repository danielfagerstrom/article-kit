"""The trust boundary: which axioms a headline theorem may depend on.

`#print axioms` on the article's proved theorems must reduce to Lean core plus the ledger's
analytic interfaces and nothing else. That list has to be declared *outside* the Lean
sources — deriving it from the `axiom` declarations would let a newly added axiom authorize
itself, which is exactly what the guard exists to prevent.

It is also not derived from `AXIOMS.md`'s `**Lean:**` back-pointers, though that was the
obvious idea. Those segments name proved declarations and downstream consequences alongside
the interfaces (43 identifiers against the 11 real axioms for scale-space-foundations), so
using them would silently widen the boundary.

So the article declares it, one name per line, in `blueprint/trust-boundary.txt` — and this
module *cross-checks* that declaration against the ledger: every name must appear in some
entry's `**Lean:**` segment. That catches the case the old inline-YAML list could not — a
name added to CI that was never reviewed into the ledger.
"""
from __future__ import annotations

import re
from pathlib import Path

from .config import Config

# Lean's own axioms. Present in every trust base; not the article's to declare.
LEAN_CORE = ("propext", "Classical.choice", "Quot.sound")


def declared(cfg: Config) -> list[str]:
    """The article's declared interface axioms, in file order."""
    path = trust_file(cfg)
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def trust_file(cfg: Config) -> Path:
    return cfg.axioms.parent / "trust-boundary.txt"


def ledger_lean_mentions(cfg: Config) -> set[str]:
    """Short declaration names mentioned in the ledger's `**Lean:**` segments.

    Deliberately over-broad — it is used only to confirm a declared axiom *was* reviewed,
    never to authorize one.
    """
    text = cfg.axioms.read_text(encoding="utf-8")
    out: set[str] = set()
    for m in re.finditer(r"\*\*Lean:\*\*(.*?)(?=\n\s*\n|\*\*Cite:\*\*|\Z)", text, re.S):
        for ident in re.findall(r"`([A-Za-z_][\w'.]*)`", m.group(1)):
            out.add(ident.split(".")[-1])
    return out


def allowlist(cfg: Config) -> list[str]:
    """Everything a headline theorem may depend on: Lean core + the declared interfaces."""
    return [*LEAN_CORE, *declared(cfg)]


def ungrounded(cfg: Config) -> list[str]:
    """Declared axioms that no ledger entry mentions — declared but never reviewed."""
    mentions = ledger_lean_mentions(cfg)
    return [d for d in declared(cfg) if d.split(".")[-1] not in mentions]
