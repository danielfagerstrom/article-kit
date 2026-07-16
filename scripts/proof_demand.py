#!/usr/bin/env python3
"""The prover's worklist: wiki demand joined against our \\leanok status.

The wiki (the Notes hub) exposes `wiki demands --json`: every blueprint label its
claims rest on, with confidence, strongest first. That is *raw* demand — by design
it carries no proved-status, because \\leanok is ours and only the live blueprint
is never stale. This script does the join we own:

    wiki demands --json  ×  blueprint \\leanok  →  unproved demand, strongest first

Proved (\\leanok) labels drop off; what remains, in the hub's own order, is what to
prove next to unblock the most wiki content. Demands naming a label the blueprint
does not have are flagged — that is the wiki asking for a *new* node (add it or
push back). We only ever read from the wiki (single-writer: the manifest out is
ours, the demand in is theirs).

Usage
    python scripts/proof_demand.py            # human-readable worklist
    python scripts/proof_demand.py --json     # the joined rows as JSON

Needs the `wiki` CLI on PATH (installed from the Notes vault); $WIKI_VAULT is set
for the subprocess if absent. See blueprint/LINKAGE.md § "The cross-repo channel".
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

from check_linkage import _git_provenance, blueprint_nodes, read_blueprint

DEFAULT_VAULT = r"C:\Users\danie\Documents\Notes"


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


def join(demands: list[dict], labels: dict[str, dict]) -> tuple[list[dict], list[str]]:
    """Join demand rows against the live blueprint; hub order is preserved.

    Returns (unproved rows annotated with our status, proved labels that dropped).
    `in_blueprint` is recomputed against the live parse — the hub computes it from
    the emitted manifest, which may lag."""
    rows, proved = [], []
    for d in demands:
        node = labels.get(d["label"])
        if node and node["leanok"]:
            proved.append(d["label"])
            continue
        if node is None:
            status = "NOT a blueprint node yet"
        elif node["notready"]:
            status = "\\notready"
        elif node["lean"]:
            status = "\\lean{} named, unproved"
        else:
            status = "no Lean decl"
        rows.append({**d, "in_blueprint": node is not None, "status": status})
    return rows, proved


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="emit the joined rows as JSON")
    ap.add_argument("--vault", default=DEFAULT_VAULT, help="Notes vault path (sets $WIKI_VAULT)")
    args = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    data = fetch_demands(args.vault)
    nodes = blueprint_nodes(read_blueprint())
    labels = {n["label"]: n for n in nodes if n["label"]}
    rows, proved = join(data.get("demands", []), labels)

    if args.json:
        print(json.dumps({"manifest": data.get("manifest"), "unproved": rows}, indent=2))
        return 0

    # The wiki's view of us: warn when its manifest lags this repo, so the demand
    # ranking (and its in_blueprint flags) are read with the right scepticism.
    man = data.get("manifest", {})
    prov = _git_provenance()
    print(f"wiki's manifest: {man.get('summary', 'absent')}")
    if man.get("dirty"):
        print("  ⚠ manifest was emitted from a dirty tree — re-emit after committing")
    elif prov["source_commit"] and man.get("source_commit") not in (None, prov["source_commit"]):
        print(
            f"  ⚠ manifest is behind this repo (ssf@{man['source_commit']} vs HEAD "
            f"{prov['source_commit']}) — re-emit with check_linkage.py --emit-manifest"
        )

    print(f"\n{len(rows) + len(proved)} demanded labels; {len(proved)} already \\leanok, dropped:"
          f" {', '.join(proved) if proved else '—'}")
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


if __name__ == "__main__":
    sys.exit(main())
