"""The side inputs the checks run against: Lean, the axiom ledger, the paper, git.

These are read the same way whatever dialect the blueprint is written in — the Lean sources
are Lean, the ledger is markdown, the paper is LaTeX — so they live outside `parse_latex`
and survive a change of blueprint format untouched.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .config import Config
from .model import LedgerEntry, PaperMarker

# a Lean declaration keyword, allowing leading attributes / modifiers
DECL_RE = re.compile(
    r"(?m)^\s*(?:@\[[^\]]*\]\s*)?"
    r"(?:(?:private|protected|noncomputable|scoped|local|partial|unsafe)\s+)*"
    r"(?:theorem|lemma|def|abbrev|structure|instance|axiom)\s+([A-Za-z_][\w']*)"
)


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def lean_declared_names(cfg: Config) -> set[str]:
    """Every declaration name in the article's Lean sources (build artifacts excluded)."""
    names: set[str] = set()
    for f in cfg.lean.rglob("*.lean"):
        if ".lake" in f.parts:
            continue
        names |= set(DECL_RE.findall(read(f)))
    return names


def ledger_entries(cfg: Config) -> dict[str, LedgerEntry]:
    """`AXX` -> its ledger entry, with the primary citation off the ``**Cite:**`` line.

    The line's grammar (AXIOMS.md, backfilled 2026-07-26): ``**Cite:** @citekey — anchor``,
    optionally more ``·``-separated segments (corroborations); the FIRST segment is the
    primary and is what the manifest projects. ``**Cite:** — pending (…)`` yields null
    citekey/anchor; a missing line leaves `has_cite_line` False (fatal check 6 flags it).
    """
    text = read(cfg.axioms)
    key = cfg.ledger_key
    out: dict[str, LedgerEntry] = {}
    for m in re.finditer(rf"(?ms)^##\s*({key})\b(.*?)(?=^##\s*{key}\b|\Z)", text):
        aid, body = m.group(1), m.group(2)
        cm = re.search(r"\*\*Cite:\*\*\s*(.+)", body)
        if not cm:
            out[aid] = LedgerEntry(id=aid, has_cite_line=False)
            continue
        first = cm.group(1).split("·")[0].strip()
        km = re.match(r"@([\w:-]+)\s*[—–-]+\s*(.+)", first)
        out[aid] = LedgerEntry(
            id=aid,
            citekey=km.group(1) if km else None,
            anchor=km.group(2).strip() if km else None,
            has_cite_line=True,
        )
    return out


def render_safe_commands(cfg: Config) -> set[str]:
    """Commands the render pipeline handles: macros.tex definitions + the vetted allowlist."""
    defined = set(re.findall(r"\\(?:new|provide|renew)command\{?\\([A-Za-z]+)", read(cfg.macros)))
    vetted = {
        line.strip()
        for line in read(cfg.allowlist).splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    return defined | vetted


def paper_markers(cfg: Config) -> list[PaperMarker]:
    """Every `% shared with blueprint <label>` marker, with the paper's nearest label."""
    out: list[PaperMarker] = []
    for f in sorted(cfg.paper.glob("*.tex")):
        t = read(f)
        for m in re.finditer(
            r"%[^\n]*?shared[^\n]*?with blueprint\s+([a-z]+:[\w-]+)", t
        ):
            labs = re.findall(r"\\label\{([^}]+)\}", t[: m.start()])
            out.append(PaperMarker(
                file=f.name,
                blueprint_label=m.group(1),
                nearest_label=labs[-1] if labs else None,
            ))
    return out


def git_provenance(root: Path) -> dict:
    """The freshness stamp for the manifest: the short HEAD SHA and whether the working tree was
    dirty at emit time. Best-effort — degrades to a null commit if git is unavailable, so a
    manifest can still be emitted outside a checkout. `source_dirty` is whole-repo on purpose: the
    manifest projects labels, Lean decls, and scripts, so a change anywhere may not be captured by
    HEAD's SHA, and the honest signal is "this did not come from a clean commit." See the freshness
    note in docs/LINKAGE.md § "The cross-repo channel"."""
    def _git(*args: str) -> str | None:
        try:
            r = subprocess.run(["git", "-C", str(root), *args],
                               capture_output=True, text=True, timeout=10)
            return r.stdout.strip() if r.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            return None

    return {"source_commit": _git("rev-parse", "--short", "HEAD"),
            "source_dirty": bool(_git("status", "--porcelain"))}
