---
paths:
  - "Formalization/**"
---

# article-kit — the Lean formalization

Framework-owned (`linkage init --sync`); do not edit here. The phases are
`../article-kit/docs/PROCESS.md` §§ 4–6.

- **Statement first.** A `[T]` node is attacked by writing its target type in
  `Formalization/Skeleton/`, `sorry`-marked, and tagging the node `\lean{…}\notready`. A declaration
  moves out of `Skeleton/` when proved, and its node goes `\leanok`. Nothing in `Skeleton/` is cited
  by the library or listed in the axiom guard.
- **The gates before a merge or a report of "done"**: `lake build`; the axiom guard
  (`lake env lean CIAxiomGuard.lean`) run to completion **with its exit code checked**, not its
  tail read; `linkage check`; `linkage axioms --check`. Run the guard before writing "Lean core"
  into an annotation: a statement quantifying over a family built on an interface picks up that
  interface however elementary its proof.
- **The proof of record follows the machine-checked route.** When the Lean proof takes another
  route than the printed one, the blueprint proof is rewritten to the checked route.
- **Statement changes** in the safe direction (narrow, split out, restate at the source's letter,
  drop what nothing reads) carry a `% CHANGED` marker and a ledger row and are reported as
  decisions; a widening, or admitting an interface, waits for the author.
- **One Lean-building agent at a time** on this machine. In a fresh worktree, copy the main
  checkout's `Formalization/.lake/build` in before the first `lake build` (parallel elaboration
  against the shared store drops olean reads).
- **A prover's scratch is its own directory** (`%TEMP%/<repo>-<name>/`), never the top of `%TEMP%`:
  a stray `enum.py` there once shadowed the standard library for every script run from `%TEMP%`.
- `Formalization/.lake/packages` holds junctions into the shared store
  (`C:/Users/danie/Documents/Notes/lake-store.py`): never `lake update` or `lake clean` in a linked
  project; after a pin bump, a gate failing on an undeclared shared name is a stale junction, fixed
  by `lake-store.py link <repo>`, not a defect.
- The Lean language-server MCP (`.mcp.json`, `lean-lsp-mcp`) gives goal states, diagnostics and
  premise search without rebuilds. The first call after a cold start can time out; retry. The
  gates above remain the gates.
