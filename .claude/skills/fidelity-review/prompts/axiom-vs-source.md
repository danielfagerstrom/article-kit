# Prompt: axiom vs source (F6), one card per ledger axiom

Two steps. (1) `librarian` agent, `model: sonnet`: "Read-only retrieval, no filing. Source
citekey `<citekey>`. I need the **verbatim statement** of <Theorem/Prop/Def, printed page> —
retrieve the page as an **image** (`library page <citekey> --printed <p> --format image`), quote
exactly, confirm the printed page number from the running header, and quote any adjacent
sentence about <sub-probability vs probability / killing / normalisation>." (2) Then this
agent, `model: opus`, read-only:

---

Fidelity-review cards for the ledger axioms, READ-ONLY. Repo `<repo>`. Read
`blueprint/PLAN-fidelity-review.md` §1 (failure mode **F6**) and one finished card for tone.
These cards are the only place in the development where an outright inconsistency could enter,
so be exact; ~30–40 lines each.

Objects: the `axiom` declarations in `<Interfaces file>` — `<name>` (A<n>) … — with their
docstrings; the ledger entries `## A<n>` in `blueprint/AXIOMS.md`; `blueprint/trust-boundary.txt`.
Unfold `<the primitives the axioms are stated in>`.

The source, image-verified today: <verbatim quotes with page numbers from step (1)>. Also
relevant: <the representation theorem the source's class rests on, if any>.

For each axiom, write the card with these rows, each answered "axiom ≤ source" (the axiom asks
no more than the source gives), "axiom = source", or "axiom > source" (STOP and explain — a
finding of the highest severity):
1. **Objects.** The axiom's hypothesis class vs the source's (measure class, integrability
   condition — check any docstring argument translating one into the other, e.g. a concavity
   bound; verify the inequality; note atoms/edge cases the axiom's predicates allow).
2. **Killing / normalisation terms** the source allows and the axiom omits or fixes — a special
   case, safe direction? Are prose-level upgrades in the source (probability vs sub-probability)
   *proved* downstream rather than assumed?
3. **What is asked for.** The axiom's conclusion vs the source's (a slice of a semigroup? a
   single measure? the exact transform identity and its domain?). Are all side conditions the
   axiom uses in the conclusion (`IsCausal`, finiteness) actually in the conclusion?
4. **Uniqueness** — asked of the axiom, or proved separately? Confirm.
5. **Hypothesis bridge to the source's definition** (e.g. self-decomposability defined on
   measures vs an axiom about functions): does reading the axiom's hypothesis as the source's pass
   through *another* ledger entry's theorem? Record whether the anchors interlock even though the
   Lean axioms are independent.
6. **Conclusion vs the source's conclusion**: does the axiom conclude less (a possibly different
   drift, no right-continuity, no uniqueness of the density) — and does its sole consumer use only
   that? Read the consumer.
7. **Consistency sanity**: standard mathematics with the source's proof; hypothesis class
   non-empty (name the instance); mis-transcription found?
8. **Minimality**: is each axiom no stronger than its single consumer needs? Read the use.

Return the cards as Markdown (`### T1.4a A<n> …`), each ending with **Verdict** and a findings
line (empty if none). Terse, exact, file:line for Lean claims.
