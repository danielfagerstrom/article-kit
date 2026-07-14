#!/usr/bin/env python3
"""Blueprint <-> Lean <-> ledger <-> paper linkage checker.

The blueprint (blueprint/src/content.tex) is the source of truth. Each statement
node carries a canonical \\label, a \\lean{} pointer (with \\leanok / \\notready),
\\ledger{} grounding for [A] nodes, and \\notes{} for its wiki content note. This
script verifies the edges that live *inside this repository*:

  FATAL (exit 1 if any fail)
    1. every \\leanok node's \\lean{Decl} names a declaration that exists in Formalization/
    2. every \\ledger{AXX} (and legacy "ledger AXX" prose) resolves to an AXIOMS.md entry
    3. every paper "% shared with blueprint <label>" names a real blueprint statement label

  ADVISORY (reported, non-fatal)
    - a paper shared statement whose own \\label differs from the blueprint label
      (the same-label opportunity; enables true single-sourcing later)
    - a \\leanok node with no \\lean{}, or a node marked both \\leanok and \\notready

The wiki edge (\\notes{slug} <-> a Notes content note) is cross-repo; it is checked
only when --wiki PATH is given.

Usage
    python scripts/check_linkage.py                 # in-repo edges
    python scripts/check_linkage.py --wiki ~/Documents/Notes   # also the wiki edge

See blueprint/LINKAGE.md for the spec this enforces.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BLUEPRINT = REPO / "blueprint" / "src" / "content.tex"
AXIOMS = REPO / "blueprint" / "AXIOMS.md"
LEAN_DIR = REPO / "Formalization"
PAPER_DIR = REPO / "paper"

STMT_ENVS = ("definition", "lemma", "proposition", "theorem", "corollary")
# a Lean declaration keyword, allowing leading attributes / modifiers
DECL_RE = re.compile(
    r"(?m)^\s*(?:@\[[^\]]*\]\s*)?"
    r"(?:(?:private|protected|noncomputable|scoped|local|partial|unsafe)\s+)*"
    r"(?:theorem|lemma|def|abbrev|structure|instance|axiom)\s+([A-Za-z_][\w']*)"
)


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def blueprint_nodes(tex: str):
    """One dict per statement environment."""
    nodes = []
    for m in re.finditer(
        r"\\begin\{(" + "|".join(STMT_ENVS) + r")\}(.*?)\\end\{\1\}", tex, re.S
    ):
        body = m.group(2)
        lab = re.search(r"\\label\{([^}]+)\}", body)
        decls = [
            d.strip()
            for dm in re.finditer(r"\\lean\{([^}]+)\}", body)
            for d in dm.group(1).split(",")
            if d.strip()
        ]
        nodes.append(
            {
                "env": m.group(1),
                "label": lab.group(1) if lab else None,
                "lean": decls,
                "leanok": r"\leanok" in body,
                "notready": r"\notready" in body,
            }
        )
    return nodes


def ledger_refs(tex: str) -> set[str]:
    refs = set(re.findall(r"\\ledger\{([^}]+)\}", tex))
    refs |= set(re.findall(r"ledger~?\s*(A\d+)", tex))  # legacy prose
    return refs


def notes_slugs(tex: str) -> set[str]:
    return set(re.findall(r"\\notes\{([^}]+)\}", tex))


def lean_declared_names() -> set[str]:
    names: set[str] = set()
    for f in LEAN_DIR.rglob("*.lean"):
        if ".lake" in f.parts:
            continue
        names |= set(DECL_RE.findall(read(f)))
    return names


def ledger_keys() -> set[str]:
    return set(re.findall(r"(?m)^##\s*(A\d+)\b", read(AXIOMS)))


def paper_shared():
    """(file, blueprint_key, nearest_preceding_paper_label)."""
    out = []
    for f in sorted(PAPER_DIR.glob("*.tex")):
        t = read(f)
        for m in re.finditer(
            r"%[^\n]*?shared[^\n]*?with blueprint\s+([a-z]+:[\w-]+)", t
        ):
            key = m.group(1)
            labs = re.findall(r"\\label\{([^}]+)\}", t[: m.start()])
            out.append((f.name, key, labs[-1] if labs else None))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--wiki", type=Path, help="Path to the Notes wiki (enables \\notes{} checking)"
    )
    args = ap.parse_args()

    tex = read(BLUEPRINT)
    nodes = blueprint_nodes(tex)
    labels = {n["label"] for n in nodes if n["label"]}
    lean_names = lean_declared_names()
    axk = ledger_keys()

    fatal: list[str] = []
    advisory: list[str] = []

    # 1. Lean decls of proved nodes exist
    for n in nodes:
        if n["leanok"] and not n["lean"]:
            advisory.append(f"[lean]   node '{n['label']}' is \\leanok but has no \\lean{{}}")
        if n["leanok"] and n["notready"]:
            advisory.append(f"[lean]   node '{n['label']}' marked both \\leanok and \\notready")
        if not n["leanok"]:
            continue  # \notready nodes may not have a Lean decl yet
        for d in n["lean"]:
            last = d.split(".")[-1]
            if last not in lean_names:
                fatal.append(
                    f"[lean]   {n['label']}: \\lean{{{d}}} not declared in {LEAN_DIR.name}/"
                )

    # 2. ledger refs resolve
    for a in sorted(ledger_refs(tex)):
        if a not in axk:
            fatal.append(f"[ledger] {a}: no '## {a}' entry in AXIOMS.md")

    # 3. paper shared statements
    for fn, key, nearest in paper_shared():
        if key not in labels:
            fatal.append(
                f"[paper]  {fn}: 'shared with blueprint {key}' but no such blueprint label"
            )
        elif nearest != key:
            advisory.append(
                f"[paper]  {fn}: shared statement labelled '{nearest}', blueprint key '{key}' "
                f"(same-label would enable single-sourcing)"
            )

    # optional: wiki notes
    if args.wiki:
        for slug in sorted(notes_slugs(tex)):
            if not list(args.wiki.rglob(slug + ".md")):
                fatal.append(f"[notes]  \\notes{{{slug}}}: no {slug}.md under {args.wiki}")

    n_lean = sum(1 for n in nodes if n["leanok"])
    print(
        f"Blueprint: {len(nodes)} statement nodes ({n_lean} \\leanok), "
        f"{len(ledger_refs(tex))} ledger refs, {len(paper_shared())} paper shared-statements."
    )
    for a in advisory:
        print("  advisory " + a)
    if fatal:
        print(f"\nLINKAGE CHECK FAILED: {len(fatal)} problem(s)\n")
        for p in fatal:
            print("  FAIL " + p)
        return 1
    print("\nLINKAGE CHECK OK: all in-repo Lean / ledger / paper edges are consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
