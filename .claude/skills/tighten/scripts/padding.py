#!/usr/bin/env python3
"""Rank LaTeX paragraphs by how much text in them says nothing a reader needs.

`overhang.py` aims a wording pass at PAGES: it sorts paragraphs by how far past a line
boundary they sit, because that is what makes an edit pay in lines. That target is right
when a page limit is the problem and wrong when the problem is padding, and the two come
apart in one specific way. Overhang decides WHICH PARAGRAPH to visit by a number that is
essentially random with respect to how much padding the paragraph holds: a paragraph full
of announcements sitting just after a boundary needs a whole width to pay and is skipped,
while a clean one a character over is visited and yields a cosmetic trim. Within whatever
paragraph you do enter, the cheapest characters really are the low-information ones, which
is why an overhang pass improves prose at all. This tool keeps that second half and
replaces the selection: it ranks by REMOVABLE MASS, the characters sitting in sentences
that carry no mathematics, no reference, no citation and no anchor, and whose content words
are the vocabulary of the document rather than of the subject.

The pattern it is built for, which no fixed-phrase detector catches:

    an abstract enumeration of what is coming ("the demand splits into three strengths,
    and the three select three different things"), then a forward reference per item, and
    at the end the content. Mirrored form: the paragraph does its work and then adds a
    sentence summarising what it just did, or handing off to the next object.

`linkage prose stats` owns the fixed-phrase families (SIGNPOST, SALIENCE, PARALADDER and
the rest) and their rates against the author's own corpus. Run it first: it answers "which
tics is this author overusing". It cannot see this pattern, because the pattern has no
fixed phrase -- on a document where every family scored zero, this ranker found the tic in
ten of sixteen paragraphs.

A CANDIDATE IS NOT A VERDICT. A signpost is not a defect; it is a defect when it is
overused or when it carries nothing. Two sentences with identical shape can differ in
whether a reader needs one. So the report lists candidates, the editor DISPOSES of each --
deleted, or kept with a reason in one word (carries a hypothesis, carries a pointer a
reader needs, is the only statement of a term) -- and the rates at the foot of the report
are what say whether the paper is overusing the shape at all.

    padding.py report FILE...  [--min-mass N] [--top N] [--json]
    padding.py rates  FILE...
"""
import argparse, json, re, signal, sys, pathlib

MATH = re.compile(r"\$[^$]*\$")
CITE = re.compile(r"\\s?cite[a-zA-Z]*(\[[^\]]*\])?\{[^}]*\}")
REF = re.compile(r"\\(eq)?ref\{[^}]*\}")
CMD = re.compile(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{)?")
ANCHOR = re.compile(r"(pp?\.|\\S|Thm|Theorem|Prop\.|Def\.|Ch\.|eq\.|Lemma|Remark|Cor\.)")

# The vocabulary of a document talking about itself. A sentence whose content words are
# mostly these, and which carries no mathematics, is talking about the text.
META = set("""section subsection paragraph sentence statement clause item list table figure
theorem proposition lemma corollary remark definition example proof question answer reading
readings sense senses kind kinds strength strengths step steps point points part parts half
route way ways form forms version thing things subject topic account note notes summary
discussion treatment exposition argument case cases side sides aspect respect""".split())

# Deixis: the sentence points somewhere else in the document rather than saying something.
DEIXIS = re.compile(r"\b(below|above|earlier|later|next|following|preceding|in turn|"
                    r"here|what follows|the rest of|turn to|takes? (?:them|it|these)|"
                    r"we (?:now|shall|will)|will be (?:seen|shown|treated|given)|"
                    r"is treated|are treated|says which|worth (?:keeping|noting|saying)|"
                    r"as follows|first \w+, then|respectively below)\b", re.I)

# An enumeration cue: a count word governing a plural noun of the META vocabulary.
COUNT = re.compile(r"\b(two|three|four|five|six|both|several|two|a few|the following)\s+"
                   r"(\w+\s+){0,2}(" + "|".join(sorted(w for w in META if w.endswith("s")))
                   + r")\b", re.I)

ANAPHORA = re.compile(r"^\s*(It|They|Them|This|That|These|Those|Both|The two|The first|"
                      r"The second|The third|The last|Each|Such)\b")

SKIP_ENV = ("theorem|lemma|definition|proposition|corollary|remark|proof|"
            "equation|align|gather|multline|displaymath|axiomlist|"
            "itemize|enumerate|description|figure|table|tabular|verbatim|lstlisting")
SKIP_CMD = (r"\section", r"\subsection", r"\subsubsection", r"\input", r"\include",
            r"\bibliography", r"\begin{document}", r"\end{document}", r"\maketitle")


def effective(text: str) -> int:
    """Source characters weighted to approximate typeset characters (as overhang.py)."""
    n = sum(len(m.group(0)) // 2 for m in MATH.finditer(text))
    t = MATH.sub("", text)
    n += 4 * len(CITE.findall(t)); t = CITE.sub("", t)
    n += 3 * len(REF.findall(t));  t = REF.sub("", t)
    t = CMD.sub("", t).replace("}", "").replace("~", " ").replace("---", "-")
    return n + len(re.sub(r"\s+", " ", t).strip())


def paragraphs(path: pathlib.Path, skip_env: re.Pattern):
    src = path.read_text(encoding="utf-8")
    lines = [l for l in src.splitlines() if not l.lstrip().startswith("%")]
    for i, block in enumerate("\n".join(lines).split("\n\n")):
        block = block.strip()
        if not block or skip_env.search(block):
            continue
        if any(block.startswith(c) for c in SKIP_CMD):
            continue
        yield i, block


def sentences(block: str):
    """Split a paragraph into sentences without splitting inside inline math."""
    masked = MATH.sub(lambda m: "\x00" * len(m.group(0)), block)
    out, start = [], 0
    for m in re.finditer(r"(?<![A-Z])(?<!\bcf)(?<!\be\.g)(?<!\bi\.e)\.\s+(?=[A-Z\\])",
                         masked):
        out.append(block[start:m.end()].strip()); start = m.end()
    tail = block[start:].strip()
    if tail:
        out.append(tail)
    return [s for s in out if s]


def classify(sent: str):
    """Return (is_candidate, reasons) for one sentence."""
    carries = []
    if MATH.search(sent):
        carries.append("math")
    if REF.search(sent):
        carries.append("ref")
    if CITE.search(sent):
        carries.append("cite")
    if ANCHOR.search(CITE.sub("", REF.sub("", sent))):
        carries.append("anchor")
    plain = CMD.sub(" ", MATH.sub(" ", CITE.sub(" ", REF.sub(" ", sent))))
    words = re.findall(r"[A-Za-z][a-z]+", plain)
    content = [w.lower() for w in words if len(w) > 3]
    meta = [w for w in content if w in META]
    ratio = len(meta) / len(content) if content else 0.0
    deixis = bool(DEIXIS.search(plain))
    count = bool(COUNT.search(plain))
    reasons = []
    if meta:
        reasons.append(f"meta {ratio:.0%} ({', '.join(sorted(set(meta))[:3])})")
    if deixis:
        reasons.append("deixis")
    if count:
        reasons.append("enumeration")
    # A candidate names part of the document (at least one META noun), points somewhere
    # else in it or counts what is coming, and carries no mathematics, reference, citation
    # or anchor of its own. The ratio floor is low on purpose: an announcement dilutes its
    # meta nouns with the subject's ("Locality has those two senses for a two-parameter
    # family, and the section takes them in turn" scores 0.22), so a high floor hides
    # exactly the sentences this is for. What does the discriminating work is the cue.
    is_cand = (not carries) and bool(meta) and ratio >= 0.12 and (deixis or count)
    return is_cand, reasons, carries


def scan(files, skip_env):
    rows = []
    for name in files:
        path = pathlib.Path(name)
        for i, block in paragraphs(path, skip_env):
            sents = sentences(block)
            cands = []
            for j, s in enumerate(sents):
                is_cand, reasons, carries = classify(s)
                if not is_cand:
                    continue
                nxt = sents[j + 1] if j + 1 < len(sents) else ""
                risk = bool(ANAPHORA.match(nxt))
                where = "lead" if j == 0 else ("trail" if j == len(sents) - 1 else "mid")
                cands.append({"text": re.sub(r"\s+", " ", s), "chars": effective(s),
                              "why": reasons, "where": where, "antecedent_risk": risk})
            if cands:
                rows.append({"file": name, "block": i, "sentences": len(sents),
                             "chars": effective(block),
                             "mass": sum(c["chars"] for c in cands),
                             "candidates": cands})
    rows.sort(key=lambda r: -r["mass"])
    return rows


def report(args):
    skip_env = re.compile(r"\\(begin|end)\{(" + args.skip_env + r")")
    rows = [r for r in scan(args.files, skip_env) if r["mass"] >= args.min_mass]
    if args.top:
        rows = rows[: args.top]
    if args.json:
        print(json.dumps(rows, indent=2)); return
    total = sum(r["mass"] for r in rows)
    print(f"{len(rows)} paragraphs with removable mass; {total} effective characters in "
          f"{sum(len(r['candidates']) for r in rows)} candidate sentences\n")
    for r in rows:
        print(f"  {r['mass']:>4}c  {pathlib.Path(r['file']).name}:{r['block']}  "
              f"({r['chars']}c, {r['sentences']} sentences)")
        for c in r["candidates"]:
            flag = " ANTECEDENT-RISK" if c["antecedent_risk"] else ""
            print(f"        [{c['where']}, {', '.join(c['why'])}]{flag}")
            print(f"        \"{c['text'][:150]}\"")
        print()
    print("Dispose of every candidate: delete it, or keep it with a reason in one word\n"
          "(hypothesis, pointer, term). A candidate is not a verdict -- a signpost is a\n"
          "defect when it is overused or carries nothing, not because of its shape.\n"
          "ANTECEDENT-RISK: the next sentence opens on a pronoun or a demonstrative, so\n"
          "deleting this one may strand it. Follow the pass with a correctness reading by\n"
          "someone who did not make the edits (see the skill's failure mode).")


def rates(args):
    """Candidate density per file and overall: the overuse signal."""
    skip_env = re.compile(r"\\(begin|end)\{(" + args.skip_env + r")")
    per = {}
    for name in args.files:
        path = pathlib.Path(name)
        chars = cands = mass = 0
        for i, block in paragraphs(path, skip_env):
            chars += effective(block)
            for s in sentences(block):
                is_cand, _, _ = classify(s)
                if is_cand:
                    cands += 1; mass += effective(s)
        per[name] = (chars, cands, mass)
    tc = sum(v[0] for v in per.values()) or 1
    print(f"  {'file':<28} {'prose c':>8} {'cands':>6} {'mass':>6} {'mass %':>7}")
    for name, (chars, cands, mass) in per.items():
        print(f"  {pathlib.Path(name).name:<28} {chars:>8} {cands:>6} {mass:>6} "
              f"{100 * mass / (chars or 1):>6.1f}%")
    print(f"  {'TOTAL':<28} {tc:>8} {sum(v[1] for v in per.values()):>6} "
          f"{sum(v[2] for v in per.values()):>6} "
          f"{100 * sum(v[2] for v in per.values()) / tc:>6.1f}%")
    print("\nThe share is the overuse signal: compare it across files and against the "
          "same\nmeasurement on an earlier revision, not against an absolute threshold.")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn, helptext in (("report", report, "rank paragraphs by removable mass"),
                               ("rates", rates, "candidate density per file")):
        s = sub.add_parser(name, help=helptext)
        s.add_argument("files", nargs="+")
        s.add_argument("--skip-env", default=SKIP_ENV)
        if name == "report":
            s.add_argument("--min-mass", type=int, default=40,
                           help="ignore paragraphs below this removable mass (default 40)")
            s.add_argument("--top", type=int, default=0)
            s.add_argument("--json", action="store_true")
        s.set_defaults(func=fn)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    main()
