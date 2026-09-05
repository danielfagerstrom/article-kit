#!/usr/bin/env python3
"""Rank LaTeX paragraphs by how cheap they are to shorten by one typeset line.

Prose sets in whole lines, so shortening a paragraph pays nothing until its character
count crosses a multiple of the line width. What matters is therefore not how long a
paragraph is but how far past the last boundary it sits. A paragraph 7 characters past a
boundary loses a whole typeset line for 7 characters of editing; one 70 past needs 70.
Sorting by that number is what makes a wording pass pay in pages instead of only in taste.

`report` prints two numbers per paragraph, which always sum to the width:

    cut    characters to remove to drop one typeset line
    room   characters that can be added before one is gained

A length that is an exact multiple of the width is the worst case in both directions, not
the best: it fills its last line exactly, so cut = width and room = 0. A naive
`chars mod width` reports 0 there and sorts those paragraphs to the top of the list.

    overhang.py report  FILE...  [--width N] [--min N] [--top N] [--json]
    overhang.py calibrate PDF    [--first N] [--last N]

`calibrate` measures the width from a built PDF and needs pdftotext (poppler-utils).
"""
import argparse, json, math, re, signal, subprocess, sys, pathlib
from collections import Counter

MATH = re.compile(r"\$[^$]*\$")
CITE = re.compile(r"\\cite[a-zA-Z]*(\[[^\]]*\])?\{[^}]*\}")
REF = re.compile(r"\\(eq)?ref\{[^}]*\}")
CMD = re.compile(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{)?")

# Environments whose contents are not ordinary prose. Theorem-like environments are here
# for a second reason: in a repository with a statement ledger they must not be edited by
# a wording pass at all, and a tool that never lists them cannot tempt an editor.
SKIP_ENV = ("theorem|lemma|definition|proposition|corollary|remark|proof|"
            "equation|align|gather|multline|displaymath|axiomlist|"
            "itemize|enumerate|description|figure|table|tabular|verbatim|lstlisting")
SKIP_CMD = (r"\section", r"\subsection", r"\subsubsection", r"\input", r"\include",
            r"\bibliography", r"\begin{document}", r"\end{document}", r"\maketitle")


def effective(text: str) -> int:
    """Source characters weighted to approximate typeset characters.

    Inline math counts half (`$\\Phi_{x,y}$` is 12 source characters, about 4 typeset),
    a citation 4 (`[7]`), a cross-reference 3, and other markup nothing.
    """
    n = sum(len(m.group(0)) // 2 for m in MATH.finditer(text))
    t = MATH.sub("", text)
    n += 4 * len(CITE.findall(t)); t = CITE.sub("", t)
    n += 3 * len(REF.findall(t));  t = REF.sub("", t)
    t = CMD.sub("", t).replace("}", "").replace("~", " ").replace("---", "-")
    return n + len(re.sub(r"\s+", " ", t).strip())


def paragraphs(path: pathlib.Path, skip_env: re.Pattern):
    """Yield (index, text) for each block that is ordinary prose."""
    src = path.read_text(encoding="utf-8")
    body = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("%"))
    for i, block in enumerate(body.split("\n\n")):
        block = block.strip()
        if not block or skip_env.search(block):
            continue
        if any(block.startswith(c) for c in SKIP_CMD):
            continue
        yield i, block


def report(args):
    skip_env = re.compile(r"\\(begin|end)\{(" + args.skip_env + r")")
    rows = []
    for name in args.files:
        path = pathlib.Path(name)
        for i, block in paragraphs(path, skip_env):
            ec = effective(block)
            if ec < args.min:
                continue
            w = args.width
            occupied = math.ceil(ec / w)
            # Characters to remove to drop one typeset line, and characters that can be
            # added before one is gained. A length that is an exact multiple of the width
            # is the WORST case in both directions, not the best: it fills its last line
            # exactly, so shortening costs a full line and one added character gains one.
            cut = ec - w * (occupied - 1)
            rows.append({
                "file": name, "block": i, "chars": ec, "lines": occupied,
                "cut": cut, "room": w - cut,
                "opening": re.sub(r"\s+", " ", block)[:58],
            })
    rows.sort(key=lambda r: r["cut"])
    if args.top:
        rows = rows[: args.top]
    if args.json:
        print(json.dumps(rows, indent=2))
        return
    total = sum(r["lines"] for r in rows)
    print(f"width = {args.width} effective chars; {len(rows)} prose paragraphs; "
          f"{total} typeset lines\n")
    print(f"  {'cut':>4} {'room':>4} {'chars':>6} {'lines':>5}  where / opening")
    for r in rows:
        print(f"  {r['cut']:>4} {r['room']:>4} {r['chars']:>6} {r['lines']:>5}  "
              f"{pathlib.Path(r['file']).name}:{r['block']}  {r['opening']}")
    print("\nWork top-down. 'cut' is how many characters to remove to drop a typeset "
          "line;\n'room' how many can be added before one is gained. They sum to the "
          "width.")


def calibrate(args):
    """Estimate the line width in characters from a built PDF.

    In a justified column every full line has the same width in points but a different
    number of characters, so the counts spread into a hump. Short lines -- paragraph
    ends, headings, display math -- form a long left tail. The MODE of the distribution
    is therefore the measure, and it is far more robust than the maximum (which catches
    a stray wide line) or the mean (which the tail drags down).
    """
    cmd = ["pdftotext", "-layout"]
    if args.first:
        cmd += ["-f", str(args.first)]
    if args.last:
        cmd += ["-l", str(args.last)]
    cmd += [args.pdf, "-"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    except FileNotFoundError:
        sys.exit("pdftotext not found - install poppler-utils, or fit the width by hand "
                 "(see the skill's 'Calibrating the width' section).")
    except subprocess.CalledProcessError as e:
        sys.exit(f"pdftotext failed: {e.stderr.strip() or e}")
    lengths = [len(l.strip()) for l in out.splitlines() if l.strip()]
    if len(lengths) < 50:
        sys.exit(f"only {len(lengths)} text lines extracted - is this a scanned or "
                 "image-only PDF, or too small a page range?")
    floor = max(lengths) / 2
    body = sorted(n for n in lengths if n >= floor)
    counts = Counter(body)
    width, hits = counts.most_common(1)[0]
    p75 = body[int(0.75 * (len(body) - 1))]
    print(f"text lines          {len(lengths)}")
    print(f"body lines (>= {floor:.0f})  {len(body)}")
    print(f"longest line        {max(lengths)}")
    print(f"mode                {width}  ({hits} lines)")
    print(f"75th percentile     {p75}")
    print(f"\nwidth = {width}   ->   --width {width}")
    if abs(p75 - width) > 3:
        print("\nWARNING: mode and 75th percentile disagree by more than 3. The sample "
              "may be\ntoo small or too heavily interrupted by displays; try a wider "
              "--first/--last range.")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("report", help="rank prose paragraphs by overhang")
    r.add_argument("files", nargs="+")
    r.add_argument("--width", type=int, default=79,
                   help="effective characters per typeset line (default 79, LNCS)")
    r.add_argument("--min", type=int, default=60,
                   help="ignore paragraphs shorter than this (default 60)")
    r.add_argument("--top", type=int, default=0, help="show only the N cheapest")
    r.add_argument("--skip-env", default=SKIP_ENV,
                   help="regex alternation of environments to skip")
    r.add_argument("--json", action="store_true")
    r.set_defaults(func=report)

    c = sub.add_parser("calibrate", help="measure the line width from a built PDF")
    c.add_argument("pdf")
    c.add_argument("--first", type=int, help="first page to sample")
    c.add_argument("--last", type=int, help="last page to sample")
    c.set_defaults(func=calibrate)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    # Let `| head` close the pipe quietly. SIGPIPE does not exist on Windows.
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    main()
