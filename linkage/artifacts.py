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
from .parse_latex import expand_inputs

# a Lean declaration keyword, allowing leading attributes / modifiers
DECL_RE = re.compile(
    r"(?m)^\s*(?:@\[[^\]]*\]\s*)?"
    r"(?:(?:private|protected|noncomputable|scoped|local|partial|unsafe)\s+)*"
    r"(?:theorem|lemma|def|abbrev|structure|instance|axiom)\s+([A-Za-z_][\w']*)"
)


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


class MissingLeanPackage(RuntimeError):
    pass


def lean_declared_names(cfg: Config) -> set[str]:
    r"""Every declaration name this article may point a `\lean{}` tag at.

    Its own sources, plus any shared Lake package named in `lean_packages` — a result that
    moved to a shared library is still proved, and the blueprint node that points at it is
    still correct. Build artifacts under the article's own `.lake` are excluded; the shared
    packages live there, so they are scanned by explicit path instead.
    """
    names: set[str] = set()
    for f in cfg.lean.rglob("*.lean"):
        if ".lake" in f.parts:
            continue
        names |= set(DECL_RE.findall(read(f)))

    for pkg in cfg.lean_packages:
        root = cfg.lean / ".lake" / "packages" / pkg
        if not root.is_dir():
            raise MissingLeanPackage(
                f"lean_packages names '{pkg}', but {root} does not exist — run `lake build` "
                f"in {cfg.lean.name}/ first. (Failing loudly on purpose: skipping it would "
                rf"make every \lean{{}} tag pointing into that package look undeclared.)")
        for f in root.rglob("*.lean"):
            if any(part == ".lake" for part in f.relative_to(root).parts):
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
    defined = set(re.findall(r"\\(?:new|provide|renew)command\{?\\([A-Za-z]+)",
                             expand_inputs(cfg.macros)))
    vetted = {
        line.strip()
        for line in read(cfg.allowlist).splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    return defined | vetted


MARKER_RE = re.compile(r"%[^\n]*?shared[^\n]*?with blueprint\s+([a-z]+:[\w-]+)")


def paper_markers(cfg: Config) -> list[PaperMarker]:
    """Every `% shared with blueprint <label>` marker, with the paper's nearest label
    and the statement it marks.

    The marked statement is the next statement environment after the marker, provided
    no *other* marker intervenes — a marker whose own statement was deleted must not
    silently adopt the following one's and report it as drift.
    """
    from .parse_latex import shared_statement, split_env_title

    env_re = re.compile(
        r"\\begin\{(" + "|".join(cfg.statement_envs) + r")\}(.*?)\\end\{\1\}", re.S)
    out: list[PaperMarker] = []
    for f in sorted(cfg.paper.glob("*.tex")):
        t = read(f)
        marks = list(MARKER_RE.finditer(t))
        for i, m in enumerate(marks):
            nxt = marks[i + 1].start() if i + 1 < len(marks) else len(t)
            em = env_re.search(t, m.end())
            body = em.group(2) if em and em.start() < nxt else None
            lm = re.search(r"\\label\{([^}]+)\}", body) if body else None
            out.append(PaperMarker(
                file=f.name,
                blueprint_label=m.group(1),
                statement_label=lm.group(1) if lm else None,
                line=t.count("\n", 0, m.start()) + 1,
                shared_statement=(shared_statement(split_env_title(body)[1])
                                  if body is not None else None),
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


def lake_package_sources(cfg: Config) -> list[dict]:
    """Where each `lean_packages` entry lives, and whether it is present.

    Read from the article's `lake-manifest.json` — the pinned url + rev lake resolved. This
    exists so the *checker* can stay toolchain-free and offline: the manifest CI job runs on
    source text alone with no lake and no elan, and a shared library is one small shallow
    clone away. `linkage packages` prints this; the workflow does the fetching with plain git.
    """
    import json

    lakefile = cfg.lean / "lake-manifest.json"
    if not lakefile.exists():
        return []
    try:
        data = json.loads(lakefile.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, TypeError):
        return []
    by_name = {p.get("name"): p for p in data.get("packages", []) if isinstance(p, dict)}
    out = []
    for pkg in cfg.lean_packages:
        entry = by_name.get(pkg) or {}
        dest = cfg.lean / ".lake" / "packages" / pkg
        out.append({
            "name": pkg,
            "url": entry.get("url"),
            # the resolved sha, not inputRev — the manifest must project the exact tree lake
            # pinned, not whatever a moving tag points at today
            "rev": entry.get("rev") or entry.get("inputRev"),
            "dest": dest,
            "present": dest.is_dir(),
        })
    return out
