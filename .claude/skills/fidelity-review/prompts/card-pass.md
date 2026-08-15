# Prompt: card pass for a chapter or tier (Tier 1 supply chain, Tier 2, Tier 3)

Spawn with `model: sonnet`, `run_in_background: true`, one agent per chapter. Read-only.

---

Fidelity-review cards, READ-ONLY (no edits, no lake). Repo `<repo>`. Read
`blueprint/PLAN-fidelity-review.md` §2 (the card shape) and one finished card in
`blueprint/REVIEW-fidelity.md` (e.g. `<T…>`) as the model of tone and length. Keep each card
SHORT (<8–25> lines); this is <chapter/tier>, not the headline theorems. <If a definition card
already exists for these objects: "Card T0.x covers the *definitions*; do not repeat; do the
*statements*.">

Nodes (blueprint `<tex file>`; the `\lean{...}` tag on each node names the declaration; draft
`<draft file>` lines <a–b> for the article's statements): <list of labels with the draft numbering
and, where useful, a specific thing to check — e.g. "the article states an *equivalence*; check
both directions are in Lean or note which", "the article's second display — is there a
counterpart?", "clause (1) MUST assert `Integrable`, not merely a norm bound (a norm bound on a
Bochner integral is provable from junk `0`)", "on which set — `Ioi 0` or the interval where the
quantity is finite?", "value or limit?", "does uniqueness quantify over the article's class or a
narrower one?", "is the scalar factor in the scaling law there?">.

For each: quote the draft statement (tight paraphrase), the blueprint statement if it differs,
then read the Lean declaration and **unfold its definitions to Mathlib primitives**, and classify
each hypothesis and each conclusion clause as same / weaker / stronger / absent-in-article /
absent-in-Lean. Junk-value audit: <the partial functions in play in this chapter>. Pay attention
to `<` vs `≤`, `Ioi` vs `Ici`, whether a "converse" is present, whether an `[A]`-parent's `[T]`
refinement is stated for the case the article's proofs actually use. Give each a verdict
(faithful / faithful-with-note / weaker / stronger-hyp / divergent-def) and, only if warranted, a
one-line finding for the ledger.

Return the cards as Markdown text ready to paste (headings `### T<n>.<k> …`), and a final list
of findings (may be empty). Cite file:line for every Lean claim. Be terse; do not pad or restate
the plan.
