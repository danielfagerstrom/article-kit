---
paths:
  - "blueprint/AXIOMS*.md"
  - "blueprint/trust-boundary.txt"
  - "Formalization/**/Interfaces.lean"
---

# article-kit — the axiom ledger and the trust boundary

Framework-owned (`linkage init --sync`); do not edit here. The ledger's format and rules are
`../article-kit/docs/LINKAGE.md`.

- **An anchor is verified only when the source's statement is transcribed verbatim from the page
  image into the entry** (the formula, its hypotheses, the sentence it sits in), beside the
  "statement as used". A paraphrase alone is not a verification: one that dropped a slowly varying
  factor was printed, typed, reviewed and admitted as a false axiom (Paper V, ledger A10). Where the
  repository keeps the transcriptions in a companion (`blueprint/AXIOMS-verbatim.md`), a new or
  changed entry gets its transcription there in the same commit. `linkage axioms --check` fails an
  entry that grounds an admitted interface and has neither a `**Verbatim:**` block nor a same-id
  section in the companion (`paths.axioms_verbatim`); an unadmitted entry only gets an advisory.
- Page anchors and wordings are read by the `librarian` from a held copy, never from memory; OCR
  text renders `≤` as `<` and `α` as `ex`, so a range or an inequality is settled from the page
  image.
- An entry states what the citation carries and what it does not; every step the cited pages do
  not carry is listed at the head of `trust-boundary.txt`.
- **Admitting a name widens the trust base and is the author's decision.** An interface admitted
  after the fidelity review re-opens its card: it gets the interface pass against the page images
  before it is relied on.
- An axiom's hypothesis range matches its citation's range; when in doubt, narrow.
