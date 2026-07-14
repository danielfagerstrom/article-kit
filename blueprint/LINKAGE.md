# Blueprint ↔ Lean ↔ ledger ↔ paper linkage

How the four artifacts of this project reference one another, and how those references are kept from
drifting. This file is the spec; [`scripts/check_linkage.py`](../scripts/check_linkage.py) enforces the
in-repo part of it.

## The hub and the canonical ID

The **blueprint** (`blueprint/src/content.tex`) is the source of truth. Every knowledge unit is one
blueprint statement node

    \begin{theorem}[human title]\label{kind:name}      % kind ∈ def | lem | prop | thm | cor

and its **`\label{kind:name}` is the canonical ID**. Every other artifact either points *at* that label
or is pointed *to* from the node. There is no second registry to keep in sync — the blueprint is the
manifest.

## The edges

| Edge | Mechanism | Meaning |
|---|---|---|
| blueprint → Lean | `\lean{Decl}` + `\leanok` (proved) / `\notready` (WIP) | node names its Lean declaration(s) |
| blueprint → blueprint | `\uses{label}` | dependency graph (leanblueprint) |
| blueprint → ledger `[A]` | `\ledger{A15}` | `[A]` node names its `AXIOMS.md` entry |
| blueprint → wiki note | `\notes{slug}` | node names its Notes content note (the "what") |
| paper → blueprint | `% shared with blueprint <label>` + the paper statement's own `\label` | shared statements |
| ledger → blueprint / Lean | `**Blueprint:**` / `**Lean:**` lines in each `AXIOMS.md` entry | reciprocal back-pointer |
| wiki note → blueprint | `blueprint: [labels]` frontmatter *(incremental)* | reciprocal back-pointer |

`\lean`, `\leanok`, `\uses`, `\notready` are the standard **leanblueprint** API (no-ops in the standalone
PDF build; live when built through leanblueprint). `\ledger` and `\notes` are this repo's additions
(`blueprint/src/macros.tex`): `\ledger{A15}` renders inline as "ledger A15"; `\notes{slug}` is a no-op in
the PDF, so private wiki slugs never leak into the public (Zenodo) build.

## The rules

1. **One node per knowledge unit**, with a stable `\label`. Renaming a label is a breaking change —
   update every edge that names it.
2. **`[A]` nodes cite the ledger** with `\ledger{AXX}`, and `AXX` must be an entry in `AXIOMS.md`.
   Legacy prose "ledger AXX" is still recognised; migrate it to the macro when you touch a node.
3. **`[T]` nodes name their Lean decl** with `\lean{}` and mark `\leanok` once proved. A `\notready`
   node need not have a Lean decl yet.
4. **A paper statement shared with the blueprint** carries `% shared with blueprint <label>`, and
   `<label>` must be a real blueprint label. **Target (strong single-sourcing):** when the paper renders
   the statement as a *labelled* theorem, its own `\label` *equals* `<label>`, so the correspondence is
   machine-exact and statements could later be `\input` from a shared file. Prose that merely references a
   blueprint node (its nearest label is a section, not a statement) is a valid weaker link — the checker
   verifies the node exists but does not advise a same-label. Labelled-statement mismatches are reported as
   advisories; align them opportunistically.
5. **The trust boundary is the ledger.** Every `[A]` fact is one `AXIOMS.md` entry grounded in a named
   theorem + page; `#print axioms` on any `[T]` theorem must reduce to Lean core + those axioms. (That is
   the `AXIOMS.md` contract, verified by Lean, not re-checked by this script.)

## The checker

`scripts/check_linkage.py` — no dependencies; run `python scripts/check_linkage.py` from the repo root.
It enforces the **in-repo** edges and fails (exit 1) on:

- a `\leanok` node whose `\lean{Decl}` is not declared in `Formalization/`;
- a `\ledger{AXX}` / "ledger AXX" with no `## AXX` entry in `AXIOMS.md`;
- a paper `% shared with blueprint <label>` naming a label the blueprint does not have.

It also prints **advisories** (non-fatal): a paper shared statement whose own label differs from the
blueprint key; a `\leanok` node with no `\lean{}`; a node marked both `\leanok` and `\notready`.

The **wiki edge** is cross-repo: pass `--wiki <path-to-Notes>` to also check that every `\notes{slug}`
resolves to a `slug.md` under the wiki.

Run it before publishing and as **gate item 7** (`paper/DRAFTING-GATE.md`); a pre-release / CI step is the
natural home.

## Status (2026-07)

- **Enforced now, checker green:** blueprint→Lean, blueprint→ledger, paper→blueprint (existence), and
  blueprint→wiki (with `--wiki`).
- **Incremental rollout:** migrate the remaining "ledger AXX" prose to `\ledger{}`; add `\notes{}` to the
  rest of the nodes; add reciprocal `blueprint:` frontmatter to the wiki content notes. (Paper
  same-labelling is settled: the non-existence theorem uses `thm:galilean-nonexistence`; the affine result
  is shared at prose level — no advisories outstanding.)
- **Larger, separate:** activate the full leanblueprint web/dep-graph build (Tier B is installed) so
  blueprint→Lean is checked by the official tool and the graph renders; and true statement
  single-sourcing via shared `\input`.

## Ownership

This file is the spec. `blueprint/src/content.tex` is the source of truth for the graph; `AXIOMS.md`
owns the `[A]` grounding; `scripts/check_linkage.py` enforces consistency. The linkage is gate item 7 in
`paper/DRAFTING-GATE.md`.
