# Reviewer output contract — draft

**Status: draft, 2026-08-15. Not yet implemented and not yet adopted by the reviewer.**

The output format for exposition-review flags, and the rules an aggregator applies over them. The
companion to [`PUBLICATION-TEMPLATE.md`](PUBLICATION-TEMPLATE.md): the template says *what* a reviewer
reviews against (§B section contracts, §C voice rubric), this says *what shape its findings come out
in*.

Same cross-repo pattern as the template. This repo owns the spec; the hub's `draft-reviewer` agent
reads it and emits to it. Neither repo writes the other's files.

## Why this exists

Fourteen blind `draft-reviewer` runs over one paper returned about 120 located flags **as prose
reports**. Every flag was well-formed and locatable. But 120 items is far past the point where a
worklist gets acted on — `@thakkar2025can` measured incorporation rising as item count falls — and the
thing that made them actionable was pooling them into ten threads that recurred *across sections*,
after which four decisions discharged most of the volume.

That pooling had to be done by reading fourteen essays. It is where the entire cost of the exercise
sat, and it is not repeatable. **The aggregation is the product; this contract is what makes the
aggregation mechanical.**

Three findings from that batch shape the design, and each is a requirement below:

1. **Rank by breadth, not severity.** The same underlying defect was labelled `[low-med]` by one
   reviewer and `[high]` by another. Once flags are pooled, per-reviewer severity stops being
   informative and count of independent discoveries starts. So severity is recorded but is never the
   sort key.
2. **Threads are detectable from shared referents.** The flags that formed threads overwhelmingly
   cited the same LaTeX labels — thread A ran through `cor:semigroup-case`, `rem:drift-boundary`,
   `prop:extreme-rays`; thread B through `def:standing-hypothesis` and `z_*`. Recording every label a
   flag implicates, not just the one it sits on, turns clustering into a set-intersection.
3. **A blind reviewer cannot name a thread.** It sees one section. Any scheme that asks reviewers to
   agree on a thread slug will fail, so the contract asks for evidence of the connection (`refs`) and
   lets the aggregator propose the cluster.

## Shape

**One JSONL file per review**, one record per line, concatenable across reviews. JSONL because the
list has to be counted, sorted, filtered and merged — the same reasoning as
`ai-prose-patterns.md` §3, which this extends.

**The JSONL is the source of truth; the readable report is rendered from it.** Requiring the reviewer
to emit both a prose report and its structured twin invites the two to disagree, and the prose one
would win by being the one a human reads. So the reviewer emits records, and `linkage review render`
prints the report the charter describes — strengths line, STRUCTURE then VOICE, ranked, boundary
restated.

### `kind: "review"` — exactly one, first

```json
{"kind":"review","target":"paper/09-signaling.tex","contract":"B.5",
 "contract_why":"main.tex assigns §9 the signaling form; definition→lemma→theorem→proof with results consumed by §10, §12. Not template §7 (Experiments) — this paper's realization slot is §11.",
 "maturity":"evergreen","strengths":"opens by motivating before it formalizes; honest about where each hypothesis bites; three genuinely worked cases",
 "floor":"linkage check — noted, not run"}
```

`contract` and `contract_why` are **required**. Every run in the trial batch had to be told that
section numbers do not map to template contract numbers (this paper's §7 is its characterization
theorem; the template's §7 is *Experiments*), and made to declare its choice. Recording the
declaration makes the mapping checkable rather than implicit, and a wrong mapping invalidates every
structural flag under it.

### `kind: "flag"` — zero or more

```json
{"kind":"flag","file":"paper/09-signaling.tex","line":231,
 "anchor":"(H) excludes the cone's extreme boundary and nothing else",
 "tag":"SCOPE","layer":"structure","severity":3,
 "claim":"Contradicted twice inside its own paragraph: the pure delay is an extreme ray with b0>0, and the same paragraph says (H) holds with z*=infinity whenever b0>0; and the Gamma family is non-extreme yet excluded at gamma<=1.",
 "probe":"Survives only as 'the extreme rays with b0=0 lie on (H)'s boundary'. Drop 'and nothing else'.",
 "refs":["prop:extreme-rays","rem:extreme-rays","def:standing-hypothesis","cor:semigroup-case"],
 "elsewhere":["paper/07-characterization.tex","paper/13-discussion.tex"],
 "shared_with_blueprint":true}
```

| field | required | notes |
|---|---|---|
| `file` | yes | repo-relative |
| `anchor` | yes | **verbatim, and occurring exactly once in `file`** |
| `line` | no | convenience only; the anchor is the identity |
| `tag` | yes | from the vocabulary below |
| `layer` | yes | `structure` (§B) or `voice` (§C) |
| `severity` | yes | 1–3, the reviewer's local read. Recorded, never the sort key |
| `claim` | yes | one sentence: what is wrong |
| `probe` | yes | what to check or change. **Never a rewrite the reviewer imposes** |
| `refs` | yes | every label the flag implicates, not only the one it sits on. This is what clusters |
| `elsewhere` | no | other files the flag reaches into |
| `shared_with_blueprint` | no | true if the anchor sits inside a `% shared with blueprint` block — the fix is then blueprint-side, and the reviewer should say so |

**The anchor rule is mechanically enforceable, and that is the point.** An anchor that does not occur
exactly once in its file is a malformed flag: reject it. This is the same discipline
`ai-prose-patterns.md` §3 argues for edits — line numbers shift within a session and unique quoted
strings do not — applied one step earlier, to findings rather than to fixes. It also has a useful side
effect: a finding too diffuse to quote is usually a finding too diffuse to act on.

## Tag vocabulary

The note's §1 vocabulary is **entirely prose-surface**, and eight of the ten threads in the trial batch
were not. Both halves are needed.

**Scope and claim** — the largest class in practice, and the one that produced every high-severity
flag:

| tag | the defect |
|---|---|
| `SCOPE` | the claim is wider than the result it rests on |
| `HYPOTHESIS` | a condition the body carries is absent where the claim is made |
| `COUNT` | an economy or enumeration claim the text's own proofs falsify |
| `FRONTIER` | unsettled or cited status not marked *at the point of claim* (absence of a marker is `note-evaluator`'s; misplacement is this) |

**Structure**

| tag | the defect |
|---|---|
| `CONTRACT` | a §B contract item the section does not meet |
| `PROMISE` | the text promises something it never delivers |
| `ORPHAN` | a numbered result nothing references |
| `ENVELOPE` | a statement environment carrying proof, rationale or conjecture |
| `POINTER` | a reference that resolves to the wrong thing, or to nothing a checker can see |
| `TRANSCLUSION` | upstream (blueprint) carries context this text dropped |

**Notation**

| tag | the defect |
|---|---|
| `NOTATION` | one symbol, two objects |
| `UNDEFINED` | a symbol or term used and never introduced anywhere |

**Voice** — `MOTIVATION` (formalism before its reason), `PICTURE` (no intuition or figure where one is
owed), `PROSE` (the argument is not followable from the text alone), plus the surface tags from
`ai-prose-patterns.md` §1: `NEGPAR`, `PARTTAIL`, `PARALADDER`, `SALIENCE`, `SINCERITY`, `SIGNPOST`,
`ADVERB`, `TRICOLON`, `ATTITUDE`.

Policy is set **per tag**, not per instance — the point of a fixed vocabulary. Expect a small number of
tags to carry most of the volume, and one rule each then replaces dozens of decisions.

## Aggregation

Over the concatenated records of every review of one artifact:

1. **Validate.** Every `anchor` occurs exactly once in its `file`; every `refs` label resolves; every
   review record declares a contract. Malformed flags are reported, not silently dropped.
2. **Cluster** by `refs` intersection, `elsewhere` pointing into another flag's `file`, and anchor
   overlap. Emit candidate threads with their member flags. This is a proposal, not a verdict — the
   trial batch's threads would have been mostly recoverable this way, but not all of them, and a
   cluster of one is a lead rather than a finding.
3. **Rank by breadth** — number of *independent reviews* contributing, then total flags, then max
   severity as the last tiebreak only.
4. **Report**: threads first with their sections, then unclustered flags by tag. Never the raw list
   first — that is the failure mode this contract exists to prevent.

**Cap what is handed on.** The evidence is that fewer items get incorporated, so the worklist is
threads plus the decisions they imply, with the flags available underneath as drill-down. Every flag
stays in the file; not every flag reaches the author's list.

## What the reviewer still owes in prose

The charter's non-mechanical obligations do not become fields:

- the **strengths line** is in the review record and is required — it is what makes the output read as
  triage rather than as a verdict;
- the **boundary restatement** (correctness is Lean's, grounding `note-evaluator`'s, integrity
  `linkage check`'s) is rendered from the review record, not repeated per flag;
- **no verdicts**, and no rewrites. `probe` says what to check; the author decides.

## Open questions

- Does the aggregator live in `linkage` (`linkage review`) or is it a hub verb? It consumes reviewer
  output, which is the hub's agent, but it runs over an article's paper, which is this side. Undecided.
- Should `severity` survive at all, given it proved uninformative when pooled? Kept for now because a
  single-section review still needs to rank its own output, and the trial batch showed the *within*-
  section ranking was sound even where the cross-section one was not.
- Thread identity across *revisions* — when a paper changes and is re-reviewed, does a thread persist?
  The hub solved the analogous problem for claims with a content hash of the anchor prose
  (`CLAIMS.md`, the audit cache). The same trick should work, and is not designed here.
