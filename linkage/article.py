"""Parts and phase: what the `[article]` table of `linkage.toml` obliges (ADR-0002).

Three things read it here:

- `problems`: what `linkage check` reports. A part the phase requires and that is missing, a
  directory of a part the repository does not list, a `released` phase with no released
  module, and on an anonymous repository the anonymity scan of the paper.
- `projection`: what `linkage parts --json` prints and `manifest.yml` writes into the hub as
  `article-<slug>.json`. The hub, the research site and the CI read it.
- `entry_lacks` and `advance`: `linkage phase`, which says what the next phase still lacks and
  moves the repository there.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import config
from .config import CONFIG_NAME, PHASES, REQUIRED_FROM, Config, phase_index

# The PROCESS.md section each phase is named after.
SECTION = {"draft": "2", "blueprint": "3", "skeleton": "4", "proving": "5", "fidelity": "6",
           "article": "7", "passes": "8", "external-review": "9", "released": "10"}
# Where each part lives when `[paths]` does not say: the directory whose presence makes an
# unlisted part an error.
PART_DIRS = {"draft": "draft", "blueprint": "blueprint", "lean": "Formalization",
             "paper": "paper"}
PROJECTION_VERSION = 1


@dataclass
class Problems:
    fatal: list[str] = field(default_factory=list)
    advisory: list[str] = field(default_factory=list)


def _where(phase: str) -> str:
    return f"phase `{phase}` (PROCESS.md § {SECTION[phase]})"


def _part_path(cfg: Config, part: str) -> str:
    p = {"draft": cfg.draft, "blueprint": cfg.blueprint, "lean": cfg.lean}.get(part)
    if part == "paper":
        return "paper/"
    return p.relative_to(cfg.root).as_posix() if p else PART_DIRS[part]


def required_at(cfg: Config, phase: str) -> frozenset[str]:
    """The listed parts that `phase` requires to exist."""
    return frozenset(p for p, first in REQUIRED_FROM.items()
                     if cfg.listed(p) and phase_index(phase) >= phase_index(first))


def problems(cfg: Config) -> Problems:
    out = Problems()
    art = cfg.article
    if not art.declared:
        out.advisory.append(
            f"[article] {CONFIG_NAME} has no `[article]` table: the parts are inferred from "
            "the tree and no phase is known, so the CI and the research site cannot follow "
            "this repository's declaration (ADR-0002; LINKAGE.md, \"Parts and phase\")")
        return out
    phase = cfg.phase()
    if phase is None:
        out.fatal.append(
            f"[phase]  {CONFIG_NAME}: `[article]` gives no `phase`, and no `[[modules]]` table "
            f"carries one -- one of {', '.join(PHASES)}")
    else:
        for part in sorted(required_at(cfg, phase) - {p for p in config.PARTS if cfg.has(p)}):
            out.fatal.append(
                f"[phase]  {_where(phase)} requires the {part} part, and there is none at "
                f"{_part_path(cfg, part)} -- create it, or step the phase back")
        if phase == "released" and not any(m.tag for m in cfg.modules):
            out.fatal.append(
                f"[phase]  {_where('released')}: no `[[modules]]` table carries a release "
                "`tag`")
    for part, d in PART_DIRS.items():
        if not cfg.listed(part) and (cfg.root / d).exists():
            out.fatal.append(
                f"[parts]  {d}/ exists, but `[article] parts` does not list {part}: nothing "
                f"reads it -- list the part, or remove the directory")
    if art.anonymous:
        from .anonymity import scan
        for f in scan(cfg):
            out.fatal.append(f"[anonymity] {f.path}:{f.line}: {f.why} -- {f.text[:80]!r}")
    return out


def projection(cfg: Config) -> dict:
    """The declaration as the hub, the research site and the CI read it.

    `jobs` is what the CI runs: `docs` when there is anything to build, `deploy` when the
    result may go to the site, `blueprint_manifest` when there is a blueprint to project,
    `lean` when there is a Lean tree and the phase has reached the skeleton.
    """
    art = cfg.article
    present = [p for p in config.PARTS if cfg.has(p)]
    phase = cfg.phase()
    sites = list(cfg.sites())
    lean_due = phase is None or phase_index(phase) >= phase_index("skeleton")
    return {
        "projection_version": PROJECTION_VERSION,
        "slug": cfg.slug,
        "declared": art.declared,
        "parts": sorted(art.parts) if art.declared else present,
        "present": present,
        "phase": phase,
        "modules": [{"name": m.name, "phase": m.phase, "site": m.site, "tag": m.tag}
                    for m in cfg.modules],
        "anonymous": art.anonymous,
        "site": art.site,
        "sites": sites,
        "cites": list(art.cites),
        "jobs": {
            "docs": any(cfg.has(p) for p in ("draft", "blueprint", "paper")),
            "deploy": bool(sites) and not art.anonymous,
            "blueprint_manifest": cfg.has("blueprint"),
            "lean": cfg.has("lean") and lean_due,
        },
    }


def next_phase(phase: str) -> str | None:
    i = phase_index(phase)
    return PHASES[i + 1] if i + 1 < len(PHASES) else None


def entry_lacks(cfg: Config, phase: str, record: Path | None = None,
                check_fatal: list[str] | None = None) -> list[str]:
    """What entering `phase` still lacks: the parts it requires, and the gate PROCESS.md
    names at that point. A judgement (the author approving the decomposition) is recorded,
    not checked: the record is a file the caller names."""
    lacks = [f"the {p} part ({_part_path(cfg, p)})"
             for p in sorted(required_at(cfg, phase) - {p for p in config.PARTS
                                                        if cfg.has(p)})]
    if check_fatal:
        lacks.append(f"`linkage check` clean ({len(check_fatal)} failure(s))")
    if phase == "proving" and not (record and (cfg.root / record).is_file()):
        lacks.append("the author's approval of the reviewed skeleton (PROCESS.md § 4), "
                     "named with --record PATH")
    if phase == "article" and cfg.listed("lean") and not (
            cfg.root / "blueprint" / "REVIEW-fidelity.md").is_file():
        lacks.append("the fidelity review's blueprint/REVIEW-fidelity.md (PROCESS.md § 6)")
    if phase == "released" and not any(m.tag for m in cfg.modules):
        lacks.append("a `[[modules]]` table with a release `tag` (RELEASE.md)")
    return lacks


_TABLE_RE = re.compile(r"(?m)^\[article\][^\n]*\n")


def set_phase(text: str, phase: str) -> str:
    """`linkage.toml`'s text with `[article] phase` set, comments and layout kept."""
    m = _TABLE_RE.search(text)
    if not m:
        raise config.ConfigError(f"{CONFIG_NAME} has no `[article]` table to advance")
    nxt = re.compile(r"(?m)^\[").search(text, m.end())
    end = nxt.start() if nxt else len(text)
    body = text[m.end():end]
    line = re.compile(r'(?m)^(phase\s*=\s*)"[^"\n]*"')
    if line.search(body):
        body = line.sub(lambda mm: f'{mm.group(1)}"{phase}"', body, count=1)
    else:
        body = f'phase = "{phase}"\n' + body
    return text[:m.end()] + body + text[end:]
