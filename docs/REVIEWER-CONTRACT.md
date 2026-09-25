# Reviewer output contract

**Status: specified and implemented, 2026-09-25 (drafted 2026-08-15). The aggregator is
[`linkage review`](../linkage/review.py); `uv run pytest tests/test_review.py` holds it to this
page. Not yet adopted by the reviewer — the hub's `draft-reviewer` still emits prose reports, and
[what it has to change](#what-the-hub-must-change-in-draft-reviewermd) is listed at the end.**

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
would win by being the one a human reads. So the reviewer emits records, and `linkage review` prints
the report the charter describes — strengths line, STRUCTURE then VOICE, ranked, boundary restated —
over one review or over twenty.

### `kind: "review"` — exactly one, first

```json
{"kind":"review","target":"paper/09-signaling.tex","contract":"B.5",
 "contract_why":"main.tex assigns §9 the signaling form; definition→lemma→theorem→proof with results consumed by §10, §12. Not template §7 (Experiments) — this paper's realization slot is §11.",
 "maturity":"evergreen","strengths":"opens by motivating before it formalizes; honest about where each hypothesis bites; three genuinely worked cases",
 "floor":"linkage check — noted, not run"}
```

`target`, `contract`, `contract_why` and `strengths` are **required**; `maturity`, `floor` and `id`
are optional. A review that omits a required field, or declares a contract that does not parse, is
**not a review**: its flags are rejected with it, because a flag whose section contract is unknown
cannot be read as structural evidence.

**The review's identity** is its `id` when it declares one, else the file stem — one JSONL file per
review is the shape precisely so that the file name can carry it. In a concatenated stream, each
`kind:"review"` record opens a review and every flag after it belongs to that review until the next
one. Identity matters here for one reason: the count of *distinct reviews* is the sort key, so two
files that are the same review counted twice would corrupt the ranking.

### The section-contract declaration

`contract` is a declaration of which [`PUBLICATION-TEMPLATE.md`](PUBLICATION-TEMPLATE.md) §B contract
the reviewed text is being held to. Its grammar:

```
contract  ::=  item ("+" item)*
item      ::=  "B." ("0" | "1" … "10")
```

- `B.1` … `B.10` are the template's §B sections, by number: `B.1` Title & Abstract, `B.2`
  Introduction, `B.3` Related work, `B.4` Preliminaries, `B.5` Main theory, `B.6` Algorithmic
  realization, `B.7` Experiments, `B.8` Discussion, `B.9` Conclusion, `B.10` Back matter.
- **Several, joined by `+`**, when one file discharges more than one contract (`B.2+B.3` for an
  introduction that absorbs related work — the template says §3 may merge into §2).
- `B.0` for text the skeleton does not cover, which `contract_why` must then justify.

Two rules make the declaration load-bearing rather than decorative:

1. **The section number is not the contract number.** This paper's §7 is its characterization
   theorem; the template's §7 is *Experiments*. Every run in the trial batch had to be told, so the
   reviewer declares its choice and `contract_why` says why *this* contract and not the
   same-numbered one.
2. **Two reviews of one target that declare different contracts are a reported conflict**, not
   something to average over. A wrong mapping invalidates every `CONTRACT`, `PROMISE` and `ORPHAN`
   flag under it, and the disagreement is the only mechanical signal that one of the two got it
   wrong.

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
| `layer` | yes | `structure` (§B) or `voice` (§C). **Determined by the tag**, not chosen: a tag belongs to one layer, and a flag whose `layer` disagrees with its tag's is malformed |
| `severity` | yes | 1–3, the reviewer's local read. Recorded, never the sort key |
| `claim` | yes | one sentence: what is wrong |
| `probe` | yes | what to check or change. **Never a rewrite the reviewer imposes** |
| `refs` | yes | every label the flag implicates, not only the one it sits on. This is what clusters |
| `elsewhere` | no | other files the flag reaches into |
| `shared_with_blueprint` | no | true if the anchor sits inside a `% shared with blueprint` block — the fix is then blueprint-side, and the reviewer should say so |

**The anchor rule is mechanically enforceable, and that is the point.** An anchor that does not occur
exactly once in its file is a malformed flag: reject it. (Once *modulo whitespace* — the quotation is
verbatim, but where LaTeX wrapped the line is not part of the text.) This is the same discipline
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

### The six that are not prose-surface, by example

These are the tags the note's §1 vocabulary does not reach, and they carried eight of the ten threads
in the trial batch. Each is given as the reviewer needs it: what the defect *is*, what it is not, and
one instance.

**`SCOPE` — the claim is wider than the result it rests on.** The text asserts something of a class,
a range or a construction for which only a subcase is established. A claim that is *wrong* is Lean's
business; this is a claim that is wider than its own support.

> *anchor:* `(H) excludes the cone's extreme boundary and nothing else`
> *claim:* the "and nothing else" is contradicted twice in the same paragraph — the pure delays are
> extreme rays with `b0>0`, and the paragraph itself says (H) holds whenever `b0>0`.
> *probe:* survives only as "the extreme rays with `b0=0` lie on (H)'s boundary". Drop "and nothing
> else". *refs:* `prop:extreme-rays`, `rem:extreme-rays`, `def:standing-hypothesis`.

**`HYPOTHESIS` — a condition the body carries is absent where the claim is made.** The proof, the
statement or the standing assumptions require something the abstract, introduction, discussion or
transition sentence does not repeat. The classic drift: the theorem says "for admissible kernels",
the introduction says "for kernels".

> *anchor:* `we obtain a closed form for every kernel of the cone`
> *claim:* `thm:closed-form` is stated under the standing hypothesis, which excludes part of the
> cone; the introduction's sentence quantifies over all of it.
> *probe:* restate the theorem's quantifier here, or say "under (H)". *refs:*
> `thm:closed-form`, `def:standing-hypothesis`.

**`COUNT` — an economy or enumeration claim the text's own proofs falsify.** "Exactly three",
"the only", "a single assumption suffices", "two ingredients". Distinct from `SCOPE` because the
defect is arithmetic and checkable inside the document: count what the text actually uses.

> *anchor:* `the construction rests on a single structural assumption`
> *claim:* the proof of `prop:main` invokes (H), the semigroup property and separability — three.
> *probe:* count the hypotheses the proofs actually invoke and either reduce the claim or the
> hypotheses. *refs:* `prop:main`, `def:standing-hypothesis`.

**`NOTATION` — one symbol, two objects.** The same symbol denotes different things in different
places, or a symbol silently changes arity, type or normalization. Not `UNDEFINED`, which is a symbol
that is never introduced at all; here it *is* introduced, twice.

> *anchor:* `where $z_*$ denotes the cut-off of the generator`
> *claim:* `z_*` is the kernel's cut-off in §4 and the generator's in §9; the two differ by the
> normalization fixed in `def:normalization`.
> *probe:* check every occurrence of `z_*` against `def:normalization` and rename one of the two.
> *refs:* `def:normalization`, `def:standing-hypothesis`.

**`TRANSCLUSION` — upstream (blueprint) carries context this text dropped.** The blueprint node the
paper shares is surrounded by a hypothesis list, a `\uses` set or a remark that the paper's rendering
left behind, so the paper's version reads as more general or less conditioned than the node. The fix
is usually blueprint-side or a re-transcription, which is what `shared_with_blueprint` is for.

> *anchor:* `By Proposition~\ref{prop:extreme-rays}, the decomposition is unique.`
> *claim:* the blueprint node `prop:extreme-rays` uses `lem:positivity`, which the paper's proof
> never invokes and never states; the uniqueness reads as unconditional here.
> *probe:* compare the node's `\uses` set against the `\ref`s in this proof. *refs:*
> `prop:extreme-rays`, `lem:positivity`. *shared_with_blueprint:* `true`.

**`FRONTIER` — unsettled or cited status not marked *at the point of claim*.** The document knows
elsewhere that a result is conjectural, proved only on paper, or imported from a source; the sentence
that uses it does not say so. The *absence* of the marker anywhere is `note-evaluator`'s business
(grounding); its *misplacement* — present in §2, missing in the sentence that leans on it — is this.

> *anchor:* `since the completeness of the family is known`
> *claim:* `thm:completeness` is an `[A]` interface node grounded in `@lindeberg2011`, and the
> §1.1 trust base says so; this sentence presents it as settled in-document.
> *probe:* mark the import where it is used, as the trust base marks it. *refs:*
> `thm:completeness`.

## Defect identity

A **defect** is one fault in the text; a **flag** is one reviewer's report of it. Two blind reviewers
who find the same fault write different anchors, different severities and different sentences, and
the count of how many of them found it is the number the ranking needs — so the flags must land under
one key, computed from the flags themselves. Nothing may depend on reviewers agreeing on a name: a
blind reviewer sees one section and cannot name a thread.

**Flags pool when they are in the same `file`, carry the same `tag`, and either**

- **cite a label in common** (`refs` intersect) — the primary rule, and the reason `refs` records
  *every* label a flag implicates rather than the one it sits on; **or**
- **cite no label at all and quote overlapping prose** — one flag's `anchor`, normalized for case and
  whitespace, contains the other's. This is the voice tags' rule; they rarely have labels to share.

Pooling is transitive: A and B pool, B and C pool, so all three are one defect.

**The key** of a pool is

```
<file>::<TAG>::<referent>
```

where the *referent* is the lexicographically smallest label the pool cites, or
`anchor:<sha1[:8]>` of its smallest normalized anchor when it cites none. Two pools in one
`(file, tag)` cannot collide: had they shared a label they would have been joined, and anchor-keyed
pools have non-overlapping anchors.

**What the key guarantees, and what it does not.** It is a function of the pooled set alone, so it is
stable across runs, across the order the review files are given in, and under adding a review that
finds the same defect. It is *not* stable across paper revisions, and adding a review that cites a
label alphabetically before the current referent renames the key. So the key identifies a defect
*within one aggregate*; durable identity across revisions is still open (below).

**Severity is recorded, never the key.** A defect carries the maximum severity any reviewer gave it,
and that number is the last tiebreak in the ranking and nothing else. The trial batch labelled one
defect `[low-med]` and `[high]`; pooling is exactly the operation that makes the disagreement visible
and the number uninformative.

## Aggregation

`linkage review <review.jsonl>… [--base DIR] [--json] [--top N]`, over the records of every review of
one artifact. `--base` is what the flags' repo-relative `file` paths resolve against. Exit 0 when
every record is well-formed, 1 when any is not (the anchor rule enforced is the point), 2 when the
tooling could not answer — the same three codes as `linkage check`.

1. **Validate.** Every `anchor` occurs exactly once in its `file` — modulo whitespace, because a
   quotation out of a `.tex` source crosses a line break about as often as not; every review declares
   a parseable contract; tag and layer agree; `severity` is 1–3; every `refs` label resolves to a
   `\label{}` under `--base`. A flag with no locatable anchor is dropped and reported (it is not
   actionable); a flag citing a label that resolves nowhere is kept and reported (the label is
   evidence, and the miss is worth knowing about). **Malformed records are reported, never silently
   dropped.**
2. **Pool** into defects by the identity rule above.
3. **Cluster** the defects into candidate **threads**: defects sharing a label, or — same tag only —
   one defect's `elsewhere` naming the other's file. A thread spans at least two files and at least
   two defects. This is a proposal, not a verdict: the trial batch's threads would have been mostly
   recoverable this way, but not all of them, and a cluster of one is a lead rather than a finding.
4. **Rank by breadth** — number of *independent reviews* contributing, then total flags, then max
   severity as the last tiebreak only. Threads rank the same way, over their members' reviews.
5. **Report**: the reviews with their strengths lines and the boundary restatement; then threads with
   their sections; then defects, STRUCTURE before VOICE, each with its count, its anchors, its claims
   and its probes. Never the raw list first — that is the failure mode this contract exists to
   prevent.

**Cap what is handed on.** The evidence is that fewer items get incorporated, so the worklist is
threads plus the decisions they imply, with the flags available underneath as drill-down: `--top N`
(default 10) bounds what each layer prints, and `--json` is the whole aggregate for a tool. Every
flag stays in the file; not every flag reaches the author's list.

## What the reviewer still owes in prose

The charter's non-mechanical obligations do not become fields:

- the **strengths line** is in the review record and is required — it is what makes the output read as
  triage rather than as a verdict;
- the **boundary restatement** (correctness is Lean's, grounding `note-evaluator`'s, integrity
  `linkage check`'s) is rendered from the review record, not repeated per flag;
- **no verdicts**, and no rewrites. `probe` says what to check; the author decides.

## What the hub must change in `draft-reviewer.md`

The adoption step is the author's: this repository owns the spec and never writes the hub's files.
What the hub's `.claude/agents/draft-reviewer.md` has to change, in one pass:

1. **Emit JSONL, not a prose report.** One `.jsonl` file per run, named for the run (the file stem
   becomes the review's identity), one record per line: the `kind:"review"` record first, then one
   `kind:"flag"` per finding. The readable report is no longer the agent's output — `linkage review`
   renders it — so the prompt's report-format section is replaced by the record shapes above.
2. **Declare the section contract.** Before flagging: name the `B.<n>` the section is held to and say
   in `contract_why` why that one and not the same-numbered template section. The agent currently
   has to be told this in the invocation; it becomes a required field.
3. **Carry the strengths line into the review record**, where it is required, instead of into the
   report's opening paragraph.
4. **Teach the six non-prose-surface tags** — `SCOPE`, `HYPOTHESIS`, `COUNT`, `NOTATION`,
   `TRANSCLUSION`, `FRONTIER` — with the definitions and examples above, beside the prose-surface
   tags it already carries from `ai-prose-patterns.md` §1. Eight of the ten threads in the trial
   batch were not prose-surface, so an agent with only the old vocabulary cannot emit most of what
   matters.
5. **Require `refs` on every flag**: *every* label the flag implicates, not the one it sits on. This
   is what pools flags into defects and defects into threads; a flag with an empty `refs` where
   labels exist is a flag that will never join a thread.
6. **Make the anchor rule explicit**: verbatim, and unique in the file. Malformed anchors are
   rejected by the aggregator, so an agent that quotes loosely loses its findings.
7. **Keep the boundary and the no-verdicts rule** unchanged: `probe` says what to check, never a
   rewrite; correctness stays Lean's, grounding `note-evaluator`'s, integrity `linkage check`'s.

Until that pass lands, `linkage review` has nothing to read; the contract is implemented on this side
and unadopted on the other.

## Open questions

**Settled, 2026-09-25:** the aggregator lives here, as `linkage review`, not as a hub verb. It runs
over an article's paper sources — it needs the `.tex` to enforce the anchor rule and resolve `refs` —
and the hub has no checkout of them. The hub's side of the channel stays what it was: the agent
emits, this repository consumes, neither writes the other's files.

- Should `severity` survive at all, given it proved uninformative when pooled? Kept for now because a
  single-section review still needs to rank its own output, and the trial batch showed the *within*-
  section ranking was sound even where the cross-section one was not.
- Thread identity across *revisions* — when a paper changes and is re-reviewed, does a thread persist?
  The hub solved the analogous problem for claims with a content hash of the anchor prose
  (`CLAIMS.md`, the audit cache). The same trick should work, and is not designed here.
