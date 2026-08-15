---
name: fidelity-review
description: >
  Audit whether a Lean formalisation proves what its article states — not something weaker,
  vacuous or junk-valued — node by node against the blueprint and the draft. Use when a
  formalisation phase closes ("the Lean is done for now"), before publication, or when a
  headline theorem's `\lean` tag is about to be cited. Produces PLAN-fidelity-review.md,
  REVIEW-fidelity.md (cards + findings ledger) and Witnesses.lean, and lands the fixes.
---

# Fidelity review

The kernel checks proofs. Nothing mechanical checks that the *statement* a `\lean{}` tag points
at means what the blueprint node says, which means what the article says — and a proof-writer's
statement drifts toward what is provable. This skill is the audit of that correspondence, tuned
by one full execution (hcs, 2026-08-15: 66 nodes, 27 findings, none claim-changing, 11
statement-tightenings landed). It assumes the article-kit layout: `linkage.toml` at the root,
`blueprint/src/parts/*.tex` with `\lean{}`/`\leanok`/`\uses{}` tags, `Formalization/<Lib>/`,
`AXIOMS.md` with page anchors, and — for the blind-restatement technique — a *draft* text
separate from the blueprint (`draft/*.md`; nodes carry `% draft: Lemma X.Y` provenance comments).

## 1. The failure modes (what a proved theorem can fail to be)

| | mode | looks like | why silent |
|---|---|---|---|
| F1 | vacuous hypothesis | a hypothesis or structure field nothing satisfies | true and useless; `lake build` cannot tell |
| F2 | junk-value conclusion | holds because a partial function returned its default: Bochner `∫ = 0` off integrability, `mellin` likewise, `Real.sSup ∅ = 0`, `x/0 = 0`, `ENNReal.toReal ⊤ = 0`, `deriv` off differentiability, `Real.log` at `≤ 0` | provable, and not the article's sentence |
| F3 | weakened conclusion | a clause missing: "in the domain" without the domain conjunct; `∃` where the article says unique; a.e. for pointwise; the object concluded is not packaged in the type the next theorem starts from | each present clause reads right |
| F4 | strengthened hypothesis / narrowed domain | extra measurability, `Ioi` for `Ici`, `≤` vs `<`, a quantifier over more than the article demands, a normalisation as a field | a special case; whether the article's reader is in it is the question |
| F5 | definitional divergence | the Lean object is not the article's (a definition widened or narrowed to make a proof go through) | every theorem is right and about something else |
| F6 | interface fidelity | an `axiom` stronger than its cited source, or missing a hypothesis the source has | the only place an inconsistency can enter; everything downstream inherits |
| F7 | proof-route divergence | the blueprint proof cites X; the Lean proves it another way | honesty of the text of record and the `\uses` graph, not correctness |
| F8 | three-way drift | draft ≠ blueprint ≠ Lean; the paper transcludes the blueprint, so a drifted blueprint *is* the published claim | |

F1–F5 are what the user usually asks; F6 and F8 are the ones they forget. F7 is last.

## 2. The card

Every audited node gets one; the review is the cards plus a **findings ledger** at the top
(`templates/card.md`, `templates/REVIEW-fidelity.md`). "Faithful" requires a **witness** line and a
**junk-value audit** line — a card without both is not done. Verdicts: faithful ·
faithful-with-note · weaker (how) · stronger-hyp (how) · divergent-def (how). Findings are tagged
F1–F8 with severity *claim-changing* / *statement-tightening* / *note-only* and a resolution
commit; a resolved row keeps its place.

## 3. Techniques, cheapest first

1. **Unfold to primitives.** Write the "Lean says" line from the definiens (`#print`, read the
   file), never from docstrings. Every `.toReal`, Bochner integral, `Classical.choose`, `sSup`,
   division, `rpow`, `deriv`, `mellin` in a *statement* is an F2 candidate: name the lemma that
   guards it or the hypothesis that excludes it.
2. **Witnesses.** `Formalization/<Lib>/Witnesses.lean`: *named* theorems (not `example`s, so the
   axiom guard can `#print axioms` them) instantiating **all** hypotheses of each headline theorem
   jointly at concrete models; nothing imports the file; every witness listed in the guard. A
   hypothesis no model satisfies is F1; one satisfiable only under a restriction the article does
   not state is a domain finding. Prefer one model that lives in Lean core (no interface axiom) —
   it certifies the hypothesis class nonempty independently of the trust boundary.
3. **Blind restatement.** A fresh agent that has *not* seen the Lean is given the draft (and only
   the draft) and writes the Lean statement it expects, with a decision list (a.e. vs pointwise,
   `Ioi`/`Ici`, junk pitfalls, ∃ vs data). Diff against the actual. This is the only technique that
   finds a *missing* conjunct. `prompts/blind-restatement.md`.
4. **Adversarial vacuity.** A second fresh agent per headline theorem, prompted to *make it
   trivial*; reports an attack or "no attack, because <lemma>". `prompts/adversarial-vacuity.md`.
5. **F6, axiom vs source.** The librarian fetches the anchored pages as *images*; an agent
   compares the `axiom` declaration clause by clause with the source's statement, every row judged
   "axiom ≤ source". Check the docstring's hypothesis-translation arguments (they are claims, not
   facts). Note whether two anchors interlock. `prompts/axiom-vs-source.md`.
6. **F7 sweep, scripted.** `scripts/f7sweep.py` (reads `linkage.toml`): for every `\leanok` node,
   the `\uses` ingredients versus the transitive imports of the Lean file proving it. Every
   "used-but-not-imported" edge must be one of two deliberate patterns — a *setting* citation
   (the node cites the headline theorem; the Lean imports the half it needs) or *specification
   instead of citation* (the Lean states a hypothesis abstractly where the text cites its supplier)
   — or the recorded `[A]`-parent / `[T]`-refinement pattern; anything else is a finding. Where a
   `\leanok` node's Lean invokes a `[T]` refinement directly, point its `\uses` at the refinement.
7. **F8 sweep.** Per chapter, an agent diffs draft statements against blueprint statements (not
   proofs, not annotations); reports genuine differences, draft items with no node, nodes with no
   provenance. `prompts/f8-diff.md`.

## 4. Order (definitions before theorems; the phase plan)

- **P0 Tier 0** — the definitions everything stands on (the axiom structure, the admissible
  class, the transforms, the standing hypotheses, every operator definition). A divergent
  definition (F5) makes every card above it meaningless, so these come first, one card each, with
  blind restatements.
- **P1** — `Witnesses.lean`.
- **P2 Tier 1** — the headline theorems: unfolded card + blind restatement + adversarial vacuity;
  land the fixes (statement-changing fixes on headline nodes only after the card exists).
- **P3** — the supply chain beneath the headline theorems; the ledger axioms (F6); the corollaries
  the article advertises.
- **P4 Tier 2** — the "theorem content" the introduction promises.
- **P5 Tier 3** — examples, refinements; the F7 and F8 sweeps.
- **P6** — verdict paragraph at the top of the review; plan marked executed; README status;
  hub outline.

`templates/PLAN-fidelity-review.md` is the plan skeleton; fill its tiers with the article's own
node labels before starting.

## 5. Rules of engagement

- A finding is **not** fixed inside the card pass; it goes to the ledger with a proposed
  direction (Lean up / blueprint down / draft edit) and is fixed in its own commit naming the row.
- The blind agent must **not** open `Formalization/`, `blueprint/`, `paper/`, README or CLAUDE.md;
  the restatement is written *before* the actual statement is read.
- Any card touching a `\lean` tag re-checks that the tag names the declaration(s) proving **all**
  the node's clauses (a tag may list several, comma-separated) — not a sibling proving the headline
  one.
- Never write backslash-bearing content through a non-raw string (`\ref` → carriage return); the
  Edit tool or raw strings only.
- Commit and push per phase, explicit paths, full gate (`lake build`, the axiom guard **run to
  completion with the exit code checked**, `build-blueprint.sh --quick`, `linkage check`).

## 6. Model split (cost)

Pass `model` explicitly on every spawn: `sonnet` for read-only card passes, blind restatements,
F8 diffs, page fetches; `opus` for the `mathematician` when it writes Lean or judges F6; the
strongest model only for the integrator. Fan-out children inherit the parent's model. In hcs,
P2 (Lean-writing) was the expensive phase; P3–P6 on this split cost a fraction of it.

## 7. Invocation

`/fidelity-review plan` — write `blueprint/PLAN-fidelity-review.md` from the template with the
article's nodes filled in (read `README.md`'s status table and the blueprint's `\lean` tags).
`/fidelity-review cards <tier|chapter>` — run the card pass for a tier or chapter with the prompts
in `prompts/`, integrate into `REVIEW-fidelity.md`. `/fidelity-review sweep` — run
`scripts/f7sweep.py` and the F8 diff. `/fidelity-review close` — P6.
