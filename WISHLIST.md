# Wishlist — requests to the framework from other constellation members

Inbound feature requests from other members of the research constellation — the wiki hub, the
librarian, and **any article repo** — for things they want *from this repo*: `linkage` checks and
CLI behaviour, manifest/emitter capabilities, blueprint scaffolding, reusable CI, the shared
mathematician agent, the process docs.

**The pattern.** A member working in its own repo, when it finds it needs something from the
framework, records the need here instead of context-switching to build it — then keeps going with
its own work. The maintainer triages these into [`ROADMAP.md`](ROADMAP.md) on its own schedule.
Same one-way principle as every cross-member reference: the requester states a need; the owner
decides whether and when to fulfil it. The mirrors point the other way: `notes-wiki/WISHLIST.md`
(requests *to the hub*), `library/WISHLIST.md` (requests *to the librarian* — where this pattern
began), and each article repo's own `WISHLIST.md`.

**What belongs here rather than in an article's wishlist.** Anything a *second* article would want
too. A request for a blueprint node, a proof, or a ledger entry is that article's; a request for a
new check, a manifest field, or a scaffolding change is the framework's. When in doubt, ask whether
fulfilling it would mean editing `linkage/`, `scaffold/`, `.github/workflows/` or `docs/` — if so,
it belongs here.

**Format.** One `##` section per request: what is wanted, who wants it, why (what it unblocks on
their side), and — if the requester has one — a suggested shape. Date it. **A fulfilled entry is
deleted** in the commit that fulfils it, whose message names it: git and `CHANGELOG`-style commit
messages hold the history, and this file holds only what is still wanted (ADR-0001).

**`process` items.** A general lesson an article session learns about the process (a rule the
next article would need, a step that was missing, an instruction that was not found) is filed here
as a `process` item at the close of the session that learned it, with its evidence. The
maintainer turns it into a change to `docs/`, a session rule in `scaffold/claude/rules/`, an agent
or a skill, and deletes the item. A lessons file inside an article repository means this failed.

---

## process: skills and agents as a Claude Code plugin

**Wanted by** ADR-0001 step 6, 2026-09-21.

The shared skills (`fidelity-review`, `tighten`) reach an article session only through user-level
junctions (`tighten`'s is not installed on this machine), and the shared agents through the hub's
`sync-agents.sh`, which runs only when a hub session starts. **Suggested shape:** article-kit as a
plugin (`.claude-plugin/plugin.json`, `skills/`, `agents/`) in a marketplace declared by each
article's scaffolded `.claude/settings.json` (`extraKnownMarketplaces`, `enabledPlugins`). The docs
say this loads in single-repository cloud sessions too. Pilot on one repository, locally and in the
cloud, before any other depends on it; note that plugin agents rank below `~/.claude/agents/`, so
the synced copies must be removed when the plugin takes over, and that plugin skills are
namespaced (`/article-kit:fidelity-review`).

---

## Sync shared sub-agents from an article session, not only from a hub session

**Wanted by** the wiki hub, 2026-08-15. Falls out of closing your `draft-reviewer` wish.

**What.** A `SessionStart` hook in `scaffold/`'s `.claude/settings.json` that keeps the constellation's
**shared** sub-agents current in `~/.claude/agents/` — the job the hub's `.claude/sync-agents.sh` does
today, running only when a *hub* session starts.

**Why.** Claude Code registers agents when a session starts, so a shared agent is installed user-level
and the installed copy is derived from whichever repo owns it (hub `adr/0008`; the mechanism exists
because an installed `librarian` was once found 12 days and 228 lines behind its source). But the sync
fires from one repo's hook. That was fine while both shared agents — `librarian`, `mathematician` — were
dispatched *from* hub sessions: the session that needed them was the session that refreshed them.

`draft-reviewer` breaks that coincidence. It was project-scoped to the hub and therefore invisible from
an article session, which is exactly where prose review is now wanted, since with one repo per article
the author drafts in the article repo. The hub has made it shared (its `AGENTS` table gained a `.`
sentinel for hub-owned agents; ownership stays with the hub, as the reviewer also targets wiki notes).
So it is the first shared agent used **mainly from article sessions** — and an author who works in an
article repo for a week gets whatever their last hub session installed, with nothing announcing it. The
failure mode is a silently stale reviewer, which is the same failure `adr/0008` was written to end,
reappearing one repo over.

**Suggested shape.** Cheapest correct version: scaffold a hook that locates the hub (`$WIKI_VAULT`, then
the usual candidate sweep) and runs its `sync-agents.sh`, staying silent when everything is current and
never blocking a session start — the script already has both properties and a `--check` mode for CI. If
you would rather the framework not depend on a hub script, the alternative is to lift the ~60 lines of
table-plus-copy into `linkage` and have every repo, hub included, call that; then the table becomes
framework data, which may be where it belongs anyway.

**Not urgent, and the hub is not blocked.** `--check` still reports staleness, and the local failure is
a stale agent rather than a missing one. Recorded now because it is the kind of gap that is obvious
while the context is fresh and invisible six weeks later.

---

## Relabel the dependency graph's orange border for the statement-first workflow

leanblueprint's legend describes the orange border (`\notready`) as "the statement of this result
is not ready to be formalized; the blueprint needs more work". Under the constellation's
statement-first convention (`Formalization/Skeleton/`, the `notready` middle state), a `\notready`
node is one whose statement is typed and reviewed and whose proof is pending or whose interface is
unadmitted — the opposite of "needs more work on the blueprint". The colouring is right; only the
description misleads a reader of the published graph (raised on Paper V's graph, 2026-09-10).

leanblueprint lets a document redefine a colour and its description (its `blueprint.py` reads
`node_type`, `color`, `color_descr` from a command and extends the legend from them at post-parse),
so the fix is one line in the framework's scaffolding, not in any article: override the
`not_ready` description to read "statement typed and reviewed; proof pending, or an interface not
yet admitted". Keep the colour. Every article gets it on the next scaffold sync.

---

## `linkage paper` checks only one main document when a repository holds several papers

`paper.lint` takes the first source carrying `\begin{document}` across *all* of `cfg.papers`
(`linkage/paper.py`, `src.main = next(...)`), so in a repository with two papers only one main
document gets the declarations, abstract-length and `\tag`-numbering checks; the other paper's
front and back matter go unchecked while the run reports `PAPER LINT OK`. Seen in
spatial-hemigroup-affine after its split into `paper/` and `paper-iso/` (its ADR-0001, #53,
2026-10-04): the summary line names `paper/main.tex` only. Paper V's `paper-b/` and `paper-c/` are
fragments without a main document, so the gap did not show there. A second symptom of the same cause: the
declaration headings are counted across *both* directories, so `paper/main.tex` reported "4/4
declarations" while it had none and `paper-iso/` had all four. The affine repository checks its second
paper with a local script meanwhile (`records/affine/check-paper-iso-backmatter.py`, #54).

Suggested shape: group the sources by paper directory and run the main-document checks once per
directory that has a main document (a directory of fragments stays the normal "no main document"
case), printing one `main document …` line per paper and prefixing each finding with its directory.
The reference and cite-key checks can stay global, since `\ref`s across papers are already resolved
against the union.

---

## process: a proof change mirrors into the paper in the same pull request

Lesson from spatial-hemigroup-affine (Paper VII, 2026-10-05). The Lean session rewrote blueprint proofs
to the Lean route (`% CHANGED ... proof rewritten to the Lean route`) and merged them, while the papers
transcribe those proofs verbatim; each merge left the papers' copies drifted, and a separate mirror pull
request was needed four times in one day (#58, #62, #66/#67, #69), each racing the next Lean merge.
PROCESS.md § 7 says "changes the paper forces on shared text are made in the blueprint and
re-transcribed (the article mirror)", but not the other direction: who mirrors when the blueprint
changes for its own reasons (a formalization rewrite, a referee fix).

Done: PROCESS.md §§ 5 and 7 now each state the rule in both directions (Q-0355). Still open: a
session rule in `scaffold/claude/rules/` carrying the same wording as template content for every
article repository's `.claude/rules/` (the affine repository's own version stays local to its
`CLAUDE.md`, #69); and, optionally, a `linkage check --strict-proofs` that fails on drift introduced
by the branch (drift present on the base stays advisory), so CI enforces it.

---

## `\ledger{}` for an entry of a required module's ledger

From the same pull request (blind-review finding IFN-3). The affine module's Lean spends one interface
of Paper V's package (`SpatialLine.fourier_toolbox_levy_unique`, V's ledger A3), and it is included by
reference since Q-0298. Its blueprint interface node `prop:line-levy-unique` is `[A]` but has no form
to ground it in: `\ledger{A3}` would resolve against this module's own A3. Check 7 passes today only
because the prose says "entry A3 of [V]'s axiom ledger", which matches `A\d+`; a rewording would fail
it. The manifest also projects `ledger: []`. Suggested: `\ledger{V:A3}`, resolved through the
`include` line of `trust-boundary.txt` against the required module's `AXIOMS.md`, and projected into
the manifest with its module.

---

## process: writing rules from an author's section review (Paper VII, pass 6)

The author's first comments on the isotropic paper of spatial-hemigroup-affine (2026-10-06, PROCESS.md
§ 8 pass 6, its introduction), after passes 1–3 and two blind reviews had passed it. Each is a general
rule; the first two are not in `WRITING.md` or `PUBLICATION-TEMPLATE.md`, the third is and was not
enforced:

1. **Programme-internal labels never reach the reader.** "the line paper [V] [2] and its cone module
   [B] [3]": the roman numerals of the programme's papers and the letters of their modules mean
   nothing to a reader. A cited paper is named as any paper is (author and year, or the bibliography
   number with a word of what it is). Where shared statements carry such a label (`[V, Thm.~7.3]` in a
   blueprint statement transcribed verbatim), the label should be a macro the blueprint and the paper
   define differently, as `\ledger{A3}` already prints the paper's cited-fact name: the blueprint keeps
   its short form, the paper prints a real citation, and `linkage check` still compares source text.
   Suggested: a `WRITING.md` § 1 rule, a scaffold macro (`\prog{V}{Thm.~7.3}` or similar), and a
   `linkage paper` advisory on a bare `[V`/`[B`-style label in paper prose.
2. **The introduction poses the questions before the answers, in plain language.** The paper's
   "answer" paragraph summarized every result with its technical detail in one paragraph (classes,
   polar profiles, thresholds, Bessel functions, extreme rays), and its prior-work paragraphs did the
   same; the author found them unreadable. The introduction says what is asked and why, then what is
   found, at the level of a reader of the abstract; the technical statement of each result is its
   section's. Suggested: a line in `PUBLICATION-TEMPLATE.md` § B.2 and a reviewer flag
   ("introduction states a result in more technical detail than the question it answers").
3. **Every name carries a real reference, and a term below the reader's floor is cited where it is
   introduced** (`WRITING.md` § 3 has the second half). Missed by every pass: "due to Zolotarev and to
   Wolfe" citing only Sato's remark that names them, and self-decomposable laws and the Matérn
   covariance introduced without a source. Suggested: the register reviewer's vague-attribution tag
   extended to a named author without a bibliography entry of their own, and to the first use of a
   named class or family without a citation.
4. **A cited result is stated with its citation, not re-justified** (the author on § 2, same day): "if we
   cite something, we don't need to explain how it is proved or what axioms it is based on, it is the
   job of the cited paper." The papers had sentences retelling how a cited paper proves a fact and on
   which axioms it rests ("In [B] the existence of the delay law ..."), a habit carried over from the
   blueprint's annotations, which record exactly that for the trust base.
5. **No sentence whose only content is what is *not* used** ("No statement of this paper uses those
   facts ..."): it does not clarify anything for a reader; what rests on what is said once, in the
   trust-base subsection. Same origin: blueprint-annotation vocabulary leaking into paper prose.
6. **A concept a reader of the target venue does not know is introduced, not only defined**: the
   author asked for an introduction to subordination "for a computer vision reader" before its
   definitions — what it is in plain words, why it matters to the paper, one familiar example.

   Suggested for 4–6: a `WRITING.md` § 2 line on blueprint vocabulary in paper prose (provenance,
   non-use, axiom accounting belong to annotations and the trust base), and register-reviewer tags
   for each.

The author on § 3 of the same paper (2026-10-10):

7. **A result the paper restates is cited at its restatement.** § 2 restated the earlier papers'
   definitions and theorems, and § 3 still cited the earlier papers ("in the sense of [V, Def. 3.1]",
   with the axioms listed again inside a lemma). Once a statement has a number in this paper, every
   later use refers to that number; the original's number stays on the restatement only. The cause is
   again a blueprint statement transcribed verbatim: the blueprint has no § 2, so it cites the source.
   Suggested: a second macro beside the label macro of rule 1, taking the paper's own label
   (`\restated{V}{Def.~3.1}{def:line-family}`), which prints the located citation in the blueprint and
   `Definition~\ref{...}` in the paper; and a `linkage paper` advisory on an external located citation
   whose target the paper restates (the restatement's title names it).
8. **A subsection opens by saying what it does and why it works, before its first statement.** "Now it
   is basically a list of statements": two sentences and four lemmas. Rule 6 at the scale of a
   subsection: the idea in the reader's own terms (here a projection of a kernel onto a line, the
   projection-slice theorem), then the plan. Suggested: a reviewer flag on a subsection whose prose
   before the first numbered statement is under some length, and on a definition introduced with no
   sentence saying what it is for or how it relates to the notation already in use ("a reminder that
   `k_d` comes from (2.1)").
9. **Axioms are stated as a definition, at the level the programme states them, before any
   reformulation.** The paper defined its families on kernels and gave the operator axioms inline, in a
   paragraph and inside a lemma, because the kernel theory was proved first. The order of proof is not
   the order of presentation: the definition a reader of the series expects comes first, the
   equivalent working form second, and a lemma connects them. Suggested: a line in
   `PUBLICATION-TEMPLATE.md` on a paper in a series (same order of axioms, definition, representation
   lemma, classification as its predecessors).

The author on §§ 3.3, 3.4 and 4 of the same paper, having read it to the end (2026-10-10):

10. **A results subsection says why its result is interesting before it proves it.** "Very technical
    and I am not completely sure why the results are interesting": the two subsections stated correct,
    formalized theorems, with the tools before the theorem, and the author of the programme could not
    say what a reader gains. Two blind register reviews and a scope audit had passed them: no pass asks
    "so what". Each subsection opens with the question in the reader's terms, what turns on the answer,
    and the main result by number; the main theorem comes before the lemmas that are its tools; one
    example the reader knows carries the result (here the Matérn kernel). Suggested: a question in the
    drafting gate per results section ("what does the venue's reader do differently, or understand, for
    knowing this"), answered in one sentence in the records before the section is written, and a
    reviewer flag on a subsection whose first numbered statement is a tool.
11. **The last section is a conclusion.** The paper ended on "Open problems", as the blueprint's last
    chapter does. A paper ends by saying what it showed and what that means; open problems are a
    subsection of it. Suggested: `PUBLICATION-TEMPLATE.md` names the section and what it holds, and
    `linkage paper` gives an advisory when the last numbered section before the back matter is not a
    conclusion or discussion.

The author on the abstract, § 1 and § 1.1 of the same paper, after its rewrite (2026-10-12):

12. **Where a paper passes from its field's vocabulary to another's, it says so in a sentence for
    the field's reader.** "From 'So the kernels from scale zero are the dilations of one law.' and
    forward the language change from scale space theory to probability theory. That is of course
    necessary as the rest is based on results from there. But a sentence saying that would be helpful
    for the scale space audience, so that they understand why everything that follows is stated in
    terms of laws etc." The introduction had glossed each borrowed term at first use (rule 3) and
    never said that the vocabulary changes, nor why. One or two sentences at the point of change: what
    the object is in the other field, that the results the paper builds on are stated there, and the
    dictionary in a clause (here kernel: law; transfer function: characteristic function; which words
    stay). The same comment found a second letter for a frequency used before it was introduced: a
    notation that differs between the two settings is said where the second form first matters.
    Suggested: a line in `WRITING.md` § 0 beside "Teach", and a reviewer flag on the first paragraph
    in which three or more terms of another field's vocabulary appear with no sentence announcing
    the change.
13. **A statement that rests on a published theorem is presented as resting on it, never as a
    hypothesis or a condition.** "'which the cone paper leaves as a hypothesis and this paper does
    too.', what does that mean? Is it a conjuncture? Or does we prove it in terms of some cited
    theorem?" and, of the trust-base sentences on the same clause, "It gives the impression that we
    have just invented an hypothesis out of thin air. When we in fact have cited a published result."
    The clause was an implication in the blueprint because its Lean takes the premise as given, and
    the paper had carried the blueprint's accounting ("conditional", "assumes", "keeps it as a
    hypothesis") into the statement's title, its lead, the paragraph after it and § 1.1. The logical
    form of a formalized statement may stay an implication; the prose says where the premise is in
    print, once, and the trust-base subsection says that the formal statement takes it as given.
    No citation goes inside the clause itself where the node is `\leanok` (it would be an assertion
    no declaration states). Suggested: a `WRITING.md` § 3 line under "Borrowed facts are stated, not
    folded in", and a reviewer flag on "hypothesis", "conditional", "assumes" or "leaves open" within
    a sentence of a citation.
14. **The trust-base subsection says what is, and carries no sentence whose content is what was not
    done when another section owns that.** "'No human, the author included, has reviewed the formal
    statements (see the statement on the use of AI at the end of the paper).', Remove, we focus on
    what is not what isn't, and this is discussed in the AI statement." Rule 5 for the trust base
    itself: who compared the formal statements with the printed ones is said positively (AI agents,
    in a review the subsection describes), and who did not is the AI statement's. A boundary a reader
    needs in order to know what is checked stays, in the positive where one exists ("proved in print",
    "computed by scripts", "the formal statement takes the family as given"); the lists of what is
    machine-checked and what is not are such boundaries. Suggested: a sentence in `WRITING.md` § 4
    ("The trust base is owned by one subsection") and in § 6 rule 3, which already keeps the trust
    boundary out of the AI statement and does not yet keep the AI statement's content out of the
    trust base.

---

## The site workflow builds one TeX root per paper, so a paper with a supplement is served as its full document

**Wanted by** spatial-hemigroup-affine (Paper VII), after the release `iso-v0.1`, 2026-10-14
(hub Q-0456, Q-0457).

The reusable `docs.yml` builds each paper from one file (`paper_tex`, and the `tex` of each entry of
`extra_papers`) with one Tectonic run. The isotropic paper is two roots, `main.tex` and
`supplement.tex`, which refer to each other through `xr-hyper`, reading the other root's `.aux`;
built alone, `main.tex` has every reference into the supplement unresolved. The export's `docs.yml`
therefore builds `paper/full.tex`, the paper and the supplement as one document, and the site
serves that, while the deposit holds the two PDFs. `research-site#12` gave the site page a
`paper_label` and a list of `files`, so that the page says what it serves and links the two
deposited PDFs: a work-around on the site's side. The repository's own draft site has the same
fault (its `iso.pdf` is `paper-iso/main.tex` built alone). **Suggested shape:** either a paper's
`tex` may be a list of roots, built in order and then once more so that each `.aux` exists when the
other reads it, each published under its own name; or, for a frozen export (`push_artifacts:
false`), the workflow publishes the committed released PDFs (`<stem>-<tag>.pdf`,
`<stem>-<tag>.supplement.pdf`) instead of building, since the DOI names those bytes and a rebuild
can only differ from them.

---

## `linkage_ref` as a full commit sha: allowed by `RELEASE.md` and `linkage pins`, refused by `lean.yml`

**Wanted by** spatial-hemigroup-affine (Paper VII), 2026-10-14 (hub Q-0452).

`RELEASE.md`, "Versioning the framework", rule 4, says that a module needing an unreleased change
"pins the commit sha for that", and `linkage pins` accepts a `linkage_ref` that is a tag or a full
sha. The reusable `lean.yml` installs `linkage` with `git clone --depth 1 --branch "<linkage_ref>"`,
and `--branch` takes a branch or a tag only: with a sha the clone fails and the job stops at its
first `linkage` step. Q-0452 pinned a sha of the branch that became `v0.4.0`, and CI failed until
the tag existed. **Suggested shape:** `git init`, `git fetch --depth 1 origin <ref>` and `git
checkout FETCH_HEAD`, which take a tag, a branch or a sha alike; or, if a sha is not to be
supported, rule 4 and `linkage pins` say so.

---

## process: Zenodo lists the zip first, and a published record's files cannot be reordered

**Wanted by** spatial-hemigroup-affine (Paper VII), release `iso-v0.1`, 2026-10-14 (hub Q-0456).

`linkage release zenodo upload` sends the paper's PDF, the supplement's PDF and the zip of the
tagged tree, in that order (`RELEASE.md`, "A paper with a supplement": the paper's PDF "stays the
default preview"), and the published record lists the zip first. A published record's files cannot
be changed or reordered; only a new version can. So the page a reader lands on offers the source
archive before the paper. **Suggested shape:** the sandbox rehearsal that `RELEASE.md` describes
becomes a checklist step before a repository's first real deposit, and what it reads includes the
file order and the default preview by name (`zenodo status` could print both from the draft, and
`publish` could refuse when the first file listed is not the paper's PDF). The draft records of
the current Zenodo carry a files `order` beside `default_preview`; whether the deposit API that
`upload` uses can set it was not checked.

---

## process: run the export's dry run early when a repository holds two papers' Lean

**Wanted by** spatial-hemigroup-affine (Paper VII), release `iso-v0.1`, 2026-10-14 (hub Q-0451,
Q-0452).

The first export of a repository holding the Lean of two papers, one of them being released,
exported 160 Lean files where the released paper's statements need 79. The closure came in through
the files every release has besides its statements (the witness file, the probe file and the axiom
guard each imported the library root) and through helper lemmas that lived in the other paper's
files and were used by this paper's proofs. Separating the two (a library file naming the paper's
own modules, one probe file per paper, the helpers moved) took a day, and it came after the paper's
final read, when the release was otherwise ready. `RELEASE.md` says that a root importing the
library whole brings the library and that the dry run prints the closure, but not when to look.
**Suggested shape:** checklist item 1 ("before anything is frozen") gains `linkage release export
--module <M> --dry-run`, its closure read against the statements the paper prints, for a
repository whose Lean serves more than one paper, and early enough that a separation is not on the
release's critical path; and `PROCESS.md` § 5 says that in such a repository a helper lemma goes in
a file of the first paper that needs it, or in a shared file that imports neither paper's results.

---

## `linkage release export` does not remove a file it no longer writes

**Wanted by** spatial-hemigroup-affine (Paper VII), release `iso-v0.1`, 2026-10-14 (hub Q-0452;
its `records/affine/RELEASE-procedure-iso.md`, §§ 2 and 7).

An export written over an earlier one keeps the earlier one's files. After the closure shrank, the
81 Lean files the second export no longer wrote would have been built with the library (its
`globs` take every file of the directory) and committed at `git add -A`; and a supplement PDF
renamed between two exports was left beside the new one. The directory was cleared by hand, which
first needs `lake-store.py unlink` on the export, since a recursive delete can follow the package
links into the store. **Suggested shape:** the export removes the files of its tree that it did
not write this time, keeping `.lake/`, `.git/` and `.zenodo-deposition.json`; or it refuses to
write into a directory holding files it would not write, and lists them.

---

## process: what a two-paper repository's first export found missing in the repository itself

**Wanted by** spatial-hemigroup-affine (Paper VII), release `iso-v0.1`, 2026-10-13 (hub Q-0451;
`records/affine/RELEASE-procedure-iso.md`, § 6, "In this repository" and "Known and left"). Not in
the `v0.4.0` changelog, which has the faults of `linkage` that the same run found.

1. There was no `LICENSES/`, which every Lean header names and which the export copies; when it is
   absent the export copies nothing and says nothing. Suggested: the scaffold creates `LICENSES/`
   with the two texts, or the dry run reports its absence.
2. The export renames a paper's directory to `paper/`. The scripts that draw the figures into the
   paper's directory named it by its path in the repository (`paper-iso/`) and broke in the export;
   each now takes whichever of the two exists. Scripts exported as the record of how a list or a
   report was made read the repository's layout and do not run in the export at all. Suggested: a
   line in `RELEASE.md` at `extra_files`: a script exported to be run finds the paper's directory
   under either name.

---

## A statement's title is cut at the first `]`, even inside braces

**Wanted by** spatial-hemigroup-affine (Paper VII), 2026-10-14 (hub Q-0457).

`split_env_title` (`linkage/parse_latex.py`, `ENV_TITLE`) ends a statement's optional title at the
first `]`. A title carrying a located citation inside braces, as LaTeX requires (a title
`the classification, {\cite[Thm.~3.6]{key}}`), is cut inside the citation, and the rest of the
title is compared as the start of the statement: `linkage check` reported all six such
restatements as "drifted after 0 chars". The affine paper now writes the citation through a macro
with no bracket (`\prog{Iso}{Thm.~3.6}`). **Suggested shape:** match the title with the brace depth
counted, as LaTeX reads an optional argument.

---

## process: the swallowed-prose gate is in the scaffold, but `linkage init` never copies it

**Wanted by** spatial-hemigroup-affine (Paper VII), writing-rules pass, 2026-10-14
(`records/affine/PASS-writing-rules-affine.md`, PR #138).

Appendix C of the affine paper printed a broken sentence ("…where they name them.of the Fourier
transform…"). A `% CHANGED` marker in the middle of a line had made the rest of that line a comment,
and passes 1–3 and two blind reviews missed it. PROCESS.md § 5 and the `lean.md` session rule both
say "the scaffolded `scripts/check-swallowed-prose.py`" gates this. The affine repository has no
such script. The scaffold does hold it (`scaffold/scripts/check-swallowed-prose.py`, added in
f79c6fa, Q-0238). But `linkage/scaffold.py` lists it in neither `FRAMEWORK_OWNED` nor `SEEDED`, so
neither `linkage init` nor `linkage init --sync` ever writes it into an article. Its sibling
`scaffold/scripts/check-control-chars.py` is in the same position: articles have it only as hand
copies. The test (`tests/test_check_swallowed_prose.py`) copies the script into its fixture with
`shutil.copy`, which is why nothing caught the missing entry. And nothing runs it: no workflow in
`.github/workflows/` calls either script, and `linkage check` does not include it. So the gate
works only in spatial-hemigroup-scale-space, the repository it was ported from, which has its own
copy. **Suggested shape:** (1) add both scripts to `FRAMEWORK_OWNED`. Then `--sync` delivers them,
`linkage check` reports an edited copy, and a test can scaffold an article and check that both are
there. (2) Run the gate without anyone having to remember it. The script compares against a base
revision, so the natural place is a pull request: one of the reusable workflows articles already call
(`manifest.yml` or `lean.yml`) runs `python scripts/check-swallowed-prose.py <the PR's base sha>` and fails on a hit. Or
`linkage check` runs it against the default branch's merge base, and reports it as advisory when
that base cannot be reached.

---

## `linkage check` pairs a proof with the statement above it before reading its `% proof of` marker

**Wanted by** spatial-hemigroup-affine (Paper VII), writing-rules pass, 2026-10-14
(`records/affine/PASS-writing-rules-affine.md`, PR #138).

Writing rule 10 puts the main theorem first, so § 3.4 of the affine paper states
`thm:affine-rigidity` and `thm:rank-deficient-step` before the three lemmas that prove them. The
two theorem proofs follow the lemmas, each under a `% proof of <label>` marker. Where nothing
separated the last shared lemma from the first of those proofs, `linkage check` compared the
theorem's proof with the lemma's proof of record. The error went away only when a printed sentence
came between them ("With the three lemmas the two theorems are proved, the single step first.",
`paper/04-classical.tex:536`). The cause is in the code: `paper_markers` (`linkage/artifacts.py`)
first tries `PROOF_AHEAD` (`linkage/parse_latex.py:221`), and that pattern skips whitespace and
*any* comment line before `\begin{proof}`, including a `% proof of` line that names a different
label. It looks at the marker (`floating_proofs`) only when it finds no adjacent proof. So the
proof is filed twice: under the theorem, through its marker, and under the lemma, as the lemma's
adjacent proof. The lemma's report is then wrong (it shows drift against the wrong proof), and
`--pin-shared` would pin the lemma to that wrong text. LINKAGE.md rule 4 calls the marker "explicit"
and says a moved proof is "matched by label", but nothing in it says what happens when the marker
and adjacency disagree. **Suggested shape:** an explicit marker takes precedence over adjacency. If
the nearest non-blank line above an adjacent `\begin{proof}` is a `% proof of <label>` marker
naming a label that is not among this statement's labels, that proof is not adjacent to this
statement. The statement then falls through to the lookup by label, to `% proof omitted`, or to the
"neither adjacent nor matched" finding, exactly as if the proof were elsewhere. A
`[Proof of …\ref{x}]` heading naming another label could be given the same precedence. Add a
sentence to rule 4 ("a `% proof of` marker overrides position") and a test with the main-theorem-
first layout.

---

*No other open requests.*

---
