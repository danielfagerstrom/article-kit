# Changelog

One entry per release, headed `## <tag> — <date> — <title>`, saying what changed and why
([`docs/RELEASE.md`](docs/RELEASE.md), "Versioning the framework"). Work since the last release
accumulates under Unreleased. A tag is what the article repositories pin: the reusable workflows
(`docs.yml`, `lean.yml`, `manifest.yml`) at `@vX.Y.Z` and the `linkage_ref` input at the same tag.

## Unreleased

- `linkage axioms --check` requires the source's verbatim transcription (LINKAGE.md rule 5): an
  entry that grounds an admitted interface name and has neither a `**Verbatim:**` block nor a
  same-id section in the companion file is an error; an unadmitted entry gets an advisory. The
  companion is `paths.axioms_verbatim` in `linkage.toml`, default `blueprint/AXIOMS-verbatim.md`.

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
