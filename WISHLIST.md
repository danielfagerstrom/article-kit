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

## process: the trust-base subsection owns a summary, and an appendix may hold the inventory

**Wanted by** `spatial-hemigroup-scale-space` (module C, the first external review's part B,
item 2), 2026-09-27.

`WRITING.md` § 4 has one early subsection (§ 1.1) own the trust base. In module C that subsection
grew to four and a half pages — coverage by clause, the ledger entries, a table, the steps each
admitted name carries beyond its pages, reproduction commands and raw `#print axioms` output — and
the mathematics started on p. 8. The external presentation review ranked moving it second of
twenty. The author took a moderate form: § 1.1 keeps the coverage by section, the list of what is
not formalized and one paragraph on the cited facts with the count of carried steps, and an
appendix holds the inventory. **Suggested shape:** § 4 of `WRITING.md` and
`PUBLICATION-TEMPLATE.md` § B say that § 1.1 owns the *statement* of the trust base, every sentence
of which a reader needs to judge a result, and that the inventory (tables, per-name notes, commands,
printouts) may live in a verification appendix that § 1.1 names. The disclosure rule is unchanged:
nothing honesty-critical leaves § 1.1.

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

## process: a shared proof of record drifts from its paper and no gate sees it

**Wanted by** `spatial-hemigroup-scale-space` (module C, the first external review), 2026-09-27.

`linkage check` compares `% shared with blueprint` **statements** byte for byte and says nothing
about the **proofs** beneath them, which the paper transcribes by hand. Module C's external referee
was therefore sent a proof of record that the blueprint had repaired five days earlier: the converse
of a signed-data corollary, whose printed step was circular (row R257 says so in those words) and
whose Lean carries the repair. A hand sweep of the chapter's ten proof environments against the
blueprint then found two more, the oldest stale since row R255, one of them a proof that had lost
both its substantive steps and asserted its conclusion bare. Nothing in the gate set could see any
of the three, and the commit that repaired the statements said only that the statement was
re-transcribed.

**Suggested shape:** an advisory in `linkage check` for a drifted proof — either a second sha beside
the statement's, over the `proof` environment that follows a `% shared with blueprint <label>`
marker, or a normalized-text comparison tolerating reference style and the deliberate removal of
machine-check bookkeeping from the reader's text. The advisory matters more than a fatal: a paper's
proof is legitimately allowed to differ, so what is wanted is a report a human reads, not a gate that
blocks. If a sha is used it needs the escape hatch the statements already have for a tracked-by-sha
node.

---

## process: a fidelity row that repairs an inference pattern names the sibling clauses it checked

**Wanted by** `spatial-hemigroup-scale-space` (module C, the first external review), 2026-09-27.

Two of that review's three worst mathematical findings were in clauses *adjacent* to clauses an
earlier fidelity row had already repaired, for the same reason. Row R123 established that inferring a
kernel-side order from a `C^k` count is invalid, because Fourier inversion gives bounded continuous
derivatives and not integrable ones, and repaired clause (2) of a proposition; clause (3) of the same
proposition made the identical inference and was still making it at the freeze. Row R83 resolved
which constant a Thorin generator carries and fixed it for the generator, leaving the clause's
subject reading "the scale derivative", which the chapter's definition had already bound to a
different normalization — so the printed formula was wrong by a factor and had separately lost a
hypothesis its cited source states in its own clause text.

**Suggested shape:** a field in the findings-ledger row format and a line in the `fidelity-review`
skill: when a row's diagnosis is an *inference pattern* rather than a local slip, the row names the
sibling clauses of the same node, and the same pattern elsewhere in the chapter, that were checked
for it — or says that none was. The cost is one sentence per row, and both defects above would have
been caught at the row that named the pattern.

---

## process: a node's annotation lists its declaration's hypotheses, not only its conclusion

**Wanted by** `spatial-hemigroup-scale-space` (module C, the first external review), 2026-09-27.

The `\statusT` annotations are where a node records how its printed statement differs from what its
declarations prove, and they are written with care. Both of module C's chapter-15 annotations
enumerated differences in the **conclusion** accurately and missed every difference in the
**hypothesis**: a `P.a = 0` the declaration carries and the print had dropped, an index set that is a
`Finset` in Lean and unbounded in print, and a compactly supported signal class the tagged identities
require and the printed statement does not name. The first of those was the one false printed
statement the review found, and the annotation that should have caught it was three paragraphs long.

**Suggested shape:** a line in the `fidelity-review` skill and in `docs/LINKAGE.md`'s account of
`\statusT`: an annotation that says what a clause's declarations carry lists the declaration's
hypotheses beside the node's, in order, and marks each as the same, stronger, weaker or absent. A
checklist would do; the failure is not subtlety but an asymmetry of attention between the two halves
of a statement.

---

## process: the release gate checks the sentence that names the export, not only the date line

**Wanted by** `spatial-hemigroup-scale-space` (module C, the first external review), 2026-09-27.

`linkage release` refuses a build whose first page still says "working draft" or does not print the
reserved DOI (`linkage/release.py`, `DRAFT_MARKS` and the first-page check). But an article's
trust-base section typically also carries a sentence naming the verification export and the DOI it is
deposited under, and that sentence is gated by nothing. Module C's review build asserted an export
repository that did not exist yet, "deposited with this version of the paper under the DOI printed on
the first page", on a first page that said "working draft" — so the external referee could resolve
neither the repository nor the DOI, and said so as a required change. The two lines had drifted apart
because only one of them was mechanically tied to the release.

**Suggested shape:** extend the release gate in both directions over a configured pair of phrases —
a release build that still carries the draft wording is a fault, and a draft build that carries the
release wording is a fault too, since that is the direction that misleads a reader. The article's own
copy is `spatial-hemigroup-scale-space`'s `scripts/export-release.py` (`deposit_sentence_faults`,
2026-09-27) if a shape is wanted; a framework version would take the phrases from `linkage.toml`
rather than hard-coding them.

---

## process: a change marker inserted mid-line swallows the rest of the line, and only the PDF shows it

**Wanted by** `spatial-hemigroup-scale-space` (module C, round 3's presentation review), 2026-09-28.

The session rules have every statement change carry a `% CHANGED` marker in the source. When an edit
script ends its replacement with the marker line, and the text it matched stopped in the middle of a
source line, the rest of that line becomes part of the comment. Nothing sees it: the build is clean,
`linkage check` strips comments on both sides of a shared statement so it stays verbatim, and every
review that reads the source reads the words. Module C carried thirteen such broken sentences through
two external rounds and a blind summary pass; the third round's presentation referee, reading the
PDF, found three, and a detector then found the rest.

**Suggested shape:** a gate beside the control-character check. The article's copy is
`spatial-hemigroup-scale-space`'s `scripts/check-swallowed-prose.py <base>`: an added comment line,
followed directly by prose, whose tail with that prose occurs as prose in the base revision's text. It
passes on the repaired tree and finds twelve of the thirteen on the unrepaired one. And a rule for the
session contract: a marker goes on its own line *before* the changed text, never after it.

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
