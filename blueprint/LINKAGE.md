# Blueprint ↔ Lean ↔ ledger ↔ paper linkage

How the four artifacts of this project reference one another, and how those references are kept from
drifting. This file is the spec; [`scripts/check_linkage.py`](../scripts/check_linkage.py) enforces the
in-repo part of it.

## The hub and the canonical ID

The **blueprint** is the source of truth. `blueprint/src/content.tex` is a thin **aggregator** that
`\input`s the per-section part files under `blueprint/src/parts/` (split so no single file grows
unwieldy with proofs); the statement nodes themselves live in the parts. Every knowledge unit is one
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
| blueprint → wiki *(projection)* | `check_linkage.py --emit-manifest` → `blueprint-manifest.json` | the wiki reads proved-status to validate a note ("check") |
| wiki → blueprint *(pull)* | `wiki demands --json` → `scripts/proof_demand.py` | the wiki's proof requests, incl. not-yet-existing nodes ("demand") |

The first seven rows are **reference** edges — pointer syntax inside one artifact. The last two are the
cross-repo **workflow** channel and are documented under [The cross-repo channel](#the-cross-repo-channel--manifest-out-demand-in) below.

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
It reads `content.tex` and inlines its `\input{parts/...}` includes, so the split is transparent to it.
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

## The cross-repo channel — manifest out, demand in

The reference edges above are pointers; the **workflow** with the wiki is two-way and runs over two
one-way projections, deliberately never one shared file. The full rationale (why not a co-written file,
why the two directions are not mirror images) is the wiki's to state — see its
[`ARCHITECTURE.md`](file:///C:/Users/danie/Documents/Notes/ARCHITECTURE.md) § "The theorem channel".
This is the satellite side of that contract.

**Out — the manifest (`check`).** `check_linkage.py --emit-manifest <path>` writes
`blueprint-manifest.json` into the wiki: a projection of every label with `kind`, `leanok`, `notready`,
its `\lean{}` decls, its `uses` dependency labels, and its normalized statement text (`statement`) with
a short hash (`statement_sha`), plus the flat Lean-decl set and this repo's `scripts/` paths. The wiki
reads it to answer "is the theorem this note claims actually proved?" — it never parses our LaTeX. Same
contract as the librarian's `library.json`: **we are the single writer, the wiki only reads.**

- *Freshness stamp (shipped 2026-07-16).* `build_manifest()` adds this repo's short git SHA, a
  generation timestamp, and a `source_dirty` flag (via `_git_provenance()`), so the wiki reports
  "manifest: `ssf@<sha>`, N days old" and warns when the manifest is unstamped or was emitted from a
  dirty tree — instead of trusting an undated file. `source_dirty` is whole-repo on purpose: the
  manifest projects labels, Lean decls, and scripts, so a change anywhere may escape HEAD's SHA, and
  the honest signal is "this did not come from a clean commit." Re-emit after committing for a clean
  read. This is what lets the wiki's audit cache re-verify a claim the moment its node flips to
  `\leanok` against a manifest whose currency is visible.
- *Statement text + hash, and `uses` (shipped 2026-07-20).* Each label entry carries `statement` —
  the node's statement text with LaTeX comments and the metadata commands (`\label`/`\lean`/`\uses`/
  `\notes`/`\ledger` with arguments; the bare `\notready`/`\leanok` tokens; `\statusT`/`\statusA`
  together with their trailing `\quad\emph{...}` status annotation — a proof-status remark, so a
  status edit does not move the sha) stripped and whitespace collapsed, the mathematical prose and
  math kept verbatim — and
  `statement_sha`, the first 12 hex chars of its sha256. The normalization is deterministic (same
  input → same hash), so the sha moves exactly when the statement's content does: the wiki's lint
  diffs a note's mirrored statement block against it to catch silent drift (the failure mode that
  motivated this — two near-verbatim mirrors drifted and were caught only by manual audit). Each
  entry also carries `uses`, the node's `\uses{}` labels in order of appearance, so the
  blueprint-internal dependency edges are verifiable vault-side rather than opaque to the hub.
- *Regeneration & delivery (CI, 2026-07-24).* The authoritative channel is
  [`.github/workflows/manifest.yml`](../.github/workflows/manifest.yml): every `main` push touching
  `blueprint/**`, `Formalization/**`, or the generator re-emits the manifest and commits it into the
  hub repo (`notes-wiki`, where the file is tracked) — with a semantic diff-guard that ignores the
  stamp fields, so stamp-only regenerations produce no hub commit. CI is the single writer of the
  hub's copy — a local emit must therefore **never target the vault**: the hub tracks the file, so a
  hand emit would dirty its tree and could be swept into a hub auto-commit, breaking the
  CI-only-writer invariant. Instead, the versioned [`.githooks/post-commit`](../.githooks/post-commit)
  hook re-emits after any commit touching the projected paths into the SSF-local, gitignored
  **`.manifest-preview.json`** (activate once per clone with `git config core.hooksPath .githooks`;
  best-effort, never fails a commit). To check un-pushed work against that preview, point the hub CLI
  at it — `wiki lint --manifest <ssf>/.manifest-preview.json` (the flag defaults to the vault's
  committed copy) — rather than overwriting the vault file; manual
  `--emit-manifest .manifest-preview.json` remains the fallback.

- *Planned — transclusion fields (decided 2026-07-25; `ROADMAP.md` #7).* The manifest becomes the
  wiki's **import source**, not only its checker: per label, `proof` + `proof_sha` (same normalization
  discipline as `statement`) and a rendered-markdown form (`statement_md` / `proof_md` +
  `rendered_sha`), rendered **at emit** — pinned pandoc over macro-expanded source, so the hub never
  handles LaTeX — plus a `manifest_version` field. Hub side: `wiki import <label> [--proof]` copies the
  rendered form into a marked block; `wiki lint` requires byte-equality against the manifest's render.
  This implements the 2026-07-25 decision (hub `ARCHITECTURE.md` § "The theorem channel"): the
  blueprint is the single source of the mathematical text; wiki notes transclude nodes verbatim, never
  paraphrase. A render gate (clean pandoc output, no unexpanded macros) joins the post-commit preview
  hook and the manifest CI job so a render-breaking node fails at commit, not at import.

**In — demand (`demand`; the hub half shipped 2026-07-16).** The inverse is a **pull, not a file we
receive**: when planning proofs, run `wiki demands --json` (with `$WIKI_VAULT` pointing at the Notes
vault) to see which blueprint labels the wiki's claims rest on and at what confidence, **strongest
first**. It reports *raw* demand — a pure function of the wiki's claims, carrying no proved-status — so
**we do the join** against our own `\leanok`, the half we own and the only one that is authoritative.
The hub's ordering already puts the most load-bearing non-frontier demand first; join it with proved
`asc` to drop what is done and the top is the prover's worklist. Frontier-flagged demands are the wiki's
declared-open leads and rank last — not blocking any note. A demand may name a label **not in the
blueprint yet** (the hub flags it `⚠ NOT a blueprint node yet`) — that is the wiki asking for a *new*
theorem; the right response is to add the node (or push back), exactly as one would triage a
`library acquire request` for a source not yet held.

- *The join (shipped 2026-07-16).* [`scripts/proof_demand.py`](../scripts/proof_demand.py) is the
  consumer: it runs `wiki demands --json`, joins against the **live** blueprint parse (not the emitted
  manifest — that is our output and can lag; `\leanok` in `content.tex` never does), and prints the
  unproved demand in the hub's order. Proved labels drop off; `\notready` / no-decl / not-in-blueprint
  are annotated, and it warns when the wiki's manifest is behind this repo's HEAD. `--json` for machine
  use. It is a *query*, run when planning proofs — `PROOFS-PLAN.md` stays hand-ordered and records the
  judgement, not the snapshot.

Neither direction certifies *faithfulness* — whether a Lean statement is true to what the note means it
to say. That is a judgement, left to a reviewing agent (the wiki's `curator`) working with the prover,
not to either projection.

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
- **Decided 2026-07-25, in build-out:** the transclusion layer — the blueprint as the single source of
  the mathematical text for wiki and article (see the *Planned — transclusion fields* bullet above;
  master roadmap `ROADMAP.md` #7, hub half `Notes/ROADMAP.md` #14). Promotes paper statement
  single-sourcing from nice-to-have to a roadmap milestone (T6).

## Ownership

This file is the spec. `blueprint/src/content.tex` is the source of truth for the graph; `AXIOMS.md`
owns the `[A]` grounding; `scripts/check_linkage.py` enforces consistency. The linkage is gate item 7 in
`paper/DRAFTING-GATE.md`.
