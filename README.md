# article-kit

The shared machinery behind the article repos: the blueprint ↔ Lean ↔ ledger ↔ paper
linkage checks, the manifest the wiki hub reads, and the scaffolding a new article starts
from.

One repo per article (each publishes its own Zenodo DOI); this repo is the framework they
all consume, installed as a CLI the same way `library` and `wiki` are.

```bash
uv tool install --editable . --python 3.13
```

## Using it from an article repo

An article declares itself with a `linkage.toml` at its root — the satellite slug plus
where its artifacts live. Then, from anywhere inside the repo:

```bash
linkage check                    # every in-repo edge
linkage check --wiki $WIKI_VAULT # also the \notes{} edge to the hub
linkage manifest                 # write blueprint-manifest-<slug>.json for the hub
linkage demand                   # unproved blueprint nodes the hub is asking for
```

CI runs `linkage check --require-render --emit-manifest <path>`: `--require-render` makes a
manifest without transclusion fields a hard failure, so one can never reach the hub.

## What is here

| Path | What |
|---|---|
| `linkage/` | the Python package — see below |
| `scaffold/blueprint/` | the LaTeX scaffolding a new article copies: theorem envs, plasTeX config, the framework's linkage macros, the render allowlist |
| `.github/workflows/` | reusable workflows (`workflow_call`) that article repos call |
| `.claude/agents/mathematician.md` | the shared sub-agent; the hub's `sync-agents.sh` installs it from here (it expects `<repo>/.claude/agents/<name>.md`) |
| `.claude/skills/fidelity-review/` | the **fidelity review** skill: does the Lean prove what the article states, or something weaker or vacuous? The method (eight failure modes, tiering, the card), agent prompt templates (blind restatement, adversarial vacuity, axiom-vs-source, card pass, witnesses, draft↔blueprint diff), plan/review templates, and `scripts/f7sweep.py` (`\uses` edges vs Lean imports, read from `linkage.toml`). Install user-wide with a junction/symlink `~/.claude/skills/fidelity-review → <this dir>` so `/fidelity-review` is available in every article repo. First executed on hcs, 2026-08-15 |
| `docs/` | `LINKAGE.md` (the spec these checks enforce), the drafting gate, the publication template, the Lean review tour, the cloud setup guide |

## The package

The stages are deliberately separable:

```
config.py      linkage.toml -> Config          (paths, slug, label shapes, pandoc pin)
parse_latex.py one blueprint dialect -> model  (the only LaTeX-aware module)
model.py       Node / LedgerEntry / PaperMarker / Blueprint — the IR
artifacts.py   Lean decls, the axiom ledger, paper markers, git provenance
checks.py      the 8 fatal checks + advisories, over the IR alone
render.py      pinned-pandoc rendering for the transclusion fields
manifest.py    the projection the hub consumes
demand.py      `wiki demands --json` joined against live \leanok status
```

`checks.py` does not import `parse_latex`. That is the load-bearing rule: it means the
checks, the manifest and the hub channel are independent of how the blueprint is written,
so supporting a second dialect is a second parser rather than a rewrite. It also keeps the
manifest schema identical across articles, which is what lets the hub read every
satellite's manifest with one reader.

## Conventions this framework assumes

- **`[T]` proved-target / `[A]` analytic interface.** Every statement node declares one.
  `[A]` nodes are the trust boundary and must be grounded in a ledger entry with a
  page-anchored citation, and must declare what that citation carries and what it does not.
- **The blueprint is the source of truth.** The paper shares its statements; the wiki
  transcludes them. Neither paraphrases.
- **Descriptive, non-hyped naming** — results are named plainly.
