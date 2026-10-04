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

*No other open requests.*
