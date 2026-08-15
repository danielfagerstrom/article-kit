# Prompt: F8 sweep — draft ↔ blueprint statements

Spawn with `model: sonnet`, `run_in_background: true`; it may fan out one child per chapter (the
children inherit sonnet). Read-only. Requires the `% draft: Lemma X.Y` provenance convention on
blueprint nodes; additive nodes should carry `% additive: not in the draft`.

---

F8 sweep for a fidelity audit, READ-ONLY (no edits). Repo `<repo>`. Failure mode F8
(`blueprint/PLAN-fidelity-review.md` §1): the *draft* (`<draft file>`, the article's working
text, numbered Definition/Lemma/Proposition/Theorem/Corollary X.Y) and the *blueprint*
(`blueprint/src/parts/*.tex`, the text of record; each node has a `% draft: Lemma X.Y` comment
giving its origin, and the paper transcludes the blueprint) may have drifted in their
**statements**. Findings already known and fixed: <list>.

Task: for every blueprint node in chapters <range> that has a `% draft:` provenance comment (or
an obvious draft counterpart by title/number), compare the **statement text only** (not proofs,
not annotations, not `\statusT` paragraphs) with the draft's statement, and report every place
where they differ *mathematically*: a hypothesis present in one and not the other, a different
quantifier or range (`<` vs `≤`, "for some" vs "for all", strip bounds), a different conclusion,
a clause dropped or added, a different normalisation. Ignore pure rewording, notation macros, and
the blueprint's deliberate splitting of one draft item into several nodes (report the split only
if the parts do not add up to the draft's statement). Also list draft numbered items that have NO
blueprint node at all, and blueprint statement nodes with no draft origin.

Return a table: `node | draft item | difference (one line, precise) | direction (draft stronger /
blueprint stronger / different / equivalent-rewording)`, listing only nodes with a genuine
difference, then the two lists. Say explicitly for each chapter "no differences" if so. Terse; no
proof or annotation commentary.
