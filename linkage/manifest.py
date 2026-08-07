"""The manifest emitter — the projection of the blueprint the hub reads.

Same role as the librarian's `library.json` (citekeys): a generated, single-writer document
another repo consumes. See docs/LINKAGE.md § "The cross-repo channel".

One thing changed at extraction: `scripts` lists the *article's* own scripts, which is what
it always meant — a wiki claim `num:<slug>:<path>` resolves against it. Before the split the
framework's two tools happened to sit in the article's `scripts/`, so they appeared there;
no claim referenced them, and after the split the list holds only article-owned scripts
(figure generators and the like), which is the intended set.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone

from .artifacts import git_provenance, read
from .config import Config
from .model import Blueprint, LedgerEntry
from .render import check_pin, render_markdown, render_residue

MANIFEST_VERSION = 2


class ManifestError(RuntimeError):
    pass


def sha12(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]


def build(
    bp: Blueprint,
    cfg: Config,
    lean_names: set[str],
    ledger: dict[str, LedgerEntry],
    require_render: bool = False,
    warn=lambda msg: None,
) -> dict:
    """Project the blueprint into the manifest the wiki reads to resolve claim proof-refs.

    `kind` is the label prefix (thm|prop|def|lem|cor) — exactly the token a wiki claim ref
    uses. `lean_decls` are short declaration names (matched on final component, as the
    in-repo \\lean{} check does).

    Carries a freshness stamp (`generated_at`, `source_commit`, `source_dirty`) so the wiki
    can report where the manifest came from and how old it is, and never silently validate a
    note against a stale view.

    Each label also carries `uses` (the node's \\uses{} dependency labels, so
    blueprint-internal edges are verifiable vault-side), the normalized `statement` text, and
    `statement_sha` (a short sha256 of it) — the wiki's lint diffs mirrored statement blocks
    against the hash to catch silent drift. The normalization is deterministic, so the sha
    changes exactly when the statement's mathematical content does.

    Manifest v2 adds the transclusion fields: per label, the normalized `proof` source +
    `proof_sha` (null when the node has no proof environment), and — when the pinned pandoc
    is available — `statement_md` / `proof_md` (Obsidian-dialect markdown, custom macros
    expanded) + `rendered_sha` over both, which is what the hub's `wiki import`/lint
    byte-compares. Top-level `render` records the renderer provenance (null when rendering
    was skipped); `manifest_version` lets the hub detect the schema.
    """
    why_not = check_pin(cfg.pandoc_pin)
    rendering = why_not is None
    render_errors: list[str] = []
    if not rendering:
        if require_render:
            raise ManifestError(f"--require-render: {why_not}")
        warn(f"{why_not} — manifest emitted without rendered fields")
    preamble = read(cfg.macros) if rendering else ""

    labels: dict[str, dict] = {}
    for n in bp.nodes:
        lab = n.label
        if not lab:
            continue
        entry = {
            "kind": n.kind,
            "env": n.env,
            "title": n.title,
            "status": n.status,
            # each ledger ref carries the entry's primary citation, so the hub can
            # cross-check the citekey against library.json and show the source in claim
            # chips / block status lines
            "ledger": [
                (ledger[a].projection() if a in ledger
                 else {"id": a, "citekey": None, "anchor": None})
                for a in n.ledger
            ],
            "leanok": n.leanok,
            "notready": n.notready,
            "lean": n.lean,
            "uses": n.uses,
            "statement": n.statement,
            "statement_sha": sha12(n.statement),
            "proof": n.proof,
            "proof_sha": sha12(n.proof) if n.proof is not None else None,
            "statement_md": None,
            "proof_md": None,
            "rendered_sha": None,
        }
        if rendering:
            try:
                entry["statement_md"] = render_markdown(
                    n.statement_render_src, preamble, cfg.pandoc_target)
                if n.proof is not None:
                    entry["proof_md"] = render_markdown(
                        n.proof_render_src, preamble, cfg.pandoc_target)
                # titles are block-header text too — render them when they carry LaTeX
                # (accents, em-dashes); plain titles pass through without a pandoc call
                title = n.title
                entry["title_md"] = (
                    render_markdown(title, preamble, cfg.pandoc_target)
                    if title and re.search(r"[\\{}]|--", title) else title
                )
                # rendered_sha covers EVERY input of the hub's block derivation (header,
                # status line, statement, proof) — so any change that alters the derived
                # block moves the sha, and the hub's lint reads it as *stale* (mechanical
                # refresh) rather than misclassifying it as a hand-edit. A leanok flip or
                # a title fix must never look like a violation.
                entry["rendered_sha"] = sha12(json.dumps(
                    [entry["env"], entry["title_md"], entry["status"], entry["ledger"],
                     entry["lean"], entry["leanok"], entry["notready"],
                     entry["statement_md"], entry["proof_md"]],
                    ensure_ascii=False))
                residue = render_residue(
                    entry["statement_md"] + "\n" + (entry["proof_md"] or "")
                )
                if residue:
                    render_errors.append(
                        f"{lab}: raw LaTeX outside math/code: {', '.join(residue)}"
                    )
            except RuntimeError as e:
                render_errors.append(f"{lab}: {e}")
        labels[lab] = entry

    if render_errors:
        for e in render_errors:
            warn(f"render failed for {e}")
        if require_render:
            raise ManifestError(
                f"--require-render: {len(render_errors)} label(s) failed to render"
            )

    scripts_dir = cfg.root / "scripts"
    scripts = (
        sorted(p.relative_to(cfg.root).as_posix() for p in scripts_dir.glob("*.py"))
        if scripts_dir.is_dir() else []
    )
    return {
        "generated_by": "linkage",
        "slug": cfg.slug,
        "note": (f"Projection of {cfg.blueprint.relative_to(cfg.root).as_posix()} "
                 "— generated, do not hand-edit."),
        "manifest_version": MANIFEST_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **git_provenance(cfg.root),
        "render": (
            {"renderer": "pandoc", "version": cfg.pandoc_pin,
             "target": cfg.pandoc_target, "wrap": "none"}
            if rendering else None
        ),
        "labels": labels,
        "lean_decls": sorted(lean_names),
        "scripts": scripts,
    }


def default_filename(slug: str) -> str:
    """The hub-side filename for a satellite's manifest.

    Per-satellite from the start: two article repos committing to one fixed name in the hub
    would break the single-writer invariant (docs/LINKAGE.md § the cross-repo channel).
    """
    return f"blueprint-manifest-{slug}.json"
