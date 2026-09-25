# Roadmap — article-kit (the shared framework)

The backlog for the **shared framework**: the `linkage` checks and manifest, the scaffolding and the
session rules, the reusable CI, the shared agent, the skills and the process docs. Prioritised by
what raises the trustworthiness and publication-readiness of the articles it serves.

This file holds **open work only**. A delivered item is deleted in the commit that delivers it (git
and the commit message hold the history); a decision taken along the way goes to `adr/`. It is not
any one article's backlog (a theorem, a ledger entry or a proof belongs in that article's
`notes/HANDOFF.md`), nor the research backlog (the hub's `RESEARCH.md`). The test for an item: *would
a second article need it too?* Requests from other members arrive in [`WISHLIST.md`](WISHLIST.md)
and are triaged into this file.

The recurring design rule: **a deterministic core owns integrity, an LLM ceiling only flags**
(`linkage check` against the `draft-reviewer`; the drafting gate's deterministic boxes against its
judgement boxes).

---

## Now

### The process home (ADR-0001)

Steps 1, 2, 4 and 5 of [ADR-0001](adr/0001-article-kit-owns-the-article-process.md) are done
(`docs/PROCESS.md`, `docs/WRITING.md`, `docs/RELEASE.md`, the session rules, the templates, the
`shape` advisories; and `linkage release export|zenodo` and `linkage prose register`, parameterized
per module from `linkage.toml`, 2026-09-25). Open:

- **Step 3, the cleanup, beyond the pilot.** `hemigroup-causal-scale-space-kernels`,
  `hemigroup-kernels-ssvm` and `scale-space-foundations`: `linkage init --sync` for the rules; each
  `CLAUDE.md` to its article's standing rules; each `README.md` to one state section; finished
  prompts, plans and running records deleted or moved to `records/`; the general rules in their
  per-project memories moved into the rules and the memories deleted. `linkage shape` is the
  worklist. The hub's own `CLAUDE.md` (4,300 words) gets the same pass.
- **Step 6**, skills and agents as a plugin (`WISHLIST.md`).
- **Step 5's follow-through in the articles.** `spatial-hemigroup-scale-space` declares its three
  `[[modules]]` in `linkage.toml` and deletes its `scripts/export-release.py`,
  `zenodo-release.py`, `count-register.py` and `scripts/tests/` once a release has been rehearsed
  through `linkage release` (its own item; article-kit's copy is the one of record from
  2026-09-25).

### E-0003 — tag `v0.1.0` and repoint the `@main` references

Prepared (Q-0027): `CHANGELOG.md` has its `v0.1.0` section, `docs/RELEASE.md` states the bump
rhythm, and `linkage pins` fails on a call at `@main`. Open: the author tags the merge commit; then
Paper I and Paper V move their `uses:` and `linkage_ref` to `v0.1.0` and add `linkage pins` to their
CI (SSF's references wait, Q-0012); the pin is the last step of the item, and it is deleted with it.
Making `linkage_ref` required in `lean.yml` and `manifest.yml` (it defaults to `main`) waits until
every caller passes it.

---

## Next

### Boundary harness — the trust base as a regression test

`blueprint/trust-boundary.txt` with `linkage axioms --check` already fails CI on any axiom outside
the declared boundary. Still to add: `#print axioms` under `#guard_msgs` per headline theorem (which
theorem gained an axiom, not only that one did); positive probes (cheap should-hold consequences);
adversarial goals, known-false in-domain statements kept as isolated `sorry`s that must never become
provable; definition scrutiny (`unfold`/`#reduce` for terms sharing a name with a standard notion).

### Dropped context around shared statements

Shared statements are checked verbatim (`LINKAGE.md` rule 4). What the check cannot see is the
context the blueprint carries around a statement and the paper drops. The mechanical part: compare
each shared node's `\uses{}` set with the `\ref`s in the paper's proof of it, as an advisory. It would
have caught a reordering in Paper I that dropped three invocations while keeping the sentence that
promised them.

### Reviewer output contract — implement and adopt

[`docs/REVIEWER-CONTRACT.md`](docs/REVIEWER-CONTRACT.md) is drafted and not adopted. Needed: the
scope-and-hypothesis tags (`SCOPE`, `HYPOTHESIS`, `COUNT`, `NOTATION`, `TRANSCLUSION`, `FRONTIER`)
beside the prose-surface ones, a stable identity per underlying defect so pooled flags rank by the
number of independent discoveries, and the section-contract declaration. Then the aggregator.

### Inferred dependency closure

The declared side exists (check 8: no `\leanok` node reaches a `[T]` statement proved nowhere). Still
missing: infer each `\leanok` declaration's actual constant closure and diff it against the
blueprint's `\uses{}` both ways, flagging proved nodes with implausibly empty inferred uses and
lemmas that feed nothing. The fidelity review's `f7sweep.py` does the `\uses`-against-imports half by
hand. The authorship direction stays blueprint-first (LaTeX is the deliverable); the inference
machinery is adopted as audit only.

---

## Later — build on real need

- **Lean agent tooling.** `lean-lsp-mcp` is in use in the articles (scaffold it: `.mcp.json` in
  `linkage init`). Candidates: the Aristotle API as an escalation path for a stuck `sorry` (never a
  statement's author; read its terms on submitted mathematics first); type-dependency-cone review
  (the minimal set of declarations whose statements a human must vet).
- **Statement-faithfulness protocol.** Re-formalize the English claim from scratch and diff against
  the Lean, never "does this match?". Partly in the fidelity review's blind restatement; codify in
  `docs/REVIEW.md`.
- **Calibration corpus for the template.** 6–10 current JMIV papers through the librarian, to tune
  `PUBLICATION-TEMPLATE.md` § B's contracts to current norms.
- **Publication logistics** if a journal or arXiv submission is ever planned: arXiv's
  personal-endorsement path per category, a full English version, `sn-jnl.cls` only for a journal.
