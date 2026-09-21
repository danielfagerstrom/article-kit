# Writing standard and use of AI

The drafting standard for every article in the constellation, and for the wiki notes that feed
them. It moved here from the hub (`writing-style-and-ai-use.md`) on 2026-09-21
([ADR-0001](../adr/0001-article-kit-owns-the-article-process.md)), because its readers are the
article sessions, the `draft-reviewer`, the drafting gate and the publication template.

It answers three questions, in the order they bind: **who is the reader** (upstream of everything),
**what does the prose sound like** (neutral, and how that is enforced), and **what does the article
say about how it was written**.

**This file is not part of any article**, though it is readable by anyone: article-kit is a public
repository. What reaches an article's reader is the use-of-AI disclosure, and § 6 points at the
statements of record rather than carrying a draft.

**Who reads this file.** A session drafting or revising a `.tex` section, a blueprint proof or a
chapter note (the path-scoped rule `.claude/rules/article-kit/writing.md` sends it here); the
`draft-reviewer` agent; gate item 5 of [`DRAFTING-GATE.md`](DRAFTING-GATE.md). It defers to the
hub's `wiki/ai-prose-patterns.md` for the tic vocabulary and the mechanics of the review pass, and to
[`PUBLICATION-TEMPLATE.md`](PUBLICATION-TEMPLATE.md) § B and § C for the section contracts and the
exposition rubric. Where they overlap, they are not restated here.

---

## 0. Audience — the floor that licenses precision

Fix the reader first. Audience is upstream of voice, register, and how much to explain.

**Audience is a floor of assumed background, not a breadth.** The floor is what licenses precision.
Told to write for a vague "general" reader, a model assumes less, and it resolves "assume less" by
softening precise claims into gestures while still name-dropping the hard tools unexplained. That is
the worst of both ends. A high, well-chosen floor is what lets the prose be as precise as the source
notes.

**Self-contained is not elementary.** An article is self-contained: the reader needs neither the
earlier papers nor prior fluency in the specialised machinery. It is not elementary: it does not
re-teach what its reader already knows. Develop everything specific to *this* theory; assume the
graduate background below.

**Primary reader.** A mathematically mature researcher in the scale-space / mathematical-imaging
tradition: the JMIV and SSVM readership, in the lineage of Koenderink, Lindeberg, and Florack.

- **Assume, never re-teach:** Fourier analysis, PDEs, distributions; linear scale-space and the
  visual-front-end / receptive-field / N-jet programme; comfort reading a
  definition–proposition–proof-sketch.
- **Don't gloss:** measure-theoretic probability from scratch, basic harmonic analysis, or what a
  Gaussian is.
- **Teach — a sentence or two of what it is and why it is the right tool here, then use it:**
  everything a module needs that sits below that floor. The list is **per module**, not per
  repo: a repository that holds several modules gets a row per module, **written before that
  module's first section is drafted**, listing only what its module uses:

  | module | teach |
  |---|---|
  | the causal hemigroup articles | hemigroups and the cascade, negative-definite functions (Schoenberg), Bernstein functions, self-decomposability, the Thorin class |
  | the spatial line characterization (Paper V, `v0.1`) | hemigroups and the cascade, negative-definite functions, Lévy exponents, self-decomposability, the stable and Matérn families |
  | the spatial cone, bridge and corners (Paper V, `cone-v0.1`) | the line paper's list, plus Bernstein functions, subordination, the Thorin class and generalized gamma convolutions, type G laws |
  | the spatial selection of the Gaussian (Paper V, module C) | to be written before drafting |
  | the infinitesimal theory (SSF, parked) | Lie-group and Lie-wedge/semigroup machinery, the covariance-bracket method, pseudodifferential symbol calculus |
  | anything on the probabilistic route | self-similar Markov and Lévy processes (Lamperti, Dufresne) |

  A term below the floor that its module's list does not cover is a defect, not a shortcut: see the
  undischarged-referent audit in the hub's `wiki/ai-prose-patterns.md` § 3, which is the
  machine-checkable form of this rule.

A strong graduate student in mathematical imaging should be able to read the article linearly,
fetching none of the original papers. **A module that follows another restates what it uses of
it** (the axioms, the main theorem, the notation table), verbatim where it is shared text, and never
assumes the earlier paper was read.

**One primary audience.** Other readers (applied-math / fractional-PDE, the temporal-memory /
state-space-model neuroscience crowd of the related work) are welcome guests, not co-targets.
Writing to two floors at once collapses to the lower one.

---

## 1. Voice — neutral

**Neutral third person** (hub ADR-0015). "This paper", "the proof", "the construction"; "the author"
for self-citation, which a double-blind venue requires and which costs nothing elsewhere. "We" is
not banned (it is idiomatic inside a proof) but it is not the default, and it is not what carries
the collaboration. The disclosure does that.

**The prose does not try to sound like anyone.** There is no impersonation target and no seasoning
pass. The article is a human–machine collaboration, the disclosure says so plainly, and a voice
performed on top of that would be both unnecessary and a standing invitation to overdo it. What
makes the writing good is the explanatory sensibility (motivation before formalism, the physical
picture that makes a hard step intuitive, candour about limits) and that is content, delivered by
the rules in § 2 and § 3, not by ornament.

**No hype, in any direction.** Not about the results ("flagship", "crown result", "novel",
"powerful", "seminal", "the sharpest result in the field"), and not about the difficulty. Name
results descriptively: *the non-existence theorem*, *the characterization theorem*. Never refer to
another deliverable of the constellation by section number.

**Understate the twist.** The conceptual centre of an article should be set up so that it lands,
then stated flatly. A result that is genuinely surprising does not need to be told that it is.

**Hedge where honestly warranted** (*at least a first step*, *no experimental evaluation is done*),
never falsely tentative, never grandiose. Where something is research-stage, say so in the text
(gate item 6): an unproved statement, an unpinned interface or a `budding` note is named as frontier
where it occurs, never narrated with a theorem's confidence.

---

## 2. The restraint budget — the rules the drafts break

This is the part of the standard drafts break most, whatever the voice label, and it is the part a
reviewer can count. It is written to be counted.

A model's default over-supplies ornament, and the ornament compounds with document length. So the
budget is stated as limits, not as preferences:

- **One main clause, at most one subordinate clause.** More than that, break the sentence.
- **Em-dashes and semicolons are rare.** Prefer a period or a comma. As a calibration: a 6,000-word
  section carrying dozens of each is an order of magnitude over budget, and that is the count real
  drafts come in at.
- **No aphoristic closers.** A section does not end on an epigram.
- **No inversions** ("none of the three is negotiable") and **no X-not-Y closers** ("it is not
  bookkeeping, it is structure"), least of all as the last words of a section.
- **Never three long sentences in a row.** Follow a long one with a short one. As a per-paragraph
  heuristic that says *where* to act: at least one sentence under about 10 words, and room for one
  over about 30. The long one is permission, not a requirement. This is a diagnostic, never a target
  handed to the model: a numeric style goal invites chopping clauses into staccato fragments, which
  is a worse tic than the one it removes.
- **Plain vocabulary.** If a plainer word exists, use it.
- **No throat-clearing** ("It is important to note that", "In this section, we will"). Light explicit
  signposting is fine and the argument often needs it; the recap is not.
- **A map where the path is long.** A section whose payoff is a statement reached through many
  technical steps opens with a short map of those steps. A short section, or one with a natural
  path, just tells rather than tells about. This is context-dependent (the author's position,
  2026-09-18, which replaced a flat rule against per-section roadmaps).
- **Put the claim first**, and elaborate in the next sentence rather than in a trailing clause.
- **Lists are allowed.** A plain itemised list of steps or results is good writing. What to avoid is
  a listicle *feel* standing in for an argument.

The named tics (negative parallelism, participial summary tails, sincerity markers, salience
hedges, paraphrase laddering, teaser cataphora, tricolon, process adverbs) are catalogued with
their causes in the hub's `wiki/ai-prose-patterns.md` § 1. That note owns the vocabulary; the
reviewer emits its tags.

**Two of those tags are content defects, not style.** *Vague attribution* ("it is well known that",
"standard results give") and *unearned reference cascade* (a paragraph that names five concepts and
discharges none) each mark a place where a citation or an argument was never actually retrieved.
They are fixed as content: expand the concept, simplify past it, or remove it. Naming it and moving
on is not an option.

**The budget applies to the whole article, and each zone of it is fixed where it is owned.** A
paper in this framework has three zones: paper-side prose (leads, connective text, captions,
paper-only remarks), the statements shared verbatim with the blueprint, and the proofs of record
and remarks transcribed from it. The register pass edits the first zone only. The other two are
blueprint text, so their punctuation and ladders are fixed *at the blueprint*, in the safe
direction, by the session that owns it, and the paper re-transcribes; a pass that finds them
reports them to that session with the counts rather than editing the copy. Calibration from
Paper V's pass (2026-09-12): the prose came in at 98 em-dashes and 117 semicolons in 12,900 words
and the proofs at 43 and 93 in 7,250. The proofs were the denser zone, and they were not the one the
review reached. Count by zone (Paper V's `scripts/count-register.py`, until it moves into
`linkage`) so that the two numbers are not confused.

---

## 3. Technical register

The mathematics stays in the text. Because the full proofs are machine-checked, the prose need not
be painfully formal, but the mathematical content (definitions, statements, the decisive
derivations and where they turn) must be on the page, not merely named.

- **Every object gets a symbol and a type signature on introduction.** Name the spaces and maps
  explicitly, and carry the notation.
- **Numbered environments for the real content**: definition, proposition, lemma, theorem. Proofs
  may be shortened or sketched, but show the decisive move: the displayed calculation, the bracket
  that cascades. Where a step is only sketched, say so and point to the formal proof.
- **A remark whose paragraphs read as a proof is a proposition with a proof**, machine-checked or
  not.
- **Motivation first, then the statement, then the comments.** Every section and subsection opens
  with what the result is and why it matters, one plain sentence on the aim before each move.
  Technical comments on a statement or a proof come *after* the statement and before the proof,
  never before the reader has seen the statement. Results before proof talk; details after.
- **Borrowed facts are stated, not folded in.** A result taken from the literature becomes its own
  numbered theorem or definition with a page anchor read from the axiom ledger, never from memory.
  This is the prose-level counterpart of that ledger, and it is gate item 3.
- **Define each technical term on first use**, emphasised, and cite where it comes from; place a
  named family in its literature, the scale-space literature included. Never drop an exotic term
  unglossed (§ 0). A paragraph that introduces a proof idea explains each new object in its own
  sentence.
- **Let displayed equations do the work.** Connecting prose stays short and functional. Do not
  narrate a calculation you can show.
- **Keep the tools to what the argument consumes.** Develop only the machinery the results in front
  of the reader use; a general framework the article exercises only a slice of makes the text
  harder, not more authoritative, and is deferred to the article that uses it (the author, on the
  covariance framework in the SSF monograph: "keep the tools to what actually is needed").
- **Illustrate generously.** The theory is geometric, and a schematic often carries a point better
  than a paragraph. A figure asserts nothing the text does not.
- **No commentary on what is machine-checked in the body.** The trust-base subsection owns it (§ 4);
  inside a proof one sentence on what is cited and what is proved is fine.
- **No talk about the draft, the blueprint or the process** in the article. An alternative route is
  presented as an alternative route.
- **Length.** No budget on a preprint; a hard one at a conference. Economic either way: room to
  explain fully is not licence to pad.

**What "not painfully formal" does not license** is replacing a derivation with an essay about it.
"This is the algebraic heart of the argument" and "one checks that this set is closed and complete"
are the drift to avoid: show the step, or state it as a numbered claim and cite it.

---

## 4. Structural mechanisms

These are the moves the finished articles used in place of a voice. They are article-level
decisions, so each article's `adr/` records its own; this standard records that they are expected.

- **One relation-to-the-previous-theory remark per section, and never inside a statement or a
  proof.** The prior theory appears in the introduction, in the bridge section, and in that one
  remark. This keeps a statement readable on its own, and keeps the comparison from becoming the
  argument.
- **The trust base is owned by one subsection.** What is machine-checked, and what the verified
  development assumes, is set out in a single place early (§ 1.1 in the finished articles) and
  cited from everywhere else, including from the AI-use disclosure, which therefore does not repeat
  it.
- **The frontier is named where it occurs**, in the sentence that would otherwise overstate.
- **Descriptive, non-hyped naming**, and no deliverable referred to by section number.
- **Proofs of record follow the machine-checked route.** Where the Lean proof and a shorter printed
  argument diverge, the printed proof is rewritten to the checked route; the other route survives
  only as a marked remark.
- **A reference into an unreleased module** is prose about further work, with a LaTeX comment
  `% TODO(module X): cite <label> when released` beside it, never a `\ref` into text the release
  does not contain.
- **Every compression is ledgered** where one article compresses another (the conference
  extraction): each statement names what it compresses, what was dropped, and why it is still
  faithful, with a hash, so that a late page-fitting trim cannot pass silently.

---

## 5. Process — draft, flag blind, fix at the anchor

The standard is enforced by review, not by a stylistic pass at drafting time. Style instructions
given to an author agent shape the first few hundred words and then wash out; a model asked to both
find and fix will rewrite; and a rewrite resamples from the same distribution that produced the
tics. So read this file before drafting, and expect the review to be what holds the line.

1. **Draft** the section for clarity and correctness against § 0–4.
2. **Review blind.** A `draft-reviewer` that had no part in the writing emits located flags (quoted
   anchor, fixed tag, severity) against `PUBLICATION-TEMPLATE.md` § B and § C and the tag
   vocabulary of `ai-prose-patterns.md`. Flags, never verdicts; never an imposed rewrite.
3. **Triage by hand.** The false-positive rate is high in a maths paper where "Note that" is
   genre-legitimate. Set policy per tag rather than per instance.
4. **Fix locally, at exact anchors.** A unique quoted string plus a replacement. An edit that cannot
   be expressed that way is too large to be safe. Verify each with a word-level diff.

Two passes with opposite schedules: the **referent audit** (§ 0) runs early and repeatedly, because
it changes what gets written next; the **tic pass** runs once, late, on text that is then frozen,
because anything polished before the content settles gets regenerated. Frozen is the ideal and
rarely the fact, so the rule in practice is: run the tic pass once on the text as it stands, then
**rerun the detector on the diff only** after any later regeneration, never the whole pass again.
The mechanics (guardrails, the JSONL record format, the extraction heuristics) are in the hub's
`wiki/ai-prose-patterns.md` § 3.

**A summary drops hypotheses.** Every sentence that restates a result (abstract, introduction,
conclusion, a table of results, a caption) is compared with its statement before a build is
frozen; each such pass so far has found one that had lost a hypothesis.

**The part no editing pass substitutes for:** put in something a model would not have generated: a
wrong turn taken, an admission that an earlier construction was impractical, a numerical surprise.
Idiosyncratic content is a far stronger signal of authorship than idiosyncratic syntax, and it is
what a reader wants from a paper that discloses heavy AI assistance.

---

## 6. Use of AI — the statements of record

**This file carries no draft disclosure**, deliberately. Start from the real statements:

- **The statement of record** is Paper I's `paper/ai-statement.tex`
  (`hemigroup-causal-scale-space-kernels`, published as `fagerstrom2026hemigroup`). Read its
  header comment as well as its text: it records why an earlier framing understated the AI
  involvement, why the trust-boundary paragraph was removed rather than repeated, and that its
  figures must be re-derived rather than restated.
- **The scoping rule for a submission** is the SSVM paper's `notes/AI-USE.md` (decided 2026-09-04):
  a disclosure attaches to *this* submission (its text, its compression decisions) and not to a
  cited work's production. It **points rather than restates**; pointing is the same relation any
  paper has to a source's provenance, and a reader who wants the full account reaches it in one
  citation. **No storytelling**: where a monograph has room to say something interesting about the
  process, a submission needs transparency, and transparency is six lines.

Four rules govern any new statement:

1. **Never claim less AI involvement than there was.** It is the one failure mode a disclosure
   cannot afford, and it is why this file holds no reusable draft: a stale draft is instantiated by
   the next session and understates the work it is attached to.
2. **Numbers come from `chronicler`, carrying the date they were computed** and their caveats: they
   are lower bounds, and they have only ever moved upward as missing material was recovered. Never
   restate a figure without re-deriving it.
3. **Do not repeat the trust boundary.** The machine-checked subsection owns it (§ 4); the
   disclosure cites it.
4. **Anonymity outranks completeness.** In a double-blind submission, describing who produced a
   cited development's code deanonymises the author in the one place where the author is the
   subject. No policy asks for it.

*Convention note (early 2026): across ICMJE, COPE, Nature, Science, IEEE, ACM, Springer and
Elsevier, AI tools cannot be listed as authors, and AI use must be disclosed with the human author
retaining full responsibility. arXiv permits AI-assisted work with disclosure. When targeting a
specific venue, read its current wording rather than inferring it from the shape of the clause.*

---

## Pointers

- Hub ADR-0015: the voice decision and what it replaced.
- The hub's `wiki/ai-prose-patterns.md`: the tic vocabulary, the causes, and the review mechanics.
- [`PUBLICATION-TEMPLATE.md`](PUBLICATION-TEMPLATE.md) § B and § C: section contracts and the
  exposition rubric.
- [`REVIEWER-CONTRACT.md`](REVIEWER-CONTRACT.md): the flag format the reviewer emits.
- [`DRAFTING-GATE.md`](DRAFTING-GATE.md) item 5: the gate box this file owns.
- [`PROCESS.md`](PROCESS.md) § 8: where the passes sit in the article's life.
