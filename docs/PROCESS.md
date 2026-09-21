# The article process

How an article goes from an idea in the wiki hub to a released module, and where every kind of text
lives on the way. This is the map; each phase names the document or skill that runs it. The
decision behind this file is [ADR-0001](../adr/0001-article-kit-owns-the-article-process.md).

An article session does not need to be told any of this: the session rules that `linkage init`
copies into `.claude/rules/article-kit/` load it, and point here.

## Where each kind of text lives

This holds in every repository, the hub's included (hub ADR-0014 is the same table for wiki pages).

| kind of text | home | never in |
|---|---|---|
| **standing rules** of this article (notation, reference policy, a scope decision in force) | the repo's `CLAUDE.md`, short, present tense | — |
| **general rules** (any article would need them) | article-kit: `docs/`, the rules in `scaffold/claude/rules/` | a repo's `CLAUDE.md` or a per-project memory |
| **state**: where the module stands, in numbers that are true today | `README.md`, one short section, rewritten when it changes | `CLAUDE.md` |
| **next session**: what to read, what is open, what waits on the author | `notes/HANDOFF.md`, *replaced* at each session close | anywhere else |
| **history**: what happened when | git and `CHANGELOG.md` | `CLAUDE.md`, `README.md`, the handoff |
| **decisions**: what was decided and why | `adr/`, one file each, append-only; one line on the hub's thread page | the handoff, beyond a pointer |
| **records**: review archives, response plans, process accounts, audits, fix lists | `records/<module>/`, written once, never read as instructions | `notes/` |
| **knowledge**: mathematics learned on the way | the hub's concept note that owns it | the repo |
| **general lessons** | article-kit's `WISHLIST.md`, a `process` item | a lessons file in the repo |

Three consequences, checked by `linkage check`'s `shape` advisories: a `CLAUDE.md`, `README.md` or
handoff carries no dated record blocks and no heading that names a record (Status, History,
Progress); each stays under its word budget; and a finished session prompt is deleted, not kept.
When a file drifts from its purpose, it is rewritten to it; git holds the old text.

## The phases

Each phase lists its entry condition, what runs it, and what it leaves.

### 0. Idea development — in the hub

The idea is developed in the wiki (`$WIKI_VAULT`): a thread page, concept notes, sources through the
librarian. **Leaves** enough material for a draft, and the decision to start a repository.

### 1. A new article repository

Run from the hub or anywhere, once:

1. `gh repo create danielfagerstrom/<slug-name> --private`, clone to `C:\Users\danie\dev\<repo>`.
2. `linkage init --slug <slug> --title "<title>"`: the blueprint scaffolding, `linkage.toml`, the
   session rules, `CLAUDE.md`, `README.md`, `CHANGELOG.md`, `notes/HANDOFF.md`, `adr/README.md`,
   `.claude/settings.json` and `cloud-setup.sh`.
3. Fill `CLAUDE.md`'s header (what the article is, where it sits) and nothing else yet.
4. The Lean project, when the blueprint has its first nodes: `Formalization/` with a
   `lakefile.toml` that pins `scale-space-lean` at a tag; link the shared package store
   (`python $WIKI_VAULT/lake-store.py link <repo>`); `.mcp.json` for `lean-lsp-mcp`
   (`uvx lean-lsp-mcp --lean-project-path Formalization`).
5. CI: the reusable workflows of `.github/workflows/` (`docs.yml`, `manifest.yml`); cloud sessions:
   [`CLOUD.md`](CLOUD.md).
6. The hub: the module in `constellation.json`, its thread page, one `wiki/log.md` line.

### 2. The draft — `draft/<name>.md`

Written section by section in dialog with the author, from the wiki's notes. Statements numbered;
borrowed facts marked with their sources. **Leaves** a complete draft. **The draft is frozen at the
module's first release**: from then on the blueprint is the only text of record, and no "draft
mirror owed" note is written.

### 3. The blueprint — `blueprint/`

Written *from* the draft, node by node: every statement `[T]` (proved target) or `[A]` (analytic
interface), `% draft:` provenance on each node, proofs as publication-quality mathematics.
The axiom ledger `blueprint/AXIOMS.md` grounds every `[A]` node in a page-anchored citation read
from a held copy by the librarian, **with the source's wording transcribed verbatim from the page
image beside the paraphrase**; an anchor without the transcription is not verified. Spec:
[`LINKAGE.md`](LINKAGE.md). **Gate**: `linkage check` clean.

### 4. The statement skeleton — `Formalization/Skeleton/`

Every node's statement is typed in Lean with `sorry` before any proof is attempted; the node is
tagged `\lean{…}\notready`. The statements are then reviewed as a batch: faithfulness to the
blueprint, domain hypotheses, satisfiability by the named instances. The author approves the
decomposition before proving starts. **Leaves** a reviewed skeleton; a node may use a `sorry`'d
upstream node only if it is typed and reviewed.

### 5. Proving waves

Proofs proceed leaf-first along the dependency graph, each by a `mathematician` agent in its own
worktree. **One Lean-building agent at a time** on this machine (two ran it out of memory). Every
merge is gated by `lake build`, the axiom guard run to completion with its exit code checked, and
`linkage check`. A proved declaration moves out of `Skeleton/` and its node goes `\leanok`. When a
Lean proof takes another route than the printed one, the blueprint proof is rewritten to the checked
route. Statement changes in the safe direction (narrowing, splitting, restating an interface at its
source's letter) carry a `% CHANGED` marker and a ledger row; a widening waits for the author.

### 6. The fidelity review

Does the Lean prove what the article states, or something weaker, vacuous or junk-valued? The
`fidelity-review` skill (`.claude/skills/fidelity-review/`). Run when the formalization phase
closes, and again for every interface admitted after it: admitting a name re-opens its card.
**Leaves** `blueprint/REVIEW-fidelity.md` with its verdict and the fixes landed.

### 7. The article — `paper/`

Before a section is written, the drafting gate: [`DRAFTING-GATE.md`](DRAFTING-GATE.md)
(`wiki gate --slot … --worklist` from the hub). Then, per section: one `.tex` file; statements
transcribed verbatim under `% shared with blueprint` markers (`linkage check` reports each
`verbatim`); the proofs of record; the ledger's page anchors printed before the `[A]` nodes; the
trust base in one subsection (§ 1.1) with the headline `#print axioms` block. The writing standard is
[`WRITING.md`](WRITING.md), the section contracts and the exposition rubric
[`PUBLICATION-TEMPLATE.md`](PUBLICATION-TEMPLATE.md). A module that follows another restates what it
uses of it. Changes the paper forces on shared text are made in the blueprint and re-transcribed
(the article mirror).

### 8. The passes

In this order, each on the text as it then stands:

1. **Readability**, against `PUBLICATION-TEMPLATE.md` § B and § C: each section opens with its aim,
   terms at first use, figures where an object needs to be seen.
2. **Register**, blind: one fresh `draft-reviewer` agent (opus) per section, flags only
   ([`REVIEWER-CONTRACT.md`](REVIEWER-CONTRACT.md)); triage per tag; fixes at exact anchors. The
   counts by zone (prose, shared statements, proofs) are the register script's.
3. **Scope audit**: restate every claim of the abstract, the introduction and the conclusion from
   its statement and compare. Every such pass so far has found a dropped hypothesis.
4. **Length**, only where there is a page limit: the `tighten` skill.
5. **The AI statement**, from the session archive through the `archivist` (sonnet), on the rules of
   `WRITING.md` § 6; numbers re-derived, never restated.
6. **The author's section-by-section review.** The session applies the comments; a comment that
   states a general rule goes to the wishlist the same day.
7. **Citation audit**: every page-anchored citation in the prose read against the held copy, late,
   by an agent that did not write the sentence.

### 9. External review

A build is frozen at a named revision; the author runs the review prompt in other systems, the
first round in another vendor's system, and saves each output verbatim into
`records/<module>/reviews/` with the system in the filename. The prompt's template is
[`templates/external-review-prompt.md`](templates/external-review-prompt.md). Every finding is
verified against the text, the blueprint and the sources before anything is changed; the response
plan (`records/<module>/PLAN-review-response.md`, `-round<N>` for later rounds) sorts them into decisions for the author and
batches of work. A change to the paper after a build is frozen means a new freeze.

### 10. Release

[`RELEASE.md`](RELEASE.md): the rules, the checklist, and the order of the commands (the DOI
reserved first, the first page checked by the scripts, the verification export where the repository
stays private).

### 11. After the release

The librarian's deposit and its report of uncited holdings; the postdoc round (hub); the restored
draft date line; the general lessons filed to article-kit's `WISHLIST.md`; the records of the module
under `records/<module>/`; `notes/HANDOFF.md` rewritten for the next module.

## Opening and closing a session

**Open**: read `notes/HANDOFF.md`, then what it names. The rules in `.claude/rules/article-kit/`
are already loaded. `git status` first after any crash.

**Close**, in this order:

1. `CHANGELOG.md` under Unreleased: what changed and why, statements renumbered or withdrawn.
2. A decision taken: one file in `adr/`, and its line on the hub's thread page.
3. `README.md`'s state section, if the state changed: rewritten, not appended to.
4. `notes/HANDOFF.md`: rewritten for the next session. It says what to read, what is open and
   what waits on the author, as of now. It does not say what this session did.
5. A general lesson: a `process` item in article-kit's `WISHLIST.md`.
6. The hub: pull, the pin in `constellation.json`, one `wiki/log.md` line, `wiki lint`, commit, push.

## Agents, skills and models

| who | for | model |
|---|---|---|
| `mathematician` (article-kit) | blueprint nodes, Lean, the ledger | opus; fable for a node that resisted opus |
| `librarian` (library repo) | every source, every page anchor; dispatch is pre-authorized | sonnet |
| `draft-reviewer` (hub) | blind review of one section's prose | opus |
| `archivist` (hub) | the process record, the AI statement's numbers | sonnet |
| `fidelity-review` skill | phase 6 | opus reviewers |
| `tighten` skill | page limits | — |

Every `Agent` call sets `model`. Mechanical days run on opus, days that prove or draft new
mathematics on fable (the rubric: `~/.claude/CLAUDE.md`).
