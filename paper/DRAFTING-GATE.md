# Section readiness gate

Before a section of the monograph is drafted as **prose**, it must pass this gate.

Prose is the last and cheapest step, not the payoff — a re-voicing of a settled structure for a fixed
audience. The value lives upstream, in the grounded notes and the blueprint spine. Writing polished
prose ahead of that structure is how precision gets lost: the writer (human or LLM) ends up papering a
structural gap with fluent words, which reads well and says less. This gate exists to stop that.

Each check names **the artifact that owns the signal**, so the gate is also the responsibility map: if a
box has no clean owner, that is a hole in the foundation, not in the prose.

---

## The gate

A section may be drafted as prose only when every applicable box is checked.

### 1. Spine — the section's role is settled
*owner: the outline — `Notes/wiki/projects/spatio-temporal-scale-space.md`, its `## Slots` section*
- [ ] Fixed place and order in the outline — i.e. the section is a slot.
- [ ] A one-line thesis: the single claim the section makes. (`thesis:` sub-bullet on the slot.)
- [ ] Scope boundary explicit — what it delivers vs. what it defers to a sibling or successor.
      (`scope:` sub-bullet.)

### 2. Statements — the formal spine exists
*owner: `blueprint/src/content.tex` + `blueprint/AXIOMS.md`*
- [ ] Every theorem/definition the section will assert is a blueprint node, tagged **[T]** or **[A]**.
- [ ] Each **[T]** node is `\leanok` (proved), or explicitly listed as frontier (item 6).
- [ ] Each **[A]** node is grounded in `AXIOMS.md` (named theorem + page), or flagged un-pinned.

### 3. Content — the knowledge is grounded and mature
*owner: the wiki content note (e.g. `Notes/wiki/covariant-memory-evolution.md`) + its quality axes*
- [ ] A content note carries the actual argument (the "what"), with references and Lean pointers.
- [ ] The note clears the **gate triple `(maturity: evergreen, confidence: verified, lifecycle: active)`**
      — or the shortfall *is* the section's declared frontier (item 6).
- [ ] Open questions / contradictions in the note are resolved or explicitly parked.

> **On the triple.** Earlier drafts of this gate asked for "maturity at or above `grounded`". There is
> no such level: `grounded` was this repo's invention, and it collapsed three independent things into
> one word. The wiki's schema is deliberately **three orthogonal axes** — `maturity` (seed → budding →
> evergreen) is how worked-out the prose is, `confidence` (speculative → probable → verified) is how
> sure it is correct, `lifecycle` (active → stale → superseded) is freshness. A note can honestly be
> `evergreen` yet only `probable`; that is a finished write-up of an open question, not a defect, and a
> single "grounded" reading cannot express it. The hub owns this schema
> ([`Notes/CLAIMS.md`](file:///C:/Users/danie/Documents/Notes/CLAIMS.md)); this gate consumes it and
> must not mint levels of its own. `wiki rollup` already aggregates each slot's notes weakest-link
> against exactly this triple.

### 4. Illustration & numerics — the story is visible and checked
*owner: `scripts/` + the content note*
- [ ] Every load-bearing figure is identified and at least sketched.
      *(If you can't draw the step, its story isn't clear yet — a fail, not a defer.)*
- [ ] Numerical claims (tail rates, masses, verifications) have a reproducible script.

### 5. Register — the writing target is fixed
*owner: the private `writing-style-and-ai-use.md` (audience + voice + technical register)*
- [ ] Every concept the section uses that sits below the audience floor has a background-then-use plan
      (a sentence or two of what it is and why it's the right tool, then use).

### 6. Honesty — the frontier is marked, not hidden
*owner: the prose, checked against items 2–3*
- [ ] Anything research-stage (an un-pinned [A], a `budding` note, an unproved [T]) is named as frontier
      in the text, never narrated with a theorem's confidence.

### 7. Single-sourcing — statements can't drift
*owner: [`blueprint/LINKAGE.md`](../blueprint/LINKAGE.md) + `scripts/check_linkage.py`*
- [ ] Each theorem the prose shares with the blueprint carries `% shared with blueprint <label>` naming a
      real blueprint label (target: the identical `\label`).
- [ ] `python scripts/check_linkage.py` passes (exit 0).

---

## The rule

- Draft prose only when **items 1–3, 5, 6** pass.
- Item 4 should precede, but figures may be drafted alongside the prose.
- Item 7 is enforced by `scripts/check_linkage.py` (run it before drafting/publishing).

**Meta-rule:** when a box fails, **fix the upstream artifact — do not compensate in the prose.**
Compensating in prose is the exact failure this gate prevents.

## Running it

The hub executes this document. From anywhere in the wiki vault, or from this repo with
`$WIKI_VAULT` set to it:

```bash
wiki gate --slot "§5"              # all seven boxes, each read from its owning artifact
wiki gate --slot "§5" --worklist   # just what to go and do, merged with the evaluator's list
wiki gate --check                  # exit 1 if a machine-checkable box fails
```

It reports items 1–4 deterministically, hands items 5–6 to a reader, and leaves item 7 here.
**It never reports READY, by design:** items 5 and 6 are judgements about prose, and item 6's cached
findings are free text that mixes violations with clearances — a tool that "read" them would be
inventing authority it does not have. What it *can* assert is whether the audit behind item 6 is
current, since a section may not lean on an audit of prose that has since changed. So its best verdict
is `NEEDS-REVIEW`: everything checkable clears, now go and read.

The hub owns that tool and its schema (`Notes/CLAIMS.md` § "The gate"); this document is the spec it
implements. If a box here changes, the change lands here first.

## Relation to the pipeline

This gate is the concrete form of the "Handoff signal" in `RESEARCH.md` (an item moves from *developing
here* to *writing in the repo* when its wiki page is mature enough). It makes "mature enough" auditable,
section by section.

The stages it sits between:

    ideas → grounded notes (refs + Lean) → blueprint spine → figures/numerics → [GATE] → prose

Prose is downstream of the gate. Everything above it is where the work — and the value — actually lives.
