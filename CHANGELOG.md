# Changelog

One entry per release, headed `## <tag> — <date> — <title>`, saying what changed and why
([`docs/RELEASE.md`](docs/RELEASE.md), "Versioning the framework"). Work since the last release
accumulates under Unreleased. A tag is what the article repositories pin: the reusable workflows
(`docs.yml`, `lean.yml`, `manifest.yml`) at `@vX.Y.Z` and the `linkage_ref` input at the same tag.

## Unreleased

- **article-kit is a Claude Code plugin** (ADR-0001 step 6, [`docs/PLUGIN.md`](docs/PLUGIN.md)):
  `.claude-plugin/plugin.json` ships the two shared skills and the `mathematician` agent, and
  `.claude-plugin/marketplace.json` publishes the plugin as the marketplace `article-kit`, which
  `scaffold/claude/settings.json` now declares (`extraKnownMarketplaces`) and enables
  (`enabledPlugins`) in every article scaffolded from it. The skills become
  `/article-kit:fidelity-review` and `/article-kit:tighten`. The manifest *points at* the files
  under `.claude/` rather than holding copies, so the framework's own sessions and every article
  session read one file (hub ADR-0008); `tests/test_plugin.py` fails on a component path that no
  longer exists and on a version that drifts from `pyproject.toml`'s. The hub-owned agents
  (`draft-reviewer`, `archivist`) and the librarian's are deliberately *not* in the plugin: they
  keep arriving through the hub's sync table and the scaffolded `SessionStart` hook, which is why
  that hook stays. Migration off the user-level junction and the synced `mathematician` copy —
  both of which outrank a plugin component — is `docs/PLUGIN.md` § Migration, and is the author's:
  it is under `~/.claude/` and in the hub.
- The release and register scripts are `linkage`'s (ADR-0001 step 5): `linkage release export`
  writes a module's verification export, `linkage release zenodo {reserve,upload,status,publish,
  discard}` deposits it through the Zenodo API with a reserved DOI, and `linkage prose register`
  prints the restraint-budget counts by zone. Every module-specific parameter — chapters, paper
  directory, tag, Lean roots, headline declaration, records directory, stem, title, export
  repository URL, keywords, related identifiers — is read from `linkage.toml`'s `[[modules]]`,
  with the creators, licence and copyright line in `[release]`. `docs/RELEASE.md` § "The commands"
  names these; `spatial-hemigroup-scale-space`'s `scripts/` held them before. Two new `[paths]`
  keys serve the export: `lean_libraries` (this tree's Lake libraries; inferred when absent) and
  `shared_namespaces` (the namespaces a shared package declares, where they differ from its name,
  as `ScaleSpaceCore` declares `ScaleSpace.*`; defaults to `lean_packages`).
- `linkage release export` carries the rule 6 gate: for a release after the module's own first
  tag, the date line must name that first release's version and date, and the version-history
  section must have an entry for the version exported; a first release is exempt from both.
- **`linkage paper`** — a deterministic lint over the paper sources themselves, sibling to
  `linkage check` and box 8 of [`docs/DRAFTING-GATE.md`](docs/DRAFTING-GATE.md). Fatal: a `\ref`
  naming no `\label`, a `\cite` key in no `.bib`, an item pointer past the target's item count
  (`Proposition~\ref{p}(3)` on a two-item statement), a hand-written `\tag{N.M}` carrying another
  section's number. Advisory: the four mandatory declarations, the abstract against
  `PUBLICATION-TEMPLATE.md` § A's 150–250 words, numbered results nothing refers to, cited entries
  with no DOI, and a bare `§`/`Thm.` with neither a citation nor a label nearby. The last three
  fatal checks are the pointer defects found by the blind reviews of Paper I, which no other check
  can see. Reads every directory `paths.paper` names; the declarations, the abstract and the `\tag`
  numbering need the main document (`\begin{document}`) and are skipped for a directory of section
  fragments.
- **The boundary harness — `linkage boundary`** ([`docs/LINKAGE.md`](docs/LINKAGE.md) rule 5), four
  checks the repository-wide axiom guard cannot do, because it reads the *union* of what the guard
  file prints: a `#guard_msgs`-pinned `#print axioms` per headline declaration (with the pinned
  axioms cross-checked against `trust-boundary.txt`, so a pin cannot be widened on its own say-so);
  a positive probe per headline result, `sorry`-free and not stated as `True`; adversarial goals
  kept as isolated `sorry`s and checked to stay `sorry`s; and a definition sharing its name with a
  standard notion. Source text only — no Lean, no toolchain. Opt-in per article through a
  `[boundary]` table in `linkage.toml`, and a no-op without one; `lean.yml` runs it as guard 3,
  with a new `boundary_strict_shadows` input.
- `linkage review <review>.jsonl …` — the aggregator of
  [`docs/REVIEWER-CONTRACT.md`](docs/REVIEWER-CONTRACT.md), which is no longer a draft. It validates
  the reviewers' records (anchor unique in its file, tag in the vocabulary and agreeing with its
  layer, a parseable `B.<n>` section-contract declaration, `refs` labels that resolve), pools flags
  from different reviewers about one defect under one key, proposes cross-section threads, and ranks
  both by the number of independent reviews that found them — severity is recorded and is only the
  last tiebreak. `--json` for the whole aggregate, `--top` to bound the worklist. Exit 1 on a
  malformed record. Adoption is the hub's step: `draft-reviewer` still emits prose, and what it has
  to change is listed at the end of the contract.

- `linkage check` prints a `[uses]` advisory per shared node whose paper proof never `\ref`s (or
  `\cref`s) some of the node's blueprint `\uses{}` targets. Advisory only; the exit code is
  unchanged ([`docs/LINKAGE.md`](docs/LINKAGE.md) rule 4).
- `linkage axioms --check` requires the source's verbatim transcription (LINKAGE.md rule 5): an
  entry that grounds an admitted interface name and has neither a `**Verbatim:**` block nor a
  same-id section in the companion file is an error; an unadmitted entry gets an advisory. The
  companion is `paths.axioms_verbatim` in `linkage.toml`, default `blueprint/AXIOMS-verbatim.md`.

- The scaffold seeds `.claude/sync-agents-hook.sh` and a second `SessionStart` hook for it: it finds
  the hub (`$WIKI_VAULT`, then `/workspace`, siblings, `~/dev`, `~/Documents/Notes`) and runs its
  `sync-agents.sh`, so shared agents such as `draft-reviewer` stay current from an article session.
  Silent when current; exits 0 always. Seeded once: an existing article copies the file and the
  hook entry by hand.

## v0.1.0 — 2026-09-21 — the first pinned release

The framework as it stands after the process home (ADR-0001) and its own test suite and CI. Before
this tag nothing was versioned: `hemigroup-causal-scale-space-kernels`,
`spatial-hemigroup-scale-space` and `scale-space-foundations` called the workflows at `@main`.

**The `linkage` package** (`linkage --help`; a CLI installed with `uv tool install`):

- `linkage check` — every in-repo edge between blueprint, Lean, ledger and paper: `\lean{}` names
  (also those of a shared Lake package), ledger references and `[A]` assignments, paper
  shared-statement markers checked verbatim against the blueprint (optionally pinned by sha, and
  `--strict-shared` to fail on drift), the dependency closure (no proved node may rest on a
  statement proved nowhere), `\leanok` on statements and proofs and the agreement of the two graph
  flags, stray control characters, the render allowlist, scaffold drift; several paper directories
  in one repository. Exit codes 0 (holds), 1 (a defect), 2 (the tooling could not answer).
- `linkage manifest` / `check --emit-manifest --require-render` — the blueprint manifest the wiki
  hub reads (manifest v2: per-label statement text and sha, `\uses` edges, transclusion fields
  rendered by the pinned pandoc, ledger projection, freshness stamp).
- `linkage demand` — the unproved nodes the hub is asking for.
- `linkage axioms --check` — the trust boundary against the ledger; `linkage packages` — shared
  Lake packages.
- `linkage prose extract|baseline|stats` — prose measurement over the paper sources against two
  baselines.
- `linkage shape` — advisories on instruction files that hold records (ADR-0001).
- `linkage init [--sync]` — scaffolds a new article (`linkage.toml`, the LaTeX and plasTeX
  scaffolding, the templates of `CLAUDE.md`, `README.md`, `CHANGELOG.md`, `HANDOFF.md`) and
  refreshes the framework-owned files.
- `linkage pins` — fails when an article repository calls an article-kit workflow, or passes
  `linkage_ref`, at a branch instead of a release. New in this release; the check that keeps the
  pins from drifting back to `@main`.

**The process** (`docs/`): the phases and gates (`PROCESS.md`), the writing standard and use-of-AI
rules (`WRITING.md`), the release rules and checklist (`RELEASE.md`), the linkage spec
(`LINKAGE.md`), the drafting gate, publication template and reviewer contract, the interactive
Lean review tour, cloud sessions; `adr/` holds the framework-wide decisions.

**The session rules and agents** (`scaffold/claude/rules/`, `.claude/`): `core`, `writing`,
`blueprint`, `ledger` and `lean` rules copied into each article by `init --sync`; the
`mathematician` agent; the `fidelity-review` and `tighten` skills.

**The reusable workflows** (`.github/workflows/`, `workflow_call`): `docs.yml` builds the paper and
blueprint PDFs and the dependency-graph view and publishes to the one research site (inputs
`source_ref` and `channel`, `extra_papers` for further papers of a multi-module repository);
`lean.yml` builds the Lean library with a Mathlib cache and authenticated fetch of private
dependencies; `manifest.yml` runs `linkage check` and projects the manifest to the hub. The
framework's own `ci.yml` runs ruff, the pytest suite, the entry point and a scaffolded article.

**Known limits.** `linkage_ref` still defaults to `main` in `lean.yml` and `manifest.yml`; a caller
must pass it (`linkage pins` enforces that). SSF's references are not pinned in this release
(Q-0012: they wait).
