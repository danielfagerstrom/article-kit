# Roadmap — scale-space-foundations (project infrastructure)

The tooling/infrastructure backlog for this repo, the article **satellite**. Prioritised by what raises
the trustworthiness and publication-readiness of the two deliverables (Lean + monograph).

**This is not the research backlog** (that lives in the wiki hub's outline page,
`Notes/wiki/outlines/spatio-temporal-scale-space.md`, and `RESEARCH.md`) **nor the write-up status**
(that is `README.md` § "Manuscript status"). Like the hub's `Notes/ROADMAP.md`, this file is *work*, not
knowledge — the split keeps work-planning out of the blueprint/paper content.

Much of the below is validated and sharpened by a 2026-07-17 brainstorm on AI-supported (author-side)
journal review. The recurring lesson is the constellation's own: **separate a deterministic core that
owns integrity from an LLM ceiling that only flags** (`wiki lint` vs the `note-evaluator`; the drafting
gate's deterministic boxes vs its prose-judgement boxes). This roadmap extends that same discipline to
**two artifacts the constellation does not yet cover deterministically: the Lean trust *boundary*, and
the paper *prose*.**

---

## Now

### 7. Blueprint as the single source of mathematical text — the transclusion layer  ·  🟡 decided 2026-07-25

**The decision.** "Write article fragments in the wiki" failed as a workflow step: freeform prose gives
an LLM no enforcement surface, so the mathematics kept getting smoothed and popularised despite
instruction. In the blueprint, formality is structurally forced (environments, `\label`s, `\lean{}`, the
ledger, `check_linkage.py`, ultimately `lake build`). So the seam moves rather than the prompt: **the
blueprint owns the mathematical text — statements *and* human-readable proofs, at publication register —
and the wiki and the article import nodes verbatim, never paraphrase them.** The wiki keeps what it is
good for: ideation, pre-formal sketches, narrative, literature. The rule at the seam: **once a blueprint
node exists, a note transcludes it; restating it in prose is a lint finding.** The inverse design (wiki
as statement source, blueprint generated) was considered 2026-07-20 and is now rejected, not deferred —
recorded in the hub's `ARCHITECTURE.md` § "The theorem channel". The note-leads-blueprint-follows
mirroring compromise (`/rework-chapter` step 1) becomes interim scaffolding: note-leads survives only
*pre-node*, as the sketch → `wiki demands` phase.

**Design (extends the manifest — same projection, same single writer, no new channel):**

- **Dual-form, dual-hash manifest entries.** Each label gains `proof` + `proof_sha` (same normalization
  discipline as the shipped `statement`/`statement_sha`) and a **rendered markdown form**
  (`statement_md`, `proof_md`, `rendered_sha`). The source-side sha detects blueprint drift; the
  rendered-side sha is what the hub's lint byte-compares. Both deterministic; `manifest_version` field
  added so the hub can warn on an old-schema manifest.
- **Rendering happens at emit, satellite-side.** The hub holds no format machinery (the rule that moved
  LaTeX→md conversion to the librarian), so `wiki import` must be a pure copy. Render route: **pinned
  pandoc** (version asserted by the emitter; installed + symlinked on the author's machines, apt in CI)
  over the normalized statement/proof source, with blueprint-local macros from `macros.tex` expanded
  *before* pandoc so the output contains no unknown commands. **Fallback if pinned-pandoc output proves
  unstable across versions/platforms:** restrict statements to a small MathJax-safe macro set and ship a
  trivial in-repo renderer — the dual-hash design is unchanged either way (that is the point of hashing
  the rendered form separately).
- **Fast feedback lives next to the blueprint workflow, not at import time.** A render gate — every
  node's statement/proof renders clean (pandoc exit 0, no raw `\command` residue, no unexpanded macro) —
  wired into both the post-commit `.manifest-preview.json` hook and the manifest CI job, so the
  mathematician learns of a render-breaking macro at commit, not when a note imports the node weeks
  later. The allowed-macro list lives beside `macros.tex`; adding a macro means adding its expansion,
  and the gate keeps that honest.

**Milestones** (T = this repo, H = hub; hub half tracked as `Notes/ROADMAP.md` #14):

- **T0 — Policy recorded**  ·  ✅ 2026-07-25 — this item; hub `ARCHITECTURE.md` decision section;
  mathematician charter register bar; `LINKAGE.md` planned-fields note; `/rework-chapter` interim note.
- **T1 — Emitter: proof + rendered forms.**  ·  ✅ 2026-07-25 — manifest v2 (spec now in
  `LINKAGE.md` § cross-repo channel): per-label `env`/`title` (split out of the statement, so
  statement shas moved once), `proof`/`proof_sha`, `statement_md`/`proof_md`/`rendered_sha`;
  pandoc pinned at 3.10 (`commonmark+tex_math_dollars`), macro expansion via pandoc's
  `latex_macros` fed `macros.tex`, `\ref{X}` → `` `X` `` code spans; `--require-render` wired
  into the CI manifest job (pinned deb install). Verified: 48/48 labels + 14 proofs render, no
  raw-LaTeX residue outside math, byte-deterministic across runs, hub `wiki lint` reads the v2
  preview cleanly (~11 s per emit).
- **T2 — Render gate.**  ·  ✅ 2026-07-25 — redesigned **source-side** during the build: pandoc
  turned out to *silently drop* unknown commands (argument and all), so output-residue checking
  cannot catch them — the failure mode is invisible content loss. The shipped gate is checker
  check 4: every `\command` in a statement/proof must be in `macros.tex` or vetted in
  `blueprint/render-allowlist.txt` (seeded from the full 97-command inventory, all standard).
  Fatal on every `check_linkage.py` run (mathematician ritual, post-commit hook, CI manifest job);
  negative-tested end-to-end. An output-residue scan stays as a belt under `--require-render`.
- **H3 — `wiki import` + lint rule** (hub-side)  ·  ✅ 2026-07-25 — `curator/transclude.py` +
  lint pass 3c + the `wiki import` verb (print / `--into` replace-or-append / `--refresh` a whole
  note; marker grammar `<!-- blueprint:<label> v<N> [proof] sha:<12hex> -->`, format-versioned).
  Lint: hand-edit inside markers = ERROR ("imported mathematics is read-only"), blueprint moved =
  stale WARNING with the mechanical fix named, unknown label/malformed/unclosed = errors. 17 new
  tests, suite green. Side find: the CI pandoc install was dirtying the workspace → every projected
  manifest stamped `source_dirty` → hub freshness warning; fixed (deb → `$RUNNER_TEMP`) and
  `source_dirty` promoted from stamp-noise to semantic in the diff-guard so the flip projects.
- **H4 — Pilot: the temporal-behaviour note.**  ·  ✅ 2026-07-25 — four mirrors replaced with
  imports; verdict: **livable, adopt** (the blueprint statements were richer than the drifted
  mirrors — the mechanism catching exactly what it was built for). Frictions found and fixed
  hub-side: definition status lines must say "formalized", not "proved"; `blueprint:` frontmatter
  now derives from claims ∪ imports. **Register-sweep input:** part 05 embeds proposition
  arguments inside statements — no `proof` environments — so the sweep should split argument from
  statement there (then imported blocks can show/hide the proof properly).
- **H5 — Migration.**  ·  ✅ 2026-07-25 (swept-part scope) — the three §2–§4 chapter notes migrated
  (19 blocks; with the pilot, 23 transcluded blocks vault-wide); mirrors that had silently drifted
  or lagged the sweep were replaced wholesale. Surfaced two render defects, both fixed same-day:
  in-prose `\ledger` refs were deleted from rendered text leaving dangling punctuation
  (`normalize_for_render` now expands them; statement shas unmoved by design), and `[A]` nodes'
  generated status lines claimed "proved in Lean" for accepted axioms (manifest now projects
  `status`/`ledger`; the hub renders "cited interface (ledger …)"). **Completed 2026-07-26**: the
  §6–§7 fillers migrated (family 2 blocks, classification 5; finite-domain a judged no-op — analysis
  register, drift channel documented note-side) — **30 transcluded blocks across 6 notes** vault-wide.
  Two further render fixes en route: `title_md` (raw-LaTeX titles) and `rendered_sha` rebased over all
  block-derivation inputs (a `leanok` flip now reads as stale, never as a hand-edit violation).
  `/rework-chapter` step-1 mirroring is retired for migrated notes.
- **T6 — Paper single-sourcing.** The `LINKAGE.md` "larger, separate" item, now load-bearing: per-node
  statement files `\input` by both blueprint and paper (LINKAGE rule 4's strong form). Decide then
  whether article proofs are shared or article-specific.
- **Ongoing — register sweep.** Blueprint proofs are the proofs of record; per-part editorial pass
  against the private writing guide, delegable to the mathematician part by part. **Progress:**
  part 05 ✅ (`14dd291` — proofs split out of statements); parts 02–04 ✅ (`b264205` — statements
  self-contained, status-annotation content moved into proofs, `\statusA` lines normalized to
  `\ledger`-first). **Citations:** venue-style prose citations ("IJCV 2005") converted blueprint-wide
  to the new `\sscite{citekey}` macro (renders `@citekey` in PDF and transcluded blocks — the hub's
  claim-ref convention, librarian-checkable). **Parts 01, 06–08 ✅ (`53370ec`)** — 3 new proof
  environments (`prop:limit-kernel-gaussian` deliberately without proof-`\leanok`: partially-checked
  node, honesty call; `prop:bessel-kernel`; `thm:receptive-field`), [A] status lines normalized,
  A11–A14 ledger prose macro-ized. **The sweep is complete — all 8 parts.** The content findings the
  frozen-content rule deferred (undefined $M$ in `def:point-measurement`, `def:lie-wedge` wording,
  proof-`\leanok` semantics, …) are now filed as inbound requests in [`WISHLIST.md`](WISHLIST.md).

### 1. Publication-structure template committed  ·  ✅ 2026-07-17
[`paper/PUBLICATION-TEMPLATE.md`](paper/PUBLICATION-TEMPLATE.md) — the prose-conformance spec (formatting
§A / section contracts §B / voice rubric §C / calibration exemplars §D / pipeline §E), the downstream
companion to [`paper/DRAFTING-GATE.md`](paper/DRAFTING-GATE.md). The gate asks *"is this section ready to
draft?"*; the template asks *"does the drafted prose meet publication structure and voice?"*. A spec, like
`CLAIMS.md` — the deterministic and LLM halves below implement it.

---

## Next

### 2. Boundary harness — lock the Lean trust base as a regression test
Adopt the axiom-footprint **lock** as committed CI, systematising what `Scratch.lean` + `AXIOMS.md` do
today as a manual ritual. Draft to adapt: `C:\Users\danie\Downloads\BoundaryHarness.lean` (opaque
placeholders → swap in the real headline theorems; this repo has real defs, not stand-ins). Pieces:

- **[A] Axiom-footprint lock** — `#print axioms <thm>` wrapped in `#guard_msgs` for each headline result
  (`no_time_causal_galilean_scale_space_on_spacetime`, `causal_galilean_evolution`, `galilean_kernel_solves`,
  the affine/Euclidean wedges). A new axiom sneaking in, or a `sorryAx` leaking, then changes the printed
  message and **breaks the build** — the trust base becomes a tripwire, not a thing you remember to check.
- **[A] Sorry-freeness** via the footprint (already true project-wide; make it enforced).
- **[A] Positive probes** — cheap "should-hold" consequences the kernel verifies.
- **[C] Adversarial goals** — known-false in-domain statements kept as isolated `sorry`s that must **never**
  become provable (a consistency tripwire for the injected literature axioms A1–A16). Isolated so they
  never contaminate the real theorems' footprint; never `import`ed into the main development.
- **[C] Definition scrutiny** — `unfold` / `#reduce` / `pp.all` for terms sharing a name with a standard
  notion (guards "you can define what you should prove").
- Minor: add an explicit **"Deviations from source"** line to each `AXIOMS.md` entry / interface docstring
  (the harness §1 convention) — the human backstop for a silently dropped/weakened hypothesis.

High *value* (turns the `#print axioms` discipline into a real CI gate); bounded effort (harness is drafted).

### 3. `scripts/check_paper.py` — deterministic paper lint
The sibling to `check_linkage.py`, over the paper `.tex` + `references.bib`. Stdlib, reports/fails like the
existing checker. The chat's own "highest reliability-to-effort" pick. Checks:
- **Declarations present** — the four Springer statements (author contributions, competing interests, data
  availability, funding).
- **Abstract** — within ~150–250 words; no undefined acronyms.
- **Cross-reference integrity** — every `\ref`/`\eqref` has a matching `\label`; no dangling `??`; every
  numbered theorem/figure/table referenced at least once (else orphaned).
- **Citation integrity** — every `\cite` key resolves in `references.bib`; flag entries missing a DOI.
- **Contribution↔section map** — a contributions passage exists and each item maps to a later section.

Becomes a new **deterministic box** in `DRAFTING-GATE.md` (alongside item 7's `check_linkage.py`).

---

### 8. Human-in-command formalization — process discipline from the 2026 field  ·  ⬜ surveyed 2026-07-25

Context: with #7 the author works mainly in the blueprint and Lean, and wants back the control that
"agents do the math as by magic" took — the mathematics should follow *his* decomposition and register.
A 2026-07-25 survey (zhu2026leanarchitect, kung2026leap, zhang2026leanmarathon + web landscape; digest
to be filed in the wiki) shows the field converging on exactly our architecture — a **human-owned
blueprint as the coordination artifact, AI filling leaves** (PNT+, FLT, Carleson, Tao's Claude-Code
workflow, Math-Inc's blueprint-seeded Gauss) — and supplies named mechanisms for the control problem.
Adopt as process rules (cheap: charter + skill edits) before any new proving campaign:

- **Frozen-statement discipline** (LeanMarathon): agents may prove a node but never silently reword
  its statement; a statement change is an explicit review event, and when one happens, dependent
  proofs are downgraded wholesale (never patched to fit drift). → mathematician charter invariant.
- **Decomposition gate — the author reviews plans, not diffs** (LEAP; Tao's skeletonize-then-fill):
  attacking a `[T]` node starts with a *compiling Lean sketch* — main argument sorry-free, `sorry`
  only at explicitly named sub-lemmas — plus the informal plan (idea / definitions / lemmas-with-
  purpose / outline naming Mathlib lemmas). **The author approves the decomposition before proving
  starts.** This is where the aesthetic control re-enters: steering happens at the plan level, where
  it is cheap. → a project skill + charter rule.
- **Read-only faithfulness reviewer** (LeanMarathon's target-reviewer): before proving, a separate
  read-only pass checks the triangle *intended meaning ↔ blueprint LaTeX ↔ Lean type* (hypotheses,
  quantifiers, definitions, conclusion) — the reviewer is never the statement's author. Strengthens
  item #4 below with a concrete protocol; natural role split: agent drafts the triangle diff, the
  author judges.
- **Vacuity probes** (LeanMarathon): for each statement and each `[A]` axiom, actively try junk-value
  totalization traps (`tsum`, `Real.sqrt`, division defaults), trivial witnesses, and boundary
  counterexamples before trusting it. Sobering datapoint: LeanMarathon's harness once *faked* missing
  theory with dummy records that type-checked and passed CI — structural gates alone cannot catch an
  ill-stated interface, and our `[A]` axioms are precisely such interfaces. → folds into #2 (boundary
  harness) as new probe classes.
- **Dependency-parity + orphan checks** (LeanArchitect; LeanMarathon CI): infer each `\leanok` decl's
  actual dependency closure (the `#print axioms`-style constant traversal) and diff it against the
  blueprint's `\uses{}` both ways; flag proved nodes with implausibly empty inferred uses (Tao caught
  a wrong statement exactly this way) and lemmas feeding nothing. → extends `check_linkage.py` /#2.
- **Recorded decision — authorship direction.** LeanArchitect (and verso-blueprint, where FLT and
  Carleson now live) make *Lean* the source and generate the blueprint text from attributes; PNT+
  migrated to this. We deliberately go the other way (#7): our deliverable is a LaTeX monograph and
  the register lives in the blueprint. What we adopt is their *inference machinery as audit*
  (auto-`\leanok` via sorryAx-closure, `\uses` inference) — not the authorship inversion. Revisit
  (verso-blueprint port via `leanblueprint-verso-helper`) only after publication.

### 9. Lean agent tooling — adoption shortlist (2026-07)  ·  ⬜ from the same survey

Ranked; each independent of the others:

1. **`lean-lsp-mcp`** (oOo0oOo; `claude mcp add lean-lsp uvx lean-lsp-mcp`) — MCP server over the
   Lean LSP: live goal states, diagnostics, hover, hosted LeanSearch/Loogle/Lean Hammer. Turns the
   agent loop from cold-`lake build`-and-pray into goal-aware editing — directly attacks this
   machine's build-latency pain. Actively maintained; Windows caveat: some local extras want WSL2,
   hosted variants fine. **Adopt first.**
2. **Aristotle API** (Harmonic; free sign-up since 2026-01, `aristotlelib` on PyPI) — purpose-built
   "close this sorry" service, documented solo-researcher workflow (arXiv 2605.20120). Use as the
   escalation path when tactic work stalls, under #8's frozen-statement rule (it gets a sorry, never
   authorship of a statement). Caveats: closed model; review ToS on submitted mathematics before use.
3. **Type-dependency-cone review** (Lean Atlas / "Lean Compass", arXiv 2604.16347) — compute the
   minimal set of project declarations whose *statements* a human must semantically vet for the
   headline theorems (they report 94–99 % node reduction). Formalizes our "verified core, axiomatized
   analysis" trust story: the author reviews the type-cone + the `[A]` ledger, nothing more. Adopt
   the discipline; the tool if convenient.
4. **Open-weight fallback provers** (Goedel-Prover-V2 32B, Kimina) — only if the closed-API route is
   rejected; needs rented GPU. Low priority.
5. **Reading list** for the process rules: Tao's Claude-Code formalization video (2026-03) + the
   equational-theories write-up (arXiv 2512.07087) — the human-adjudication philosophy #8 encodes.

## Later — capture; build on real need

### 4. Statement-faithfulness protocol
Codify the "independent re-formalization + diff" move (never *"does this match?"* — that invites
sycophantic agreement): re-formalize the English claim from scratch, diff against the Lean, treat
divergence as the signal. Most useful variant is scope/hypothesis mismatch ("prose says *for all
distributions*; statement assumes compact support"). Home: extend `Formalization/REVIEW.md` and the
hub's `curator` faithfulness job — the LLM flags, the human is the oracle at the boundary.

### 5. Calibration corpus for the template
Acquire 6–10 current JMIV papers via the librarian (Lindeberg 2024, Bednarski–Lellmann 2023, the JMIV
"Variational Image Regularisation" 2025 special issue) and tune `PUBLICATION-TEMPLATE.md` §B contracts and
proportions to 2026 norms. A `literature-study` task, run from the wiki.

### 6. Publish logistics
Fold into `README.md`'s existing publish step. arXiv tightened endorsement (Dec 2025): as an unaffiliated
first-time submitter you fall to the **personal-endorsement path** (request a code, pass it to an
established arXiv author in the target category — pick from your cited, arXiv-active authors); endorsement
is **per-category**; every submission needs a **full English version** (since Feb 2026). Choose the primary
category deliberately (`eess.IV` / `cs.CV` / `math.NA`). `sn-jnl.cls` alignment only if a journal
submission actually follows the preprint.

---

## Wishes from other members

See [`WISHLIST.md`](WISHLIST.md) for blueprint/Lean/manifest requests other constellation members
have filed *to this repo*; triage into the tiers above (infrastructure) or the proof/blueprint
backlog (content). Same pattern as the hub's and the librarian's wishlists.

## The LLM ceiling lives partly elsewhere

The adversarial-reviewer half of the template (§B *LLM* prompts + §C voice rubric) is a **`/review-draft`
skill owned by the hub** — because the author develops notes *there*, in dialog, and wants publication
awareness during authoring, not only over a finished `.tex`. It reads this repo's
`PUBLICATION-TEMPLATE.md` as its spec (the same cross-repo spec/consumer pattern as `CLAIMS.md`). See
`Notes/ROADMAP.md`.
