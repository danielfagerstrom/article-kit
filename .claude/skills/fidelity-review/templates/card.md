### T<tier>.<n> `<node label>` · <draft numbering> · `<Lean declaration(s)>` (`<file>:<line>`)

**Draft says.** <the statement, quoted or tightly paraphrased>

**Blueprint says.** <ditto; note any difference from the draft>

**Lean says (unfolded).** <the statement with every project definition unfolded to Mathlib
primitives — what a reader who trusts Mathlib and nothing of ours has to accept>

**Hypotheses/clauses.**
| article | Lean | class |
|---|---|---|
| <hypothesis or clause> | <its rendering> | same / weaker / stronger / absent-in-article / absent-in-Lean |

**Junk-value audit.** <every partial function in the statement and why its default cannot fire,
or which theorem rules it out>

**Witness.** <the concrete model satisfying every hypothesis at once — the `Witnesses.lean`
theorem that says so>

**Blind restatement.** <what the draft-only agent wrote, and where it agreed/disagreed>
*(Tier 0 and headline theorems.)*

**Adversarial vacuity.** <attack found, or "no attack, because <lemma>">
*(headline theorems.)*

**Verdict.** faithful / faithful-with-note / weaker (how) / stronger-hyp (how) / divergent-def (how)

**Actions.** <Lean strengthening, blueprint annotation, draft edit, or none — as ledger rows>
