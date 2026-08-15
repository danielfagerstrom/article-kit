# Fidelity review: does the Lean prove what the article claims?

<Written <date>, at the point where the formalisation is closed to what Mathlib allows. Fill the
tier tables in §3 with this article's node labels; keep §1, §2, §4–§6 as they are unless the
article's layout differs. Template from article-kit's `fidelity-review` skill.>
## 1. The question, sharpened

The kernel has checked every proof. What it has not checked — what nothing mechanical can
check — is the *statement*: that the Lean proposition a `\lean{}` tag points at means what the
blueprint node says, which means what the draft's numbered theorem says. That correspondence
was written by hand, mostly by the same sessions that wrote the proofs, and a proof-writer's
statement drifts toward what is provable. So the review is a fidelity audit, and it has a small,
closed list of ways a proved theorem can fail to be the claimed one:

| failure mode | what it looks like | why it is silent |
|---|---|---|
| **F1 vacuous hypothesis** | a hypothesis (or a field of a structure) that nothing satisfies, or only trivial things | the theorem is true and useless; `lake build` cannot tell |
| **F2 junk-value conclusion** | a conclusion that holds because a partial function returned its default: `Bochner integral = 0` when non-integrable, `Real.sSup ∅ = 0`, `x / 0 = 0`, `ENNReal.toReal ⊤ = 0`, `Real.log` of a non-positive, `mellin` of a non-convergent integrand | the equation is provable, and it does not say the article's sentence |
| **F3 weakened conclusion** | the Lean concludes strictly less: an existence where the article says unique, a.e. where the article says pointwise, "for some `c`" where the article says "for every `c` in the range", `A g = h` where the article says `g ∈ dom A` and `A g = h`, `(b₀,k)` where the article says "`F` of the form (7.1)" | each clause reads right; the missing clause is not there to read |
| **F4 strengthened hypothesis / narrowed domain** | an extra measurability or integrability hypothesis, `Ioi 0` for `Ici 0`, a `≤` where the article has `<` (or the reverse), a hypothesis quantified over more than the article demands (all `c'` vs. one `c`), a structure field that is a *normalisation* the article does not impose | the theorem is a special case; whether the article's readers are in it is the question |
| **F5 definitional divergence** | the Lean object is not the article's object: an abscissa defined by `sSup`, a standing hypothesis, a locality predicate widened for a proof, an operator's normalisation, an object "constructed against the specification" | every theorem about the object is correct and about something else |
| **F6 interface fidelity** | a ledger axiom stated *stronger* than the cited source, or with a hypothesis the source has dropped | the only place an outright inconsistency can enter; everything downstream inherits it |
| **F7 proof-route divergence** | the blueprint proof cites Bernstein–Widder / Feller / a `\uses` edge; the Lean proves it another way (README already lists several: `prop:moments`, `thm:increments-bernstein`, chapter 9 Route B) | not a correctness issue; an *honesty* issue in the text of record and a `\uses`-graph issue |
| **F8 three-way drift** | draft (the article) ≠ blueprint (text of record, transcluded by the paper) ≠ Lean; the draft has Theorem 7.3 with "(χ, F) unique up to χ(1)=1", the blueprint has three nodes, the Lean has a bundle plus three halves | the paper transcludes the blueprint, so a blueprint that drifted from the draft *is* the published claim |

So: yes, the questions asked — did we prove the main statements or something weaker or
vacuous, are hypotheses too strong, are domains right, how faithful is the blueprint prose to
the Lean — are the right ones. They are F1–F5 and F7. Two are missing and are added above:
**F6**, because a mis-stated axiom is the one defect that makes *everything* suspect at once and
the ledger's page anchors were verified against the *source's* statement, not against the Lean
declaration's; and **F8**, because "the article's statements" live in `draft/` and the paper
reads them from the blueprint, so the audit is a three-column comparison, not two.

What is deliberately **not** on the list: re-verifying proofs (the kernel did that), style, and
whether the informal proofs are *complete* as mathematics (that is `draft-reviewer`'s job, and
independent of the Lean). F7 is the lowest priority of the eight — it changes exposition, not
what is true — and is done last.

## 2. Method: the fidelity card

Every audited node gets one card, and the review's output is the collection of cards plus a
findings ledger. A card is short and has a fixed shape, so that cards can be compared and so
that a fresh reader can check one in ten minutes:

```
### <node label>  ·  <draft numbering>  ·  <Lean declaration(s)>
Draft says:      <the statement, quoted or tightly paraphrased>
Blueprint says:  <ditto; note any difference from the draft>
Lean says:       <the statement with every project definition unfolded to Mathlib primitives —
                  what a reader who trusts Mathlib and nothing of ours has to accept>
Hypotheses:      <side-by-side; each Lean hypothesis classified: same / weaker / stronger /
                  absent-in-article / absent-in-Lean>
Conclusion:      <ditto; each Lean conjunct matched to an article clause; article clauses with
                  no Lean conjunct listed>
Junk-value audit:<every partial function in the statement and why its default cannot fire, or
                  which theorem rules it out>
Witness:         <a concrete F / family that satisfies every hypothesis at once — name of the
                  Lean `example` that says so>
Verdict:         faithful / faithful-with-note / weaker (say how) / stronger-hyp (say how) /
                  divergent-def (say how)
Actions:         <Lean strengthening, blueprint annotation, draft edit, or nothing>
```

Four techniques, in the order they are cheapest:

1. **Unfold to primitives.** For every definition in a headline statement, write out what it is
   in Mathlib terms (`#print`, and read the definiens). The Lean-says line is written from that,
   not from docstrings. Docstrings are the *claim*; the definiens is the fact. In particular:
   every transform (Bochner, or `lintegral` then `.toReal`?), every Mathlib `mellin`/`mellinInv`
   (junk `0` off convergence; check the normalisation against the article's display), every
   operator that is total-with-junk (the article's domain restriction must then reappear as a
   hypothesis of the theorems), every `ℝ≥0∞`-valued object (each `.toReal` downstream is an F2
   candidate), and every `Classical.choose`n object (its properties must flow only through a
   `_spec` lemma).
2. **Witnesses.** For each headline theorem, *named* Lean theorems instantiating *all* its
   hypotheses simultaneously at named models — the article's own examples, plus the simplest
   degenerate member of the class (in hcs: pure drift), and if possible one model that needs no
   interface axiom at all. A hypothesis no witness satisfies is F1 until shown otherwise; a
   witness that satisfies a hypothesis only under a restriction the article does not state is a
   domain finding. These go in `Formalization/<Lib>/Witnesses.lean` (sorry-guarded like the
   rest; nothing cites it) and are listed in the axiom guard so they cannot rot.
3. **Blind restatement.** A fresh agent that has *not* seen the Lean is given the draft
   statement — and only the draft — plus the ambient design facts (function space, measure type,
   which quantities are `ℝ≥0∞`) and asked to write the Lean statement it would expect, with a
   decision list. Diff against the actual one. This is the only technique that finds F3 — a
   missing conjunct is invisible when you read the conjuncts that are there.
4. **Adversarial vacuity.** A second fresh agent per Tier-1 node, prompted to *make the theorem
   trivial*: find a way the hypotheses are unsatisfiable, or a way the conclusion follows from a
   junk value without the mathematics. It reports either an attack or "no attack found, because
   ⟨named theorem⟩ rules it out". Cheap, and it is what F2 needs.

For F6, the technique is different: the librarian fetches the anchored pages as images, and the
card compares the *source's* hypotheses and conclusion clause by clause with the `axiom`
declaration — the direction of every inequality of strength must be "axiom ≤ source". Where
`AXIOMS.md` carries a hypothesis-translation argument, the card checks it rather than trusting it,
and it records whether two anchors interlock (one axiom's bridge to its source passing through the
other's theorem).

For F7/F8, the technique is a diff: for each Tier-1/2 node, the blueprint proof's cited
ingredients versus the Lean proof's actual imports and the `#print axioms` line; and the draft
statement versus the blueprint statement (the paper's `\input` of the blueprint node makes the
second the one that gets published).

## 3. Priority: what to audit, in order

Prioritised by (a) whether it is a headline claim of the article, (b) how much of the
development sits beneath it — an F5 in the axiom structure invalidates every card above it — and
(c) how much hand-written statement there is to get wrong. Definitions come *before* the theorems
that use them.

### Tier 0 — the definitions everything stands on (audit first, one card each)

| object | file | what to look at |
|---|---|---|
| <the axiom structure / primitive object> | | every clause against the article's definition; deliberate choices to *confirm*, not rediscover |
| <the admissible class / exponent structure> | | fields vs the article's conditions; normalisations that are not constraints; how "F ≢ 0" is rendered — and whether it is rendered twice |
| <transforms, `ℝ≥0∞`-valued objects, chosen objects> | | where each `.toReal` is protected; `Classical.choose` used only through `_spec` |
| <standing hypotheses, abscissae, strips> | | `sSup` in `ℝ≥0∞` not `ℝ`; strip bounds never through `.toReal` |
| <every operator definition> | | total or partial; normalisation vs the article's display; index conventions |
| <definitions shaped by proofs (locality-type)> | | widened or narrowed relative to the draft? |

### Tier 1 — the article's headline claims

1. <headline theorem 1> — its declaration and its halves; things noticed on first scan
2. <headline theorem 2>
3. <the supply chain beneath them>
4. <the ledger axioms, F6, with the librarian fetching the anchored pages>
5. <the corollaries the article advertises (recovering the prior theory, etc.)>

### Tier 2 — the "theorem content" the introduction promises

### Tier 3 — the rest (examples, refinements of `[A]` parents, the F7 sweep)

## 4. Deliverables

* `blueprint/REVIEW-fidelity.md` — the cards (Tier 0–2 in full; Tier 3 abbreviated) and a
  **findings ledger** at the top: one line per finding, tagged F1–F8, with severity
  (*claim-changing* / *statement-tightening* / *note-only*) and its resolution commit.
* `Formalization/<Lib>/Witnesses.lean` — the named witness theorems of §2(2), listed in the
  axiom guard.
* Fixes, each its own commit, in the direction the finding dictates: Lean strengthening (e.g.
  a round-trip corollary so that the analysis direction concludes in the type the construction
  starts from), blueprint statement or annotation edit (in the vocabulary the Lean can tag, per
  the article's CLAUDE.md), draft edit where the draft is
  the one that is loose. Every fix re-runs the full gate (`lake build`, the axiom guard to
  completion with exit code checked, `scripts/build-blueprint.sh`, `linkage check`).
* README/`PLAN-chapters-8-12.md`: no change unless a finding changes the status table.

## 5. Execution

Sequenced so that nothing is audited against a definition that has not itself been audited.

| phase | scope | how | rough size |
|---|---|---|---|
| **P0** | Tier 0 cards | integrator, by unfolding; one blind-restatement agent per definition group (draft only) | <n> cards |
| **P1** | Witnesses file | one `mathematician` agent: instantiate every hypothesis of each headline theorem at the article's models, the simplest degenerate member first | 1 file |
| **P2** | Tier 1 headline cards | for each: (a) the integrator's unfolded Lean-says line, (b) blind restatement by a fresh agent, (c) adversarial-vacuity pass by a second fresh agent, (d) merge; land the fixes | 2–3 cards, several fixes |
| **P3** | Tier 1 cards 3–5 (supply chain, the ledger axioms with librarian page fetch, the advertised corollaries) | as P2 but a single agent per card | ~12 cards |
| **P4** | Tier 2 | one agent per chapter | ~10 cards |
| **P5** | Tier 3, F7 sweep, F8 draft↔blueprint diff | `scripts/f7sweep.py` from the skill; one diff agent per chapter | 1 script + notes |
| **P6** | Findings ledger closed; every finding resolved or recorded as accepted-with-note; verdict, README, hub outline | integrator | — |

Rules of engagement, drawn from CLAUDE.md and from what this review is for:

* An agent auditing a statement **does not get to see its proof first**, and the blind
  restatement is written before the actual Lean statement is read. Order matters; it is the whole
  value of the technique.
* A finding is *not* fixed inside the card-writing pass. It goes to the ledger with a proposed
  direction (Lean up / blueprint down / draft edit), and the fix is a separate commit that names
  the finding. Statement-changing fixes to Tier 1 are confirmed with the author before landing;
  note-only ones are not.
* "Faithful" on a card requires a **witness** and a **junk-value audit** line; a card without
  both is not done.
* Any card that touches a `\lean` tag re-checks that the tag points at the declaration that
  proves *all* of the node's clauses (a bundle that assembles the halves is the usual cure) — not a sibling that
  proves the headline one.
* Commit and push after each card batch, explicit paths only.

## 6. What "done" looks like

Every Tier 0–2 node has a card with a verdict; every non-faithful verdict has a ledger entry
that is either resolved by a commit or explicitly accepted with the reason in the blueprint's
annotation of that node; `Witnesses.lean` shows the headline theorems' hypotheses are jointly
satisfiable at named models; and each headline theorem's Lean statement carries every clause the
article's statement does.
