# Interactive review guide

For reading through the formalisation with a Claude Code agent as a guide (VS Code extension). Paste
the kickoff prompt below to start; the rest is a suggested tour and what to scrutinise at each stop.

## Kickoff prompt (copy–paste)

> I want to **review** this Lean formalisation interactively — you are my guide, not a coder. **Do
> not edit any files** unless I explicitly ask. First read `Formalization/README.md` and
> `Formalization/REVIEW.md`, then walk me through the project along the suggested tour, one stop at a
> time, at my pace — pause after each stop for my questions. At each stop: explain the mathematics in
> plain terms *and* the Lean specifics, tie it to the blueprint / the SSVM 2007 paper, and proactively
> surface any caveats or things a reviewer should question. Use the tools freely to answer me — read
> the source, and when I ask about a theorem's trust base run its `#print axioms` (e.g.
> `lake env lean Scratch.lean`, or a scratch `#print axioms <name>`). Start by giving me the map from
> the README and the two dependency graphs, then propose the first stop.

## Before you start

- The build is cached and **`sorry`-free**. Open `Scratch.lean` first and let the Lean server finish
  loading Mathlib (cold load is slow; you'll see the Infoview populate the `#print axioms` output).
  After that, hovering shows types, ctrl/cmd-click jumps to definitions, and the Infoview shows the
  goal state inside any proof.
- The fastest trust-boundary check is `lake env lean Scratch.lean` — it prints `#print axioms` for
  every headline result.

## Suggested tour

1. **The map.** `Formalization/README.md` — module map + the two dependency graphs (imports; and
   headline `[T]` theorems → the `[A]` axioms they rest on). Orient here.
2. **The contract (read this before the proofs).** `Interfaces.lean` + `../blueprint/AXIOMS.md`, then
   run `lake env lean Scratch.lean`. This is *what is proved vs. what is assumed* — the `[A]` trust
   base is the labelled axioms **A1–A10**, each grounded to a named source in the ledger. Note what is
   **not** here: there is no "bridge" axiom (the causality bridge is proved — stop 4).
3. **The structural spine.** `Symbol.lean` (the `ad(γ)` cascade arithmetic) → `NonExistence.lean`
   (`no_time_causal_galilean_scale_space_on_spacetime`, and the sharp `α₀ = 2`).
4. **The temporal characterisation + the discharged bridge** — the crux modelling of this cycle.
   `Temporal.lean`: `power_law` (dilation covariance ⇒ Laplace symbol `sᵅ`, a `log`-substitution onto
   the continuous Cauchy solution), then Bernstein (A5) pinning a causal kernel to `0 < α < 1`
   (`causalKernel_alpha_not_nat`). Then back in `NonExistence.lean`: `IsTimeCausal b` is *defined* as
   `IsCausalScaleSpaceKernel (laplaceExponent b)`, and the single Samko-grounded identity
   `laplaceExponent_eq_temporalOrder` (A6) turns `timeCausal_temporalOrder_not_nat` from a
   self-referential **axiom** into a **theorem**. Scrutinise this decomposition closely.
5. **Generator / evolution / locality** (`TemporalGenerator.lean`, IJCV §5, symbol-level). The
   generator symbol `-sᵅ = -D^α_{t,+}` (`generator_symbol_eq_neg_rlLeft`, A9); the evolution order
   `1/α` via `(sᵅ)^{1/α}=s` (`evolution_eigenvalue`, Lean core) and the RL eigenfunction A10; and the
   **signaling equation `α=1/2`** as the unique local + positive causal scale-space
   (`signaling_equation_unique`, A7+A8), which recovers the `α=1/2` kernel of stop 7.
6. **Generators by geometry.** `AffineLine.lean` (Feller/Riesz), `Euclidean.lean` (Riesz Laplacian),
   `CausalAffine.lean` (right-sided RL), `CausalGalilean.lean` (`causal_galilean_evolution` — the
   constructive counterpart to non-existence).
7. **The analysis result.** `Kernel.lean` — ledger **A4 promoted from axiom to a proved `[T]`**:
   `galilean_kernel_solves` verifies the coupled PDE system by real differentiation
   (`spatial_heat`, `temporal_heat`, the drift-cancellation); `spatial_heat_dim`, `kernel_eq_closedForm`.
8. **The symbol calculus.** `PsiSymbol.lean` (translation-invariance lemma; the Poisson bracket;
   `IsCovariant` / `ScaleSpaceWedge`; `galileanGens_covariant`) alongside
   `../blueprint/DESIGN-symbol-calculus.md` (why the calculus is truncated, and where that is exact).

## What's most worth scrutinising

- **Is the trust boundary really just those axioms?** Ask the agent to `#print axioms` any headline
  theorem and confirm it reduces to Lean core + only its labelled `[A]` axioms — and that
  `no_time_causal_…` reduces to `{A5 leaves, A6}` with **no bridge axiom and no Fagerström
  self-reference** (the 2026-07-08 invariant).
- **The crux — is the discharged bridge honest, or a definitional shortcut?** Two things to check:
  (a) is defining `IsTimeCausal b := IsCausalScaleSpaceKernel (laplaceExponent b)` a *faithful* model
  of time-causality, and (b) is `laplaceExponent_eq_temporalOrder` (A6) the *only* substantive
  assumption added — and is it genuinely Samko's (RL derivative ↦ Laplace symbol `sᵅ`), not
  Fagerström's? This is the "defined vs. related" decision; the alternative would smuggle a theorem
  into a definition.
- **The symbol-level modelling of the RL operators** (stop 5). Generator/evolution are stated on
  Laplace symbols (`rlLeftDerivSymbol`, `rlRightEigenvalue`: opaque values pinned by A9/A10 axioms).
  Is that faithful? Note the *uniqueness* claims (Hille–Phillips abstract Cauchy problem) are **not**
  formalised — deferred with `thm:generation`.
- **Are the `[A]` axioms faithful to the cited sources?** `AXIOMS.md` ties each to a named
  theorem/page (A5→Feller §XIII.4 p.440; A6/A9→Samko §7.2; A7→Samko §2 (2.29); A8→Feller §VI.1
  pp. 170–171 as the local case of A1; A10→Samko §9.3 tables). Two flagged residuals: **A10**'s
  exponential-eigenvalue formula is OCR-garbled in the scan (location + `Re λ > 0` confirmed,
  `λ^β` glyph not); and A3's
  asymmetric range.
- **Are the theorem *statements* faithful to the paper**, not just the proofs? Cross-check against the
  blueprint (`../blueprint/src/content.tex`, the `\lean{}` tags — `thm:galilean-nonexistence` and
  `prop:temporal-characterization` are the relevant nodes) and the SSVM/IJCV papers.
- **The deliberate boundaries** (all documented): the kernel PDE is verified for `d = 1` (spatial part
  all `d`); the fractional symbols' covariance holds for `ξ > 0` (the `|ξ|^α` kink); the RL operators
  are modelled by their symbols; `def:g-wedge` *minimality*, `thm:generation`, and the
  generator/evolution *uniqueness* are not yet modelled.

## Pointers

- `../blueprint/AXIOMS.md` — axiom provenance ledger.
- `../blueprint/DESIGN-symbol-calculus.md` — the truncated-calculus decision.
- `../blueprint/src/content.tex` — the shared spec; theorem statements are shared with the paper.
