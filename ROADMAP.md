# Roadmap — scale-space-foundations (project infrastructure)

The tooling/infrastructure backlog for this repo, the article **satellite**. Prioritised by what raises
the trustworthiness and publication-readiness of the two deliverables (Lean + monograph).

**This is not the research backlog** (that lives in the wiki hub's project page,
`Notes/wiki/projects/spatio-temporal-scale-space.md`, and `RESEARCH.md`) **nor the write-up status**
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

## The LLM ceiling lives partly elsewhere

The adversarial-reviewer half of the template (§B *LLM* prompts + §C voice rubric) is a **`/review-draft`
skill owned by the hub** — because the author develops notes *there*, in dialog, and wants publication
awareness during authoring, not only over a finished `.tex`. It reads this repo's
`PUBLICATION-TEMPLATE.md` as its spec (the same cross-repo spec/consumer pattern as `CLAIMS.md`). See
`Notes/ROADMAP.md`.
