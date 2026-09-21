---
paths:
  - "blueprint/src/**"
---

# article-kit — the blueprint

Framework-owned (`linkage init --sync`); do not edit here. The rules the checks enforce are
`../article-kit/docs/LINKAGE.md`; the phase is `../article-kit/docs/PROCESS.md` § 3.

- **The blueprint is the text of record.** The paper and the wiki transcribe its nodes verbatim.
  Statements and proofs are publication-quality mathematics in the register of
  `../article-kit/docs/WRITING.md`; "see Lean" is not a proof.
- Every statement node is `[T]` or `[A]`; an `[A]` node is grounded in a ledger entry with a
  page-anchored citation and says what the citation carries and what it does not.
- After the module's first release the draft is frozen and the blueprint is the only text of
  record; no "draft mirror owed" note is written.
- The framework-owned files under `blueprint/src/` (`blueprint.sty`, `theorems.tex`,
  `linkage-macros.tex`, `latexmkrc`) are edited in article-kit, never here.
- Never write backslash-bearing content through a non-raw Python string: `"\begin"` holds a
  backspace, `"\ref"` a carriage return. The control-character check runs first in the build.
