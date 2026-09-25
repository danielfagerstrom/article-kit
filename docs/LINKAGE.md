# Blueprint ↔ Lean ↔ ledger ↔ paper linkage

How the four artifacts of this project reference one another, and how those references are kept from
drifting. This file is the spec; [`linkage check`](../linkage/checks.py) enforces the
in-repo part of it.

## The hub and the canonical ID

The **blueprint** is the source of truth. `blueprint/src/content.tex` is a thin **aggregator** that
`\input`s the per-section part files under `blueprint/src/parts/` (split so no single file grows
unwieldy with proofs); the statement nodes themselves live in the parts. Every knowledge unit is one
blueprint statement node

    \begin{theorem}[human title]\label{kind:name}      % kind ∈ def | lem | prop | thm | cor

and its **`\label{kind:name}` is the canonical ID**. Every other artifact either points *at* that label
or is pointed *to* from the node. There is no second registry to keep in sync — the blueprint is the
manifest.

## The edges

| Edge | Mechanism | Meaning |
|---|---|---|
| blueprint → Lean | `\lean{Decl}` + `\leanok` (proved) / `\notready` (WIP) | node names its Lean declaration(s) |
| blueprint → blueprint | `\uses{label}` | dependency graph (leanblueprint) |
| blueprint → ledger `[A]` | `\ledger{A15}` | `[A]` node names its `AXIOMS.md` entry |
| blueprint → wiki note | `\notes{slug}` | node names its Notes content note (the "what") |
| paper → blueprint | `% shared with blueprint <label>` + the paper statement's own `\label` | shared statements |
| ledger → blueprint / Lean | `**Blueprint:**` / `**Lean:**` lines in each `AXIOMS.md` entry | reciprocal back-pointer |
| wiki note → blueprint | `blueprint: [labels]` frontmatter *(incremental)* | reciprocal back-pointer |
| blueprint → wiki *(projection)* | `linkage manifest` → `blueprint-manifest-<slug>.json` | the wiki reads proved-status to validate a note ("check") |
| wiki → blueprint *(pull)* | `wiki demands --json` → `linkage demand` | the wiki's proof requests, incl. not-yet-existing nodes ("demand") |

The first seven rows are **reference** edges — pointer syntax inside one artifact. The last two are the
cross-repo **workflow** channel and are documented under [The cross-repo channel](#the-cross-repo-channel--manifest-out-demand-in) below.

`\lean`, `\leanok`, `\uses`, `\notready` are the standard **leanblueprint** API (no-ops in the standalone
PDF build; live when built through leanblueprint). `\ledger` and `\notes` are this repo's additions
(`blueprint/src/macros.tex`): `\ledger{A15}` renders inline as "ledger A15"; `\notes{slug}` is a no-op in
the PDF, so private wiki slugs never leak into the public (Zenodo) build.

## The rules

1. **One node per knowledge unit**, with a stable `\label`. Renaming a label is a breaking change —
   update every edge that names it.
2. **`[A]` nodes cite the ledger** with `\ledger{AXX}`, and `AXX` must be an entry in `AXIOMS.md`.
   Legacy prose "ledger AXX" is still recognised; migrate it to the macro when you touch a node.
3. **`[T]` nodes name their Lean decl** with `\lean{}` and mark `\leanok` once proved. A `\notready`
   node need not have a Lean decl yet.

   **What `\notready` means here, and what the rendered legend says it means.** In this programme a
   `\notready` node is one whose *statement* is typed and reviewed and whose **proof** is pending or
   deliberately unscheduled — a debt with a date, not a doubt about the statement. leanblueprint's
   dependency-graph legend says the opposite: "the statement of this result is not ready to be
   formalized". That sentence cannot be overridden — `make_legend` hard-codes it
   (`leanblueprint/Packages/blueprint.py`, lines 261-263, registered as a post-parse callback at
   priority 150), and `\graphcolor{not_ready}{…}{…}` sets only the colour and the colour's *name*.
   So the orange border is read against this rule, not against the legend, and a repository's
   `Formalization/Skeleton.lean` says the same thing to the reader who arrives from the Lean side.
   (Established 2026-09-25 after a queue item tried to relabel it; the alternatives were a plasTeX
   package of our own hooked above priority 150, or a patch upstream, and neither is worth coupling
   this framework to another project's internals for one sentence.)
4. **A paper statement shared with the blueprint** carries `% shared with blueprint <label>`, and
   `<label>` must be a real blueprint label. **Target (strong single-sourcing):** when the paper renders
   the statement as a *labelled* theorem, its own `\label` *equals* `<label>`, so the correspondence is
   machine-exact and statements could later be `\input` from a shared file. Prose that merely references a
   blueprint node is a valid weaker link — the checker verifies the node exists but does not advise a
   same-label. Labelled-statement mismatches are reported as advisories; align them opportunistically.

   **The grammar is a list, with an optional pinned sha per label** (2026-08-15):

   ```
   % shared with blueprint <label>[@<sha12>][, <label>[@<sha12>]]…
   ```

   **Why a list.** The relationship is **n:1, not 1:1**. The blueprint is deliberately finer-grained
   than the paper — it splits statements so Lean progress is legible, and it re-splits as proving
   proceeds — while the paper renders the pieces as one readable statement. In the first article 25 of
   87 nodes are marked by no paper marker at all, being halves of something the paper states whole
   (`thm:main-construction` / `thm:main-analysis` / `prop:main-uniqueness` against the paper's one
   `thm:main-characterization`; `prop:gamma-density` + `prop:gamma-moments`; `prop:volterra-uniqueness`).
   A one-label marker cannot say that, and reported five correct statements as drifted.

   **Why a sha.** A merged statement cannot be compared as text — the paper rewrites when it merges —
   but it can record *which version* of each node it was written against. That matters because the
   blueprint moves for two different reasons: **splitting**, after which the paper is still right, and
   **new mathematical learning**, after which the paper must follow. Nothing else distinguishes them.
   The pin is over `shared_statement`, not `statement_sha`: the latter covers the formalisation notes
   too, so editing a note would report the paper stale when nothing it shares had moved.

   **The four states**, reported by `linkage check`:

   | state | meaning |
   |---|---|
   | **verbatim** | one label, text identical. Single-sourcing as a verified fact, not an intention. Needs no pin. |
   | **tracked** | rendered editorially (a merge, or reworded) and pinned to each node's current sha |
   | **stale** | a pinned node has moved since — read the statement, then re-pin |
   | **unpinned** | neither identical nor pinned; nothing relates the two texts |

   Advisory by default, fatal under `--strict-shared`; `--pin-shared` writes the shas, since markers
   maintained by hand would not be. **Pinning is an assertion that someone read the statement against
   that version of the node** — auto-pinning a backlog wholesale converts the check into a rubber
   stamp, so pin deliberately, one statement at a time.

   Before comparing, both sides are reduced to what they are supposed to share: everything from the
   `[T]`/`[A]` status tag onward is blueprint-only (a node may carry free-standing `\emph{}`
   formalisation notes after it, which the paper is right to omit — 45 of 87 nodes in the first
   article do), and the environment word the paper writes before a `\ref` is dropped, since
   leanblueprint renders it itself. Without the first reduction 35 of 62 markers look drifted; without
   the second, 16; with both, 11 — and every one of those eleven turned out to be a real structural
   fact rather than noise. The 1:1 comparison is by text rather than sha because both sides are in
   memory: the check reports *where* two statements part company, which a sha cannot.
   (`statement_sha` remains the hub's wire format and is untouched by any of this — the reduction is
   a comparison key, never projected, so no published sha moves.)

   **The proof's context is compared too, as an advisory** (2026-09-25). Rule 4 sees only the
   statement; the blueprint also carries the node's `\uses{}` set, the lemmas its proof invokes. For
   each shared node with `\uses{}`, when a `proof` environment directly follows the paper's marked
   statement, `linkage check` lists the `\uses{}` targets that proof never cites with `\ref`
   (`\cref`, `\Cref`, `\autoref`, `\eqref`, `\vref` and comma lists are read too; comments are ignored):

   ```
   [uses]   paper/paper.tex:12 thm:x: the paper's proof never \ref's 3 of 4 blueprint \uses target(s): lem:b, lem:c, lem:d
   ```

   Never an error and never `--strict-shared`: a paper may legitimately inline a lemma, and the
   check cannot tell that from a dropped reference, so it asks for a look. It is silent when the
   paper states the result without a following proof (proved elsewhere, or by citation) and when the
   node lists no `\uses{}`. Only `\uses{}` in the statement environment count, the ones the manifest
   projects as edges.

   **A repository may hold several papers** (2026-09-15). `paths.paper` in `linkage.toml` takes a
   directory *or a list of them*:

   ```toml
   paper = ["paper", "paper-b", "paper-c"]
   ```

   Every listed directory is read for markers, compared with the blueprint, written by `--pin-shared`,
   and counted — the summary adds a `papers:` line breaking the shared-statement count down per
   directory when there is more than one. Markers are located by **repo-relative path**
   (`paper-b/sections.tex:41`), so two papers may hold a file of the same name. There is one blueprint
   whichever paper a statement is shared with: the modules of an article are different renderings of
   the same body of results, and a second blueprint would be a second article.

   Requested by `spatial-hemigroup-scale-space`, whose Paper V drafts two modules alongside a released
   line paper, each with its own release tag and verification export; with one directory their shared
   statements were invisible to this rule and `--strict-shared` could not be turned on for them. The
   reusable `docs.yml` builds the further papers too, through its `extra_papers` input (a JSON list
   of `{name, tex, title}`; one matrix leg each, published to the artifacts branch and listed on the
   site as `<name>.pdf`, added 2026-09-15 for Paper V's module B).
5. **The trust boundary is the ledger.** Every `[A]` fact is one `AXIOMS.md` entry grounded in a named
   theorem + page; `#print axioms` on any `[T]` theorem must reduce to Lean core + those axioms. (That is
   the `AXIOMS.md` contract, verified by Lean, not re-checked by this script — so this rule alone has no
   numbered check, and the checker's numbering runs one behind the rules' from here on.)

   **An entry carries the source's wording verbatim** (2026-09-21, from Paper V's module B): the
   statement as printed (the formula, its hypotheses, the sentence it sits in), transcribed from the
   page image by the librarian, beside the "statement as used". An anchor is not verified until the
   transcription is in the entry or in the repository's verbatim companion
   (`blueprint/AXIOMS-verbatim.md`, one section per entry, written in the same commit as the entry).
   A paraphrase alone dropped a slowly varying factor from Sato's (53.28), and the result was
   printed, typed, reviewed and admitted as a false axiom. `linkage axioms
   --check` now checks it: an entry whose `**Lean:**` segment names an admitted interface axiom (one
   in `trust-boundary.txt`) and that has neither a `**Verbatim:**` block nor a same-id `## AXX` section
   in the companion **fails**; an entry that grounds no admitted name gets an advisory. The companion's
   path is `paths.axioms_verbatim` in `linkage.toml`, default `blueprint/AXIOMS-verbatim.md`.

   **Ledger identifiers are opaque and stable** (2026-08-09, from `hcs`). Assign them in order of
   introduction; never reuse, never renumber. They are *published names* — `manifest` gives every node a
   `ledger` array and the hub reads it, so renumbering silently changes what an existing hub note means,
   in a place no check can see. The tempting convention, numbering in order of first use through the
   draft, is a trap: it requires a complete and correctly ordered ledger before any proving starts, which
   presumes a finished dependency graph, and a draft is a proof sketch. Formalisation routinely isolates
   an interface the draft never separated — a Lean route that needs a *construction* where the paper cites
   a *representation theorem*, say — and under that convention each such discovery forces either a
   renumbering migration or an entry that lies about its position. Keep order in an index table instead.
   An article that has not yet pinned a ledger may prefer mnemonic ids outright (`ledger_key` is
   per-article configurable; `A\d+` is only the default); one that has should leave its ids alone.

   A ledger entry need not be `\ledger{}`-referenced. Check 2 is one-directional — every reference must
   resolve to an entry, not every entry be referenced — which is what lets an article carry a **Lean-side
   entry**: an interface the Lean development needs because it reaches a theorem by a different route than
   the blueprint's proof, and which therefore grounds no `[A]` node. Such an entry is still fully
   reviewed; it is the `**Lean:**` segment, not a `\ledger{}` reference, that `trust-boundary.txt` is
   cross-checked against.
6. **Every statement node declares `\statusT` or `\statusA`.** The hub's confidence grading keys on the
   projected status, so a node without one is a node the hub cannot grade.
7. **Every `[A]` node declares its assignment** (ADR-0011, 2026-07-30): a `\textbf{Assignment.}` clause
   inside the node's status annotation, saying **which ledger entry is answerable for which clause of this
   statement** and **what it does not carry** — the parts held as `[T]`, and the parts deliberately outside
   the trust base. The clause must name at least one entry. It lives in the status annotation because
   `normalize_statement` strips that region, so writing or revising a declaration never moves a
   `statement_sha` and never disturbs a transcluded block.

   Two conventions make the projection honest. Inside the clause, use `\ledger{AXX}` only for an entry that
   genuinely carries part of *this* node's statement — the manifest projects every `\ledger{}` in the node
   body as one of its sources (de-duplicated, first-mention order), so a macro'd cross-reference to an entry
   the node merely mentions would show up in the hub as a source it does not have. Name such an entry in
   plain text ("A18's", "not A1"). And a part carried as `[T]` needs a **proof of record in the blueprint**,
   not a promise: the blueprint is the text of record, so "elementary, not formalised" is a proof debt only
   when the elementary proof is written down.

   The rationale is ADR-0010's: an `[A]` statement may say more than its citation, provided every part is
   either cited with a page anchor or carried as `[T]`; what is forbidden is an *unassigned* part, ours and
   unproved, riding on the `[A]` grade. Three such parts were found by hand in 2026-07 and none by any
   automated control. A checker can require that the judgement be written; it cannot make it, and it cannot
   tell a wrong declaration from a right one. What it removes is the silent case.

8. **A proved node rests only on proved or written-down mathematics** (2026-07-31). No `\leanok` node may
   reach, through the transitive `\uses` closure, a `[T]` statement node (`thm`/`prop`/`lem`/`cor`) that is
   proved nowhere — neither `\leanok` nor carrying a proof environment in the blueprint. This is the
   structural property behind what `\leanok` means to a reader, and to the hub, which grades a note
   `confidence: verified` off the projected flag.

   Two exemptions, both principled. **`[A]` nodes** are the trust boundary itself (rule 5): they are
   accepted on a page-anchored citation and reviewed in `AXIOMS.md`, and resting on one is the
   verified-core/axiomatized-analysis split working as designed. **Definitions** are vocabulary rather than
   claims; a proved node may legitimately name an unformalised one.

   The exemption is for `[A]` nodes as *targets*, and the fatal walk still traverses **through** them: an
   `[A]` node's own statement may not be phrased in terms of a statement proved nowhere either. That is the
   stronger reading and it costs nothing here. It is not hypothetical: `[A]` nodes do `\uses` our own nodes —
   the pre-split `thm:covariant-lamperti` carried `\uses{def:covariant-memory,thm:memory-family}` — and the
   A15 split exists because that node had absorbed an unproved clause of ours into the ledger once already.
   A cited interface earns its trust from a page anchor, not from what it happens to `\uses`; but a reader
   cannot even *read* the statement if the labels it is phrased in terms of stand for nothing.

   And one distinction the naive form of the rule gets wrong: *not `\leanok`* is not *unproved*. ADR-0010
   rule 2 permits a node whose blueprint proof is complete but which Lean does not state — Lean models
   symbols where the proof needs operators, or formalisation is simply pending. Resting on such a node is a
   **proof debt**, reported as an advisory with the proof's size, not a defect. `prop:conservative` is the
   current instance: the naive form scored its sixteen dependents as violations on the day it went `[A]
   \leanok` → `[T] \notready` *while gaining* a proof of record — a strict improvement read as sixteen
   regressions. Only a statement with no argument anywhere is a violation. What the checker cannot judge is
   whether a proof of record is a *proof* — "see Lean" is not one (`ROADMAP.md` #7); that stays review's
   job, and the advisory prints the size so a stub is visible.

   **The two walks are deliberately asymmetric** (2026-07-31): the fatal walk goes through `[A]` nodes, the
   advisory's dependent count **stops at** them. They ask different questions. The fatal one asks *is
   anything a proved node rests on missing an argument altogether* — where a longer reach is strictly safer.
   The advisory one is the formalisation worklist: *which proved nodes would gain if this statement were
   formalised?* A node that reaches the statement only through an `[A]` interface would gain nothing — its
   trust already passes through the ledger at that point, and whether *that* is sound is `AXIOMS.md`'s
   review, not a formalisation task. Counting it inflates the number and points effort at the wrong node.
   Today `prop:conservative` has **10** dependents ahead of the boundary and **16** counting through it; the
   six that differ all reach it behind `prop:memory-positivity-cone` (`\ledger{A18}`). Both numbers are
   printed, because the gap says how much of the debt an axiom already covers. A `\leanok` `[A]` node that
   `\uses` the statement *itself* still counts as a dependent — the labels in its own statement are its own
   dependency, even though nothing above it inherits them; that is why `prop:feller-negdef` is among the ten.

## The checker

`linkage check` (linkage/checks.py) — no dependencies; run `linkage check` from the repo root.
It reads `content.tex` and inlines its `\input{parts/...}` includes, so the split is transparent to it.
It enforces the **in-repo** edges and fails (exit 1) on:

- a `\leanok` node whose `\lean{Decl}` is not declared in `Formalization/` (rule 3);
- a `\ledger{AXX}` / "ledger AXX" with no `## AXX` entry in `AXIOMS.md`, or an entry with no `**Cite:**` line (rule 2);
- a paper `% shared with blueprint <label>` naming a label the blueprint does not have (rule 4);
- a `\leanok` on a node's *proof* whose statement carries none (rule 10);
- under `--strict-shared`: a shared paper statement whose text has drifted from its blueprint
  node (rule 4). Advisory without the flag, so an article can adopt the check before its
  existing drift is cleared;
- a `\command` in a statement or proof that the render pipeline cannot handle (the clean-render gate);
- a stray control character in any `.tex`, `.md` or `.lean` source — anything below U+0020 that
  is not LF, or CR immediately before LF (rule 9);
- a statement node with no `\statusT` / `\statusA` (rule 6);
- a `\statusA` node with no `\textbf{Assignment.}` clause, or whose clause names no ledger entry (rule 7);
- a `\leanok` node whose transitive `\uses` closure contains a `[T]` statement proved nowhere (rule 8) —
  reported once per reached statement, naming the dependents and a shortest path to it. The walk is
  breadth-first with a visited set, so it terminates whatever the edges do (a `\uses` cycle is a modelling
  error, not something this check should hang on).

9. **No source file carries a stray control character** (2026-08-15). Legal below U+0020: LF,
   and CR immediately before LF. Everything else — a bare TAB, a lone CR, a backspace, a vertical
   tab — is corruption, and there is no legitimate use of one in these files. Writing LaTeX or Lean
   through a *non-raw* Python string literal silently turns `\begin` into U+0008, `\texttt`
   into a TAB and `\varphi` into U+000B: the diff looks almost right, every other check passes,
   and `latexmk` fails hundreds of lines later naming the character rather than the cause, in a file
   the author does not recall touching.

   Fatal with no grace period, unlike rule 4's text comparison — there is no legitimate use to
   grandfather, and measuring first confirmed neither article carried one. It earned that on its
   first run, in the article that had *not* reported the problem: `scale-space-foundations`'
   `blueprint/PROOFS-PLAN.md:63` held `\varphi` corrupted to U+000B, undetected since the
   framework split.

   Scope is every `.tex` / `.md` / `.lean` file under the repo, with build output and `.claude/`
   worktrees excluded. That includes `paper/`, which the article-side script this replaced did not
   cover — and the paper is both the tree an author edits most and the one `--pin-shared` writes to.
10. **A node's two `\leanok` flags agree** (2026-09-15). leanblueprint colours the dependency
   graph from **two independent flags**, and a node may carry either:

   | flag | where | graph effect |
   |---|---|---|
   | `\leanok` in the statement environment | node body | **green border** — the statement is formalised |
   | `\leanok` inside the following `proof` environment | the proof | **green background** — the proof is formalised |

   A node with the first and not the second paints green-bordered on *blue*, which the generated
   legend reads as "the proof of this result is ready to be formalized" — i.e. **not done**. Until
   this rule `linkage` modelled the statement flag only: it counted such a node in its `\leanok`
   total and passed, so the graph and the check disagreed silently. The graph is the artifact the
   hub and human readers actually look at.

   **The missing proof flag is an advisory; the converse is fatal.** A `\leanok` proof under a
   statement that carries none is incoherent rather than under-reported — a formalised proof of an
   unformalised statement — and paints a combination the legend has no reading for.

   **Three exemptions, all mechanical:** a node with no `proof` environment (nothing to flag —
   definitions colour from the statement flag alone), a `\notready` node (stated but unproved by
   construction), and a label that is not a claim kind. The rule properly concerns a `\lean{}`
   naming a Lean *theorem*; a declaration name cannot be told from a definition's without Lean, and
   carrying a proof environment is the mechanical proxy.

   Raised by a reader asking why a node they knew was proved was painting blue. Six nodes in
   `hemigroup-causal-scale-space-kernels` were affected, every one machine-checked, sorry-free and
   listed in that article's `#print axioms` guard; four had been wrong for weeks, and **two were
   introduced in the session that fixed the other four.** That is the argument for a check rather
   than for care: the flag is invisible at the point of writing, because the statement and the proof
   are separate environments and only one of them is in front of the author. All three articles were
   clean when the check shipped, so like rule 9 it starts with no backlog to grandfather. The summary
   line now prints both counts (`N \leanok, M with a \leanok proof`).
It also prints **advisories** (non-fatal): a paper shared statement whose own label differs from the
blueprint key; a `\leanok` node with no `\lean{}`; a node marked both `\leanok` and `\notready`; a
`\leanok` statement whose proof environment carries no `\leanok` (rule 10 — the node paints
green-bordered on blue, which the graph's legend reads as not done); and — the
formalisation worklist — each statement a `\leanok` node reaches that is proved on paper but not in Lean,
with its proof size and **both** dependent counts, those ahead of the trust boundary and those counting
paths through an `[A]` interface (rule 8; the first is the headline, since it is the number formalising the
statement would actually discharge). Its summary line reports the whole dependency picture,
including `[T]` statements proved nowhere that nothing proved reaches: those are our open conjectures, and
naming them keeps the difference between "open" and "leaned on while open" visible.

11. **The inferred `\uses` — `linkage closure`** (2026-09-25). Rules 3 and 8 check the *declared*
   dependency graph: the `\uses{}` edges an author wrote, and what they imply. A `\leanok` node makes
   two claims at once — "this is proved" and "here is what it rests on" — and the Lean declaration it
   points at knows the second one for a fact. `linkage closure` computes it and diffs the two, **as an
   audit, never as a source**: authorship stays blueprint-first, the LaTeX is the deliverable, `\uses{}`
   is written for the reader and for leanblueprint's graph, and nothing here proposes or writes an edge.
   It is a separate command, not part of `linkage check`, and it always exits 0 (2 only when it could
   not read its input): it reports judgement calls, and a gate that fails on them would be waived rather
   than fixed.

   **Two routes to the constant set.** An exact answer needs Lean's environment, which needs a build,
   which this package deliberately does not have (`manifest.yml` runs on source text, offline, with no
   elan). So:

   | route | input | when |
   |---|---|---|
   | **export** | `paths.lean_uses` (default `Formalization/lean-uses.json`), `{"Decl.Name": ["Const", …]}` written by a Lean meta program over a built environment | used when the file exists, or `--export PATH` |
   | **source scan** | the declaration's own source text, identifier tokens resolved against this article's declarations only | the default, and what the tests exercise |

   The source scan is the coarse-to-fine descendant of `f7sweep.py`, which asks the file-level version
   of the same question (is a `\uses` target's declaration in the Lean file's transitive *import*
   closure?) and which this supersedes for `\leanok` nodes.

   **Four advisories**, the two directions of the diff and two whole-node flags:

   | tag | meaning |
   |---|---|
   | `[declared]` | a `\uses{}` target whose declaration is nowhere in the **transitive** inferred closure — the blueprint cites it and the Lean proof appears not to |
   | `[inferred]`| a declaration the node's Lean proof cites **directly**, owned by a node no `\uses` path from here reaches — a route the blueprint does not tell the reader about |
   | `[empty]` | a proved claim node whose declaration cites nothing of this article's *while* its `\uses{}` names formalised nodes — the two accounts have nothing in common (wrong tag, or a proof carried entirely by automation) |
   | `[orphan]` | a `lem` node nothing depends on in **either** graph — dead weight, a missing `\uses` edge, or a result that has become a theorem in its own right |

   **Direct versus transitive is deliberately asymmetric**, for rule 8's reason. A `\uses{}` label counts
   as supported if its declaration is anywhere in the transitive inferred closure: the Lean proof may
   reach a cited ingredient through a private helper that has no blueprint node, and that is a route,
   not a finding. An inferred dependency counts as missing only when the node's transitive `\uses`
   closure does not reach it at all: `\uses{}` records *direct* edges, so an indirect dependency is
   legitimately absent. `[empty]` is the total form of `[declared]`, and suppresses that node's
   per-label lines — one finding per node, since they have one cause. `[orphan]` is `lem` only: a `thm`,
   `prop` or `cor` that nothing uses is the ordinary shape of a headline result, while a lemma exists to
   be used.

   **What the source scan cannot see**, i.e. the false positives of the `[declared]` direction: a lemma
   pulled in by a **`simp` set** (`@[simp]` at the lemma, `simp` at the use site names nothing); a fact
   used through **notation**, a `macro`/`syntax` expansion or an `abbrev`; an **instance** found by
   typeclass resolution, which is what instances are for; anything reached by `omega`, `aesop`,
   `positivity`, `gcongr` or `fun_prop`; and defeq unfolding, where `rfl` consumes a definition without
   naming it. Each makes a real use look absent — which is why this direction is advisory, and why the
   export route exists for an article that wants the exact answer. The `[inferred]` direction has the
   opposite profile: a token match is evidence of a real citation, and its own false positive is a name
   collision with a Mathlib declaration of the same short name (an ambiguous short name resolves to
   nothing rather than to a guess). A node whose `\lean{}` points into a shared Lake package is reported
   as unreadable, not scored as citing nothing; a `\uses` target with no `\lean{}` — an `[A]` or
   untagged node — has no declaration to look for and is left to the reader.

The **wiki edge** is cross-repo: pass `--wiki <path-to-Notes>` to also check that every `\notes{slug}`
resolves to a `slug.md` under the wiki.

Run it before publishing and as **gate item 7** (`paper/DRAFTING-GATE.md`); a pre-release / CI step is the
natural home.

## The cross-repo channel — manifest out, demand in

The reference edges above are pointers; the **workflow** with the wiki is two-way and runs over two
one-way projections, deliberately never one shared file. The full rationale (why not a co-written file,
why the two directions are not mirror images) is the wiki's to state — see its
[`ARCHITECTURE.md`](file:///C:/Users/danie/Documents/Notes/ARCHITECTURE.md) § "The theorem channel".
This is the satellite side of that contract.

**Out — the manifest (`check`).** `linkage manifest <path>` writes
`blueprint-manifest-<slug>.json` into the wiki: a projection of every label with `kind`, `leanok`, `notready`,
its `\lean{}` decls, its `uses` dependency labels, and its normalized statement text (`statement`) with
a short hash (`statement_sha`), plus the flat Lean-decl set and this repo's `scripts/` paths. The wiki
reads it to answer "is the theorem this note claims actually proved?" — it never parses our LaTeX. Same
contract as the librarian's `library.json`: **we are the single writer, the wiki only reads.**

- *Freshness stamp (shipped 2026-07-16).* `build_manifest()` adds this repo's short git SHA, a
  generation timestamp, and a `source_dirty` flag (via `_git_provenance()`), so the wiki reports
  "manifest: `ssf@<sha>`, N days old" and warns when the manifest is unstamped or was emitted from a
  dirty tree — instead of trusting an undated file. `source_dirty` is whole-repo on purpose: the
  manifest projects labels, Lean decls, and scripts, so a change anywhere may escape HEAD's SHA, and
  the honest signal is "this did not come from a clean commit." Re-emit after committing for a clean
  read. This is what lets the wiki's audit cache re-verify a claim the moment its node flips to
  `\leanok` against a manifest whose currency is visible.
- *Statement text + hash, and `uses` (shipped 2026-07-20).* Each label entry carries `statement` —
  the node's statement text with LaTeX comments and the metadata commands (`\label`/`\lean`/`\uses`/
  `\notes`/`\ledger` with arguments; the bare `\notready`/`\leanok` tokens; `\statusT`/`\statusA`
  together with their trailing `\quad\emph{...}` status annotation — a proof-status remark, so a
  status edit does not move the sha) stripped and whitespace collapsed, the mathematical prose and
  math kept verbatim — and
  `statement_sha`, the first 12 hex chars of its sha256. The normalization is deterministic (same
  input → same hash), so the sha moves exactly when the statement's content does: the wiki's lint
  diffs a note's mirrored statement block against it to catch silent drift (the failure mode that
  motivated this — two near-verbatim mirrors drifted and were caught only by manual audit). Each
  entry also carries `uses`, the node's `\uses{}` labels in order of appearance, so the
  blueprint-internal dependency edges are verifiable vault-side rather than opaque to the hub.
- *Regeneration & delivery (CI, 2026-07-24).* The authoritative channel is
  [`.github/workflows/manifest.yml`](../.github/workflows/manifest.yml): every `main` push touching
  `blueprint/**`, `Formalization/**`, or the generator re-emits the manifest and commits it into the
  hub repo (`notes-wiki`, where the file is tracked) — with a semantic diff-guard that ignores the
  stamp fields, so stamp-only regenerations produce no hub commit. CI is the single writer of the
  hub's copy — a local emit must therefore **never target the vault**: the hub tracks the file, so a
  hand emit would dirty its tree and could be swept into a hub auto-commit, breaking the
  CI-only-writer invariant. Instead, the versioned [`.githooks/post-commit`](../.githooks/post-commit)
  hook re-emits after any commit touching the projected paths into the SSF-local, gitignored
  **`.manifest-preview.json`** (activate once per clone with `git config core.hooksPath .githooks`;
  best-effort, never fails a commit). To check un-pushed work against that preview, point the hub CLI
  at it — `wiki lint --manifest <ssf>/.manifest-preview.json` (the flag defaults to the vault's
  committed copy) — rather than overwriting the vault file; manual
  `--emit-manifest .manifest-preview.json` remains the fallback.

- *Transclusion fields — manifest v2 (shipped 2026-07-25; `ROADMAP.md` #7 T1).* The manifest is now
  the wiki's **import source**, not only its checker — it implements the 2026-07-25 decision (hub
  `ARCHITECTURE.md` § "The theorem channel"): the blueprint is the single source of the mathematical
  text; wiki notes transclude nodes verbatim, never paraphrase. Per label, v2 adds: `env` + `title`
  (the environment name and its optional `[human title]`, split out of the statement — presentation
  metadata for the import's block header, so titles no longer sit in `statement`/`statement_sha`);
  `proof` + `proof_sha` (the trailing `proof` environment, same normalization as `statement`; null
  when absent — 14 of 48 nodes carry one today); and the rendered forms `statement_md` / `proof_md` +
  `rendered_sha`, produced at emit by a **version-pinned pandoc** (`PANDOC_PIN = 3.10`,
  `commonmark+tex_math_dollars`, `--wrap=none` — Obsidian's `$`/`$$` math dialect) over the
  normalized source with `macros.tex` fed as a preamble, so custom macros expand (inside math too)
  and `\ref{X}` renders as the code span `` `X` ``. Top-level: `manifest_version: 2` and a `render`
  provenance block. Determinism is the point: `rendered_sha` is what the hub's `wiki import`/lint
  byte-compares, so **the pandoc version is pinned in the emitter and installed pinned in CI** —
  never `apt install pandoc`. Degrade path: no pandoc / wrong version → the manifest emits without
  rendered fields and warns; `--require-render` (used by the CI job, the hub copy's single writer)
  turns that or any per-label render failure into a hard error. The **clean-render gate** (T2,
  shipped same day) is *source-side* — check 4 of the checker, run on every invocation: each
  `\command` in a statement/proof must be defined in `macros.tex` (it expands at render) or vetted in
  [`render-allowlist.txt`](render-allowlist.txt) (standard LaTeX pandoc/MathJax know natively).
  Source-side because pandoc **silently drops** unknown commands — argument and all — so output-side
  residue checking cannot catch them; an output residue scan remains as a belt under
  `--require-render`. The gate fails the plain check (the mathematician's pre-report ritual), the
  post-commit preview hook (warning), and the CI manifest job — a render-breaking node fails at
  commit, never at import.

**In — demand (`demand`; the hub half shipped 2026-07-16).** The inverse is a **pull, not a file we
receive**: when planning proofs, run `wiki demands --json` (with `$WIKI_VAULT` pointing at the Notes
vault) to see which blueprint labels the wiki's claims rest on and at what confidence, **strongest
first**. It reports *raw* demand — a pure function of the wiki's claims, carrying no proved-status — so
**we do the join** against our own `\leanok`, the half we own and the only one that is authoritative.
The hub's ordering already puts the most load-bearing non-frontier demand first; join it with proved
`asc` to drop what is done and the top is the prover's worklist. Frontier-flagged demands are the wiki's
declared-open leads and rank last — not blocking any note. A demand may name a label **not in the
blueprint yet** (the hub flags it `⚠ NOT a blueprint node yet`) — that is the wiki asking for a *new*
theorem; the right response is to add the node (or push back), exactly as one would triage a
`library acquire request` for a source not yet held.

- *The join (shipped 2026-07-16).* `linkage demand` is the
  consumer: it runs `wiki demands --json`, joins against the **live** blueprint parse (not the emitted
  manifest — that is our output and can lag; `\leanok` in `content.tex` never does), and prints the
  unproved demand in the hub's order. Proved labels drop off; `\notready` / no-decl / not-in-blueprint
  are annotated, and it warns when the wiki's manifest is behind this repo's HEAD. `--json` for machine
  use. It is a *query*, run when planning proofs — `PROOFS-PLAN.md` stays hand-ordered and records the
  judgement, not the snapshot.

Neither direction certifies *faithfulness* — whether a Lean statement is true to what the note means it
to say. That is a judgement, left to a reviewing agent (the wiki's `curator`) working with the prover,
not to either projection.

## Status (2026-07)

- **Enforced now, checker green:** blueprint→Lean, blueprint→ledger, paper→blueprint (existence),
  blueprint→wiki (with `--wiki`), and blueprint→blueprint (the dependency invariant, rule 8 — clean, with
  `prop:conservative` the one advisory formalisation debt).
- **Incremental rollout:** migrate the remaining "ledger AXX" prose to `\ledger{}`; add `\notes{}` to the
  rest of the nodes; add reciprocal `blueprint:` frontmatter to the wiki content notes. (Paper
  same-labelling is settled: the non-existence theorem uses `thm:galilean-nonexistence`; the affine result
  is shared at prose level — no advisories outstanding.)
- **Shipped 2026-08-08 — the web/dep-graph build is deployed, not just installed.** The reusable
  [`docs.yml`](../.github/workflows/docs.yml) gained a `web` job: plasTeX renders
  `blueprint/src/web.tex` and the deploy job publishes it at `/blueprint/` on the article's
  Cloudflare Pages project, so the `\uses` graph and the `[T]`/`[A]` tags are a shareable URL
  rather than a local artifact. Opt out per article with `build_web: false`. Locally,
  `scripts/build-blueprint.sh` in each article rebuilds the same view.

  Two dependencies bite, and both are silent — a desk with MiKTeX and Graphviz installed hides
  each of them, and neither failure stops the build. **Graphviz is needed at build time**:
  `plastexdepgraph` pulls in `pygraphviz`, a binding against the Graphviz C library, and without
  the system package it installs from a wheel and emits a graph with *no nodes*. (The
  `graphvizlib.wasm` the plugin also ships only lays the graph out in the reader's browser.) And
  **`\input` resolution goes through `kpsewhich`**: TeX is not needed for images — all mathematics
  goes to MathJax, so plasTeX emits none — but a runner without TeX cannot resolve an
  extensionless `\input`, so `content.tex` must write `\input{parts/foo.tex}` or every part file
  is dropped with a warning the build survives. Both were found by the first real CI run, not by
  review; the workflow's validation now counts graph nodes for exactly this reason.
- **Still larger, separate:** have blueprint→Lean checked by leanblueprint's *own* tooling
  (`checkdecls`) rather than only by `linkage check`'s declaration scan; and true statement
  single-sourcing between paper and blueprint via shared `\input`.
- **Decided 2026-07-25, in build-out:** the transclusion layer — the blueprint as the single source of
  the mathematical text for wiki and article (see the *Planned — transclusion fields* bullet above;
  master roadmap `ROADMAP.md` #7, hub half `Notes/ROADMAP.md` #14). Promotes paper statement
  single-sourcing from nice-to-have to a roadmap milestone (T6).

## Ownership

This file is the spec. `blueprint/src/content.tex` is the source of truth for the graph; `AXIOMS.md`
owns the `[A]` grounding; `linkage check` (linkage/checks.py) enforces consistency. The linkage is gate item 7 in
`paper/DRAFTING-GATE.md`.
