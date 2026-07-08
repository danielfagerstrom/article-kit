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
   run `lake env lean Scratch.lean`. This is *what is proved vs. what is assumed* — the whole
   `[A]` trust base is five axioms, each grounded to a named source in the ledger.
3. **The structural spine.** `Symbol.lean` (the `ad(γ)` cascade arithmetic) → `NonExistence.lean`
   (`no_time_causal_galilean_scale_space_on_spacetime`, and the sharp `α₀ = 2`).
4. **Generators by geometry.** `AffineLine.lean` (Feller/Riesz), `Euclidean.lean` (Riesz Laplacian),
   `CausalAffine.lean` (right-sided RL), `CausalGalilean.lean` (`causal_galilean_evolution` — the
   constructive counterpart to non-existence).
5. **The analysis result.** `Kernel.lean` — ledger **A4 promoted from axiom to a proved `[T]`**:
   `galilean_kernel_solves` verifies the coupled PDE system by real differentiation
   (`spatial_heat`, `temporal_heat`, the drift-cancellation); `spatial_heat_dim`, `kernel_eq_closedForm`.
6. **The symbol calculus.** `PsiSymbol.lean` (translation-invariance lemma; the Poisson bracket;
   `IsCovariant` / `ScaleSpaceWedge`; `galileanGens_covariant`) alongside
   `../blueprint/DESIGN-symbol-calculus.md` (why the calculus is truncated, and where that is exact).

## What's most worth scrutinising

- **Is the trust boundary really just those axioms?** Ask the agent to `#print axioms` any headline
  theorem and confirm it reduces to Lean core + at most one labelled `[A]` axiom.
- **Are the `[A]` axioms faithful to the cited sources?** `AXIOMS.md` ties each to a named
  theorem/page; A3's asymmetric range carries a flagged residual.
- **Are the theorem *statements* faithful to the paper**, not just the proofs? Cross-check against the
  blueprint (`../blueprint/src/content.tex`, the `\lean{}` tags) and the paper.
- **The deliberate boundaries** (all documented): the kernel PDE is verified for `d = 1` (spatial part
  all `d`); the fractional symbols' covariance holds for `ξ > 0` (the `|ξ|^α` kink); `def:g-wedge`
  *minimality* and `thm:generation` are not yet modelled.

## Pointers

- `../blueprint/AXIOMS.md` — axiom provenance ledger.
- `../blueprint/DESIGN-symbol-calculus.md` — the truncated-calculus decision.
- `../blueprint/src/content.tex` — the shared spec; theorem statements are shared with the paper.
