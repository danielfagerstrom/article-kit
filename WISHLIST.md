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

Suggested: one line in PROCESS.md § 5 (proving waves) and § 7, and a session rule in
`scaffold/claude/rules/`: *a pull request that changes a proof of record or a shared statement that a
paper prints re-transcribes the paper's copy in the same pull request, and opens only when `linkage
check` shows no new proof drift or stale pin.* Optionally a `linkage check --strict-proofs` that fails
on drift introduced by the branch (drift present on the base stays advisory), so CI enforces it. The
affine repository adopted the rule in its `CLAUDE.md` (#69).

---

## process: every ledger entry a Lean proof spends is a blueprint node, or the graph overclaims

Lesson from spatial-hemigroup-affine (Paper VII, 2026-10-06). leanblueprint paints a node dark green
("fully proved") when it and every `\uses` ancestor have a `\leanok` proof; definitions are exempt,
and an axiom counts against a node only if it is itself a node without a proof. The affine module had
not made its ledger entries into nodes. Its `[A]` nodes carried `\ledger{A3}` and a sorry-free Lean
proof that calls the axiom, so all 87 proved nodes rendered dark green, though 41 rest on a cited
fact. Paper V had avoided this by convention: each cited interface is an `[A]` node with no proof
(`prop:fourier-toolbox`), and its spenders `\uses` it. Nothing in the framework required that. The
fix there was nine interface nodes and fifty edges (spatial-hemigroup-affine #82).

Suggested:
- PROCESS.md § 5, the statement skeleton, says that each ledger entry the Lean declares as an axiom
  gets an interface node: the entry's statement as used, `\lean{<axiom>}\leanok`, and no proof. Each
  node naming the entry on its status line `\uses` it.
- `linkage check` warns when a `\leanok` node's proof is `\leanok`, it carries `\ledger{AX}`, and no
  node in its `\uses` closure is AX's interface node, i.e. the node would render fully proved while
  resting on an axiom.

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

---

*No other open requests.*
