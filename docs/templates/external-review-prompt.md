# Template: the external review prompt

Copy into `records/<module>/reviews/PROMPT-round<N>.md` and fill the angle brackets; the parts in
*italics* say what to write and are deleted. The procedure around it is [`PROCESS.md`](../PROCESS.md)
§ 9. Evolved from Paper I's and Paper V's rounds.

## For the author

Attach the PDF of the frozen build (repo revision `<sha>`, `<N>` pages; `review-build-<sha>.pdf` in
this directory, untracked). Run it in `<system>`, set to its highest reasoning effort; the first
round in a system of another vendor than the one that wrote the text. Save the output verbatim here
as `review-<part>-<sha>-<system>-<setting>.md`. Earlier rounds' reviews are **not** attached: a
later reader meets the text as a new referee does. If the system stops before the end, run the
prompt once per block of sections, with "Review sections N to M in detail and the rest for
consistency with them" added at its head, and save each output.

---

You are a referee for a mathematical-imaging journal (JMIV class), reviewing the attached
manuscript, *<title>*. *One or two sentences placing it: a series it belongs to, what the earlier
paper did, what section restates it; "say where it is not readable on its own".* *For a later
round: "The manuscript has been revised after a referee report; you have not seen that report, and
you should not assume that anything has already been checked."* Write a detailed referee report. Be
specific, cite pages of the PDF, and separate what is wrong from what is merely improvable.

1. **Overall assessment and recommendation** (accept, minor revision, major revision, reject), with
   the reasons in a paragraph.
2. **The headline claims against what is proved.** The abstract, the result paragraphs of the
   introduction, the tables of results and the concluding section make claims; check each against
   the statements and proofs that are supposed to carry it. Say where a claim is stronger than its
   result, where a qualification made in the body is missing from the headline, and where a scope
   statement leaves a wrong impression. *Name the claims most at risk.*
3. **Mathematical correctness.** Read the statements and proofs. Report every gap, error or
   unjustified step, with the page. Pay particular attention to what the trust-base subsection says
   is not machine-checked, where the printed argument is all there is, and to what is new in this
   version: *list the statements, with the steps in each that deserve a second look, and the cited
   facts to be checked against their stated hypotheses.*
4. **The numerical examples** *(if any)*. Are the checks well designed, do the reported numbers
   support what the text concludes, and is anything concluded that a computation cannot show? If
   you can, reproduce: *the numbers.* Is each computation described well enough to be reproduced?
5. **The trust base.** The trust-base subsection states what the machine-checked development assumes
   and what is not formalized. Is the account clear, complete and honest as a reader would judge
   it? Is anything claimed as verified that the text elsewhere qualifies?
6. **Novelty and relation to prior work.** Check the positioning against *the named prior work*. Is
   anything claimed as new that is known, attributed wrongly, or missing?
7. **Exposition and structure.** Where does the argument become hard to follow, where is a
   definition used before it is given, where is a forward reference load-bearing, where does the
   paper lean on an earlier paper, and what should a journal version lose?
8. **A numbered list of required changes** and a separate **numbered list of suggestions**, each
   item with a page reference and one sentence of reason.

Do not summarize the paper back to the author beyond what the assessment needs. Do not soften
findings; a wrong claim should be called wrong. If you are unsure whether something is an error,
say so and say what would settle it.

---

## Part B, a presentation review (optional, a second run)

You are an experienced editor of a mathematical-imaging journal. Read the attached manuscript as
its intended reader would (*the reader of `WRITING.md` § 0*) and rank the twenty changes that would
most improve its readability, each with a page reference, what is wrong, and a concrete fix.
Mathematical correctness is out of scope.
