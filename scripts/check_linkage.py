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
    - a *labelled* paper statement that shares a blueprint node but uses a different label
      (rename to the blueprint label for true single-sourcing). Prose that merely references a
      blueprint node -- nearest preceding label is a section, not a statement -- is a valid
      weaker link and is not advised.
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
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BLUEPRINT = REPO / "blueprint" / "src" / "content.tex"
AXIOMS = REPO / "blueprint" / "AXIOMS.md"
LEAN_DIR = REPO / "Formalization"
PAPER_DIR = REPO / "paper"

STMT_ENVS = ("definition", "lemma", "proposition", "theorem", "corollary")
# label prefixes that denote a statement (as opposed to a section/equation)
STMT_LABEL_RE = re.compile(r"^(?:thm|prop|def|lem|cor):")
# a Lean declaration keyword, allowing leading attributes / modifiers
DECL_RE = re.compile(
    r"(?m)^\s*(?:@\[[^\]]*\]\s*)?"
    r"(?:(?:private|protected|noncomputable|scoped|local|partial|unsafe)\s+)*"
    r"(?:theorem|lemma|def|abbrev|structure|instance|axiom)\s+([A-Za-z_][\w']*)"
)


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def read_blueprint() -> str:
    """content.tex, with `\\input{...}` includes inlined (the nodes live in parts/)."""
    inp = re.compile(r"^\s*\\input\{([^}]+)\}")

    def expand(path: Path) -> str:
        out = []
        for line in read(path).splitlines(keepends=True):
            m = inp.match(line)
            if m and not line.lstrip().startswith("%"):
                inc = m.group(1)
                if not inc.endswith(".tex"):
                    inc += ".tex"
                out.append(expand(path.parent / inc))
            else:
                out.append(line)
        return "".join(out)

    return expand(BLUEPRINT)


def normalize_statement(body: str) -> str:
    """The statement text of a node body, normalized for stable hashing.

    Strips LaTeX comments and the metadata commands (\\label/\\lean/\\uses/\\notes/\\ledger
    with their arguments; the bare \\notready/\\leanok tokens; \\statusT/\\statusA together
    with their trailing \\quad\\emph{...} status annotation — proof-status remarks, not
    statement content, so a status edit does not move the sha), then collapses all whitespace
    runs to single spaces. The mathematical prose and math are kept verbatim, so the text —
    and its sha — changes exactly when the statement's content does. Deterministic: a pure
    function of the body string, no environment input.
    """
    body = re.sub(r"(?<!\\)%[^\n]*", "", body)
    body = re.sub(r"\\(?:label|lean|uses|notes|ledger)\{[^}]*\}", "", body)
    # \statusT / \statusA plus the annotation that follows them: optional \quad / \qquad
    # spacing, then an optional \emph{...} group (balanced to two brace-nesting levels —
    # the annotations contain \texttt{...} / \ref{...}).
    body = re.sub(
        r"\\status[TA]\b(?:\s|\\quad\b|\\qquad\b)*"
        r"(?:\\emph\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\})?",
        "",
        body,
    )
    body = re.sub(r"\\(?:statusT|statusA|notready|leanok)\b", "", body)
    return re.sub(r"\s+", " ", body).strip()


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
        uses = [
            u.strip()
            for um in re.finditer(r"\\uses\{([^}]+)\}", body)
            for u in um.group(1).split(",")
            if u.strip()
        ]
        nodes.append(
            {
                "env": m.group(1),
                "label": lab.group(1) if lab else None,
                "lean": decls,
                "uses": uses,
                "leanok": r"\leanok" in body,
                "notready": r"\notready" in body,
                "statement": normalize_statement(body),
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


def _git_provenance() -> dict:
    """The freshness stamp for the manifest: the short HEAD SHA and whether the working tree was
    dirty at emit time. Best-effort — degrades to a null commit if git is unavailable, so a
    manifest can still be emitted outside a checkout. `source_dirty` is whole-repo on purpose: the
    manifest projects labels, Lean decls, and scripts, so a change anywhere may not be captured by
    HEAD's SHA, and the honest signal is "this did not come from a clean commit." See the freshness
    note in blueprint/LINKAGE.md § "The cross-repo channel"."""
    def _git(*args: str) -> str | None:
        try:
            r = subprocess.run(["git", "-C", str(REPO), *args],
                               capture_output=True, text=True, timeout=10)
            return r.stdout.strip() if r.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            return None

    return {"source_commit": _git("rev-parse", "--short", "HEAD"),
            "source_dirty": bool(_git("status", "--porcelain"))}


def build_manifest(nodes, lean_names: set[str]) -> dict:
    """Projection of the blueprint the wiki reads to resolve `claim/…` proof-refs.

    Same role as the librarian's library.json (citekeys): a generated, single-writer
    manifest another repo reads. `kind` is the label prefix (thm|prop|def|lem|cor) —
    exactly the token a wiki claim ref uses. `lean_decls` are short declaration names
    (matched on final component, as the in-repo \\lean{} check does). See blueprint/LINKAGE.md.

    Carries a freshness stamp (`generated_at`, `source_commit`, `source_dirty`) so the wiki can
    report where the manifest came from and how old it is, and never silently validate a note
    against a stale view.

    Each label also carries `uses` (the node's \\uses{} dependency labels, so blueprint-internal
    edges are verifiable vault-side), the normalized `statement` text, and `statement_sha` (a
    short sha256 of it) — the wiki's lint diffs mirrored statement blocks against the hash to
    catch silent drift. The normalization (`normalize_statement`) is deterministic, so the sha
    changes exactly when the statement's mathematical content does.
    """
    labels: dict[str, dict] = {}
    for n in nodes:
        lab = n["label"]
        if not lab:
            continue
        labels[lab] = {
            "kind": lab.split(":", 1)[0],
            "leanok": n["leanok"],
            "notready": n["notready"],
            "lean": n["lean"],
            "uses": n["uses"],
            "statement": n["statement"],
            "statement_sha": hashlib.sha256(
                n["statement"].encode("utf-8")
            ).hexdigest()[:12],
        }
    scripts = (
        sorted(p.relative_to(REPO).as_posix() for p in (REPO / "scripts").glob("*.py"))
        if (REPO / "scripts").is_dir()
        else []
    )
    return {
        "generated_by": "scripts/check_linkage.py",
        "note": "Projection of blueprint/src/content.tex — generated, do not hand-edit.",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **_git_provenance(),
        "labels": labels,
        "lean_decls": sorted(lean_names),
        "scripts": scripts,
    }


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
    ap.add_argument(
        "--emit-manifest",
        type=Path,
        metavar="PATH",
        help="Write the blueprint manifest (labels + leanok + Lean decls + uses + statement hashes) the wiki reads "
        "to resolve claim proof-refs, e.g. --emit-manifest ~/Documents/Notes/blueprint-manifest.json",
    )
    args = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    tex = read_blueprint()
    nodes = blueprint_nodes(tex)
    labels = {n["label"] for n in nodes if n["label"]}
    lean_names = lean_declared_names()
    axk = ledger_keys()

    if args.emit_manifest:
        args.emit_manifest.write_text(
            json.dumps(build_manifest(nodes, lean_names), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        n_lab = sum(1 for n in nodes if n["label"])
        print(f"Wrote manifest ({n_lab} labels, {len(lean_names)} Lean decls) → {args.emit_manifest}")

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
        elif nearest != key and nearest and STMT_LABEL_RE.match(nearest):
            advisory.append(
                f"[paper]  {fn}: labelled statement '{nearest}' shares blueprint '{key}' "
                f"(rename to the blueprint label for single-sourcing)"
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
