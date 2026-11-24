r"""`linkage citations --inventory` — every citation of the paper sources, one row each.

Pass 7 of `docs/PROCESS.md` § 8 reads every page-anchored citation against the held copy; this
is the list it reads from. A row carries the file, the line, the citekey, the locator, the
paragraph around the citation (comments stripped), the zone (`prose`, or `shared-statement` for
a citation inside an environment a `% shared with blueprint` marker marks) and, for a shared
statement, the blueprint node.

The forms an article uses:

- `[\sscite{key}, loc]` and `\sscite{key}` (any `\...cite...` macro, as `paper.CITE_RE`; `form` is the macro name, or `prog`, `progpaper`), also several in one bracket, `[\sscite{a}, loc; \sscite{b}, loc]`;
- `\cite[loc]{key}`, where the last optional argument is the locator;
- `\prog{module}{loc}` and `\progpaper{module}` (no locator). The key is the citekey the paper
  maps the module label to (`\@namedef{progkey@<label>}{<key>}` in its macros), or the label
  where it maps none; `module` keeps the label (null on the other rows).

A `\cite{a,b}` gives one row per key. A macro's own definition (`#1`) is not a citation.
"""

from __future__ import annotations

import re

from .artifacts import MARKER_RE
from .config import Config
from .paper import CITE_RE, Sources, _braced, _line, read

# `\prog{module}{loc}`, `\progpaper{module}`: the name must not run on (`\prog@key`).
PROG_RE = re.compile(r"\\prog(paper)?(?![A-Za-z@])\s*\{")
# The `[` ... `]` of the bracketed form, immediately before a citation macro: `[\sscite{k}, loc]`.
# Several citations share one bracket, `[\sscite{a}, loc; \sscite{b}, loc]`: a locator ends at
# the `]` or at a `;` that opens the next citation.
_BRACKET_TAIL = re.compile(r"\s*,\s*([^\]\[]*?)\s*(?:\]|;(?=\s*\\[A-Za-z]*[Cc]ite))")
# The paper's map from a module label to its citekey, `\@namedef{progkey@V-line v0.1}{key}`.
_PROGKEY_RE = re.compile(r"\\@namedef\{progkey@([^}]*)\}\{([^}]*)\}")
_OPT = re.compile(r"\s*\[([^\]]*)\]")


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _paragraph(text: str, pos: int) -> str:
    """The blank-line-delimited paragraph around `pos`, whitespace collapsed."""
    a = text.rfind("\n\n", 0, pos)
    b = text.find("\n\n", pos)
    return _clean(text[a + 2 if a >= 0 else 0: b if b >= 0 else len(text)])


def _shared_spans(cfg: Config, src, text: str) -> list[tuple[int, int, str]]:
    """(start, end, first blueprint label) of each environment a shared marker marks.

    Read from the raw file, since the marker is a comment: `strip_comments` keeps every
    offset, so the spans apply to the stripped text too.
    """
    raw = src.path.read_text(encoding="utf-8", errors="replace")
    env_re = re.compile(
        r"\\begin\{(" + "|".join(cfg.statement_envs) + r")\}.*?\\end\{\1\}", re.S)
    marks = list(MARKER_RE.finditer(raw))
    out = []
    for i, m in enumerate(marks):
        nxt = marks[i + 1].start() if i + 1 < len(marks) else len(raw)
        em = env_re.search(raw, m.end())
        if em and em.start() < nxt:
            label = m.group(1).split(",")[0].strip().split("@")[0].split("+")[0]
            out.append((em.start(), em.end(), label))
    return out


def _scan(text: str) -> list[tuple[int, str, str, str]]:
    r"""(position, key, form, locator) for every citation in `text`, in order; a `\prog`
    row's key is the module label."""
    found: list[tuple[int, str, str, str]] = []
    for m in CITE_RE.finditer(text):
        macro = m.group(0)
        # The optional arguments sit between the macro name and the key group.
        head = macro[:macro.rfind("{")]
        opts = _OPT.findall(head)
        loc = _clean(opts[-1]) if opts else ""
        if not loc:
            tail = _BRACKET_TAIL.match(text, m.end())
            # Only a bracket the citation opens: `[` right before the macro, however much
            # text precedes it.
            # (or a `;` inside one, for the second citation of a shared bracket).
            before = text[:m.start()].rstrip()
            opened = before.rfind("[") > before.rfind("]")
            if tail and (before.endswith("[") or (before.endswith(";") and opened)):
                loc = _clean(tail.group(1))
        # The macro name, so `\sscite` and `\cite` rows differ.
        form = re.match(r"\\([A-Za-z]*[Cc]ite[A-Za-z]*)", macro).group(1)
        for key in m.group(1).split(","):
            key = key.strip()
            if not key or "#" in key or "\\" in key:
                continue
            found.append((m.start(), key, form, loc))
    for m in PROG_RE.finditer(text):
        key = _clean(_braced(text, m.end()))
        if not key or "#" in key:
            continue
        loc = ""
        if not m.group(1):
            j = m.end() + len(_braced(text, m.end())) + 1
            while j < len(text) and text[j].isspace():
                j += 1
            if j < len(text) and text[j] == "{":
                loc = _clean(_braced(text, j + 1))
        if "#" in loc:
            continue
        found.append((m.start(), key, "progpaper" if m.group(1) else "prog", loc))
    return sorted(found, key=lambda r: r[0])


def inventory(cfg: Config, src: Sources | None = None) -> list[dict]:
    """One row per citation, over every paper source (those `\\input`ed included)."""
    src = src or read(cfg)
    progkeys = {_clean(a): b.strip()
                for s in src.files for a, b in _PROGKEY_RE.findall(s.text)}
    rows: list[dict] = []
    for s in src.files:
        spans = _shared_spans(cfg, s, s.text)
        for pos, key, form, loc in _scan(s.text):
            node = next((lab for a, b, lab in spans if a <= pos < b), None)
            module = key if form in ("prog", "progpaper") else None
            rows.append({
                "file": s.rel,
                "line": _line(s.text, pos),
                "key": progkeys.get(key, key) if module else key,
                "module": module,
                "form": form,
                "locator": loc,
                "zone": "shared-statement" if node else "prose",
                "node": node,
                "paragraph": _paragraph(s.text, pos),
            })
    for i, r in enumerate(rows, 1):
        r["id"] = f"C{i:03d}"
    return [{"id": r["id"], **{k: v for k, v in r.items() if k != "id"}} for r in rows]
