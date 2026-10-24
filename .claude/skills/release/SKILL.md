---
name: release
description: >
  The release discipline for an article module, RELEASE.md: the rules and the checklist (a DOI
  reserved first, the first page checked, the export, the site). Invoke before any release step
  and again after a compaction; the release itself is the author's.
---

# Releasing a module: the rules and the checklist

`docs/RELEASE.md` § "The rules" and § "The checklist", verbatim. The commands, in their order, are §
"The commands" of `${CLAUDE_PLUGIN_ROOT}/docs/RELEASE.md`: read it at the step that runs them.
Relative links below are to `${CLAUDE_PLUGIN_ROOT}/docs/` (in article-kit itself, `docs/`).
Generated from the document by `linkage.skills`; edit the document, not this file.

## The rules

1. **Self-contained and correct at its scope.** A release states its axioms, proves its theorems in
   full, marks every open item as open, and promises no sequel. It may *import* a result from
   another module by citing that module's released version and statement number. It may not depend
   on an unreleased draft. "Complete" is not a requirement; "nothing asserted beyond what is shown"
   is. A reference into an unreleased module is prose about further work with a
   `% TODO(module X): cite <label> when released` comment beside it, never a `\ref`.
2. **A changelog per module.** `CHANGELOG.md` at the repository root, one entry per release, saying
   what changed and why, and in particular which statements were renumbered, strengthened, weakened
   or withdrawn, so that a reader who cited an earlier version can see whether the citation still
   holds.
3. **The draft is frozen at the module's first release.** From then on the blueprint is the only
   text of record; draft syncs end.
4. **Prior art found after a release is recorded at once and cited in the next** (hub ADR-0017).
   Record it the day it is found, in the wiki note that owns the object, saying plainly what is
   prior and naming the location at the page. The release is not retracted and its text is not
   quietly edited; the citation rides the next release, with the changelog entry recording it. A
   source counts as read only **at the page, for the object in question**.
5. **What a released PDF prints is checked by the scripts, not by a reader of a checklist.** The
   first page carries the release date, the version and the version DOI; the export refuses a build
   that says "working draft" or lacks them. (Two first tags went on "working draft" builds with the
   checklist item already written.)
6. **A later version names its first release, and closes with a version history** (the author's
   decision, 2026-09-22). Priority is carried by the timestamped public record — each Zenodo version
   DOI with its date, arXiv-style — and per result: a theorem first appears in the version that adds
   it. The PDF travels alone, so a later version says both things itself, since the version and the
   first release are both facts about the same PDF and neither substitutes for the other:
   - **The date line names the first release.** For every version after the first, the frozen
     `\date{...}` reads: this version, its date and version DOI, then "first released as
     `<first version>`, `<date>` (DOI …)", with the concept DOI as the thing to cite. The first
     release's date line is as now (just the release form).
   - **A version history at the end of the paper, not on the first page** (a first-page footnote
     grows with every version, and a growing footnote is exactly the shape rule 5 exists to keep off
     the first page). An unnumbered section, placed **after the conclusions and before the
     references** (not an appendix: `PUBLICATION-TEMPLATE.md` § B.10 reserves appendices for long
     proofs, and version history is metadata about the record, read the way a reader looks for an
     errata note just before the bibliography, not a proof to check), one entry per version, newest
     first, substantive changes only: results added (with their statement numbers), results
     corrected or strengthened, the renumbering map when numbers moved (old → new, since versioned
     statement numbers are citable), and a change to the trust base (an axiom proved or added, a
     Lean refactor that changes what the machine-checked perimeter covers). Drawn from the module's
     `CHANGELOG.md` entries, reworded for a reader of the paper; the full history stays in
     `CHANGELOG.md`, git and Zenodo. A first release has no version history section. Template:
     [`scaffold/paper/version-history.tex.in`](../scaffold/paper/version-history.tex.in).

## The checklist

In order; a release is not done until the last item.

1. **Before anything is frozen.** The external rounds answered ([`PROCESS.md`](PROCESS.md) § 9);
   the scope audit and the citation audit done (§ 8); the AI statement's review paragraph,
   citation clause and figures updated; the gates clean: `linkage check`, `linkage axioms --check`,
   the axiom guard with its exit code, the control-character check, the register counts. Every
   open item either closed or marked open in the text. Every interface admitted since the fidelity
   review has had its card. In a repository whose Lean serves more than one paper, also run
   `linkage release export --module <M> --dry-run` and read its closure against the statements the
   paper prints; do it early, before the paper's final read, so that separating the papers' Lean
   (the witness, probe and axiom-guard files, helper lemmas that live in the other paper's files)
   is not on the release's critical path. The affine repository's first export took 160 Lean files
   where the paper's statements needed 79, and the separation took a day after the final read.
2. **The changelog entry** headed `## <tag> — <date> — <title>`; the version chosen (`v0.x` while a
   preprint, `v1.0` at journal submission of *that module*). A multi-module repository prefixes its
   tags with the module (`cone-v0.1`), and the export carries the plain `vX.Y`.
3. **Reserve the DOI** (author): the Zenodo deposit opened as a private draft through the API, which
   prints the DOI the PDF will carry. The first release creates the concept DOI; later ones are new
   versions under it. The token is the author's and stays in the author's terminal: an assistant
   never reads, stores or asks for it.
4. **Freeze the paper.** The `\date` in `main.tex` becomes the release form (date, version, DOI
   link); for a version after the first, it also names the first release (rule 6). The draft line is
   kept in a comment for the next cycle. For a version after the first, add this version's entry to
   the version history section (rule 6; `scaffold/paper/version-history.tex.in` on the first later
   version), reworded from the `CHANGELOG.md` entry already written in checklist item 2. The PDF is
   built into the paper's own directory and its first page — and, for a later version, the version
   history entry — read. Commit.
5. **Export, build, tag.** Where the repository stays private (it holds unreleased modules), the
   release is a **verification export**: a separate public repository holding the Lean modules the
   released statements rest on, the trust boundary and the ledger, the released blueprint chapters,
   the paper and its PDF, the process account and the reviews. The export is built from scratch
   and its guard must reproduce the paper's printed `#print axioms` block. Tag the release commit
   here, commit and tag the export; the public repository is created at the author's word.
   **A public, single-module repository needs no separate public export repository** (Paper I's
   `v1.1.0`, 2026-09-27): the repository itself is already what a reader would clone, so `<export>`
   is a local staging tree, tagged and read by the Zenodo commands but never pushed anywhere on its
   own. It still sits **beside the repository, under a name of its own** (`lake-store`'s link
   needs this — #31), not inside it or reusing its name.
6. **Deposit** (author): `reserve` a draft (checklist item 3), `upload` the PDF and a zip of the
   tagged tree — which also makes the PDF the draft's default preview — then read the draft
   deposit as a stranger would (title, abstract, creator with ORCID, licence, version, date,
   related identifiers, the PDF's first page), then `publish`. If the draft's metadata was lost or
   changed since, `metadata` sets it again from `.zenodo.json`, restores the records API's
   `pids.doi` if that left it empty, and sets the preview again; `preview` alone re-sets just the
   default preview. `status` and `publish` both read the draft back and print or refuse on what a
   deposit must carry (title, creators, resource type, the reserved DOI) — a check by the script,
   not only by eye, since a bad write can empty a draft that then reads fine to a stranger who
   never compares it against `.zenodo.json`. Record the version and concept DOIs in the changelog.
7. **The library.** The librarian deposits the PDF and markdown so later sessions read the release
   by citekey, and in the same dispatch reports what the library holds on the module's subjects
   that the module does not cite.
8. **The site.** A release that is not on the research site is not published where a reader
   looks. Three things, in this order:
   - **The export publishes its channel.** Give the export repository
     `.github/workflows/docs.yml` calling article-kit's reusable workflow with the module's
     `slug`, `channel: <version>`, `push_artifacts: false` (a frozen export's released PDF is
     already committed; a CI-built copy beside it invites a mistake), and the three R2 secrets
     (`R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `CLOUDFLARE_ACCOUNT_ID`). A paper with a
     supplement passes both roots, `paper_tex: paper/main.tex paper/supplement.tex`, and the
     channel serves `paper.pdf` and `paper.supplement.pdf` (see "A paper with a supplement"
     below). Dispatch it. The channel is **write-once**: a second successful run is refused,
     because a DOI names those bytes.
   - **The hub's `constellation.json` names it.** A whole repository's paper gets a `site`
     entry; a module of a multi-module repository gets one naming `module: <its slug>`, which
     takes the title, version, export and DOI from that module's record in `modules` rather
     than restating them. `site` is a list when a repository publishes more than one paper.
     **The `slug` is a permanent public URL** — reader-facing, chosen once, never reused.
   - **The routing table follows itself.** The hub's own `notify-site` workflow dispatches
     `research-site`'s `site-sync` on the push that changed `constellation.json` (and daily,
     as a safety net); `site-sync` regenerates `src/routes.json` and the generated pages from
     the hub's `main` (`npm run build`), commits that to `research-site`'s `main` naming the
     hub commit, deploys, and runs `npm run verify`, which fails the run if a channel the
     manifest promises does not answer. Nothing to run here: see the commit on
     `research-site`'s `main` (or the `site-sync` run in its Actions tab) to know it reached
     the site, and if it failed, read that run's log — a refused `site` block, or a verify
     that found a promised channel nobody wrote. Until the manifest names it, the channel
     exists and nothing serves it — which is the order to want, not a defect. **If the
     workflow cannot run** (the read-only deploy key is missing, a new export repository is
     not yet in `research-site`'s `EXPORT_REPOS`, Actions is down), the manual fallback, from
     a machine with the hub and the export repositories checked out: `npm run routes`,
     `npm run pages` (or `npm run build`, which is both), read the diff (it is the diff that
     publishes an article), commit, push; CI deploys. Then `npm run verify`.
9. **The hub**: the items of its `RELEASES.md` (the manifest pin and `release.latest`, the thread
   page, the programme page, the log, the citation check of importing modules, the postdoc round).
10. **Open the next cycle.** Restore the draft date line at the first edit after the release; move
   the module's records to `records/<module>/`; file the general lessons to article-kit's
   `WISHLIST.md`; rewrite `notes/HANDOFF.md` for the next module.
