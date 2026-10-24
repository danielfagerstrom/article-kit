---
name: write
description: >
  The article writing standard's drafting rules, WRITING.md §§ 0–4: the restraint budget (the
  rules the drafts break), the reader's floor, the neutral voice, the technical register and the
  structural mechanisms. Invoke before drafting or revising any article prose (a paper or draft
  section, a blueprint proof, a chapter note), and again after a compaction.
---

# The writing standard: the drafting rules

`docs/WRITING.md` §§ 0–4, verbatim, the restraint budget first. On demand, at the step that needs
them: § 5 (the process: draft, flag blind, fix at the anchor) and § 6 (the AI statement) in
`${CLAUDE_PLUGIN_ROOT}/docs/WRITING.md`; the section contracts and the exposition rubric, § B and §
C of `${CLAUDE_PLUGIN_ROOT}/docs/PUBLICATION-TEMPLATE.md`, for the section being written; its § D
for the calibration exemplars. Relative links below are to `${CLAUDE_PLUGIN_ROOT}/docs/` (in
article-kit itself, `docs/`). Generated from the document by `linkage.skills`; edit the document,
not this file.

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
review reached. Count by zone (`linkage prose register`, which reports prose, statement and proof
apart) so that the two numbers are not confused.

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
  everything a module needs that sits below that floor. **One default list covers the whole
  programme**, not a row per module: the reader is not assumed to know the more advanced parts of
  probability theory or Lie theory, so the tools from them that the programme uses are taught when
  first used.

  **The default list:** hemigroups and the cascade, negative-definite functions (Schoenberg), Lévy
  exponents, Bernstein functions, self-decomposability, subordination, the Thorin class,
  generalized gamma convolutions, type G laws, the stable and Matérn families, Pólya frequency
  functions, total positivity and the variation-diminishing property.

  **Beyond the default, per module, only where a module genuinely goes beyond it:**

  | module | beyond the default |
  |---|---|
  | the infinitesimal theory (SSF, parked) | Lie-group and Lie-wedge/semigroup machinery, the covariance-bracket method, pseudodifferential symbol calculus |
  | anything on the probabilistic route | self-similar Markov and Lévy processes (Lamperti, Dufresne) |
  | the selection of the Gaussian (Paper V, module C) | the modified Bessel equation with its solution basis and behaviour at the origin; generalized axially symmetric potential theory, that is the half-plane Dirichlet problem for $z_{xx} + z_{yy} + (k/y)z_y = 0$ and its Poisson kernel |

  A module checks the default list before drafting its first section and adds a line to the table
  above only for what it uses that goes beyond it; most modules add nothing. A term below the floor
  that neither the default list nor the module's "beyond the default" line covers is a defect, not
  a shortcut: see the undischarged-referent audit in the hub's `wiki/ai-prose-patterns.md` § 3,
  which is the machine-checkable form of this rule.

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

**A cited paper is named as any paper is.** Author and year, or the bibliography number with a word
of what it is — never the programme's internal paper letters or module letters ("the line paper [V]
and its cone module [B]" names nothing a reader outside the constellation can resolve). Where a
statement shared verbatim with the blueprint carries such a label inside its own transcribed
citation (a `\ledger{A3}`-style cite), that is a macro question, not a prose one: see § 4.

**Understate the twist.** The conceptual centre of an article should be set up so that it lands,
then stated flatly. A result that is genuinely surprising does not need to be told that it is.

**Hedge where honestly warranted** (*at least a first step*, *no experimental evaluation is done*),
never falsely tentative, never grandiose. Where something is research-stage, say so in the text
(gate item 6): an unproved statement, an unpinned interface or a `budding` note is named as frontier
where it occurs, never narrated with a theorem's confidence.

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
- **Blueprint habits do not transfer to paper prose, in either direction.** A cited result is stated
  with its citation, not re-derived, re-explained, or marked with what it is *not* used for in the
  citing prose: provenance, axiom accounting and non-use are the trust-base subsection's business
  (§ 4), said there once, never scattered through prose that retells how a cited paper proves its
  fact. The habit runs the other way for a concept below the reader's floor (§ 0): the blueprint's
  definition alone is its shorthand for a specialist reader, not an introduction, so the paper
  introduces the concept in plain words — what it is, why it matters here, one familiar example —
  before giving its formal definition.
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
  it. That subsection owns the *statement* of the trust base: every sentence a reader needs to judge
  a result. At least that is the coverage by section (which results are machine-checked, and to
  what statement), everything that is not formalized, every assumption the verified development
  rests on, and the cited facts taken as given, with the count of the steps they carry beyond their
  sources. The *inventory* behind that statement (tables, per-name notes, reproduction commands,
  raw `#print axioms` output) may move to a verification appendix that the subsection names. The
  disclosure rule is unchanged: nothing honesty-critical leaves § 1.1. The appendix adds detail to
  what § 1.1 says; it never holds a caveat, a gap or an assumption that § 1.1 does not state, and
  when it is unclear which side a sentence falls on, it stays in § 1.1. This is a rule about where
  the disclosure is made, not a length budget. (Module C of `spatial-hemigroup-scale-space` had
  four and a half pages here before the mathematics began; the moderate split above is what it
  kept.)
- **The frontier is named where it occurs**, in the sentence that would otherwise overstate.
- **Descriptive, non-hyped naming**, and no deliverable referred to by section number.
- **Proofs of record follow the machine-checked route.** Where the Lean proof and a shorter printed
  argument diverge, the printed proof is rewritten to the checked route; the other route survives
  only as a marked remark.
- **A reference into an unreleased module** is prose about further work, with a LaTeX comment
  `% TODO(module X): cite <label> when released` beside it, never a `\ref` into text the release
  does not contain.
- **A programme-internal label inside a shared statement is a macro question, not a prose one.**
  § 1's rule against printing `[V]`/`[B]`-style labels to a paper's reader still applies when such a
  label sits inside a statement transcribed verbatim from the blueprint. The fix, when it exists, is
  a macro the blueprint and the paper render differently — on the model of `\ledger{A3}`, which
  already prints the cited-fact's name rather than the raw label — so the blueprint keeps its short
  form, the paper prints a real citation, and `linkage check` still compares the source text
  (`\prog{V}{Thm.~7.3}` or similar). **Not built**: `scaffold/blueprint/linkage-macros.tex` is owned
  by, and synced from, the `linkage` repo, so the macro is that repo's item, not an article's or this
  one's to add here. Until it exists, a transcribed statement's citation is rewritten by hand to a
  real reference wherever it reaches a paper.
- **Every compression is ledgered** where one article compresses another (the conference
  extraction): each statement names what it compresses, what was dropped, and why it is still
  faithful, with a hash, so that a late page-fitting trim cannot pass silently.

---
