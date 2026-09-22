# Releasing a module

The rules every release follows, the checklist, and the order of the commands. General to every
article; what is the programme's (the manifest, the shared notation table, the paper labels, the
dependencies between modules, what the hub does) stays in the hub's `RELEASES.md`. Moved here from
the hub's `RELEASES.md` and Paper V's `notes/RELEASE-procedure.md` on 2026-09-21
([ADR-0001](../adr/0001-article-kit-owns-the-article-process.md)).

Articles are **modules**: focused, versioned, importing each other by reference. Preprints are
**releases**.

## Versioning the framework

article-kit is itself versioned, because every article calls its reusable workflows and installs
its CLI. The rhythm:

1. A framework change lands on `main` through a pull request; CI (`ruff`, `pytest`, the scaffolded
   article) is green. `CHANGELOG.md` gets its line under Unreleased in the same change.
2. It gets a tag when it is worth consuming: the Unreleased entry is headed `## vX.Y.Z — <date> —
   <title>`, and the author tags the merge commit (`git tag vX.Y.Z <commit>`, `git push origin
   vX.Y.Z`). Versions are `v0.x.y` until the framework is stable: a new check, workflow input or
   rule is a minor bump; a fix is a patch; anything that makes a passing article fail (a check
   turned from advisory to fatal, an input renamed) is a minor bump while `v0`, and says so in the
   changelog.
3. Each module moves its pin **when it next runs**, not when the tag appears: it changes the
   `@vX.Y.Z` of every `uses: …/article-kit/.github/workflows/…` and the `linkage_ref` input beside
   it, runs `linkage init --sync` for the rules, and reads the changelog entries between its old
   and new tag. Nothing is pushed to the modules by the framework.
4. The pin is held by a check: `linkage pins` fails on a call at `@main`, or a `linkage_ref` that is
   not a tag or a full sha, and belongs in each article's CI beside `linkage check`. A module never
   points at `@main`, not even to try an unreleased change; it pins the commit sha for that.

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
   review has had its card.
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
6. **Deposit** (author): upload the PDF and a zip of the tagged tree, read the draft deposit as a
   stranger would (title, abstract, creator with ORCID, licence, version, date, related identifiers,
   the PDF's first page), then publish. Record the version and concept DOIs in the changelog.
7. **The library.** The librarian deposits the PDF and markdown so later sessions read the release
   by citekey, and in the same dispatch reports what the library holds on the module's subjects
   that the module does not cite.
8. **The hub**: the items of its `RELEASES.md` (the manifest pin and `release.latest`, the thread
   page, the programme page, the log, the citation check of importing modules, the postdoc round).
9. **Open the next cycle.** Restore the draft date line at the first edit after the release; move
   the module's records to `records/<module>/`; file the general lessons to article-kit's
   `WISHLIST.md`; rewrite `notes/HANDOFF.md` for the next module.

## The commands

Paper V (`spatial-hemigroup-scale-space`) holds the scripts until they move into `linkage`
(ADR-0001, step 5): `scripts/export-release.py` and `scripts/zenodo-release.py`. With the module's
parameters as EXPORT:

```
EXPORT --draft                                              # a first export carries the metadata
python scripts/zenodo-release.py reserve --export <export>  # author; prints the reserved DOI
#   date line and DOI into main.tex; build into the paper's directory; read page 1; commit
EXPORT --doi 10.5281/zenodo.N --build                       # links the Lean store, builds, runs the guard
#   tag here; commit and tag the export; create the public repository (author's word); push
python scripts/zenodo-release.py upload  --export <export> --tag v0.1
python scripts/zenodo-release.py status  --export <export>
python scripts/zenodo-release.py publish --export <export>  # author; cannot be undone
```

EXPORT for a module names its chapters, paper directory, tag, headline declaration, interface roots,
process account, response plans, review directory, title, repository URL and related identifiers;
`export-release.py --help` lists them, and Paper V's `records/cone/RELEASE-procedure.md` holds the
command as run for `cone-v0.1`. Paths through the Bash tool use forward slashes. The whole
of the deposit can be rehearsed on sandbox.zenodo.org (`--sandbox`, `ZENODO_SANDBOX_TOKEN`).

What the first runs taught, now built into the scripts: the release date line may span two lines
(the gate reads the whole braced `\date{...}`); guard lines are matched to exported modules by
qualified name; exported review records have local paths replaced by `<local path>`; after a
re-export that changes the guard file, the guard is run again in the export so that the published
`axioms.txt` is its output. A release takes about three hours, most of it the Lean build from
scratch in the export.

**The rule 6 gate** belongs here too, in `export-release.py` (Q-0049; not yet built — this repository
only states what it must check): for a version after the first, the build fails unless the date line
names the first release (its date and version DOI, beside the concept DOI) and the version-history
section has an entry for the version being exported. The first version is exempt from both, the same
way it is exempt from having a version history section at all.
