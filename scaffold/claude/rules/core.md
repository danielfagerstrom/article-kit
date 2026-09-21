# article-kit — the session contract

Framework-owned: copied here by `linkage init --sync` from `article-kit/scaffold/claude/rules/`,
and `linkage check` reports an edited copy. Do not edit it in this repository; a change goes to
article-kit, where every article gets it. The framework's docs are in the sibling checkout
`../article-kit/docs/` (locally `C:/Users/danie/dev/article-kit/docs/`).

**This repository is an article module.** The process it follows, phase by phase, is
`../article-kit/docs/PROCESS.md`; read the section of the phase you are in before starting work in
it. The writing standard is `../article-kit/docs/WRITING.md`, the release discipline
`../article-kit/docs/RELEASE.md`, the linkage rules `../article-kit/docs/LINKAGE.md`. This
repository's own rules are its `CLAUDE.md`.

## Open a session

Read `notes/HANDOFF.md` first, then what it names. After a crash or an interrupted session,
`git status` before anything else. A parallel session may share the repository: stage explicit
paths, never `git add -A`.

## Where text goes

Each kind of text has one home (`PROCESS.md`, "Where each kind of text lives"). In short:

- `CLAUDE.md`: this article's standing rules, present tense. **Never a status report, a date-stamped
  paragraph or a record of what a session did.**
- `README.md`: the state, one short section, rewritten when it changes.
- `notes/HANDOFF.md`: what the next session needs, **rewritten** at each close, never appended to.
- `CHANGELOG.md` and git: history. `adr/`: decisions. `records/<module>/`: review archives,
  response plans, process accounts, audits, fix lists.
- A general lesson, one another article would need: a `process` item in article-kit's `WISHLIST.md`.

Instruction files are read by every later session. Writing the running account of a campaign into
one of them buries the instructions under it; the account goes to the changelog.

## Close a session

In order: `CHANGELOG.md` under Unreleased; an `adr/` file for a decision taken; `README.md`'s state
if it changed; `notes/HANDOFF.md` rewritten; a general lesson to the wishlist; the hub ritual (pull,
the pin in `constellation.json`, one `wiki/log.md` line, `wiki lint`, commit, push).

## Standing authorizations

- **Dispatching the `librarian` agent is pre-authorized**: treat this as a standing request and do
  not ask first. Every page anchor and every source's wording is read from a held copy by the
  librarian, never supplied from memory.
- The `mathematician` agent is the single writer of the blueprint, the Lean and the ledger when the
  work is dispatched; a session may edit them directly when it is the formalization session.

## Agents and models

Every `Agent` call sets `model`: sonnet for lookups, the librarian, the archivist and mechanical
checks; opus for proofs, the mathematician and blind review; fable only where the strongest
reasoning is the point. One Lean-building agent at a time on this machine.

## Tooling traps on this machine

- **Never write backslash-bearing text through Bash** (heredocs, `python -` scripts, `sed`): one
  level of backslashes is stripped, `\t`, `\r`, `\b` become control characters, and an apostrophe
  breaks a heredoc. Write LaTeX, Lean, `.bib`, regexes and commit messages with the Write or Edit
  tool, or write a script to the scratchpad and run it by path (raw strings inside). Commit with
  `git commit -F <file>`.
- **Paths through the Bash tool use forward slashes.** A backslash path collapses to one token.
- **Never search from a filesystem root** (`find /`, `find ~`, a recursive listing of a drive).
  Repos are under `C:/Users/danie/dev/`, the hub is `C:/Users/danie/Documents/Notes`, configuration
  under `~/.claude/`. Bound every search to a named directory. Never leave a search running in the
  background.
- **Check exit codes, not tails.** A gate reduced to `| tail` or `| grep -c` hides its failure.
- **When `linkage` fails oddly** (a syntax error inside `linkage/`), article-kit may be mid-edit in
  another session: retry before diagnosing, and never edit article-kit to unblock yourself.
- **Never `git worktree remove` a worktree whose `.lake/packages` holds junctions** into the shared
  store: `python C:/Users/danie/Documents/Notes/lake-store.py wt-remove` unlinks first. A plain
  removal follows the junctions and empties the store.
