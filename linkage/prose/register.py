r"""Restraint-budget counts by zone: `linkage prose register`.

For each paper source file, count em-dashes (`---`), semicolons and "ask" used for a requirement,
and find runs of three or more consecutive long sentences, separately in three zones:

  prose      paper-side connective text, remarks and captions -- the text the register pass edits
  statement  the blocks under a `% shared with blueprint` marker (byte-shared, never edited here)
  proof      `\begin{proof} ... \end{proof}` blocks (the proofs of record; edited at the blueprint)

Comments, math displays and inline math are stripped before counting, so that a semicolon in a
formula or in a `\cite` key list does not count. Sentences are split on `.` `!` `?` followed by a
space; a "long" sentence has more than `--long-at` words.

The `ask` column counts `ask(s|ed)` where an axiom system or a definition *requires* something
("Burt and Adelson ask it to be separable", "(A8) asked at one dilation", "asks more than a pyramid
needs"): `WRITING.md` § 3 says "require". The question sense ("this section asks which stencils")
is not counted: a question word, `about`, `by` or "question" after the verb rules a match out, as
does a person as its object ("ask all observers to report", "ask themselves whether"), and `ask(ed)
to` counts only before `be` or a determiner ("asked to point out" is a request to a person).
Tuned against the `prose-baseline.json` sources (2026-11-20): the author's four papers have no
`ask(s|ed)?`; the genre's nine have fifteen, and the four counted are requirements ("ask that the
analysis commutes", "ask for a reverse heat equation", "asks for", "the properties asked to the
scale-space"). The tests carry each of the fifteen.

Ported from `spatial-hemigroup-scale-space`'s `scripts/count-register.py` (ADR-0001 step 5): the
paper directory it hard-coded is now the module's, read from `linkage.toml`.

Why this lives beside `linkage prose stats` rather than inside it: `stats` measures the article
against the author and genre baselines and says *which patterns* to fix; this counts two marks
and one shape per zone, which is what the writing standard's restraint budget is stated in, and
its zones are the linkage ones (a shared statement is not the paper's text to edit).
"""
from __future__ import annotations

import re
from pathlib import Path

DEFAULT_LONG = 30

_DET = r"(?:the|a|an|every|each|all|its|their|this|these|those|one|two|no)"
_QUESTION = r"(?:which|what|whether|if|how|why|when|where|who|whom|whose|about|by)"
_PERSON = (r"(?:(?:all|the|a|every|each)\s+)?(?:observers?|readers?|persons?|people|authors?|"
           r"subjects?|oneself|ourselves|themselves|himself|herself|us|you|me)")
ASK_REQUIREMENT = re.compile(
    r"\bask(?:s|ed)?\b"
    rf"(?!\s+{_QUESTION}\b)"                            # the question sense
    r"(?!\s+(?:[A-Za-z]+\s+){0,2}(?:questions?|problems?)\b)"
    rf"(?!\s+{_PERSON}\b)"                              # a request to a person
    rf"(?!\s+to\s+(?!be\b|{_DET}\b))"                   # "asked to point out"
    r"(?=\s+(?:"
    rf"to\s+(?:be|{_DET})\b"                            # "asked to be", "asked to the"
    r"|(?:for|more|less|only|much|little|nothing|that|too|at|of|on|along|between|throughout)\b"
    r"|X\b"                                             # inline maths: "asks $u(0) \le f(0)$"
    r"|\([A-Z]+\d*\)"                                   # an axiom label: "asks (I4) at one"
    rf"|(?:it|them|{_DET})\b"                           # an object: "asks it to", "asks every"
    r"|[A-Za-z]+(?:\s+[A-Za-z]+)?\s+to\s"               # "asks the kernel to", "asks X to"
    r"))",
    re.I)

_COUNT = r"(?:two|three|four|five|six|seven|eight|nine|ten|[2-9])"
# "It asks two questions." / "Two questions remain:", then the items as bare questions.
COUNT_OF_QUESTIONS = re.compile(
    rf"\b{_COUNT}\s+(?:[A-Za-z-]+\s+)?(?:questions?|points?|issues?|problems?)\b", re.I)
# "Four results carry it.": a sentence that is only a count and a verb of carrying.
COUNT_CARRIES = re.compile(
    rf"^(?:there\s+are\s+|we\s+have\s+)?{_COUNT}\s+(?:[A-Za-z-]+\s+)?"
    r"(?:results?|facts?|points?|ideas?|ingredients?|steps?|observations?|consequences?|"
    r"statements?|theorems?|lemmas?|propositions?|things?|properties|claims?|parts?)"
    r"(?:\s+(?:carry|drive|underlie|support|organi[sz]e|structure|follow|matter|stand\s+out)"
    r"(?:\s+(?:it|this|them|the\s+[A-Za-z-]+))?)?\s*[.:]$",
    re.I)

ENV_END = re.compile(r"\\end\{(definition|proposition|lemma|theorem|corollary|remark)\}")
ZONES = ("prose", "proof", "statement")


def zones(lines):
    """Yield (zone, lineno, text) for each line, zone in prose/statement/proof."""
    zone = "prose"
    pending_statement = False
    for i, raw in enumerate(lines, 1):
        line = raw.split("%")[0] if not raw.lstrip().startswith("%") else ""
        stripped = raw.strip()
        if stripped.startswith("% shared with blueprint"):
            pending_statement = True
            continue
        if pending_statement and stripped.startswith("\\begin{"):
            zone = "statement"
            pending_statement = False
        if zone == "prose" and stripped.startswith("\\begin{proof}"):
            zone = "proof"
        yield zone, i, line
        if zone == "statement" and ENV_END.search(stripped):
            zone = "prose"
        if zone == "proof" and stripped.startswith("\\end{proof}"):
            zone = "prose"


def strip_math(text: str) -> str:
    text = re.sub(r"\\\[.*?\\\]", " ", text, flags=re.S)
    text = re.sub(r"\\begin\{(equation|align|gather)\*?\}.*?\\end\{\1\*?\}", " ", text, flags=re.S)
    text = re.sub(r"\$[^$]*\$", " X ", text)
    text = re.sub(r"\\(sscite|cite|ref|label|eqref)\{[^}]*\}", " ", text)
    return text


def asks(lines) -> list[tuple[str, int, str]]:
    """(zone, line, matched text) for each "ask" of a requirement. The next line is read as
    lookahead, so a verb at the end of a line still sees its object."""
    zoned = [(zone, i, strip_math(line)) for zone, i, line in zones(lines)]
    hits = []
    for k, (zone, i, line) in enumerate(zoned):
        text = line + " " + (zoned[k + 1][2] if k + 1 < len(zoned) else "")
        for m in ASK_REQUIREMENT.finditer(text):
            if m.start() < len(line):
                hits.append((zone, i, " ".join(text[m.start():].split()[:5])))
    return hits


_BREAK = re.compile(r"\\(?:(?:sub)*section|paragraph|begin|end|item)\b")
_SENTENCE = re.compile(r"\S.*?(?:[.!?](?=\s|$)|\Z)", re.S)


def _plain(text: str) -> str:
    """Prose without its markup: an `\\emph{...}` keeps its words, a heading and an environment's
    name and title go, and so do other commands."""
    text = strip_math(text).replace("~", " ")
    text = re.sub(r"\\(?:begin|end|(?:sub)*section|paragraph)\*?\{[^}]*\}(?:\[[^]]*\])?", " ",
                  text)
    text = re.sub(r"\\(?:emph|textit|textbf|prog)\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\[A-Za-z]+\*?", " ", text)
    return re.sub(r"[{}]", "", text)


def paragraphs(lines):
    """Yield (zone, [(line, sentence), ...]) for each paragraph: a blank line, a change of zone,
    a sectioning command, `\\begin`, `\\end` or `\\item` ends one."""
    para: list[tuple[str, int, str]] = []

    def flush():
        if not para:
            return
        text, starts = "", []
        for _, i, t in para:
            starts.append((len(text), i))
            text += t + " "
        yield para[0][0], [(max(i for off, i in starts if off <= m.start()),
                            " ".join(m.group().split())) for m in _SENTENCE.finditer(text)]
        para.clear()

    for zone, i, line in zones(lines):
        if not line.strip() or (para and para[-1][0] != zone) or _BREAK.match(line.strip()):
            yield from flush()
        if line.strip():
            para.append((zone, i, _plain(line)))
    yield from flush()


_LIST = re.compile(r"\\begin\{(?:enumerate|itemize|description)\}")


def _opens_list(lines, i: int) -> bool:
    """Whether the paragraph holding line `i` (1-based) is followed by a list environment."""
    j = i
    while j < len(lines) and lines[j].strip() and not _BREAK.match(lines[j].strip()):
        j += 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    return j < len(lines) and bool(_LIST.match(lines[j].strip()))


def enumerations(lines) -> list[tuple[str, int, str, str]]:
    """(zone, line, sentence, form) for each announced count (`WRITING.md` § 5,
    `REVIEWER-CONTRACT.md` `TALLY`). `form` is "questions" for a count of questions or points
    followed by the items as bare questions ("It asks two questions. What …?"), looked for in the
    same paragraph, and "count" for a sentence that is only a count of results and a verb of
    carrying them ("Four results carry it."). A count is not wrong in itself: the question form
    is the costly one, and a bare count matters where it recurs (`recurring`). A count that ends
    its paragraph with a colon and opens a list ("Three steps follow:", then
    `\\begin{enumerate}`) gives its items at once and is not located."""
    lines = list(lines)
    hits = []
    for zone, sents in paragraphs(lines):
        for k, (i, s) in enumerate(sents):
            nxt = sents[k + 1][1] if k + 1 < len(sents) else ""
            m = COUNT_OF_QUESTIONS.search(s)
            questions = m and ((s.endswith((".", ":")) and nxt.endswith("?"))
                               or (":" in s[m.end():] and s.endswith("?")))
            listed = s.endswith(":") and k == len(sents) - 1 and _opens_list(lines, i)
            if questions:
                hits.append((zone, i, s, "questions"))
            elif COUNT_CARRIES.match(s) and not listed:
                hits.append((zone, i, s, "count"))
    return hits


RECURRING_AT = 2   # bare counts in one file (a section) before they are a pattern, not a sentence


def recurring(hits) -> bool:
    """Whether the bare counts among one file's `enumerations` hits recur (`TALLY`: density)."""
    return sum(1 for h in hits if h[3] == "count") >= RECURRING_AT


STATEMENT_ENV = re.compile(r"\\begin\{(theorem|proposition|lemma|corollary|definition)\}")
_NOT_TERMS = {"not", "only", "every", "all", "any", "each", "one", "some", "no", "none",
              "exactly", "strictly", "both", "either", "neither", "same", "must", "may", "can",
              "never", "always", "is", "are", "and", "or", "but", "at", "in", "on", "of", "for"}
DEFINED_IN_PROSE_AT = 3


def _term(raw: str) -> str | None:
    """The `\\emph{...}` text as a term: `~` and maths read as spaces, a leading article and a
    trailing index ("stratum~3", "stratum $k$") dropped. None for emphasis that is not a term."""
    words = _plain(raw).lower().split()
    if words and words[0] in ("the", "a", "an"):
        words = words[1:]
    while words and re.fullmatch(r"\d+|[a-z]|x", words[-1]):
        words = words[:-1]
    if not words or len(words) > 4 or (len(words) == 1 and (words[0] in _NOT_TERMS
                                                           or len(words[0]) < 3)):
        return None
    return " ".join(words)


def _forms(word: str) -> set[str]:
    """A word's singular and plural, English and Latin ("stratum", "strata")."""
    forms = {word, word + "s", word + "es"}
    for end, other in (("ies", "y"), ("es", ""), ("s", ""), ("y", "ies"), ("um", "a"),
                       ("a", "um"), ("on", "a")):
        if word.endswith(end):
            forms.add(word[: len(word) - len(end)] + other)
    return forms


def _term_pattern(term: str) -> re.Pattern:
    *head, last = term.split()
    alts = "|".join(sorted(map(re.escape, _forms(last)), key=len, reverse=True))
    return re.compile(r"\b" + "".join(re.escape(w) + r"\s+" for w in head) + rf"(?:{alts})\b")


def prose_terms(files: list[Path], at: int = DEFINED_IN_PROSE_AT):
    """(file, line, term, [labels]) for each term emphasised in the prose zone, outside any
    numbered environment, that at least `at` later statements (theorem, proposition, lemma,
    corollary, definition, in any zone and any later file) use, and that no definition environment
    emphasises: a class the paper names and uses throughout is a numbered definition (`WRITING.md`
    § 3). `files` are read in order; an `\\emph` that heads an `\\item` is a list heading."""
    defined, terms, statements = set(), [], []
    for n, f in enumerate(files):
        lines = Path(f).read_text(encoding="utf-8").splitlines()
        env = None
        for zone, i, line in zones(lines):
            m = STATEMENT_ENV.search(line)
            if m and env is None:
                env = [m.group(1), (n, i), ""]
            if env is not None:
                env[2] += line + " "
            for e in re.finditer(r"\\emph\{((?:[^{}]|\{[^{}]*\})*)\}", line):
                t = _term(e.group(1))
                if t is None:
                    continue
                if env is not None and env[0] == "definition":
                    defined.add(t)
                elif env is None and zone == "prose" and not re.search(
                        r"\\item(?:\[[^]]*\])?\s*$", line[: e.start()]):
                    terms.append((n, i, f, t))
            if env is not None and re.search(rf"\\end\{{{env[0]}\}}", line):
                label = re.search(r"\\label\{([^}]*)\}", env[2])
                statements.append((env[1], label.group(1) if label else f"{f.name}:{env[1][1]}",
                                   _plain(re.sub(r"\\begin\{\w+\}\[([^]]*)\]", r" \1 ",
                                                 env[2])).lower()))
                env = None
    hits, seen = [], []
    for n, i, f, t in terms:
        pat = _term_pattern(t)
        if any(pat.search(d) for d in defined) or any(pat.search(s) for s in seen):
            continue
        seen.append(t)
        uses = [label for pos, label, text in statements if pos > (n, i) and pat.search(text)]
        if len(uses) >= at:
            hits.append((f, i, t, uses))
    return hits


def analyse(path: Path, show_runs: bool = False, long_at: int = DEFAULT_LONG):
    """({zone: (em-dashes, semicolons, words, asks, enumerations)},
    [(first line, sentence lengths)])."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    buf: dict[str, list[tuple[int, str]]] = {z: [] for z in ZONES}
    for zone, i, line in zones(lines):
        buf[zone].append((i, line))
    ask_zones = [zone for zone, _, _ in asks(lines)]
    enum_zones = [h[0] for h in enumerations(lines)]
    out = {}
    for zone, items in buf.items():
        text = strip_math("\n".join(ln for _, ln in items))
        out[zone] = (text.count("---"), text.count(";"),
                     len(re.findall(r"[A-Za-z][A-Za-z'\-]*", text)), ask_zones.count(zone),
                     enum_zones.count(zone))
    # long-sentence runs, prose zone only, paragraph by paragraph
    runs: list[tuple[int | None, list[int]]] = []
    if show_runs:
        para: list[str] = []
        start: int | None = None
        for i, line in [*buf["prose"], (None, "")]:
            if line.strip() == "" or i is None:
                if para:
                    text = strip_math(" ".join(para))
                    sents = [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
                    lens = [len(re.findall(r"[A-Za-z][A-Za-z'\-]*", s)) for s in sents]
                    run = 0
                    for n in lens:
                        run = run + 1 if n > long_at else 0
                        if run == 3:
                            runs.append((start, lens))
                            break
                para, start = [], None
            else:
                if start is None:
                    start = i
                para.append(line)
    return out, runs


def report(files: list[Path], show_runs: bool = False, long_at: int = DEFAULT_LONG,
           show_asks: bool = False, show_enumerations: bool = False,
           show_terms: bool = False) -> list[str]:
    out = [f"{'file':24s} {'zone':10s} {'---':>5s} {'semi':>5s} {'words':>7s} {'ask':>5s} "
           f"{'enum':>5s}"]
    tot = {z: [0, 0, 0, 0, 0] for z in ZONES}
    for f in files:
        counts, runs = analyse(f, show_runs, long_at)
        for zone in ZONES:
            d, s, w, a, e = counts[zone]
            out.append(f"{f.name:24s} {zone:10s} {d:5d} {s:5d} {w:7d} {a:5d} {e:5d}")
            for k, v in enumerate((d, s, w, a, e)):
                tot[zone][k] += v
        for start, lens in runs:
            out.append(f"    long-run at {f.name}:{start}  sentence lengths {lens}")
        lines = Path(f).read_text(encoding="utf-8").splitlines()
        if show_asks:
            for zone, i, text in asks(lines):
                out.append(f"    ask at {f.name}:{i} ({zone})  {text}")
        if show_enumerations:
            hits = enumerations(lines)
            for zone, i, text, form in hits:
                out.append(f"    enumeration at {f.name}:{i} ({zone}, {form})  {text}")
            if recurring(hits):
                n = sum(1 for h in hits if h[3] == "count")
                out.append(f"    recurring counts in {f.name}: {n} (TALLY: density)")
    for zone in ZONES:
        d, s, w, a, e = tot[zone]
        out.append(f"{'TOTAL':24s} {zone:10s} {d:5d} {s:5d} {w:7d} {a:5d} {e:5d}")
    if show_terms:
        for f, i, term, uses in prose_terms(files):
            shown = ", ".join(uses[:3]) + (", …" if len(uses) > 3 else "")
            out.append(f"    term in prose at {Path(f).name}:{i}  '{term}', used in {len(uses)} "
                       f"later statements ({shown})")
    return out


def sources(paper: Path) -> list[Path]:
    """The paper's own section sources: every `.tex` of the directory except `main.tex`, which
    is the preamble and the `\\input` list, not prose."""
    return [f for f in sorted(paper.glob("*.tex")) if f.name != "main.tex"]
