# Prompt: blind restatement (Tier 0 definitions and headline theorems)

Spawn with `model: sonnet`, `run_in_background: true`. Fill the `<…>`. Group items so one agent
covers one chapter or one cluster of definitions (3–5 items).

---

You are performing a BLIND RESTATEMENT for a fidelity audit of a Lean 4 / Mathlib formalisation.
The value of the exercise depends entirely on you NOT looking at the existing formalisation. Hard
rules:
- Do NOT open, grep, or list anything under `Formalization/`, `blueprint/`, or `paper/` in
  `<repo>`. Do not read README.md or CLAUDE.md there either.
- Read ONLY `<draft file>` in that repo, at the line ranges named below (you may read a little
  surrounding context in the draft for notation).
- Do not write any files. Return your answer as text.

Ambient conventions you may assume the formalisation uses (design facts, not the answers):
<function space and its Lean type; measure type; which quantities are `ℝ≥0∞`-valued; what is
carried as data vs proved; relevant Mathlib primitives available (`mellin`, `MellinConvergent`,
`Real.Gamma`, …) and their junk-value conventions; anything deliberately NOT defined (e.g.
complete monotonicity)>.

Task: for each item below, write the Lean statement/structure you would EXPECT a faithful
formalisation to have, then list every decision point where the draft is ambiguous or where a
naive Lean rendering could be vacuous, weaker, or stronger than the prose (a.e. vs pointwise;
`Ioi 0` vs `Ici 0`; `<` vs `≤`; junk values of partial functions like `x/0 = 0`, `Real.log`,
`Real.sSup ∅ = 0`, `ENNReal.toReal ⊤ = 0`, Bochner integral = 0 when non-integrable; existential
vs bundled data; conditions at endpoints; how "F ≢ 0"-type conditions should become; whether an
increasing bijection needs to be data or property; "for some" vs "for every" height/parameter;
equality of meromorphic functions vs germ agreement vs pointwise). For each decision point say
what you would choose and why.

Items (draft line numbers):
1. <Definition X.Y, lines a–b — as a Lean structure; treat clauses P, Q explicitly>
2. <…>

Be concrete: actual Lean-style text (it need not compile), and a bulleted decision list per
item. Also flag anything in the draft's own statements that is imprecise enough that two
reasonable formalisers would produce inequivalent statements.
