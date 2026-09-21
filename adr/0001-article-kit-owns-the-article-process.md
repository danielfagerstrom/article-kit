# ADR-0001 — article-kit owns the article process, and instruction files hold only instructions

- **Status:** Accepted 2026-09-21
- **Mechanism:** [`docs/PROCESS.md`](../docs/PROCESS.md) (the lifecycle and where each kind of text
  lives); [`docs/WRITING.md`](../docs/WRITING.md) (the writing standard, moved from the hub);
  [`docs/RELEASE.md`](../docs/RELEASE.md) (the release discipline and procedure); the
  framework-owned session rules `scaffold/claude/rules/*.md`, copied into every article's
  `.claude/rules/article-kit/` by `linkage init --sync`; the `shape` advisories of `linkage check`
  (`linkage/shape.py`).

## Context

An article goes from idea development in the wiki hub to its own repository, and there through a
draft, a blueprint, a Lean formalization and the article. The later stages are run from the article
repository. The author found that an article session could not do its work without being told the
process from scratch, and an assessment on 2026-09-21 of article-kit, the hub and the four article
repositories (`hemigroup-causal-scale-space-kernels`, `hemigroup-kernels-ssvm`,
`spatial-hemigroup-scale-space`, `scale-space-foundations`) found four causes.

1. **No file described the process.** article-kit held the checkable machinery (the linkage spec,
   the drafting gate, the publication template, the reviewer contract, two skills). The lifecycle
   itself lived in hand-written session prompts (`notes/PROMPT-module-b.md` was the most complete
   account of the article stage anywhere), in rules each repo's `CLAUDE.md` had rediscovered
   (statement skeleton first, the proof of record follows the Lean route, the merge gates), in
   repo scripts (`export-release.py`, `zenodo-release.py`, `count-register.py`), in the hub
   (`writing-style-and-ai-use.md`, `RELEASES.md`), and in per-project memories, which no other
   repository can see.
2. **What existed was not reachable where the writing happens.** The writing standard was named in
   one clause of one repo's status section; neither the `draft-reviewer` nor the `mathematician`
   definition mentioned it. The module-B draft was written without it, and the author's review
   corrected, section after section, what it forbids (Paper V's
   `notes/LESSONS-for-article-kit.md`, item 5).
3. **Instructions were buried under records.** The pilot repo's `CLAUDE.md` had grown to 6,900
   words, three quarters of it a dated status diary; its handoff note to 14,700 words, its
   "start here" block to 480 lines. A session loading them spent its budget on the history of
   campaigns it was not running and took the shape as licence to append more. The hub met the same
   failure on a wiki page and fixed it (hub ADR-0014 and the `wiki lint` shape check); the fix
   never reached the article repositories.
4. **Lessons had no way back.** A rule learned in one article (the verbatim transcription beside
   every ledger paraphrase, learned at the Paper I SSVM extraction) did not reach the next, which
   admitted a false axiom for want of it.

## Decision

**All general knowledge about writing an article lives in article-kit or is referred from there,
and every file an agent or a human reads as instructions holds only the current instructions it is
for.**

1. **The process is written down once, in article-kit.** `docs/PROCESS.md` is the map: the phases
   with their entry and exit gates, the file or skill that runs each, and where each kind of text
   lives. The writing standard moves from the hub to `docs/WRITING.md`; the general part of the
   hub's `RELEASES.md` (rules 1, 2, 5, the checklist) and the pilot's release procedure become
   `docs/RELEASE.md`. The hub keeps what is the programme's: the manifest, the shared notation
   table, the paper labels, the dependencies between modules, what the hub does at a release.
2. **It reaches every article session through framework-owned rules.** `linkage init` copies
   `scaffold/claude/rules/*.md` into `.claude/rules/article-kit/`, and `linkage check` reports an
   edited copy, as it already does for `blueprint.sty`. One rule loads at every session start
   (the session contract: how to open and close a session, the tooling traps, the standing
   authorizations, the model rubric); the others are path-scoped and load when a matching file is
   read, so the writing rules are in context when a session opens `paper/`, the ledger rules when
   it opens `blueprint/AXIOMS.md`, the Lean rules in `Formalization/`. The rules are short and
   point into `docs/`, which a session reads from the sibling checkout (`../article-kit`).
   Copies rather than `@`-imports because a copy works unchanged in a cloud session and on any
   machine, needs no approval dialog, and its drift is already detectable.
3. **Each kind of text has one home, in every repository.** Hub ADR-0014's table, extended to the
   article repos: the repo `CLAUDE.md` holds the article's own standing rules and nothing dated;
   `README.md` holds the state, as one short present-tense section; `notes/HANDOFF.md` holds what
   the next session needs and is *replaced* at each session close, never appended to; history goes
   to git and `CHANGELOG.md`; decisions to `adr/`; review and process records to `records/<module>/`,
   which no instruction file quotes. A session prompt is not a file: a phase is started by naming
   its skill or its section of `PROCESS.md` and the handoff.
4. **The shape is checked.** `linkage check` gains `shape` advisories over the instruction files
   (`CLAUDE.md`, `README.md`, `notes/HANDOFF*.md`, the rules): a word budget per file, dated record
   blocks, and headings that name a record (Status, History, Progress). Advisories, like the hub's
   shape warnings: a worklist and a signal, not a gate that can stop a release.
5. **Lessons come back through the wishlist.** A general lesson learned in an article goes to
   article-kit's `WISHLIST.md` as a `process` item at the session close that learned it, and from
   there into `docs/` or a rule. A lessons file inside an article repo is a sign this failed.

### The plan

1. *This ADR*, `docs/PROCESS.md`, the rules, the scaffolded `CLAUDE.md` and handoff templates, the
   shape check.
2. *The writing standard and the release discipline move*; every pointer to the old locations is
   updated in the same change (the hub's `CLAUDE.md`, the `draft-reviewer` agent, the
   `rework-chapter` skill, the drafting gate, the article repos).
3. **The cleanup, everywhere.** Every file used as agent or human instructions, in article-kit, the
   hub and each article repo, is rewritten to its current state and its purpose. What documents
   an ongoing or finished process is deleted when git and the changelog already hold it, or moved
   to the home the table names: status diaries out of `CLAUDE.md`, finished session prompts deleted,
   running records out of handoff notes, completed roadmap items out of roadmaps, general rules out
   of per-project memories and into the rules. The hub did this for its wiki pages under ADR-0014;
   it is now done for every instruction file in the constellation, the hub's own included.
4. *The lessons of Paper V's module B* are filed to their homes, item by item.
5. *Scripts* that every article needs (`export-release.py`, `zenodo-release.py`,
   `count-register.py`) move into `linkage` as subcommands parameterized from `linkage.toml`.
6. *Distribution of skills and agents* as a Claude Code plugin declared in each article's
   `.claude/settings.json`, piloted locally and in a cloud session before any repo depends on it;
   until then the junctions and the hub's `sync-agents.sh`.

**The pilot is `spatial-hemigroup-scale-space`**, whose module C is the next article: its cleanup is
done with steps 1 to 3, and module C is opened from the handoff and `PROCESS.md` alone, with no
hand-written prompt. The other three repositories follow the pilot.

### Rejected

- **`@`-importing article-kit's docs from each `CLAUDE.md`.** An import loads the whole file at
  every session start whatever the session does, resolves outside the project (an approval dialog
  per project, and a path that differs between this machine and a cloud session), and gives no
  scoping. Path-scoped rules load what the files in hand need.
- **Keeping the writing standard in the hub and pointing to it.** Its readers are the article
  sessions, the `draft-reviewer`, the drafting gate and the publication template, all of which are
  article-kit's; the wiki notes that also follow it can point across as easily.
- **A capped status section in `CLAUDE.md`.** Rejected in the hub for the same reason (ADR-0014):
  still on the context path of every session, still a duplicate of the changelog, and a cap invites
  filling it.
- **Session prompts as the way a phase starts.** They restated the process each time, drifted
  between copies (`PROMPT-external-review.md` existed in four variants), and were not found by the
  next article.

## Consequences

- An article session knows the process from what loads by itself: the session contract at start,
  the phase rules when it opens the phase's files, `PROCESS.md` one link away. A new article repo
  gets all of it from `linkage init`.
- Framework-owned rules cannot be quietly rewritten by a session, since `linkage check` reports the
  edit; a session that wants a rule changed says so in its report, and the change is made here.
- Every article repository carries a copy of the rules and must run `linkage init --sync` to get a
  change: the cost ADR-0008 in the hub already accepted for the LaTeX scaffolding.
- The cleanup deletes text. Nothing is lost: git holds every version, and the records that are
  deliverables (review archives, process accounts, response plans shipped in releases) move to
  `records/` rather than away.
- The hub's `writing-style-and-ai-use.md` and the general half of `RELEASES.md` are gone from the
  hub; its ADRs that name them (0015, 0017) are history and keep their wording.
