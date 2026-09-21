---
paths:
  - "paper*/**"
  - "draft/**"
---

# article-kit — writing the article

Framework-owned (`linkage init --sync`); do not edit here.

**Before drafting or revising any prose in this repository, read
`../article-kit/docs/WRITING.md` in full**, and `../article-kit/docs/PUBLICATION-TEMPLATE.md`
§ B for the section you are writing. The first draft of a module written without the standard had
to be corrected section by section at the author's review.

The rules that are broken most, as a reminder, not a substitute:

- The article is read on its own. A module that follows another restates what it uses of it.
- Each section opens with its aim; a long path gets a map. Motivation, then the statement, then the
  comments on it, then the proof.
- Every term below the reader's floor (`WRITING.md` § 0, the row for this module) is introduced at
  first use with its literature. If this module has no row there yet, write it before drafting.
- No commentary on machine-checking in the body: the trust-base subsection owns it.
- One main clause and at most one subordinate; em-dashes and semicolons rare; no X-not-Y closers,
  no inversions, no aphoristic endings.
- Statements and the proofs of record are blueprint text: transcribe them verbatim under
  `% shared with blueprint` markers and never edit them paper-side. A needed change is made in the
  blueprint and re-transcribed.
- A reference into an unreleased module is prose with `% TODO(module X): cite <label> when
  released`, never a `\ref`.
- Every number in a numerical example names the exact object computed.
- A summary sentence (abstract, introduction, conclusion, a table, a caption) is compared with its
  statement before a build is frozen: summaries drop hypotheses.

The passes (readability, blind register review, scope audit, AI statement, citation audit) are
`../article-kit/docs/PROCESS.md` § 8. The gates before a commit touching the paper: the build clean,
`linkage check` with every shared statement `verbatim`, the control-character check.
