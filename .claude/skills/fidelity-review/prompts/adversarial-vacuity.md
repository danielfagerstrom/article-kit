# Prompt: adversarial vacuity (one per headline theorem)

Spawn with `model: sonnet` (or `opus` for the article's single most important theorem),
`run_in_background: true`. Read-only. If a fix agent is editing concurrently, tell it to read
committed versions with `git show HEAD:<path>`.

---

Adversarial-vacuity pass for a fidelity audit (repo `<repo>`; read
`blueprint/PLAN-fidelity-review.md` §1–2 first for the failure modes F1–F5 and the method).
READ-ONLY: do not edit or create files, do not run lake.

Target: **<theorem name>**, `<declaration>` in `<file>`, and the lemmas it assembles: <list>.
The article's statement is <draft item, lines>; the blueprint node is `<label>` in `<tex file>`.

Your job is to TRY TO MAKE THE THEOREM TRIVIAL. For each conjunct, attack from every angle:
1. **Vacuous hypotheses**: can the hypotheses be satisfied only trivially, or be contradictory?
   (`Witnesses.lean` exhibits models — check they are genuine and non-degenerate, not satisfied
   through junk in some auxiliary definition.)
2. **Junk-value conclusions**: every partial function in the conclusion — `ENNReal.toReal`,
   `Real.log`, Bochner integrals, Mathlib `mellin`/`mellinInv`, `Classical.choose`n objects,
   `x⁻¹`, `Real.rpow`, `deriv`. For each: could the conclusion hold because of a default value,
   without the mathematics? Where the theorem states an equation between two possibly-junk
   quantities, is convergence/finiteness asserted or proved (name the lemma)?
3. **Weakened conclusion**: list every clause of the article's statement that has NO
   counterpart among the Lean conjuncts. Known already: <what the integrator has noticed>. Find
   anything else — normalisations concluded in the article but not in Lean; identifications
   between two Lean objects that the article treats as one (`u = Φ f`), bridges (operator-level
   vs measure-level uniqueness) that exist as lemmas but are not conjuncts.
4. **Strengthened hypotheses**: every Lean hypothesis not in the article, classified.
5. **Definitional divergence in the conclusion**: is each Lean object in the conclusion the
   article's object, with the article's normalisation and index conventions?

Report either an attack (concrete: which hypothesis/conclusion, how it trivialises) or "no
attack, because <named lemma/argument>", per item. Be terse and precise; cite file:line. End with
a ranked list of the genuine findings, distinguishing "vacuous/junk" from "weaker than the
article" from "cosmetic".
