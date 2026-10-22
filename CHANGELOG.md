# Changelog

One entry per release, headed `## <tag> — <date> — <title>`, saying what changed and why
([`docs/RELEASE.md`](docs/RELEASE.md), "Versioning the framework"). Work since the last release
accumulates under Unreleased. A tag is what the article repositories pin: the reusable workflows
(`docs.yml`, `lean.yml`, `manifest.yml`) at `@vX.Y.Z` and the `linkage_ref` input at the same tag.

## Unreleased

- **`linkage init` writes `LICENSES/`; the export's dry run warns when it is absent (hub Q-0488).**
  Every Lean header names `LICENSES/Apache-2.0.txt`, and the export copies `LICENSES/` — and
  copied nothing, silently, from a repository without it (found by the affine repository's first
  export). `init` now writes both texts (`Apache-2.0.txt`, `CC-BY-4.0.txt`) when absent; `--sync`
  does not, so existing repositories are untouched. `release export` prints a warning naming a
  missing text, under `--dry-run` too. `RELEASE.md` at `extra_files` says that a script exported
  to be run finds the paper's directory under either name (`paper-iso/` or `paper/`).
- **CI runs on `ubuntu-latest` for pull requests (hub Q-0511).** The `check` job was
  `windows-latest`; Linux is now a platform the queue's VM runs (ADR-0028) and costs half as much.
  No test exercises the Windows-only facts (cp1252 console, uv-tool trampoline), so the full suite
  runs on Windows only on push to `main`; the workflow's comment says why.
- **`docs.yml` builds a paper of several TeX roots, so a paper with a supplement is served as
  its two PDFs (hub Q-0485).** Paper VII's isotropic paper is `main.tex` and `supplement.tex`,
  which refer to each other through `xr-hyper`; built alone, `main.tex` leaves every reference
  into the supplement unresolved, so the export's `docs.yml` built a `paper/full.tex` and the
  site served that, while the deposit holds two PDFs. Now `paper_tex` may name several roots
  separated by spaces (`paper/main.tex paper/supplement.tex`), and an extra paper's `tex` may
  be a JSON list. The roots are built in order with their `.aux` kept, then all once more, so
  that each finds the other's `.aux`; the first is published as `paper.pdf` (`<name>.pdf`), each
  further root as `paper.<stem>.pdf` (`paper.supplement.pdf`), and the artifacts README, the
  landing page and the validation of `dist/` list every one. **Why this shape and not the
  other the request offered** (a frozen export publishing its committed `<stem>-<tag>.pdf` and
  `<stem>-<tag>.supplement.pdf` instead of building): it fits the inputs a caller already
  passes, serves a development repository's draft site too (whose `iso.pdf` had the same
  fault), and keeps one path for every PDF the site serves. Publishing the committed bytes of a
  frozen export can still be added after; nothing here precludes it. **What a caller changes:
  nothing** unless it wants this: one root builds exactly as before (one Tectonic run, no kept
  intermediates), every input keeps its type and default, and the per-run artifact `paper-pdf`
  holds `paper.pdf` as it did (and the further roots beside it). New refusal: two roots that
  would be published under one name (`paper.x.pdf` from `a/x.tex` and `b/x.tex`). A caller
  gains this by moving its pin to the release that carries it; the export of `iso-v0.1` can
  then drop `paper/full.tex` from its `docs.yml`, and `research-site` the `paper_label` and
  `files` work-around of `research-site#12`. `tests/test_docs_workflow.py` runs the workflow's
  helper and its two site steps, and builds `tests/fixtures/supplement/` with Tectonic where it
  is installed; the WISHLIST entry is removed.

- **`zenodo status` prints the file order and default preview; `publish` checks them (hub Q-0486).**
  In affine's `iso-v0.1` the published record listed the zip first, and a published record's files
  cannot be reordered. `upload` now writes `files.order` (paper PDF, supplement, zip) beside
  `default_preview` through the records API draft; `status` reads both back by name; `publish`
  refuses when the first file is not the paper's PDF (`--allow-file-order` overrides).
  `docs/RELEASE.md` lists the two lines as a sandbox-rehearsal step. The `order` write follows the
  records API's shape and has not been run against live Zenodo. `tests/test_release.py`; the
  WISHLIST entry is removed.

- **`linkage release export` removes the files it no longer writes (hub Q-0484).** An export over
  an earlier one kept the earlier one's files: in affine's `iso-v0.1`, 81 Lean files the second
  export no longer wrote would have been built and committed, and a renamed supplement PDF stayed
  beside the new one. The export now records what it writes and removes the rest of its tree and
  the directories that leaves empty, keeping `.git/`, `.zenodo-deposition.json` and any `.lake/`.
  A symlink or junction is never followed or removed: it is named and left, and the run exits 1
  without building. It refuses, listing the files, when `--out` is or holds the repository or
  held no earlier export (no `README.md`). `--dry-run --out DIR` lists what would be removed.
  `tests/test_release.py`; the WISHLIST entry is removed.

- **`docs.yml` builds in one job (hub Q-0496).** GitHub bills each job rounded up to a whole
  minute, and the six jobs (`paper`, `extra_paper`, `blueprint`, `web`, `publish`, `deploy`) each
  took 15–60 seconds, so a docs run that did about a minute of work billed five or six. In
  affine (private, billed), 1–17 October, 311 runs did 733 minutes of work and billed 1,856. The
  pieces are now steps of one job `docs`, in the same order and under the same conditions: the
  extra papers are a loop over `extra_papers` in place of the matrix, and Tectonic is installed and
  its package cache restored once. **What a caller gains:** a docs run bills about the minutes it
  works, rounded once, not once per piece; a public caller is not billed and notices only that a run
  is a little shorter. **What a caller changes: nothing.** Every input, secret and default of
  `workflow_call` is as it was, so no `with:` changes. A caller gains this only by moving its pin
  to the release that carries it; callers pinned to an earlier tag keep the six jobs.
  Behaviour kept: a failed build still fails the run and still does not push or deploy; a failed
  PDF build does not hide the other builds' errors; a failed web build still blocks the deploy
  but not the artifacts push; `build_blueprint: false` still deploys nothing. Differences a
  caller can see: the job is one (`docs / docs` in the checks list); the job holds
  `contents: write` (the push token reaches only the push step; checkout no longer persists it);
  the extra papers' per-run artifacts are one `extra-papers-pdf`, not one `<name>-pdf` each.
  `tests/test_docs_workflow.py` pins the single job and the interface.

- **`lean.yml` and `manifest.yml` install `linkage` from a tag, a branch or a full commit sha
  (hub Q-0483).** `docs/RELEASE.md` rule 4 and `linkage pins` allow a `linkage_ref` that is a sha,
  but `git clone --branch` takes a branch or a tag only, so the first `linkage` step failed. Both
  workflows now `git init`, `git fetch --depth 1 <url> <ref>` and `git checkout FETCH_HEAD`; the
  token handling and the error message are unchanged.

## v0.4.0 — 2026-10-14 — a supplement in a release, two probe files, and what the first export of a two-paper repository found

- **`linkage release`: a supplement, and what Paper VII's first export found (hub Q-0451).** The
  isotropic paper is the first release with a supplement, the first whose witness file imports
  its library root, and the first with its abstract and its figures beside `main.tex`. Nothing
  here changes an export that has none of these. New module keys: `supplement` (the export
  carries its PDF in `paper/` and as `<stem>-<tag>.supplement.pdf`, the release gate reads its
  first page, and `zenodo upload` sends it after the paper's PDF, which stays first for the zip's
  name and the default preview: `zenodo.release_pdfs`) and `extra_files` (files exported at their
  own path). Faults repaired, each with a test:
  - a module that imports the library root entered the closure alone, and the generated root then
    imported it back, a cycle: `closure_of` follows the root's imports, `root_file` leaves out
    what imports the root, and the exported guard keeps the development guard's own imports;
  - `theorem Datum.lemma` counted as a declaration of the tag `Datum`, which made every module
    with a lemma in that namespace a root of the closure (`decl_pattern`);
  - the deposit's description was empty when the abstract is in a file of its own
    (`plain_abstract` reads the other sources after `main.tex`); `abstract_macros` now also
    expands a bare `\name`, so that mathematics can be given a plain-text reading; the
    description is HTML-escaped;
  - a figure beside the sources was exported to `figures/`, where the exported paper does not
    look for it; it stays in `paper/`;
  - the generated `content.tex` input `theorems-extra.tex` in an article that has none;
  - the README gave, for a block of several declarations, their names and the words between
    them as the headline's axioms; it reads the headline's own line;
  - local paths in an exported `.py` file were not replaced; `__pycache__` was exported.

- **`[boundary] probes` may be a list, and a qualified tag is found in its own namespace (hub
  Q-0452).** Both for a repository that holds the Lean of two papers of which one is released
  first, so that the release's export holds none of the other's results.
  - `[boundary] probes` is a path, as before, or a list of paths (`Boundary.probes` is a tuple).
    Each file is held to the probe rules, and a headline declaration needs a probe in one of
    them; a file that is missing is reported, and its headline results are not then listed as
    unprobed. With one file per paper, a paper's probe file imports that paper's Lean alone.
    **An article that sets a list needs a `linkage` with this change**: an older one refuses the
    list ("must be a path"), in `linkage boundary` and in every other command, since all of
    them read `linkage.toml`.
  - `find_modules` narrows a tag with a namespace (`Lib.OriginDatum.exponentL`) to the modules
    that declare the qualified name or open that namespace, when several modules declare the
    short name; `def exponentL` under another namespace in another file had made that file a
    root of the release's closure. If the narrowing leaves nothing, the hits stand as before.

- **`PROCESS.md` § 7 says what "page anchors printed before the `[A]` nodes" meant (Q-0413).** The
  clause read as a per-node sentence on which cited facts the statement rests on, which
  `WRITING.md` § 3 assigns to the trust-base subsection. It now reads: each cited fact is stated
  once as a numbered theorem with its page anchor before its first use; which statement rests on
  which fact is § 1.1's table. Wording only; no rule or tool changed.

## v0.3.0 — 2026-10-10 — the trust base read from Lean, and a home for every shared statement

Everything since v0.2.0. Cut for Paper VII (`spatial-hemigroup-affine`), which waits on it for the
cross-module `\ledger{}` (Q-0379), for dropping its hand-made `lean-uses.json` (Q-0389) and for
rule 15's citations (Q-0395), and for Paper V's adoption of rule 15 (Q-0396). A minor bump under
the `v0` rule. **One thing here makes a passing article fail, and it is meant to:**
- the reusable `lean.yml` now runs `linkage check --fresh-axioms` after the build. A marked
  trust-base section that names a ledger entry its statements' axioms do not reach, or leaves out
  one they do, fails the Lean job; before this tag the comparison read nothing in CI.

Nothing else does:
- check 14 (interface nodes) and rule 15 (homes) are advisory;
- a committed `lean-uses.json` fails only when it carries a stamp that no longer matches; an
  unstamped one is an advisory;
- `\ledger{<package>:<id>}`, `\statedin{}` and `\restates{}` are new syntax, used by nobody until
  an article writes them. The two macros arrive with `linkage init --sync`.

A module moves to this tag when it next runs (`docs/RELEASE.md`, "Versioning the framework").

- **`linkage check`, rule 15: a node that tags a shared-library declaration is the declaration's
  home, cites the home, or is reported (Q-0392).** The shared library has no blueprint (hub
  ADR-0026, amended 2026-10-10); a statement's prose is the blueprint node of the article that
  first needed it, and nothing checked that a later article cites that node instead of stating
  the lemma again. `linkage/homes.py` reads the library's `site/library/data.json` (Q-0391) with
  `git show` at the revision the lake manifest pins and classifies each tagging node as home,
  citation, standard material, owed or uncited use. Two macros in the framework's
  `linkage-macros.tex`, both no-ops in the PDF and stripped from the statement text:
  `\statedin{<article>:<label>}` cites a home, `\restates{<article>:<label>[@<sha12>]}` marks a
  repeated statement, which is compared with the home's text where a required package ships it
  and reported as uncompared where none does. Advisory throughout, with one summary line; an
  article that requires no package with a record sees no change. New: `library_article` in
  `linkage.toml` (default `slug`), `--library-record PATH` and `--library-article NAME` on
  `check` (and `$LINKAGE_LIBRARY_RECORD`, `$LINKAGE_LIBRARY_ARTICLE`) for a run against a record
  no article pins yet. **An article picks the macros up with `linkage init --sync`**; until
  then `check` reports its `linkage-macros.tex` as differing from the framework's.
  `docs/LINKAGE.md` rule 15; `tests/test_homes.py`.
- **The reusable `lean.yml` runs `linkage check --fresh-axioms` after the build, and a
  committed `lean-uses.json` export with no stamp is no longer dated by mtime (Q-0388).** Q-0383
  made rule 13's ledger comparison read `#print axioms` under `--fresh-axioms` or a
  `#guard_msgs` pin, but assumed the articles are pinned; none is, and the reusable
  workflows never ran `linkage check` where Lean exists, so the comparison read nothing
  anywhere and "named but not read" was always an advisory. `lean.yml` gains a guard —
  gated the same way as the neighbouring linkage steps (`axiom_guard_file` set, the
  default) — that runs the whole check with `--fresh-axioms` right after the build and
  the axiom guard, so a ledger entry a statement's axioms do not reach, or reach and
  never name, now fails CI. The export's modification-time fallback is gone: CI is
  always a fresh clone, where checkout order rather than edit history sets every file's
  mtime, so it could never honestly answer "is this export current" there. An unstamped
  export is now an advisory (`[lean-uses]`) naming `linkage closure --stamp-export`: its
  currency is unknown, not wrong, and nothing fatal reads it (the author, 2026-10-10); a
  stamped one is still compared by digest and fails when stale, unchanged. The advisory
  for an unpinned, unread declaration now names `--fresh-axioms` and the Lean CI job
  first, pinning second. `docs/LINKAGE.md` rules 11 and 13; `tests/test_trust_base.py`.
  The default (offline) `linkage check` and `linkage closure`'s advisory audit are
  unchanged.
- **`linkage check`, rule 13: a `\leanok` statement's ledger entries are read from `#print axioms`,
  not the source scan (Q-0383).** The trust-base comparison read the `linkage closure` constant map,
  whose source scan resolves identifiers textually and reported Paper VII's affine statements as
  resting on A2, which `#print axioms` shows they do not (Q-0377). It now reads Lean's output under
  `--fresh-axioms`, else the boundary harness's `#guard_msgs` pin; an unpinned declaration is an
  advisory, and the section's named entries are then not compared against it. A committed
  `lean-uses.json` export, still read by `linkage closure`, fails `linkage check` when it is
  stale (see the Q-0388 entry above for exactly how staleness is decided). An article that kept
  the export only for rule 13 can delete it.
- **`\ledger{<package>:<id>}`: a node cites an entry of a required module's ledger (Q-0374).**
  Resolved through the `include <package> @ <revision>` line of `blueprint/trust-boundary.txt`
  against that module's own `AXIOMS.md` at the pinned revision, failing closed when the package is
  not included or the entry is absent there; the manifest projects it with its module. The
  own-module `\ledger{AXX}` is unchanged. `docs/LINKAGE.md`; `tests/test_ledger_module.py`.
- **`linkage check`, check 14: a fully proved node that rests on a ledger entry `\uses` the
  entry's interface node (Q-0356), read from the status line only (Q-0378).** leanblueprint
  paints a node fully proved when it and its `\uses` ancestors have proofs, so an `[A]` node whose
  Lean calls an axiom rendered as proved unless the axiom is itself a node without a proof (Paper
  VII: 41 nodes, fixed there in its #82). `docs/PROCESS.md` § 5 states the convention; the check
  advises (`[iface]`). It reads the `\ledger{}` tokens on the status line (`Node.status_ledger`,
  not projected into the manifest), so an entry an Assignment clause mentions as *not* spent is
  not taken for a spend. `docs/LINKAGE.md` rule 14; `tests/test_checks_interface.py`.
- **`linkage paper` checks every paper's main document in a multi-paper repository (Q-0354).**
- **Process and writing rules** (documents only): a blueprint proof change is mirrored into the
  paper in the same pull request (`docs/PROCESS.md`, Q-0355); the rules from the author's
  pass-6 review of Paper VII (`docs/WRITING.md`, `docs/PUBLICATION-TEMPLATE.md`,
  `docs/REVIEWER-CONTRACT.md`, Q-0375).

## v0.2.0 — 2026-10-06 — a required module's trust boundary by reference

Everything since v0.1.0. Cut for Paper VII (`spatial-hemigroup-affine`), whose axiom guard reads a
`trust-boundary.txt` with an `include` line: `linkage axioms --check` at v0.1.0 reads that line as
an axiom name and fails, so the guard needs this tag's `linkage_ref`. A minor bump under the `v0`
rule. Nothing turns a passing article's advisory into a failure:
- the reusable workflows gain only an optional input (`docs.yml`'s `push_artifacts`, default true)
  and run `linkage boundary` as a no-op without a `[boundary]` table;
- `linkage paper`'s fatal checks run only where an article calls them.

A module moves to this tag when it next runs (`docs/RELEASE.md`, "Versioning the framework").

- **`linkage axioms`: a trust boundary includes a required module's boundary by reference
  (Q-0298).** A line `include <package> @ <revision> [<path>]` in `blueprint/trust-boundary.txt`
  admits exactly the names that file lists in the required package (default
  `blueprint/trust-boundary.txt`), read with `git show` at the commit `lake-manifest.json` pins —
  never the working tree. A package the manifest lacks, a revision other than its `inputRev` or
  resolved sha, an unfetched package or a missing path is refused and admits nothing. Included
  names are reported apart from the article's own and are not looked for in its `AXIOMS.md`; a
  nested include resolves against the consumer's manifest. From Paper VII, which requires Paper V's
  `SpatialHemigroup @ v0.1` and whose first guarded theorem through it would print
  `SpatialLine.fourier_toolbox_levy_unique`. `docs/LINKAGE.md` rule 5,
  `scaffold/claude/rules/ledger.md`, `tests/test_trust_include.py`. The WISHLIST entry is removed.
- **`linkage check` matches a proof moved to an appendix to its shared statement by
  label (Q-0297).** Check 3d (Q-0234) only ever looked directly after a `% shared with
  blueprint` statement for its proof, so Paper VII's move of most §3–§5 proofs into
  appendices (`spatial-hemigroup-affine` PR #45) silently dropped coverage from 18
  compared proofs to 4. A proof with no adjacent match is now looked up elsewhere in the
  paper by an explicit `% proof of <label>` comment, or a single `\ref` in its own
  optional heading (`\begin{proof}[Proof of Proposition~\ref{label}]`) — or, with
  neither, a single `\ref` on the line introducing it with no blank line in between, to
  avoid filing a proof under an unrelated label its introductory paragraph happened to
  cite. A matched proof is compared exactly as the adjacent case, `--pin-shared`
  included; a shared statement whose node has a proof of record but whose paper proof is
  neither adjacent nor matched is now reported `[proof] unmatched` (advisory, counted in
  the summary), with `% proof omitted` as the opt-out for a paper that deliberately
  prints none. Read-only runs: `spatial-hemigroup-affine` went from 4 compared proofs to
  39 compared + 24 unmatched (of 64 proof environments); `spatial-hemigroup-scale-space`
  from 25 compared to 25 compared + 73 unmatched (that paper does not yet use the moved-
  proof convention, so the gain is entirely newly-surfaced unmatched findings). Advisory
  only in both; neither article's exit code changed. `docs/LINKAGE.md` rule 4;
  `tests/test_checks_moved_proof.py`, `tests/test_checks_shared_proof.py`. The WISHLIST
  entry is removed.
- **`linkage check --pin-shared` rewrites a stale statement pin (Q-0296).** The advisory for a
  stale statement pin (a pinned node has moved since the paper was written against it) has told
  the reader to re-pin with `--pin-shared` since Q-0234's proof pins landed, but the stale marker
  was never added to `f.unpinned` — only a never-pinned one was — so `--pin-shared` left it
  untouched and the advisory fired on every run. Fixed to match the proof pin's behaviour, which
  already collects both the stale and the never-pinned case. `tests/test_checks_shared.py`.
- **`fidelity-review` § 5: a card reads an annotation's hypothesis side too** (Q-0236's companion
  line, which its unattended session could not write under `.claude/`). Four delivered WISHLIST
  entries removed again: the scope audit (Q-0108), the drifted shared proof (Q-0234), the deposit
  sentence (Q-0237) and the annotation's hypotheses (Q-0236). Their deletions were undone on
  2026-10-01 when GitHub's "Update branch" merge of `main` into `queue/q-0236` (`749e395`)
  resolved `WISHLIST.md` on the old side.
- **`scaffold/scripts/build-blueprint.sh` tolerates an article with no Lean (Q-0258).** The
  leanok statement/proof-agreement step now runs `scripts/audit-leanok.py --check` only when
  that script exists, rather than unconditionally; a plain `Formalization/` is not the signal,
  since `linkage.toml` requires that path to exist even where there is no Lean development, as
  an intentionally empty placeholder. The web-theorem-list step (`scripts/check-web-thms.py`,
  web.tex's theorem list against theorems.tex) is likewise guarded, and now runs under `--web`
  as well as the default and `--quick` builds, matching `check`. `linkage init --sync` into
  `spatial-hemigroup-affine` (hub Q-0153) had overwritten that article's own copy, which has
  neither script, with the framework's unconditional one, so `bash scripts/build-blueprint.sh
  --quick` exited 2 there.
- **`linkage check` advises on a shared proof that has drifted from its blueprint (Q-0234).**
  A marker's ref may now carry a proof pin, `<label>[@<sha12>]+<sha12>`, over the node's
  `shared_proof` (the proof without its machine-check bookkeeping, reference style reduced). The
  `proof` environment directly after a shared statement is verbatim, tracked by that pin, or a
  `[proof]` advisory (stale pin, or unpinned and different, with where the texts part company);
  `--pin-shared` writes the pin. Advisory under every flag, `--strict-shared` included. From Paper
  V module C, where a referee was sent a circular proof the blueprint had repaired five days
  earlier. `docs/LINKAGE.md` rule 4; `tests/test_checks_shared_proof.py`. The WISHLIST entry is
  removed.
- **The reviewer contract adopted, with a scope-audit mode and the `QUANTITY` tag (Q-0108).**
  `docs/REVIEWER-CONTRACT.md`: the hub's `draft-reviewer` now emits the contract's JSONL records
  (returned as its final message, since it is read-only, and saved by the caller) instead of a
  prose report; a new § "The scope-audit mode" restates every summary surface of a paper (abstract,
  introduction results, conclusion, tables, captions) from the statement it cites and flags the
  mismatches, which `WRITING.md` § 5 and `PROCESS.md` § 8 require before a frozen build; the review
  record gains an optional `mode`; and `QUANTITY` is the tag for a number that does not name the
  object computed. `linkage review` knows the tag and carries the mode (`tests/test_review.py`).
- **`fidelity-review`: a row that repairs an inference pattern says which siblings it checked
  (Q-0235).** `SKILL.md` § 2 and the `REVIEW-fidelity.md` template: a finding that diagnoses a
  pattern rather than a local slip ends its resolution with **Siblings checked:** (the node's
  other clauses and the chapter's other instances, with outcomes) or "none". A labelled clause in
  the resolution cell, not a seventh column, so existing six-column ledgers stay valid. From Paper
  V module C, where R123 and R83 each repaired one clause and left the same defect beside it.
  The WISHLIST entry is removed, with the one for Q-0105, whose rule (admitting a name re-opens
  its card) was delivered on 2026-09-21 (`08bac11`) and whose entry had outlived it.
- **`docs/RELEASE.md` item 8 and "The commands": the site step as `research-site` now runs it
  (Q-0181).** The routing table and generated pages are no longer a manual `npm run routes` /
  `npm run verify` pair: the hub's `notify-site` workflow dispatches `research-site`'s
  `site-sync` on the push that changes `constellation.json` (and daily as a safety net), which
  regenerates, commits, deploys and verifies on its own — the earlier text omitted `npm run
  pages`, which Paper I's `v1.1.0` needed on 2026-09-27. The manual fallback (`npm run routes`,
  `npm run pages`, commit, push, `npm run verify`) stays, for when the workflow cannot run.
- **`linkage lean clones`: the trunk's second-demand rule, observable (Q-0189, E-0010).** A new
  verb finds the Lean members through the hub's `constellation.json` (`--wiki`, else
  `$WIKI_VAULT`), compares every pair that is checked out, and reports the declarations that are
  the same text up to renaming, anchored on the **statement text** rather than the name, with the
  count of matches under different names (the number a rename would move). It exits 1 above
  `--max-clones` (default 0) except for names in `--allow` / `--allow-file`, 2 when it could not
  answer, and has `--json`. The parser is the engineer's survey's, with one repair (a declaration
  ends at the next top-level command, not only the next declaration; the survey missed 6 of 86
  clones at the end of a namespace) and three guards that anchoring on the statement needs
  (definitions anchor on their whole text; a theorem statement under `--min-tokens` tokens does
  too; a declaration's own name is blanked). Config-free, like `prose` and `review`. See
  `docs/LINKAGE.md` § "The trunk's second-demand rule".
- `linkage release zenodo metadata` restores the records API's `pids.doi` when the legacy
  metadata PUT left it empty: it reads the draft back (`Accept: vnd.inveniordm.v1+json`) and, if
  `pids.doi` is empty, reserves it through `POST /records/<id>/draft/pids/doi` (InvenioRDM's own
  REST API, the same call the draft page's "Get a DOI now!" button makes); it refuses, without
  writing further, if the DOI that comes back differs from the one the PDF already prints. Paper
  I's `v1.1.0` draft kept `prereserve_doi` (legacy) but not `pids.doi` after #32's fix, so
  `preview`'s guard still refused it; the author re-reserved it by hand on the draft page, which
  happened to derive the same DOI from the record id. `linkage release export`'s generated
  `.gitignore` now lists `.zenodo-deposition.json` and `*.zip`, which `reserve` and `upload` write
  at the export's root and which a plain `git add -A` there had put in the tagged tree and the
  public zip.
- `linkage release zenodo preview`: the write-back is labelled `application/json`. The draft
  endpoint reads RDM from plain JSON and answers 415 to its own media type, which #32 sent;
  only the read needs `Accept: application/vnd.inveniordm.v1+json`.
- **`linkage release zenodo`: setting the default preview no longer empties the draft.** It
  read the draft from the records API as plain JSON, which Zenodo answers in the legacy
  serialization, and wrote it back as RDM, dropping the DOI, resource type, creators and
  keywords of Paper I's v1.1.0 draft. Both requests now name the RDM media type, and a draft
  that reads without creators, a resource type or a DOI is refused rather than written back.
  A new `metadata` step sets the metadata again from `.zenodo.json` (then the preview) without
  uploading; `status` prints the reserved DOI, type, creators, title, version, keywords and
  licence; and `publish` refuses a draft missing the title, creators, type or reserved DOI.
- `linkage release export --build`: the exported lakefile's `defaultTargets` keeps only the
  libraries the export carries (a `Skeleton` target failed Paper I's v1.1.0 build, whose
  nodes are all proved); an export not beside its repository under a name of its own is
  refused before the build, and a failed `lake-store link` stops it, since either means
  cloning every package and compiling Mathlib (three and a half hours, and a tree that
  `lake-store gc` cannot see). `zenodo upload` names the source zip after the PDF, not the
  export's directory.
- `linkage release zenodo upload` makes the PDF the draft's **default preview**, through the
  records API's `files.default_preview` (the legacy deposit API has no such field); a new
  `preview` step sets it again on a draft uploaded before. The steps print the draft's own
  page, `/uploads/<id>`, not the legacy `/deposit/<id>`, which now redirects to a record page
  that exists only once published. Both found in Paper I's v1.1.0 sandbox rehearsal.
- `linkage release`: a three-part tag (`v1.0.0`, `v1.1.0`) now parses, so the rule 6 gate finds a
  later version's first release; it used to treat Paper I's `v1.1.0` as a first release and skip
  the date-line and version-history checks without a word. And a Lean declaration whose name ends
  in a prime (`sonine_conservation'`) is found, where the pattern's trailing `` never matched
  after `'` (and let `foo` match `foo'`). Both found by the first dry run of Paper I's v1.1.0.
- `linkage paper`'s item-count check (`\ref{p}(3)` past a statement's item count) is now
  module-aware (Q-0171): it resolves a label within the referencing file's own `paths.paper`
  module first, falling back to the repository-wide map only when that module defines the label
  nowhere itself. A repository with several paper modules may legitimately restate an earlier
  module's statement under the same label — an abridged copy, not drift, so each module's own
  `\ref`s resolve locally — and the old repository-wide map answered every module's pointers from
  whichever module's copy it read last, failing a correct `\ref{p}(3)`/`(4)` in the module that
  states the result in full against a shorter restatement elsewhere (seven such failures on
  `spatial-hemigroup-scale-space`'s `prop:thorin-subclass`). `linkage check`'s shared-statement
  comparison (rule 4) does not have this blind spot — see `docs/LINKAGE.md` "A label, once per
  module".

- `linkage check` reads a paper's **trust-base subsection** and compares it with the development
  (LINKAGE.md rule 13, Q-0170; requested by `spatial-hemigroup-scale-space` after Paper V's module C
  went stale twice in two days). The paper marks the subsection with `% trust base: begin` and
  `% trust base: end`. Inside it, a row calling a `\ref`'d statement machine-checked or prose-only
  must agree with the node's `\leanok`. The ledger entries the region names must equal those its
  statements read: through the `linkage closure` index for a `\leanok` node, through its `[A]`
  ancestors for any other. A printed `#print axioms` block must carry a `% printed at <commit|date>`
  stamp, may print only Lean core and declared boundary axioms, and must match its `#guard_msgs`
  pin where the boundary harness has one. `--fresh-axioms` also runs `#print axioms` through
  `lake env lean` and compares; the default run needs no Lean. A paper without the marker is not
  read and the check's output is unchanged; with one, the summary gains a `Trust base:` line.
  Fixtures in `tests/test_trust_base.py` cover a matching subsection and each drift.

- `scripts/build-blueprint.sh` is now framework-owned: `scaffold/scripts/build-blueprint.sh`, delivered
  to an article's `scripts/` by `linkage init --sync` (skipped in a repository with no blueprint) and
  reported by `linkage check` as scaffold drift when the copy diverges. Two article repositories had
  byte-identical hand copies; the copies are now deliveries, and the original is here. It also fixes
  the web step on Windows: plasTeX writes the `\lean`-tag declaration list in Python's default
  encoding (cp1252) and died on a non-ASCII Lean name such as `b₀`; the plasTeX command now runs
  with `PYTHONUTF8=1`. Linux CI was never affected. `init` also writes framework-owned files as
  bytes, so a shell script keeps its LF endings on Windows.

- `linkage init --sync` works in a paper-only repository. It reads the slug from `linkage.toml`
  without validating the artifact paths (`config.load(root, validate=False)`), so a repository with
  no blueprint, ledger or Lean directory no longer stops with a CONFIG ERROR. Chosen: the rules for
  artifacts the repository lacks are **skipped**, not copied — `blueprint.md` and `ledger.md`
  without the blueprint, `lean.md` without the Lean directory — and with no blueprint the
  `blueprint/` build files and the stamp are skipped too, so a paper-only repo gets only `core.md`,
  `writing.md` and the `.claude/` seeds. `init` without `--sync` and `linkage check` are unchanged.
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

- `linkage closure` — the inferred half of the `\uses` edge ([`docs/LINKAGE.md`](docs/LINKAGE.md)
  rule 11). Per `\leanok` node it reads the Lean declaration the node points at — from the
  declaration source, or from an exported constant map (`paths.lean_uses`, default
  `Formalization/lean-uses.json`; `--export PATH`) when the article has a built environment to
  write one from — and diffs the constants it uses against the node's `\uses{}` both ways:
  `[declared]` (a `\uses` target nowhere in the declaration's transitive inferred closure),
  `[inferred]` (a declaration cited directly that no `\uses` path reaches), plus `[empty]` (a
  proved node whose declaration cites nothing of ours while its `\uses{}` names formalised nodes)
  and `[orphan]` (a `lem` nothing depends on in either graph). Advisory only and a separate
  command: it always exits 0, `linkage check`'s exit code is untouched, and nothing here writes a
  `\uses{}` edge — authorship stays blueprint-first. Supersedes the `\uses`-against-imports half of
  `f7sweep.py` for `\leanok` nodes.
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
