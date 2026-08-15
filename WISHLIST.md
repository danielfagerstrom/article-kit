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
their side), and — if the requester has one — a suggested shape. Date it. Leave fulfilled entries in
place with a resolution line, so the channel keeps its history.

---

## Make the control-character check a `linkage check` fatal rule

**Wanted by** `hemigroup-causal-scale-space-kernels`, 2026-08-12.

**What.** `scaffold/scripts/check-control-chars.py` rejects stray control characters (anything but
LF, or CR immediately before LF) in `.tex`, `.md` and `.lean` sources. It is currently a scaffolded
script an article has to remember to wire into its own blueprint gate. It would be better as a
fatal check inside `linkage check`, where every article gets it without wiring.

**Why.** Writing LaTeX or Lean through a non-raw Python string literal silently turns `\begin`
into U+0008, `\texttt` into a TAB and `\ref` into a CR. This happened three times in one session.
Each time the diff looked almost right, `linkage check` passed, and `latexmk` failed several
hundred lines later with *"Unicode character ^^H (U+0008) not set up for use with LaTeX"* — a
message that names the character and not the cause, in a file the author had not knowingly touched
at that point. The failure is cheap to detect and expensive to diagnose, which is the profile a
fatal check wants.

**Suggested shape.** A fatal check alongside the existing render-safety check (they scan the same
files), reporting `path:line` and a byte-context snippet, plus the one-line remedy: use a raw
string or `bytes([92])`. The script is written to be lifted as-is — it takes paths, defaults to the
tracked source trees, and returns a non-zero exit code.

**Resolved 2026-08-15** — shipped as fatal check 9 (`LINKAGE.md` rule 9). Implemented as suggested,
with three adjustments the framework's own shape asked for:

- The scan is I/O, so it lives in `artifacts.py` with the other side inputs and is passed into
  `checks.run()`; `checks.py` holds only the policy and still touches no files.
- Paths come from `linkage.toml` rather than hardcoded globs, since article layouts differ — and the
  scope now includes **`paper/`**, which the script's globs omitted. That is the tree an author edits
  most, and the one `--pin-shared` writes to.
- Fatal with no grace period, unlike check 3b: there is no legitimate use of these characters, and
  measuring first showed neither article carried one.

It earned its place on the first run, in the *other* article: `scale-space-foundations`'
`blueprint/PROOFS-PLAN.md:63` had `arphi` corrupted to U+000B (`` → vertical tab), undetected
since the framework split. Repaired in the same pass.

The scaffolded `scripts/check-control-chars.py` stays: it is wired into `build-blueprint.sh`, where
it fails fast before `latexmk` and without needing the framework importable. `linkage check` now
covers the same ground more broadly; the duplication is deliberate and cheap.

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

## Check that a proved node carries `\leanok` on its *proof*, not only on its statement

**Wanted by** `hemigroup-causal-scale-space-kernels`, 2026-08-15.

**What.** A `linkage check` rule: if a node's `\lean{...}` names a Lean *theorem* and its statement
carries `\leanok`, its `proof` environment should carry `\leanok` too. Advisory is probably the
right severity — there are legitimate exemptions, listed below.

**Why.** leanblueprint colours the dependency graph from **two independent flags**, and `linkage`
models only one of them:

| flag | where | graph effect |
|---|---|---|
| `\leanok` in the statement environment | node body | **green border** — "the statement is formalized" |
| `\leanok` inside the `proof` environment | the following proof | **green background** — "the proof is formalized" |

A node with the first and not the second paints green-bordered with a *blue* background, which the
generated legend reads as "the proof of this result is ready to be formalized" — i.e. **not done**.
`linkage check` counts statement-level `\leanok` only, includes the node in its `\leanok` total,
and passes. So the graph and the linkage count disagree, silently, and the graph is the artifact
the hub and human readers actually look at.

Found by a reader asking why a node they knew was proved was painting blue. Six nodes in this
article were affected — `prop:moments`, `lem:potential-kernel`, `prop:sonine-pair-exists`,
`lem:delay-core`, `lem:generator-properties`, `lem:local-polynomial-symbol` — every one of them
machine-checked, sorry-free, and listed in the article's `#print axioms` guard. Four had been wrong
for weeks. **Two were introduced in a single session by an author who had just fixed the other
four**, which is the argument for a check rather than for care: the flag is invisible at the point
of writing, because the statement and the proof are separate environments and only one of them is
in front of you when you tag the node.

**Suggested shape.** In the pass that already parses `\leanok` / `\notready` / `\lean{}`, record
whether the `proof` environment immediately following a statement contains `\leanok`, and report
the mismatch as `path:line`. Three exemptions, all mechanical:

- **definitions** — no proof environment, so nothing to flag; they colour from the statement flag
  alone;
- **`\notready` nodes** — stated but unproved by construction;
- **nodes with no proof environment at all** — though in this constellation that is already
  disallowed by the "the blueprint is the text of record" rule.

The converse mismatch is worth reporting too, and more loudly: `\leanok` on a proof whose statement
lacks it is incoherent rather than merely under-reported.

**Not blocking.** The six are fixed here by hand, and a one-off audit script took twenty lines —
which is rather the point. It should not be twenty lines that each article rediscovers after a
reader notices a wrong colour.

---

*No other open requests.*
