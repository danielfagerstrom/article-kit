"""The prover's worklist: wiki demand joined against our \\leanok status.

The wiki (the Notes hub) exposes `wiki demands --json`: every blueprint label its claims
rest on, with confidence, strongest first. That is *raw* demand — by design it carries no
proved-status, because \\leanok is ours and only the live blueprint is never stale. This
does the join we own:

    wiki demands --json  ×  blueprint \\leanok  →  unproved demand, strongest first

Proved (\\leanok) labels drop off; what remains, in the hub's own order, is what to prove
next to unblock the most wiki content. Demands naming a label the blueprint does not have
are flagged — that is the wiki asking for a *new* node (add it or push back). We only ever
read from the wiki (single-writer: the manifest out is ours, the demand in is theirs).

Needs the `wiki` CLI on PATH (installed from the Notes vault). The vault is located by
`--wiki`, else `$WIKI_VAULT`. See docs/LINKAGE.md § "The cross-repo channel".
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import artifacts, config, parse_latex
from .model import Node


def resolve_vault(explicit: Path | None) -> str:
    if explicit:
        return str(explicit)
    if env := os.environ.get("WIKI_VAULT"):
        return env
    sys.exit(
        "error: no wiki vault — pass --wiki PATH or set $WIKI_VAULT to the Notes vault"
    )


def fetch_demands(vault: str) -> dict:
    if not shutil.which("wiki"):
        sys.exit(
            "error: `wiki` CLI not on PATH — install it from the Notes vault "
            "(uv tool install --editable . --python 3.13)"
        )
    env = {**os.environ}
    env.setdefault("WIKI_VAULT", vault)
    r = subprocess.run(
        ["wiki", "demands", "--json"], capture_output=True, text=True, env=env, timeout=60
    )
    if r.returncode != 0:
        sys.exit(f"error: `wiki demands --json` failed:\n{r.stderr.strip()}")
    return json.loads(r.stdout)


def join(demands: list[dict], labels: dict[str, Node]) -> tuple[list[dict], list[str]]:
    """Join demand rows against the live blueprint; hub order is preserved.

    Returns (unproved rows annotated with our status, proved labels that dropped).
    `in_blueprint` is recomputed against the live parse — the hub computes it from the
    emitted manifest, which may lag."""
    rows, proved = [], []
    for d in demands:
        node = labels.get(d["label"])
        if node and node.leanok:
            proved.append(d["label"])
            continue
        if node is None:
            status = "NOT a blueprint node yet"
        elif node.notready:
            status = "\\notready"
        elif node.lean:
            status = "\\lean{} named, unproved"
        else:
            status = "no Lean decl"
        rows.append({**d, "in_blueprint": node is not None, "status": status})
    return rows, proved


def main(args) -> int:
    cfg = config.load(getattr(args, "root", None))
    bp = parse_latex.parse(cfg)

    data = fetch_demands(resolve_vault(args.wiki))
    rows, proved = join(data.get("demands", []), bp.by_label)

    if args.json:
        print(json.dumps({"manifest": data.get("manifest"), "unproved": rows}, indent=2))
        return 0

    # The wiki's view of us: warn when its manifest lags this repo, so the demand ranking
    # (and its in_blueprint flags) are read with the right scepticism.
    man = data.get("manifest", {})
    prov = artifacts.git_provenance(cfg.root)
    print(f"wiki's manifest: {man.get('summary', 'absent')}")
    if man.get("dirty"):
        print("  ⚠ manifest was emitted from a dirty tree — re-emit after committing")
    elif prov["source_commit"] and man.get("source_commit") not in (None, prov["source_commit"]):
        print(
            f"  ⚠ manifest is behind this repo ({cfg.slug}@{man['source_commit']} vs HEAD "
            f"{prov['source_commit']}) — re-emit with `linkage manifest`"
        )

    print(f"\n{len(rows) + len(proved)} demanded labels; {len(proved)} already \\leanok, "
          f"dropped: {', '.join(proved) if proved else '—'}")
    if not rows:
        print("\nNothing unproved is demanded — the wiki's claims all rest on proved nodes.")
        return 0

    print("\nUnproved demand, strongest first (the hub's order, preserved):\n")
    for i, r in enumerate(rows, 1):
        frontier = "  [frontier — declared-open lead, non-blocking]" if r["frontier_only"] else ""
        flag = "  ⚠ " if not r["in_blueprint"] else "  "
        notes = sorted({c["note"] for c in r["claims"]})
        print(f"{i:3}. {r['label']:34} {r['confidence']:9} ×{r['claim_count']}"
              f"{flag}{r['status']}{frontier}")
        for n in notes:
            print(f"     └ {n}")
    print("\nWhile proving, `wiki show <label>` gives the wiki's intended meaning for a node.")
    return 0
