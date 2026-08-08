# Blueprint ↔ Lean ↔ ledger ↔ paper linkage

How the four artifacts of this project reference one another, and how those references are kept from
drifting. This file is the spec; [`linkage check`](../linkage/checks.py) enforces the
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
| blueprint → wiki *(projection)* | `linkage manifest` → `blueprint-manifest-<slug>.json` | the wiki reads proved-status to validate a note ("check") |
| wiki → blueprint *(pull)* | `wiki demands --json` → `linkage demand` | the wiki's proof requests, incl. not-yet-existing nodes ("demand") |

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
   the `AXIOMS.md` contract, verified by Lean, not re-checked by this script — so this rule alone has no
   numbered check, and the checker's numbering runs one behind the rules' from here on.)
6. **Every statement node declares `\statusT` or `\statusA`.** The hub's confidence grading keys on the
   projected status, so a node without one is a node the hub cannot grade.
7. **Every `[A]` node declares its assignment** (ADR-0011, 2026-07-30): a `\textbf{Assignment.}` clause
   inside the node's status annotation, saying **which ledger entry is answerable for which clause of this
   statement** and **what it does not carry** — the parts held as `[T]`, and the parts deliberately outside
   the trust base. The clause must name at least one entry. It lives in the status annotation because
   `normalize_statement` strips that region, so writing or revising a declaration never moves a
   `statement_sha` and never disturbs a transcluded block.

   Two conventions make the projection honest. Inside the clause, use `\ledger{AXX}` only for an entry that
   genuinely carries part of *this* node's statement — the manifest projects every `\ledger{}` in the node
   body as one of its sources (de-duplicated, first-mention order), so a macro'd cross-reference to an entry
   the node merely mentions would show up in the hub as a source it does not have. Name such an entry in
   plain text ("A18's", "not A1"). And a part carried as `[T]` needs a **proof of record in the blueprint**,
   not a promise: the blueprint is the text of record, so "elementary, not formalised" is a proof debt only
   when the elementary proof is written down.

   The rationale is ADR-0010's: an `[A]` statement may say more than its citation, provided every part is
   either cited with a page anchor or carried as `[T]`; what is forbidden is an *unassigned* part, ours and
   unproved, riding on the `[A]` grade. Three such parts were found by hand in 2026-07 and none by any
   automated control. A checker can require that the judgement be written; it cannot make it, and it cannot
   tell a wrong declaration from a right one. What it removes is the silent case.

8. **A proved node rests only on proved or written-down mathematics** (2026-07-31). No `\leanok` node may
   reach, through the transitive `\uses` closure, a `[T]` statement node (`thm`/`prop`/`lem`/`cor`) that is
   proved nowhere — neither `\leanok` nor carrying a proof environment in the blueprint. This is the
   structural property behind what `\leanok` means to a reader, and to the hub, which grades a note
   `confidence: verified` off the projected flag.

   Two exemptions, both principled. **`[A]` nodes** are the trust boundary itself (rule 5): they are
   accepted on a page-anchored citation and reviewed in `AXIOMS.md`, and resting on one is the
   verified-core/axiomatized-analysis split working as designed. **Definitions** are vocabulary rather than
   claims; a proved node may legitimately name an unformalised one.

   The exemption is for `[A]` nodes as *targets*, and the fatal walk still traverses **through** them: an
   `[A]` node's own statement may not be phrased in terms of a statement proved nowhere either. That is the
   stronger reading and it costs nothing here. It is not hypothetical: `[A]` nodes do `\uses` our own nodes —
   the pre-split `thm:covariant-lamperti` carried `\uses{def:covariant-memory,thm:memory-family}` — and the
   A15 split exists because that node had absorbed an unproved clause of ours into the ledger once already.
   A cited interface earns its trust from a page anchor, not from what it happens to `\uses`; but a reader
   cannot even *read* the statement if the labels it is phrased in terms of stand for nothing.

   And one distinction the naive form of the rule gets wrong: *not `\leanok`* is not *unproved*. ADR-0010
   rule 2 permits a node whose blueprint proof is complete but which Lean does not state — Lean models
   symbols where the proof needs operators, or formalisation is simply pending. Resting on such a node is a
   **proof debt**, reported as an advisory with the proof's size, not a defect. `prop:conservative` is the
   current instance: the naive form scored its sixteen dependents as violations on the day it went `[A]
   \leanok` → `[T] \notready` *while gaining* a proof of record — a strict improvement read as sixteen
   regressions. Only a statement with no argument anywhere is a violation. What the checker cannot judge is
   whether a proof of record is a *proof* — "see Lean" is not one (`ROADMAP.md` #7); that stays review's
   job, and the advisory prints the size so a stub is visible.

   **The two walks are deliberately asymmetric** (2026-07-31): the fatal walk goes through `[A]` nodes, the
   advisory's dependent count **stops at** them. They ask different questions. The fatal one asks *is
   anything a proved node rests on missing an argument altogether* — where a longer reach is strictly safer.
   The advisory one is the formalisation worklist: *which proved nodes would gain if this statement were
   formalised?* A node that reaches the statement only through an `[A]` interface would gain nothing — its
   trust already passes through the ledger at that point, and whether *that* is sound is `AXIOMS.md`'s
   review, not a formalisation task. Counting it inflates the number and points effort at the wrong node.
   Today `prop:conservative` has **10** dependents ahead of the boundary and **16** counting through it; the
   six that differ all reach it behind `prop:memory-positivity-cone` (`\ledger{A18}`). Both numbers are
   printed, because the gap says how much of the debt an axiom already covers. A `\leanok` `[A]` node that
   `\uses` the statement *itself* still counts as a dependent — the labels in its own statement are its own
   dependency, even though nothing above it inherits them; that is why `prop:feller-negdef` is among the ten.

## The checker

`linkage check` (linkage/checks.py) — no dependencies; run `linkage check` from the repo root.
It reads `content.tex` and inlines its `\input{parts/...}` includes, so the split is transparent to it.
It enforces the **in-repo** edges and fails (exit 1) on:

- a `\leanok` node whose `\lean{Decl}` is not declared in `Formalization/` (rule 3);
- a `\ledger{AXX}` / "ledger AXX" with no `## AXX` entry in `AXIOMS.md`, or an entry with no `**Cite:**` line (rule 2);
- a paper `% shared with blueprint <label>` naming a label the blueprint does not have (rule 4);
- a `\command` in a statement or proof that the render pipeline cannot handle (the clean-render gate);
- a statement node with no `\statusT` / `\statusA` (rule 6);
- a `\statusA` node with no `\textbf{Assignment.}` clause, or whose clause names no ledger entry (rule 7);
- a `\leanok` node whose transitive `\uses` closure contains a `[T]` statement proved nowhere (rule 8) —
  reported once per reached statement, naming the dependents and a shortest path to it. The walk is
  breadth-first with a visited set, so it terminates whatever the edges do (a `\uses` cycle is a modelling
  error, not something this check should hang on).

It also prints **advisories** (non-fatal): a paper shared statement whose own label differs from the
blueprint key; a `\leanok` node with no `\lean{}`; a node marked both `\leanok` and `\notready`; and — the
formalisation worklist — each statement a `\leanok` node reaches that is proved on paper but not in Lean,
with its proof size and **both** dependent counts, those ahead of the trust boundary and those counting
paths through an `[A]` interface (rule 8; the first is the headline, since it is the number formalising the
statement would actually discharge). Its summary line reports the whole dependency picture,
including `[T]` statements proved nowhere that nothing proved reaches: those are our open conjectures, and
naming them keeps the difference between "open" and "leaned on while open" visible.

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

**Out — the manifest (`check`).** `linkage manifest <path>` writes
`blueprint-manifest-<slug>.json` into the wiki: a projection of every label with `kind`, `leanok`, `notready`,
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

- *Transclusion fields — manifest v2 (shipped 2026-07-25; `ROADMAP.md` #7 T1).* The manifest is now
  the wiki's **import source**, not only its checker — it implements the 2026-07-25 decision (hub
  `ARCHITECTURE.md` § "The theorem channel"): the blueprint is the single source of the mathematical
  text; wiki notes transclude nodes verbatim, never paraphrase. Per label, v2 adds: `env` + `title`
  (the environment name and its optional `[human title]`, split out of the statement — presentation
  metadata for the import's block header, so titles no longer sit in `statement`/`statement_sha`);
  `proof` + `proof_sha` (the trailing `proof` environment, same normalization as `statement`; null
  when absent — 14 of 48 nodes carry one today); and the rendered forms `statement_md` / `proof_md` +
  `rendered_sha`, produced at emit by a **version-pinned pandoc** (`PANDOC_PIN = 3.10`,
  `commonmark+tex_math_dollars`, `--wrap=none` — Obsidian's `$`/`$$` math dialect) over the
  normalized source with `macros.tex` fed as a preamble, so custom macros expand (inside math too)
  and `\ref{X}` renders as the code span `` `X` ``. Top-level: `manifest_version: 2` and a `render`
  provenance block. Determinism is the point: `rendered_sha` is what the hub's `wiki import`/lint
  byte-compares, so **the pandoc version is pinned in the emitter and installed pinned in CI** —
  never `apt install pandoc`. Degrade path: no pandoc / wrong version → the manifest emits without
  rendered fields and warns; `--require-render` (used by the CI job, the hub copy's single writer)
  turns that or any per-label render failure into a hard error. The **clean-render gate** (T2,
  shipped same day) is *source-side* — check 4 of the checker, run on every invocation: each
  `\command` in a statement/proof must be defined in `macros.tex` (it expands at render) or vetted in
  [`render-allowlist.txt`](render-allowlist.txt) (standard LaTeX pandoc/MathJax know natively).
  Source-side because pandoc **silently drops** unknown commands — argument and all — so output-side
  residue checking cannot catch them; an output residue scan remains as a belt under
  `--require-render`. The gate fails the plain check (the mathematician's pre-report ritual), the
  post-commit preview hook (warning), and the CI manifest job — a render-breaking node fails at
  commit, never at import.

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

- *The join (shipped 2026-07-16).* `linkage demand` is the
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

- **Enforced now, checker green:** blueprint→Lean, blueprint→ledger, paper→blueprint (existence),
  blueprint→wiki (with `--wiki`), and blueprint→blueprint (the dependency invariant, rule 8 — clean, with
  `prop:conservative` the one advisory formalisation debt).
- **Incremental rollout:** migrate the remaining "ledger AXX" prose to `\ledger{}`; add `\notes{}` to the
  rest of the nodes; add reciprocal `blueprint:` frontmatter to the wiki content notes. (Paper
  same-labelling is settled: the non-existence theorem uses `thm:galilean-nonexistence`; the affine result
  is shared at prose level — no advisories outstanding.)
- **Shipped 2026-08-08 — the web/dep-graph build is deployed, not just installed.** The reusable
  [`docs.yml`](../.github/workflows/docs.yml) gained a `web` job: plasTeX renders
  `blueprint/src/web.tex` and the deploy job publishes it at `/blueprint/` on the article's
  Cloudflare Pages project, so the `\uses` graph and the `[T]`/`[A]` tags are a shareable URL
  rather than a local artifact. Opt out per article with `build_web: false`. It needs neither TeX
  nor a graphviz binary — all mathematics goes to MathJax client-side (so plasTeX emits no images;
  the job passes `--imager=none` to make that explicit rather than relying on a fallback), and
  `plastexdepgraph` ships Graphviz as WebAssembly, laying the graph out in the reader's browser.
  Locally, `scripts/build-blueprint.sh` in each article rebuilds the same view.
- **Still larger, separate:** have blueprint→Lean checked by leanblueprint's *own* tooling
  (`checkdecls`) rather than only by `linkage check`'s declaration scan; and true statement
  single-sourcing between paper and blueprint via shared `\input`.
- **Decided 2026-07-25, in build-out:** the transclusion layer — the blueprint as the single source of
  the mathematical text for wiki and article (see the *Planned — transclusion fields* bullet above;
  master roadmap `ROADMAP.md` #7, hub half `Notes/ROADMAP.md` #14). Promotes paper statement
  single-sourcing from nice-to-have to a roadmap milestone (T6).

## Ownership

This file is the spec. `blueprint/src/content.tex` is the source of truth for the graph; `AXIOMS.md`
owns the `[A]` grounding; `linkage check` (linkage/checks.py) enforces consistency. The linkage is gate item 7 in
`paper/DRAFTING-GATE.md`.
