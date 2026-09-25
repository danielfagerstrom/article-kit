# Adopting the boundary harness

What an article creates to turn `linkage boundary` on, and a worked example: the four checks
applied to `hemigroup-causal-scale-space-kernels`, which piloted them (Q-0077, 2026-09-25).

The rules and the reasoning are [`LINKAGE.md`](../LINKAGE.md) rule 5, "the boundary harness".
This page is the shape of the edit.

Set it up **as the fidelity review closes** ([`PROCESS.md`](../PROCESS.md) phase 6). The harness
asks the review's own four questions — is the trust base what we said, is the theorem still
saying something, could the development prove a falsehood, does this definition mean what its
name says — and asks them again on every push, which is the part a review cannot do.

---

## The edit

Three new files and one table. Nothing in the existing development moves.

| | what it is | who enforces it |
|---|---|---|
| `[boundary]` in `linkage.toml` | which declarations are headline, and where the other two files live | — |
| the guard file, extended | one `#guard_msgs`-pinned `#print axioms` per headline declaration | Lean (the pin) + `linkage boundary` (the pin's *existence*, and its axioms against `trust-boundary.txt`) |
| `Formalization/Probes.lean` | a cheap should-hold consequence per headline result | Lean (it builds) + `linkage boundary` (it exists, is not a `sorry`, is not `True`) |
| `Formalization/Adversarial.lean` | known-false statements kept as isolated `sorry`s | `linkage boundary` alone — the file is never built |

Two things to get right when wiring it up:

- **The adversarial file must be outside `lean.yml`'s `sorry_guard_dir`.** It is `sorry`s by
  design; if guard 2 scans it, CI fails on the file's whole reason to exist. Set
  `sorry_guard_dir` to the library subtree (`Formalization/<Library>`) and keep
  `Adversarial.lean` at the package root, beside the axiom guard.
- **Nothing may import it.** `linkage boundary` fails if any library source does, because a
  `sorry` that reaches the development is exactly what guard 2 exists to prevent.

### `linkage.toml`

```toml
[boundary]
guard       = "Formalization/CIAxiomGuard.lean"
probes      = "Formalization/Probes.lean"
adversarial = "Formalization/Adversarial.lean"

headline = [
  "Namespace.the_main_theorem",
  "Namespace.the_uniqueness_clause",
]

[boundary.shadows]
"Namespace.laplace" = "the one-sided transform of a measure on [0,∞) — not the Laplacian"
```

`headline` is the article's own judgment about which results are worth pinning one by one.
Keep it short: these are the declarations the paper's headline claims rest on, not every
`\leanok` node. Every other `#print axioms` line in the guard file stays advisory and keeps
being covered by the repository-wide union check.

### The pins

Paste **Lean's own output**, verbatim, including its line wrapping — do not retype it:

```sh
cd Formalization && lake env lean CIAxiomGuard.lean
```

then, for each headline declaration, put its printed line above the `#print axioms` as a doc
comment and add `#guard_msgs in`:

```lean
/-- info: 'Namespace.the_main_theorem' depends on axioms:
[propext, Classical.choice, Quot.sound, Namespace.the_one_interface] -/
#guard_msgs in
#print axioms Namespace.the_main_theorem
```

From then on Lean fails the build when the real axiom set differs from the pin, and
`linkage boundary` fails when the pin names an axiom `blueprint/trust-boundary.txt` does not
declare. Neither half is enough alone — see rule 5 for why.

### Adoption order

1. Add the table with `headline` and the three paths; run `linkage boundary`. It will name every
   missing pin and probe. That list is the work.
2. Pin, probe, and write the adversarial goals. Re-run until it is green.
3. Leave the shadow findings advisory while you go through them one by one: `unfold` or `#print`
   the local declaration and the standard notion, then either rename or write the
   `[boundary.shadows]` entry saying what differs. When the list is empty, pass
   `boundary_strict_shadows: true` to `lean.yml` so a new collision cannot appear unnoticed.

---

## Worked example — `hemigroup-causal-scale-space-kernels`

Run read-only over that repository's `Formalization/` tree (136 tracked sources, 366
`#print axioms` lines in `CIAxiomGuard.lean`). The content below is what its own pull request
should add; it is recorded here because the harness was designed against it.

### Its `[boundary]` table

```toml
[boundary]
guard       = "Formalization/CIAxiomGuard.lean"
probes      = "Formalization/Probes.lean"
adversarial = "Formalization/Adversarial.lean"

# Theorem 7.3's two halves, the analysis direction, and the interface-free collation the
# article's asymmetry claim rests on. These four are pinned one by one and each needs a probe.
headline = [
  "Hemigroup.SelfDecomposableExponent.cascadeFamily",
  "Hemigroup.SelfDecomposableExponent.gauge_and_exponent_unique",
  "Hemigroup.CascadeCore.similarity_form",
  "Hemigroup.CascadeCore.main_analysis",
]
```

Those four are the right set for this article because its central claim is an **asymmetry**: the
constructive direction reduces to Lean core, the analysis direction crosses the boundary at A18
and nowhere else. That is a claim about the per-theorem breakdown, which the union check cannot
see — `main_analysis` could pick up a second interface and the repository-wide guard would still
pass, because A18 is declared and some declaration is expected to carry it.

The pins today (read off the guard file's own prose; paste Lean's real output when writing them):
Lean core for `cascadeFamily`, `gauge_and_exponent_unique` and `similarity_form`, and Lean core
plus `Hemigroup.exists_antitone_density_of_dilation_increments` — ledger A18 — for
`main_analysis`.

### What the shadow check found

Five collisions, all real, none of them previously recorded anywhere:

| declaration | the standard notion it reads as |
|---|---|
| `Hemigroup/Construction.lean` `def kernel` | `ProbabilityTheory.Kernel` — a measurable family of measures, not a measure indexed by a scale pair |
| `Hemigroup/DelayCore.lean` `theorem conv`, `Hemigroup/Levy.lean` `lemma IsCausal.conv` | `MeasureTheory.Measure.conv`, which is two-sided and carries no causality |
| `Hemigroup/Levy.lean` `def laplace` | the Laplace *transform* here; the name also reads as the Laplacian |
| `Hemigroup/MellinEuler.lean` `theorem deriv` | `_root_.deriv` — this one is worth renaming rather than acknowledging |

Each needs the `unfold`/`#print` comparison and then either a rename or a `[boundary.shadows]`
entry. `deriv` is the one to look at first: a *theorem* named `deriv` in a file about a
derivative is the case the check exists for.

### `Formalization/Probes.lean`

A probe must **use** its headline declaration — that is how the lint pairs them — and be a
consequence a reader of the paper would call obvious. Projection notation (`F.cascadeFamily hF`)
and a namespaced reference (`CascadeCore.main_analysis Fam hcov`) both count; a probe merely
*named* after the headline does not.

```lean
/-- `thm:main-construction` really produces a *cascade*: the family it builds composes across
a middle scale. If the construction were weakened to a family with no cascade law, this line
would stop building. -/
theorem probe_cascadeFamily_cascade (x y z : ℝ) (hx : 0 ≤ x) (hxy : x ≤ y) (hyz : y ≤ z) :
    (F.cascadeFamily hF).Φ x z = (F.cascadeFamily hF).Φ x y ∘ (F.cascadeFamily hF).Φ y z :=
  (F.cascadeFamily hF).cascade x y z hx hxy hyz

/-- `prop:main-uniqueness` pins the gauge to the identity, not merely to *some* increasing
function: the conclusion's first clause read at a single point. A uniqueness statement weakened
to "the two gauges agree up to a monotone reparametrisation" would not give this. -/
theorem probe_gauge_is_identity_at_one … : χ 2 = 2 :=
  (SelfDecomposableExponent.gauge_and_exponent_unique hpos hmono hzero heq hχ1 hne).1 2 (by norm_num)

/-- The analysis direction still delivers a *nondegenerate* exponent — not the zero exponent,
which every cascade family would satisfy trivially. This is the clause a vacuity-by-weakening
would drop first. -/
theorem probe_main_analysis_nondegenerate :
    ∃ b₀ : ℝ, ∃ k : ℝ → ℝ, ∃ s : ℝ, 0 < s ∧ levyExponentD b₀ k s ≠ 0 := by
  obtain ⟨_, b₀, k, _, _, _, _, _, _, _, _, _, _, _, ⟨s, hs, hne⟩⟩ :=
    CascadeCore.main_analysis Fam hcov
  exact ⟨b₀, k, s, hs, hne⟩
```

The pattern to copy: **destructure the headline result and keep one clause**. A conjunction that
loses a clause is the commonest way a formalised statement gets quietly weaker, and a probe that
projects out the clause is the cheapest thing that notices.

### `Formalization/Adversarial.lean`

The good adversarial goal for an article is **the negation of a boundary condition the paper
states in prose** — the places where the text says a hypothesis is needed. If the development
could prove one, that hypothesis would be doing no work and the theorem carrying it would be
weaker than the paper claims.

```lean
/-- **FALSE — causality is a real restriction.** If this were provable, `IsCausal` would hold
of every finite measure and the article's central hypothesis would be vacuous: every
scale-space kernel would be causal, including the Gaussian, which is what chapter 1 excludes. -/
theorem every_finite_measure_isCausal (ν : Measure ℝ) [IsFiniteMeasure ν] : IsCausal ν :=
  sorry

/-- **FALSE — the normalisation `χ 1 = 1` is load-bearing.** Without it `χ = fun u => 2 * u` is
a counterexample. If this closes, the uniqueness clause proves more than Theorem 7.3 states. -/
theorem gauge_unique_without_normalisation … : ∀ u : ℝ, 0 < u → χ u = u :=
  sorry

/-- **FALSE — A18 is not free.** A nonincreasing Lévy density is exactly what
self-decomposability buys; the compound-Poisson exponent of a measure concentrated away from
the origin is a counterexample. If this closes, A18 is provable here and should be retired from
`trust-boundary.txt` — or something upstream is unsound. -/
theorem every_levyExponent_has_antitone_density … :
    ∃ k : ℝ → ℝ, AntitoneOn k (Ioi 0) ∧ … :=
  sorry

/-- **FALSE — scale covariance is a real restriction.** Every cascade core admitting a
similarity form would make `IsScaleCovariant` vacuous and `thm:main-analysis` a theorem about
all cascade families, which is not what chapter 6 proves. -/
theorem every_cascadeCore_has_similarity_form (Fam : CascadeCore) … :=
  sorry
```

Note what each docstring does: it says *why* the statement is false and *what it would mean* if
it became provable. Without that, the next reader deletes the line. The lint asks for a comment
on every goal for exactly this reason.

**When one of these fails, do not close the goal and do not delete the line.** Find out what
made it provable.

---

## What the harness is not

It does not run Lean, and it does not decide whether a probe is a *good* probe or an adversarial
goal is really false. Those are the fidelity review's judgments; the harness keeps them from
rotting. A probe that holds vacuously for a reason the lint cannot see (a hypothesis nothing
satisfies) is still the review's problem — see `.claude/skills/fidelity-review/`.
