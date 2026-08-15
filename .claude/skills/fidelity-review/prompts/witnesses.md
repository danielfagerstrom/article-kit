# Prompt: Witnesses.lean (P1)

Spawn the `mathematician` agent with `model: opus`, `run_in_background: true`.

---

Repo `<repo>`. Read CLAUDE.md first, then `blueprint/PLAN-fidelity-review.md` §2 item 2 and §5 row
P1 — this task is P1 of that plan.

Goal: create `Formalization/<Lib>/Witnesses.lean` — a file of *named* theorems (not `example`s,
so the axiom guard can `#print axioms` them) showing that the hypotheses of the headline theorems
are **jointly satisfiable at concrete models**. A hypothesis no model satisfies is a vacuity
finding; a hypothesis a model satisfies only under an extra restriction (e.g. a parameter range
the article does not mention) is a domain finding. Both are the point of the file. Nothing in the
development may import this file.

Targets (the hypotheses to instantiate; read the declarations first):
- `<headline theorem 1>` in `<file>`: <its hypotheses, and how to witness each conjunct's
  hypotheses — e.g. the (⇒) direction needs a structure instance: witness it with the constructed
  family; uniqueness needs a `χ`: witness `χ = id`>.
- `<headline theorem 2>`: <hypotheses; note any *signal*-type hypothesis and the trap that a
  naive choice violates one clause (in hcs: the primitive of an indicator is not integrable —
  choose `g` with `∫ g = 0`)>.
- <corollaries and classification lemmas>.

Models, in order of expected difficulty — do the first fully before the others:
1. **<the simplest degenerate member of the class>** (in hcs: pure drift `b₀ > 0, k = 0`, whose
   kernels are point masses, so every hypothesis is checkable by hand). Build it as an instance if
   none exists. This is the model that should discharge every hypothesis of every target.
2. **<the article's main example>** (a Mathlib-identified law if possible): the standing
   hypothesis for the parameter range the article names — record precisely which range each
   target admits.
3. **<a further example>**: at least the cheap hypotheses; the expensive one if cheap.
Also, if reachable in Lean core: a model of the *hypothesis class of the analysis direction*
that does not go through the constructed kernels (in hcs: the pure-delay core `Φ x y = τ_{y−x}`),
so that nonemptiness is certified independently of any interface axiom.

Deliverables:
- `Formalization/<Lib>/Witnesses.lean`, sorry-free, with a module docstring listing per target and
  per model which hypotheses are discharged and which are not (and why), and each theorem named
  `witness_<target>_<model>`.
- `import <Lib>.Witnesses` in `Formalization/<Lib>.lean` and `#print axioms` lines for each witness
  in the axiom guard under a `/-! ### Witnesses (PLAN-fidelity-review P1) -/` header.
- `lake build` clean, and the axiom guard run to completion with exit code 0 (check the code, not
  the tail).
- Do NOT commit; do not stage. Do not touch `blueprint/`. Report: what was proved, what could not
  be and why, and any *finding* about the hypotheses (hard to satisfy, or satisfiable only under
  a restriction the article does not mention). Keep it factual and short. If a step is genuinely
  out of reach, leave a docstring note rather than a `sorry` — the file must stay sorry-free.
