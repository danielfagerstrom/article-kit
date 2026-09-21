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

## process: `linkage axioms --check` requires the verbatim transcription

**Wanted by** `spatial-hemigroup-scale-space` (module B, lesson 1), 2026-09-21.

`LINKAGE.md` rule 5 now requires every ledger entry to carry the source's wording verbatim, in the
entry or in `blueprint/AXIOMS-verbatim.md`. Nothing checks it. **Suggested shape:** an entry that
grounds an admitted interface name and has neither a `**Verbatim:**` block nor a section of the
same id in the verbatim companion fails `linkage axioms --check`; an unadmitted entry gets an
advisory. The evidence: ledger A10 of Paper V, a paraphrase that dropped Sato's slowly varying
factor, admitted as a false axiom and found by the first external review.

---

## process: an interface admitted after the fidelity review re-opens its card

**Wanted by** `spatial-hemigroup-scale-space` (module B, lesson 2), 2026-09-21.

The fidelity review read each admitted interface against page images; the three A10 names were
admitted five days later and never had that pass. **Suggested shape:** a standing rule in the
`fidelity-review` skill (admitting a name re-opens its card, and the interface pass runs before the
name is relied on). The rule is already in `scaffold/claude/rules/ledger.md` and `docs/PROCESS.md`
§ 6; the skill's own text still lacks it. Not edited on 2026-09-21 because the skill had an
uncommitted change from another session.

---

## process: `linkage init --sync` in a paper-only repository

**Wanted by** `hemigroup-kernels-ssvm` (the ADR-0001 cleanup), 2026-09-21.

`linkage init --sync` stops with a CONFIG ERROR in a repository with no blueprint (the conference
extraction), because it loads the config with the default blueprint, ledger and Lean paths; the
session rules had to be copied by hand, so `linkage check`'s drift detection is the only thing that
will notice a stale copy there. **Suggested shape:** `--sync` needs only the slug, so it reads
`linkage.toml` without validating the artifact paths; and the path-scoped rules for artifacts a
repository does not have (`blueprint.md`, `ledger.md`, `lean.md`) are either skipped or harmless,
since they load only when a matching file is read.

---

## process: the release and register scripts move into `linkage`

**Wanted by** `spatial-hemigroup-scale-space` (module B, lessons 11 and 12; ADR-0001 step 5),
2026-09-21.

`scripts/export-release.py` (the verification export, parameterized per module),
`scripts/zenodo-release.py` (deposits through the Zenodo API with a reserved DOI, and the
first-page gate) and `scripts/count-register.py` (the register counts by zone) exist only in Paper
V and are needed by every article. **Suggested shape:** `linkage release export|zenodo` and
`linkage prose register`, with the per-module parameters in `linkage.toml` (`[[modules]]`: name,
chapters, paper directory, tag prefix, headline, roots, records directory), so that
`docs/RELEASE.md`'s commands stop naming one repository's scripts.

---

## process: summaries and numbers get a scope audit before a frozen build

**Wanted by** `spatial-hemigroup-scale-space` (module B, lessons 8 and 9), 2026-09-21.

Every pass that restated claims from their statements and compared them with the prose found a
dropped hypothesis (rows R167, R168, R170), and a numerical example reported the errors of one
variant under the description of another. `WRITING.md` § 5 and `PROCESS.md` § 8 now require the
audit; **suggested shape:** a mode of the `draft-reviewer` contract (`REVIEWER-CONTRACT.md`) that
takes the abstract, the introduction's result paragraphs, the conclusion, the tables and the
captions, restates each claim from the statement it cites, and flags every mismatch in scope, and a
tag for a number that does not name the object computed.

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

*No other open requests.*
