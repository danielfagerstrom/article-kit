# Publication-structure template & voice rubric

The prose-conformance spec for the monograph: what a journal-grade mathematical-imaging paper
(JMIV-class) is expected to *contain and how it is structured* — checked separately from whether the
mathematics is correct.

**It is the downstream companion to [`DRAFTING-GATE.md`](DRAFTING-GATE.md).** The gate answers *"is this
section ready to be drafted as prose?"* (spine settled, statements exist, content grounded and mature).
This document answers the next question: *"does the drafted prose meet publication structure and voice?"*
The two never overlap — the gate is a readiness check on upstream artifacts; this is a conformance check
on the written text.

Origin: distilled from a 2026-07-17 brainstorm on AI-supported (author-side) journal review. That
conversation had no access to this repo, so a few things it proposes already exist here — the mapping
below says which, so the overlaps are explicit rather than duplicated.

## How this fits the constellation's floor/ceiling discipline

The whole setup separates a **deterministic core that owns integrity** from an **LLM ceiling that only
flags** (`wiki lint` vs the `note-evaluator`; the drafting gate's deterministic boxes vs its
prose-judgement boxes). This template is the same discipline extended to the paper:

| Layer here | What owns it | Status in the repo |
|---|---|---|
| §A Formatting (fixed) | adopt Springer `sn-jnl.cls`; preprint-first | logistics — see `README.md` publish step |
| §B *Det.* checks (deterministic structural lint) | a planned `scripts/check_paper.py`, sibling to `check_linkage.py` | **backlog** — `ROADMAP.md` |
| §B *LLM* + §C voice (adversarial-reviewer flags) | the hub's `/review-draft` skill (flags, never verdicts) | **backlog** — hub `Notes/ROADMAP.md` |
| Math correctness | Lean + the axiom-footprint **boundary harness** | `#print axioms` today; harness adoption in `ROADMAP.md` |

Correctness is never this template's job — it stays with Lean, `AXIOMS.md`, and the boundary harness.
The template checks *exposition and structure*, never proof validity.

---

*Target: preprint-first, but built to journal-grade (JMIV-class) quality. The
skeleton is a checklist against omissions, not a mould — structure follows the
argument. Three layers, kept separate because each is checked differently:*

1. **Publisher formatting** — fixed, adopt don't derive (§A).
2. **Structural skeleton** — section contracts (§B). This is the machine-checkable part.
3. **Expository voice** — the Utrecht-school qualities you're after (§C).

---

## §A. Formatting layer (fixed — just adopt)

Even for a preprint, aligning to the journal target now saves a reformat later.

- **Class:** Springer `sn-jnl.cls` (v3.1, Dec 2024; replaces legacy `svjour3`).
  For a math journal use `\documentclass[pdflatex,sn-mathphys-num]{sn-jnl}`
  (numbered refs) or `-ay` (author-year). Enable `[lineno]` for review copies.
  Submit as a single `.tex`, pre-compile the `.bbl`.
- **Abstract:** ~150–250 words.
- **Mandatory declarations** (easy to forget — the template won't force them):
  author contributions, competing interests, data availability, funding.
- **For arXiv:** no structure is *required*, but the skeleton below still applies;
  pick your primary category deliberately (e.g. `eess.IV`, `cs.CV`, `math.NA`),
  full English version required, plan the endorsement step.

---

## §B. Structural skeleton — section contracts

Each section lists **Contract** (what it must accomplish), **Det.** (deterministic
checks — cheap, reliable, CI-able), and **LLM** (adversarial-reviewer prompts —
flags, never verdicts). Rough proportions assume a theory-primary paper.

### 1. Title & Abstract  (~5%)
- **Contract:** name the object, the gap, the contribution, and the *kind* of
  result (theorem / construction / algorithm), parseable by a non-specialist
  mathematician.
- **Det.:** word count in range; abstract contains no undefined acronyms; the
  main contribution noun-phrase also appears in the introduction's contribution list.
- **LLM:** "Does the abstract state a *specific* contribution or only a topic?
  Could a reader tell what is *new* here versus prior work?"

### 2. Introduction  (~10–15%)
- **Contract:** (a) motivate from both sides — the imaging problem *and* the
  mathematical question; (b) state the gap/question precisely; (c) an explicit
  **Contributions** paragraph or list; (d) high-level positioning vs. prior work;
  (e) a roadmap sentence.
- **Det.:** an explicit contributions passage exists; a roadmap sentence exists;
  every later section is reachable from the roadmap.
- **LLM:** "Is the gap stated as a precise question or hand-waved? Is each listed
  contribution actually delivered by a later section (map each to its section)?
  Does the intro overclaim scope the theorems don't reach?"

### 3. Related work / Background  (~10%; may merge into §2)
- **Contract:** position against the literature *and* establish the mathematical
  setting the reader needs; make explicit what you take from where.
- **Det.:** every cited-as-foundational result has a resolvable reference (ties to
  your BibTeX/DOI lint); no "citation needed" gaps on load-bearing claims.
- **LLM:** "Is prior work *positioned* (how this differs) or merely *listed*?
  Any obvious neighbour missing?"

### 4. Preliminaries / Mathematical framework  (~10–15%)
- **Contract:** fix notation, definitions, standing assumptions, and cited results
  used as given. *This is where your axiom hygiene lives* — each imported result
  documented with its exact source and transcribed hypotheses.
- **Det.:** every symbol defined before first use; no symbol overloaded; each
  standing assumption labelled and referenced where invoked.
- **LLM:** "For each definition sharing a name with a standard notion, does it
  match the standard? Flag divergences. Is any assumption stronger than the result
  needs (state where each is actually used)?"

### 5. Main theory / Results  (~30–40%, the core)
- **Contract:** definition → motivation → theorem → proof (or sketch + appendix).
  Each formal object motivated *before* it's stated. Invariance/covariance
  principles made explicit (the scale-space DNA: which transformations the
  construction respects, and why that's the right demand).
- **Det.:** every theorem/lemma is either proved inline or has an appendix pointer;
  every numbered result is referenced somewhere later (else it's orphaned); no
  `\ref`/`\eqref` dangles.
- **LLM:** "Is each result interpreted, or stated and abandoned? Independently
  re-state each theorem in plain English and diff against the surrounding prose
  claim — flag mismatches in scope or hypotheses." *(Correctness stays with Lean +
  the boundary harness, not the LLM.)*

### 6. Algorithmic realization / discretization  *(optional, ~10%)*
- **Contract:** bridge continuous theory to computation; state the discretization
  and which continuous properties it preserves (and which it doesn't).
- **Det.:** every algorithm has stated inputs/outputs and complexity; parameters
  introduced here are defined.
- **LLM:** "Does the discretization *demonstrably* inherit the theory's key
  property, or is that only asserted?"

### 7. Experiments / numerical validation  *(optional, ~10–15%)*
- **Contract:** state which claim *each* experiment tests; report honestly;
  ensure reproducibility.
- **Det.:** data-availability statement present; code/data DOIs resolve; every
  figure/table referenced in text; each experiment maps to a claim.
- **LLM:** "Does any experiment test a claim the paper doesn't make (or vice
  versa)? Are negative/limiting cases shown or only favourable ones?"

### 8. Discussion  (~8%)
- **Contract:** interpret each main result, reconnect to the motivating problem,
  and state limitations *explicitly*; revisit prior-work relation now that results
  are in hand.
- **Det.:** a limitations passage exists; each §5 main result is mentioned here.
- **LLM:** "Are limitations concrete or performative? Is each main theorem's
  *significance* (not just its statement) discussed?"

### 9. Conclusion / outlook  (~3%)
- **Contract:** crisp restatement of the contribution + honest future directions.
- **Det.:** no *new* claims/results introduced here.
- **LLM:** "Does the conclusion restate the delivered contribution accurately, or
  drift beyond it?"

### 10. Back matter
- **Contract:** declarations, appendices (long proofs), references.
- **Det.:** all four declarations present; every appendix referenced; reference
  list style-consistent; `#`-of-citations-in-text ≈ reference-list length.

---

## §C. Voice rubric (Utrecht-school exposition)

Checked separately from structure — these are the qualities you admire in
Koenderink/Florack, made into review items. Study them for *voice*, not for
structural liberties (Koenderink's essayistic form is reputation-earned; don't
imitate the structure, imitate the clarity). Lindeberg is the living, rigorous,
JMIV-native heir to study for *both*.

- **Motivate before you formalize.** Every definition is preceded by *why this
  object* — what it captures geometrically or perceptually.
- **A picture per theorem.** Each major result comes with an intuition or
  geometric reading, before or after the formal statement.
- **Principles made explicit.** Invariance, covariance, causality, scale-selection
  — name the principle the construction serves and argue it's the right demand.
- **A worked limiting/special case** that grounds each abstraction.
- **Figures that explain, not just report.** At least some illustrate the concept,
  not only the output.
- **Prose carries the logic.** The argument is followable reading text alone;
  formulas are load-bearing, not decorative, and not the only connective tissue.
- **Honest about assumptions.** Where each bites, and what fails without it.

*LLM voice pass (flags only):* "Find definitions stated cold with no motivation;
theorems with no intuition; assumptions whose role is never explained."

---

## §D. Calibration exemplars (current, mostly open-access)

Read these for the *current* surface conventions (your instincts will be ~15 yrs
stale on form, not substance) and to calibrate the contracts above. Favour the
scale-space lineage closest to your taste.

- **Lindeberg — "Approximation properties … hybrid discretizations of Gaussian
  derivative operators"** (arXiv:2405.05095, 2024). The through-line to your
  Utrecht school: rigorous, definition-theorem discipline, continuous↔discrete
  bridging. Best single structural + voice model here.
- **Lindeberg — "Discrete approximations of Gaussian smoothing and Gaussian
  derivatives"** (JMIV 66(5):759–800, 2024). Long-form theory structure.
- **Bednarski & Lellmann — "Inverse Scale Space Iterations for Non-Convex
  Variational Problems"** (arXiv:2203.10865; JMIV 2023). Theory-with-illustration
  structure; clean contribution framing.
- **"Generalised Diffusion Probabilistic Scale-Spaces"** (JMIV 2024, open access).
  Modern theory-meets-ML positioning and related-work handling.
- **JMIV Special Issue "Variational Image Regularisation in the Era of Deep
  Learning"** (2025, open access) — skim several papers for the *current* accepted
  structure across a range of paper types.

*Method to derive your own template from these:* for each, extract the ordered
sections + each section's contract + rough proportions + where definitions/
theorems/figures land. Keep the invariants (present in nearly all) as your
template; treat variants as documented optional slots. Don't overfit to one author.

> **Not yet done — a `ROADMAP.md` backlog item.** The exemplars above are a starting
> reconstruction, not yet calibrated against a real corpus read through the librarian.
> Acquire 6–10 and tune the contracts/proportions to 2026 norms before relying on them.

---

## §E. How this plugs into the pipeline

- **Deterministic structural layer** (the §B *Det.* items): parseable from the
  `.tex` AST — declarations present, abstract length, orphaned results, dangling
  refs, contribution↔section map, experiment↔claim map. Reliable; fail the build.
  *(Home: a planned `scripts/check_paper.py`, the sibling to `check_linkage.py`.)*
- **LLM structural + voice layer** (the §B *LLM* and §C items): adversarial
  reviewer emitting located flags with severity — triage, don't gate.
  *(Home: the hub's `/review-draft` skill.)*
- **Math correctness** stays where it belongs: Lean + the boundary/falsification
  harness. The template checks *exposition and structure*, never proof validity.
