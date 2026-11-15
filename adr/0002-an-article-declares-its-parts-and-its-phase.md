# ADR-0002 — An article declares its parts and its phase, and the checks, CI and the site follow

- **Status:** Accepted 2026-11-15
- **Mechanism:** the `[article]` table of `linkage.toml` (`linkage/config.py`); the commands
  `linkage parts` and `linkage phase` and the phase checks of `linkage check` (`linkage/article.py`,
  `linkage/cli.py`); the anonymity scan (`linkage/anonymity.py`); in the reusable workflows, which
  read the declaration themselves, a draft build and a deploy no longer gated on the paper
  (`docs.yml`) and the declaration's projection (`manifest.yml`), with the seeded caller
  `.github/workflows/article.yml` for a new repository; [`docs/PROCESS.md`](../docs/PROCESS.md)
  § 1 and the phase headings, [`docs/LINKAGE.md`](../docs/LINKAGE.md), "Parts and phase". Outside
  article-kit: the hub's `constellation.json` and `wiki lint`, and the research site's
  `scripts/build-routes.mjs`.

## Context

[`PROCESS.md`](../docs/PROCESS.md) describes one path: a draft (§ 2), a blueprint built from it
(§ 3), the statement skeleton and the proving waves (§§ 4–5), the fidelity review (§ 6), and only
then the article (§§ 7–10). The tooling assumes the end of that path from the first day. Every
`linkage` command reads the blueprint, the ledger, the Lean tree and the paper. `docs.yml` deploys
only when the paper builds. `manifest.yml` needs a blueprint. Two kinds of repository fall outside
that assumption.

1. **A repository early in the process.** `spatial-hemigroup-pyramids` had a draft and notes and
   nothing else for its first six weeks. Its area on the research site (`/drafts/<slug>/`) needed
   hand work in three places.
   - The hub manifest got a `site` block with `draft.source`. The routing table followed from that.
   - A placeholder page went up by hand.
   - The repository got its own `.github/workflows/docs.yml`. It renders `draft/*.md` with pandoc
     and pushes to the site's bucket, with the site slug hard-coded in the workflow. It exists
     because the reusable `docs.yml` has no input for a markdown draft and deploys nothing without a
     paper. It was later rewritten into a landing page for the draft, the blueprint PDF, the web
     blueprint and the notes, copying `docs.yml`'s Tectonic and plasTeX steps and pins "in
     lockstep". Its header says it gives way to the reusable workflow once `paper/` exists.

   Every new repository would repeat this.
2. **A repository that will never have some parts.** One example is a paper-only conference
   version of a long paper, private and anonymous until well after submission. Its statements are
   the long paper's, and the long paper's repository carries the blueprint and the Lean. Its
   `linkage.toml` leaves the blueprint and Lean paths out, and a comment explains why. `linkage
   check` still filled in the default paths and exited 2 because they did not exist. Its CI is a
   hand-written workflow with its own anonymity guard. Its check of statements against the long
   paper's blueprint is a script of its own.

The narrow fix (article-kit#92) treats a part whose path `linkage.toml` leaves out, and which is
not at its default path, as absent rather than missing. That makes `linkage check` pass in both
repositories. But absence is still inferred from the tree. Nothing tells a repository that has no
blueprint *yet* from one that will never have one. Nothing says how far along a repository is.
Nothing says that a repository must not appear on the site at all. So the CI, the hub and the site
are still configured by hand, and each new repository is configured again.

## Decision

**Each article repository declares, in `linkage.toml`, the parts it has or will have, the phase it
is in, and whether it is anonymous. The checks, the CI, the hub and the site read that declaration.
None of them is configured per repository by hand.**

### 1. The declaration

```toml
[article]
parts     = ["draft", "blueprint", "lean", "paper"]   # the parts this repository will ever have
phase     = "proving"                                # where it stands, PROCESS.md's vocabulary
anonymous = false                                    # true: under double-blind review
site      = "hemigroup-image-pyramids"               # the site slug; absent: not on the site
cites     = []                                       # ["<slug>@<tag>"]: whose blueprint it states from
```

**Parts.** There are four: `draft` (`draft/`, PROCESS.md § 2), `blueprint` (`blueprint/`, § 3),
`lean` (`paths.lean`, §§ 4–5) and `paper` (`paths.paper`, § 7). `parts` lists the parts the
repository will have when it is complete, not the ones it has today. A part not listed is **never
part of this repository**. Its checks, its scaffold files and its CI job do not exist for it, and a
directory of that name that appears anyway is an error, since it would be read by nothing.

**Phase.** One of these values, each named after the PROCESS.md section it stands for:

| `phase` | PROCESS.md | the parts that must exist, of those listed |
|---|---|---|
| `draft` | § 2 The draft | `draft` |
| `blueprint` | § 3 The blueprint | + `blueprint` |
| `skeleton` | § 4 The statement skeleton | + `lean` |
| `proving` | § 5 Proving waves | the same |
| `fidelity` | § 6 The fidelity review | the same |
| `article` | § 7 The article | + `paper` |
| `passes` | § 8 The passes | the same |
| `external-review` | § 9 External review | the same |
| `released` | §§ 10–11 | the same, and a released module tag |

Phases 0 and 1 happen before `linkage.toml` exists, so a new repository starts at `draft`. A part
that is not listed is skipped in the right-hand column. A paper-only repository has
`parts = ["paper"]` and goes from `article` to `released`. A repository that publishes several
modules (a line paper and its modules) writes `phase` on each `[[modules]]` table instead. The
repository then needs the parts that its most advanced module needs. A part may exist
before its phase requires it. A blueprint started during the draft is normal.

**Anonymous.** `anonymous = true` means the work is under double-blind review. Nothing about it
leaves the repository except to the private hub. It has no site area, and no deploy step runs even
if a caller workflow asks for one. `linkage check` scans its paper for identifying text. The
patterns are the creators' names and the repository's own `identity` list, both read from its
private `linkage.toml`, so the public framework never carries them. Anonymity is set
and cleared by hand, with the review timetable. Repository **visibility** stays where it is, in the
hub's `constellation.json`, because it is a GitHub setting and the hub audits it. The only rule
connecting the two is that an anonymous repository is private.

**Site.** `site` is the slug of the repository's area on the research site, the value its
`docs.yml` caller hard-codes today. It is absent for a repository that is not on the site, and an
anonymous repository may not set it. A repository with several site entries (one per module) gives
it per `[[modules]]` table.

**Cites.** `cites` names the articles, each at a release tag, whose blueprint this repository's
statements are taken from. This is the declared form of "the statements are the long paper's".
Accepting this ADR only records it. Checking a `% shared with blueprint <slug>:<label>` marker
against the cited article's manifest at that tag (in the hub, `blueprint-manifest-<slug>.json`) is
a later step. That step generalises the conference version's own statement-ledger script.

### 2. How the tooling treats a part

- **`linkage check`.** The checks of a part that is not listed are skipped. The checks of a part
  that is listed but not yet required (the Lean tree at the `blueprint` phase) run on what exists.
  An empty Lean tree is not an error before `skeleton`. A part that the phase requires and that is
  missing is fatal, and the message names the phase and the PROCESS.md section. The check
  introduced in article-kit#92 stays as the fallback. A repository without an `[article]` table is
  read as today, absence inferred from the tree, with one advisory asking it to declare.
- **`linkage init`** writes the `[article]` table at `phase = "draft"` and the `draft/` directory,
  besides what it writes today. **`linkage init --sync`** writes the framework files of the listed
  parts that exist, so a paper-only repository never gets `blueprint/`'s build files.
- **The CI.** Each reusable workflow runs `linkage parts --json` in the repository it checked out.
  That prints the declaration and which parts exist, and the workflow does only what the output
  allows. An existing caller therefore needs only its pin moved. `linkage init` seeds
  `.github/workflows/article.yml`, one caller of all three, for a new repository.
  - `docs.yml` builds whatever exists: the draft (pandoc, a new `draft` input, the step pyramids
    wrote), the blueprint PDF and web blueprint, the paper. It writes a landing page listing what
    it built, and deploys when at least one of them built, no longer only when the paper did. It
    refuses to deploy when the declaration is anonymous.
  - `manifest.yml` always runs. It writes the declaration's projection into the hub (§ 3), and
    writes `blueprint-manifest-<slug>.json` only when there is a blueprint.
  - `lean.yml` runs once `lean` is listed and the phase is `skeleton` or later.

  A repository's own extra steps, such as a page-limit gate or a statement ledger, stay in a
  workflow of its own beside `article.yml`.
- **The hub manifest.** `manifest.yml` writes `article-<slug>.json` to the hub beside the blueprint
  manifests. It contains the declaration, the parts that exist and the source commit. This is the
  hub's only copy of the phase. It is written by machine on every push to `main`.

### 3. The site and the hub read the declaration

- **`constellation.json` loses `site.draft.source`.** It is always the member's own key, and
  whether a draft area exists now follows from the projection: a `site` slug set and
  `anonymous = false`. `site.slug`, `title` and `blurb` stay, since the hub owns how the programme
  presents itself. `site.published` stays as well, derived from the release record (E-0021 already
  moves its `source` to the manifest's `public_export`).
- **`wiki lint`** checks the projections against `constellation.json`:
  - the `site` slug matches `site.slug`;
  - an anonymous member has no `site` block and is `private`;
  - a projection is not older than the member's last push it can see.
- **The research site's `build-routes.mjs`** creates a draft route for each member whose projection
  allows one. It drops any route whose projection says `anonymous`, whatever `constellation.json`
  says. The drafts index can show each article's phase.

### 4. Moving from one phase to the next

`linkage phase` prints the current phase, the next one, and what the next one's entry condition
still lacks: the parts it requires and the gate PROCESS.md names, such as `linkage check` clean for
`blueprint` and a reviewed skeleton for `proving`. `linkage phase --advance` edits `phase` in
`linkage.toml` and runs `--sync` for any part this phase adds. It does this only when the condition
holds. Phase changes go through a pull request like any other edit, so the author sees each one.
The entry conditions that are judgements (the author approving the decomposition, § 4) are
recorded, not checked: `--advance` asks for the record's path.

### 5. What it replaces

- The reading of absence from the tree, in article-kit#92 and in `scaffold._absent_artifacts`. It
  remains only as the fallback for a repository without `[article]`.
- pyramids' standalone `.github/workflows/docs.yml`, with its copied Tectonic and plasTeX steps and
  its hard-coded slug.
- `constellation.json`'s `site.draft.source`, the hand-placed draft placeholder, and the research
  site's hand-kept list of producing repositories.
- PROCESS.md § 1 step 5 (add the reusable workflows by hand), and the paper-only repository's
  comment explaining which paths it leaves out.

## Consequences

- A new repository, whatever its shape, is configured once in `linkage.toml` at creation. Its draft
  is on the site from its first push. Moving to a new phase is one command and one pull request.
- A paper-only or anonymous repository uses the framework's CI, keeping only the steps that are
  truly its own.
- `linkage.toml` gains a table the hub depends on, and `manifest.yml` now runs in every repository.
  A repository that never pushes leaves a stale projection, which `wiki lint` reports.
- `docs.yml`'s deploy condition changes, and the change can put a draft on the site that was not
  there before. The site is behind Cloudflare Access at `/drafts/*`, and the `anonymous` refusal is
  enforced twice, in `docs.yml` and in `build-routes.mjs`.
- Anonymity is not something the tooling can fully enforce. A public repository (this one
  included) or a public wiki page that names an anonymous repository defeats it, and no check reads
  other repositories' prose for that. The declaration makes the set of anonymous repositories
  known, so a check across the constellation's public repositories for their names becomes possible.
- Rollout, after acceptance, one pull request per repository:
  - **article-kit:** the table, the two commands, the phase gates, `article.yml`, the `docs.yml` and
    `manifest.yml` changes, the docs, released as a minor version.
  - **The hub:** `constellation.json`, `wiki lint`, `ARCHITECTURE.md`, and a hub ADR amending
    ADR-0016 § 2's `draft.source`.
  - **The research site:** `build-routes.mjs`.
  - **Each article repository:** its `[article]` table and the `article.yml` caller. pyramids also
    drops its own `docs.yml`.
