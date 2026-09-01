"""LaTeX prose -> classified blocks of normalized sentences.

The one format-aware module of the prose pass. Everything downstream (counters,
baselines, the report) works on `Block`/`Sentence` alone, so a second input dialect
is a second extractor rather than a rewrite.

Three things it must get right, because every length statistic downstream inherits
them:

1. **Display math does not end a sentence.** In mathematical prose a display sits
   *inside* a sentence far more often than after one. Both display and inline math
   become placeholder tokens and the sentence runs through them.
2. **`.` is usually not a full stop.** `Thm.~5.2`, `p.~49`, `\\S`, `e.g.` — LaTeX
   gives one signal a plain-text splitter lacks: a period followed by `~` is an
   abbreviation, always.
3. **Nothing is dropped silently.** A command this module does not know is recorded
   and reported, never quietly stripped. (The blueprint render gate learned this the
   expensive way: pandoc drops unknown commands *with their arguments*, so checking
   the output for residue cannot detect the loss -- see ROADMAP T2.)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# --- placeholders -------------------------------------------------------------
# Chosen to be visible in a dump and to contain no ASCII letters, so word counting
# can never mistake one for prose.
EQ = "\u27e8EQ\u27e9"        # display math
MATH = "\u27e8M\u27e9"       # inline math
CITE = "\u27e8CITE\u27e9"    # \cite / \sscite
REF = "\u27e8REF\u27e9"      # \ref / \eqref / \pageref
PLACEHOLDERS = (EQ, MATH, CITE, REF)

# --- environment classification -----------------------------------------------
STATEMENT_ENVS = {"theorem", "proposition", "lemma", "corollary", "definition",
                  "example", "conjecture", "claim", "fact", "axiom"}
PROOF_ENVS = {"proof", "proofsketch"}
REMARK_ENVS = {"remark", "note", "observation"}
LIST_ENVS = {"itemize", "enumerate", "description"}
MATH_ENVS = {"equation", "align", "gather", "multline", "displaymath", "eqnarray",
             "split", "aligned", "cases", "array", "alignat", "flalign"}
FLOAT_ENVS = {"figure", "table", "tabular", "tikzpicture", "center", "wrapfigure"}
ABSTRACT_ENVS = {"abstract"}

KIND_OF_ENV = (
    [(e, "statement") for e in STATEMENT_ENVS]
    + [(e, "proof") for e in PROOF_ENVS]
    + [(e, "remark") for e in REMARK_ENVS]
    + [(e, "abstract") for e in ABSTRACT_ENVS]
)
ENV_KIND = dict(KIND_OF_ENV)

# --- commands we understand ---------------------------------------------------
# Content-bearing: the braces' contents are prose and stay.
KEEP_ARG = {"emph", "textit", "textbf", "texttt", "textsc", "underline", "text",
            "mbox", "textrm", "textnormal", "footnote", "caption"}
# Structural: the command and its argument are not prose.
DROP_ARG = {"label", "index", "vspace", "hspace", "graphicspath", "includegraphics",
            "bibliographystyle", "bibliography", "input", "usepackage",
            "documentclass", "newcommand", "renewcommand", "newtheorem",
            "theoremstyle", "setlength", "title", "date", "author"}
# Bare tokens with no argument that carry no prose.
DROP_BARE = {"maketitle", "appendix", "noindent", "centering", "par", "bigskip",
             "medskip", "smallskip", "hfill", "clearpage", "newpage", "item",
             "toprule", "midrule", "bottomrule", "quad", "qquad", "leavevmode"}
# Bare tokens that render as a character.
LITERAL = {"S": "\u00a7", "P": "\u00b6", "ldots": "...", "dots": "...",
           "textemdash": "\u2014", "textendash": "\u2013", "&": "&", "%": "%",
           "_": "_", "#": "#", "$": "$", "{": "{", "}": "}",
           "TeX": "TeX", "LaTeX": "LaTeX", "ie": "i.e.", "eg": "e.g."}
ACCENTS = {'\\"o': "\u00f6", '\\"a': "\u00e4", '\\"u': "\u00fc", "\\'e": "\u00e9",
           "\\'a": "\u00e1", "\\`e": "\u00e8", "\\^o": "\u00f4", "\\~n": "\u00f1",
           '\\"O': "\u00d6", '\\"A': "\u00c4", "\\o": "\u00f8", "\\aa": "\u00e5"}

# --- sentence splitting -------------------------------------------------------
# A period ending one of these is an abbreviation, not a full stop. Kept short and
# specific: over-listing costs missed sentence ends, which inflates length stats.
ABBREV = {"thm", "thms", "prop", "props", "lem", "lems", "cor", "cors", "def",
          "defs", "eq", "eqs", "fig", "figs", "tab", "sec", "secs", "ch", "app",
          "p", "pp", "vol", "no", "nos", "cf", "resp", "approx", "est", "ca",
          "etc", "viz", "al", "et", "dr", "prof", "st", "mr", "ms", "ex",
          "i.e", "e.g", "vs", "min", "max", "inf", "sup"}


@dataclass
class Sentence:
    text: str
    words: int          # alphabetic prose tokens only
    math: int           # placeholder count: inline + display
    cites: int
    refs: int


@dataclass
class Block:
    """A paragraph of one kind, inside one section, with its sentences."""
    kind: str           # prose | statement | proof | remark | abstract | list | heading
    env: str | None     # the LaTeX environment name, when there was one
    section: str        # nearest enclosing \section title
    subsection: str | None
    source: str         # file the block came from
    line: int           # 1-indexed line of the block's first character
    text: str
    title: str | None = None    # \begin{theorem}[the optional title]
    sentences: list[Sentence] = field(default_factory=list)
    emphases: list[str] = field(default_factory=list)
    emdashes: int = 0

    @property
    def words(self) -> int:
        return sum(s.words for s in self.sentences)


@dataclass
class Extraction:
    blocks: list[Block]
    unknown: dict[str, int]        # command -> occurrences, for the audit
    dropped_envs: dict[str, int]   # environment -> occurrences skipped wholesale
    # One sample of surrounding source per unrecognised command. A bare count says
    # something escaped; only the context says whether it was math that should have
    # been masked or a wrapper whose prose was rightly kept.
    unknown_ctx: dict[str, str] = field(default_factory=dict)

    @property
    def words(self) -> int:
        return sum(b.words for b in self.blocks)


# --- comment stripping --------------------------------------------------------

def strip_comments(src: str) -> str:
    """Remove `%` comments, keeping line numbering intact.

    Line count must survive: block line numbers are how a finding is located, and
    a paper's `.tex` opens with a dozen lines of editorial commentary that would
    otherwise shift every number after it.
    """
    out = []
    for line in src.split("\n"):
        i, n = 0, len(line)
        while i < n:
            if line[i] == "\\":
                i += 2
                continue
            if line[i] == "%":
                line = line[:i]
                break
            i += 1
        out.append(line)
    return "\n".join(out)


# --- math and verbatim removal ------------------------------------------------

_MATH_PATTERNS = [
    (re.compile(r"\\\[.*?\\\]", re.S), EQ),
    (re.compile(r"\$\$.*?\$\$", re.S), EQ),
    (re.compile(r"\\begin\{(" + "|".join(sorted(MATH_ENVS)) + r")\*?\}.*?\\end\{\1\*?\}",
                re.S), EQ),
    # Inline math may span a wrapped line but never a blank line, so an unpaired `$`
    # cannot swallow the prose up to the next formula. `\\[\s\S]` rather than `\\.`
    # because a control space at end of line (`…,\` + newline) is ordinary LaTeX and
    # `.` would not cross it — that single case shifts every later `$` pairing by one.
    (re.compile(r"(?<!\\)\$(?:\\[\s\S]|[^$\\\n]|\n(?!\s*\n))*\$"), MATH),
]


# The closing delimiter of a display, whichever dialect wrote it.
_DISPLAY_CLOSE = re.compile(r"(?:\\\]|\$\$|\\end\{[A-Za-z]+\*?\})\s*$")


def display_ends_sentence(display: str) -> bool:
    """Does this display carry the sentence's terminating punctuation?

    A display usually sits *inside* a sentence, which is why the placeholder does not
    break one. But when a sentence ends at a display the author punctuates the display
    itself --- `\\text{for every } c \\in (0,1).` --- and treating that as a continuation
    silently welds the next sentence onto this one. The trailing mark is the signal, and
    it is the only reliable one: the following word being capitalised is not, since a
    sentence may legitimately resume with a proper noun or a symbol.
    """
    return _DISPLAY_CLOSE.sub("", display).rstrip().endswith((".", "!", "?"))


def mask_math(src: str, patterns=_MATH_PATTERNS) -> tuple[str, list[int]]:
    """Replace math with placeholders, returning the text and a per-character map
    back to the *source* line number.

    Masking must happen before anything splits the text, because a display block
    routinely contains blank lines and paragraph splitting would cut it in half,
    orphaning its delimiters and spilling `\\frac`, `\\alpha` … into the prose. But
    collapsing many lines into one token also destroys line numbering, and a line
    number is how a finding is located later. So the map is carried rather than
    recomputed.

    A display that ends its sentence keeps the terminating mark, so the splitter can
    see it; the splitter's own lowercase-continuation rule then still declines to
    break if the next word says otherwise.
    """
    out: list[str] = []
    lines: list[int] = []
    i, ln, n = 0, 1, len(src)
    while i < n:
        for pat, tok in patterns:
            m = pat.match(src, i)
            if m:
                if tok == EQ and display_ends_sentence(m.group(0)):
                    tok = EQ + "."
                out.append(tok)
                lines.extend([ln] * len(tok))
                ln += m.group(0).count("\n")
                i = m.end()
                break
        else:
            out.append(src[i])
            lines.append(ln)
            if src[i] == "\n":
                ln += 1
            i += 1
    lines.append(ln)
    return "".join(out), lines


# --- argument-aware command handling ------------------------------------------

def _match_brace(s: str, i: int) -> int:
    """Index just past the `{...}` group starting at `s[i] == '{'`; -1 if unbalanced."""
    depth = 0
    while i < len(s):
        if s[i] == "\\":
            i += 2
            continue
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


_CMD = re.compile(r"\\([A-Za-z]+)\*?")


def normalize(src: str, unknown: dict[str, int], emphases: list[str],
              contexts: dict[str, str] | None = None) -> tuple[str, int]:
    """LaTeX prose -> plain text. Returns (text, em-dash count).

    Math is already masked. Anything not recognised is counted in `unknown` and its
    argument is *kept* -- an unknown command is far more likely to be a wrapper
    around prose than a replacement for it, and keeping the text errs toward
    over-counting rather than silent loss.
    """
    for tex, ch in ACCENTS.items():
        src = src.replace(tex, ch)

    out = []
    i, n = 0, len(src)
    while i < n:
        # Non-letter control sequences: the spacing commands are the ones that turn up
        # in prose (`i.e.\ dilating`), and left alone they leave a stray backslash
        # inside a word. Escaped literals (\% \& \_ …) fall through to the literal
        # substitution below.
        if src[i] == "\\" and i + 1 < n and src[i + 1] in " ,;:!":
            out.append(" " if src[i + 1] == " " else "")
            i += 2
            continue
        m = _CMD.match(src, i)
        if not m:
            out.append(src[i])
            i += 1
            continue
        name = m.group(1)
        j = m.end()
        # skip optional [..] argument
        if j < n and src[j] == "[":
            k = src.find("]", j)
            if k != -1:
                j = k + 1
        has_arg = j < n and src[j] == "{"
        end = _match_brace(src, j) if has_arg else -1

        if name in KEEP_ARG and end != -1:
            inner = src[j + 1:end - 1]
            if name in ("emph", "textit"):
                emphases.append(re.sub(r"\s+", " ", inner).strip())
            out.append(inner)
            i = end
        elif name in DROP_ARG:
            i = end if end != -1 else j
        elif name in DROP_BARE:
            out.append(" ")
            i = j
        elif name in LITERAL:
            out.append(LITERAL[name])
            i = j
        else:
            unknown[name] = unknown.get(name, 0) + 1
            if contexts is not None and name not in contexts:
                contexts[name] = re.sub(
                    r"\s+", " ", src[max(0, i - 90):i + 50]).strip()
            if end != -1:
                out.append(src[j + 1:end - 1])   # keep the argument's prose
                i = end
            else:
                i = j

    text = "".join(out)
    # LaTeX literals -> characters. `~` is deliberately kept: the sentence splitter
    # reads `.~` as a positive abbreviation signal, and it is stripped at word count.
    text = text.replace("``", '"').replace("''", '"')
    emdashes = text.count("---")
    text = text.replace("---", "\u2014").replace("--", "\u2013")
    for esc, ch in (("\\%", "%"), ("\\&", "&"), ("\\_", "_"), ("\\#", "#"),
                    ("\\$", "$"), ("\\{", "{"), ("\\}", "}"), ("\\\\", " ")):
        text = text.replace(esc, ch)
    return text, emdashes


# --- sentence splitting -------------------------------------------------------

_WORD = re.compile(r"[A-Za-z\u00c0-\u024f][A-Za-z\u00c0-\u024f'\u2019-]*")


def _is_abbrev(before: str) -> bool:
    """Does the text ending at a period end an abbreviation rather than a sentence?"""
    tail = before.rstrip()
    if not tail.endswith("."):
        return False
    tok = re.search(r"([A-Za-z.]+)\.$", tail)
    if not tok:
        return False
    w = tok.group(1).lower().rstrip(".")
    if w in ABBREV:
        return True
    return len(w) == 1          # an initial, or an enumerating letter


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text.replace("~", " ~ ")).strip()
    text = text.replace(" ~ ", "~")
    out, start = [], 0
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in ".!?":
            nxt = text[i + 1] if i + 1 < n else " "
            # `.~` is an abbreviation, always -- the tie LaTeX gives us for free.
            if nxt == "~":
                i += 1
                continue
            if c == "." and _is_abbrev(text[start:i + 1]):
                i += 1
                continue
            j = i + 1
            while j < n and text[j] in '")\u201d]':
                j += 1
            if j >= n or text[j] == " ":
                after = text[j:].lstrip()
                # A lowercase continuation means the period was not a full stop
                # (an unlisted abbreviation, or a decimal).
                if after and after[0].islower():
                    i += 1
                    continue
                seg = text[start:j].strip()
                if seg:
                    out.append(seg)
                start = j
                i = j
                continue
        i += 1
    tail = text[start:].strip()
    if tail:
        out.append(tail)
    return out


def measure(sent: str) -> Sentence:
    stripped = sent
    counts = {}
    for tok, key in ((EQ, "eq"), (MATH, "m"), (CITE, "c"), (REF, "r")):
        counts[key] = stripped.count(tok)
        stripped = stripped.replace(tok, " ")
    return Sentence(
        text=sent.replace("~", " "),
        words=len(_WORD.findall(stripped)),
        math=counts["eq"] + counts["m"],
        cites=counts["c"],
        refs=counts["r"],
    )


# --- the document walk --------------------------------------------------------

_SECTION = re.compile(r"\\(section|subsection|subsubsection|paragraph)\*?\{")
_BEGIN = re.compile(r"\\begin\{([A-Za-z*]+)\}")
_END = re.compile(r"\\end\{([A-Za-z*]+)\}")
_CITE_CMD = re.compile(r"\\(?:ss)?cite[tp]?(?:\[[^\]]*\])*\{[^}]*\}")
_REF_CMD = re.compile(r"\\(?:eq|page|auto|c)?ref\{[^}]*\}")


def _heading_text(src: str, brace: int) -> tuple[str, int]:
    end = _match_brace(src, brace)
    if end == -1:
        return "", brace + 1
    return src[brace + 1:end - 1], end


def extract(path: Path) -> Extraction:
    raw = strip_comments(path.read_text(encoding="utf-8"))
    raw = _CITE_CMD.sub(CITE, raw)
    raw = _REF_CMD.sub(REF, raw)
    raw, line_of = mask_math(raw)

    unknown: dict[str, int] = {}
    unknown_ctx: dict[str, str] = {}
    dropped: dict[str, int] = {}
    blocks: list[Block] = []

    section, subsection = "(preamble)", None
    env_stack: list[str] = []
    buf, buf_at = [], 0
    pending_title: str | None = None

    def kind_now() -> str:
        for e in reversed(env_stack):
            base = e.rstrip("*")
            if base in ENV_KIND:
                return ENV_KIND[base]
            if base in LIST_ENVS:
                return "list"
        return "prose"

    def flush() -> None:
        nonlocal buf, buf_at, pending_title
        text = "".join(buf).strip()
        buf = []
        title, pending_title = pending_title, None
        if not text:
            return
        emph: list[str] = []
        norm, dashes = normalize(text, unknown, emph, unknown_ctx)
        norm = re.sub(r"\s+", " ", norm).strip()
        if not norm or not _WORD.search(norm.replace(EQ, " ").replace(MATH, " ")):
            return
        b = Block(kind=kind_now(), env=env_stack[-1] if env_stack else None,
                  section=section, subsection=subsection, source=path.name,
                  line=line_of[buf_at], text=norm, title=title, emphases=emph,
                  emdashes=dashes)
        b.sentences = [measure(s) for s in split_sentences(norm)]
        blocks.append(b)

    i, n = 0, len(raw)
    while i < n:
        if raw.startswith("\n\n", i):
            flush()
            while i < n and raw[i] == "\n":
                i += 1
            buf_at = i
            continue
        m = _SECTION.match(raw, i)
        if m:
            flush()
            title, after = _heading_text(raw, m.end() - 1)
            level = m.group(1)
            tnorm, _ = normalize(title, unknown, [], unknown_ctx)
            tnorm = re.sub(r"\s+", " ", tnorm).strip()
            if level == "section":
                section, subsection = tnorm, None
            elif level in ("subsection", "subsubsection"):
                subsection = tnorm
            else:   # \paragraph -- a run-in heading, not a sentence
                blocks.append(Block(kind="heading", env=None, section=section,
                                    subsection=subsection, source=path.name,
                                    line=line_of[i], text=tnorm))
            i = after
            buf_at = i
            continue
        m = _BEGIN.match(raw, i)
        if m:
            flush()
            env = m.group(1)
            base = env.rstrip("*")
            if base in FLOAT_ENVS:
                close = re.compile(r"\\end\{" + re.escape(env) + r"\}")
                mo = close.search(raw, m.end())
                dropped[base] = dropped.get(base, 0) + 1
                i = mo.end() if mo else m.end()
                buf_at = i
                continue
            env_stack.append(env)
            i = m.end()
            # `\begin{lemma}[self-decomposable exponents]` — the optional argument is
            # the statement's *title*, not the first words of its prose.
            if i < n and raw[i] == "[":
                depth, k = 0, i
                while k < n:
                    if raw[k] == "[":
                        depth += 1
                    elif raw[k] == "]":
                        depth -= 1
                        if depth == 0:
                            break
                    k += 1
                if k < n:
                    t, _ = normalize(raw[i + 1:k], unknown, [], unknown_ctx)
                    pending_title = re.sub(r"\s+", " ", t).strip() or None
                    i = k + 1
            buf_at = i
            continue
        m = _END.match(raw, i)
        if m:
            flush()
            if env_stack and env_stack[-1].rstrip("*") == m.group(1).rstrip("*"):
                env_stack.pop()
            i = m.end()
            buf_at = i
            continue
        if raw.startswith("\\item", i):
            flush()
            i += len("\\item")
            buf_at = i
            continue
        buf.append(raw[i])
        i += 1
    flush()
    return Extraction(blocks=blocks, unknown=unknown, dropped_envs=dropped,
                      unknown_ctx=unknown_ctx)
