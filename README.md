# article-kit

The shared framework behind the article repositories: **how an article is written** (the process,
the writing standard, the release discipline, the session rules every article session loads) and
**the machinery that checks it** (the blueprint ↔ Lean ↔ ledger ↔ paper linkage checks, the manifest
the wiki hub reads, the scaffolding a new article starts from, the reusable CI).

One repository per article (each publishes its own Zenodo DOI); this repository is the framework
they all consume, installed as a CLI the same way `library` and `wiki` are:

```bash
uv tool install --editable . --python 3.13
```

**Start here: [`docs/PROCESS.md`](docs/PROCESS.md)**, the article's life from the wiki to a release
and where every kind of text lives. The decision behind it is
[ADR-0001](adr/0001-article-kit-owns-the-article-process.md).

## Using it from an article repo

```bash
linkage init --slug <slug> --title "<title>"   # a new article: scaffolding, rules, templates
linkage init --sync                             # refresh the framework-owned files
linkage check                                   # every in-repo edge, plus drift and shape advisories
linkage check --wiki $WIKI_VAULT                # also the \notes{} edge to the hub
linkage paper                                   # the paper sources: refs, cite keys, pointers, front matter
linkage closure                                 # what each \leanok node's Lean decl cites, against its \uses{} (advisory)
linkage shape [DIR]                             # instruction files that hold records (no linkage.toml needed)
linkage manifest                                # write blueprint-manifest-<slug>.json for the hub
linkage demand                                  # unproved blueprint nodes the hub is asking for
linkage axioms --check                          # the trust boundary against the ledger
linkage boundary                                # per-theorem axiom pins, probes, adversarial goals, shadowed names
linkage pins                                    # fail if a workflow call or linkage_ref is at a branch, not a tag
linkage review <review>.jsonl …                 # pool the reviewers' flags by defect, rank by breadth
```

CI runs `linkage check --require-render --emit-manifest <path>`: `--require-render` makes a
manifest without transclusion fields a hard failure, so one can never reach the hub.

## What is here

| Path | What |
|---|---|
| `docs/PROCESS.md` | the phases, their gates, where each kind of text lives, how a session opens and closes |
| `docs/WRITING.md` | the writing standard and the use-of-AI rules (moved from the hub, 2026-09-21) |
| `docs/RELEASE.md` | the release rules, checklist and commands |
| `docs/LINKAGE.md` | the spec the checks enforce, the ledger's format |
| `docs/DRAFTING-GATE.md`, `docs/PUBLICATION-TEMPLATE.md`, `docs/REVIEWER-CONTRACT.md` | is a section ready to draft; the section contracts and exposition rubric; the reviewer's flag format |
| `docs/REVIEW.md`, `docs/CLOUD.md` | the interactive Lean review tour; cloud sessions |
| `docs/templates/` | the external review prompt; adopting the boundary harness (`boundary-harness.md`, with the pilot's worked example) |
| `scaffold/claude/rules/` | the **session rules**, framework-owned, copied into each article's `.claude/rules/article-kit/`: `core.md` at every session start, `writing.md`, `blueprint.md`, `ledger.md`, `lean.md` when a matching file is read |
| `scaffold/repo/` | the templates of a new article's `CLAUDE.md`, `README.md`, `CHANGELOG.md`, `notes/HANDOFF.md`, `adr/` and `records/` |
| `scaffold/blueprint/` | the LaTeX scaffolding: theorem environments, plasTeX config, the linkage macros, the render allowlist |
| `.github/workflows/` | reusable workflows (`workflow_call`) the article repos call |
| `.claude/agents/mathematician.md` | the shared sub-agent; the hub's `sync-agents.sh` installs it user-wide |
| `.claude/skills/fidelity-review/` | does the Lean prove what the article states, or something weaker or vacuous: the method, prompts, templates and `scripts/f7sweep.py`. Installed user-wide by a junction `~/.claude/skills/fidelity-review → <this dir>` |
| `.claude/skills/tighten/` | shorten a document to a page limit by measuring which paragraphs are cheapest to shorten. Installed the same way |
| `adr/` | framework-wide decisions |
| `ROADMAP.md`, `WISHLIST.md` | open work; requests and `process` lessons from the other members |

## The package

The stages are deliberately separable:

```
config.py      linkage.toml -> Config          (paths, slug, label shapes, pandoc pin)
parse_latex.py one blueprint dialect -> model  (the only LaTeX-aware module)
model.py       Node / LedgerEntry / PaperMarker / Blueprint — the IR
artifacts.py   Lean decls, the axiom ledger, paper markers, git provenance
checks.py      the fatal checks + advisories, over the IR alone
trust.py       the declared trust boundary, cross-checked against the ledger
boundary.py    the boundary harness: axiom pins, probes, adversarial goals, shadowed names
render.py      pinned-pandoc rendering for the transclusion fields
manifest.py    the projection the hub consumes
demand.py      `wiki demands --json` joined against live \leanok status
scaffold.py    `linkage init`, and drift detection for the framework-owned copies
shape.py       the instruction-file advisories (ADR-0001)
prose/         prose measurement over the paper sources
review.py      the reviewer output contract: pool flags by defect, rank by breadth
```

`checks.py` does not import `parse_latex`. That is the load-bearing rule: the checks, the manifest
and the hub channel are independent of how the blueprint is written, so supporting a second dialect
is a second parser rather than a rewrite, and the manifest schema is identical across articles.

## Conventions this framework assumes

- **`[T]` proved target / `[A]` analytic interface.** Every statement node declares one. `[A]` nodes
  are the trust boundary and must be grounded in a ledger entry with a page-anchored citation and the
  source's wording, and must declare what that citation carries and what it does not.
- **The blueprint is the source of truth.** The paper shares its statements; the wiki transcludes
  them. Neither paraphrases.
- **Descriptive, non-hyped naming**: results are named plainly.
