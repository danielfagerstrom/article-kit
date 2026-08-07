"""The LaTeX blueprint parser — one dialect in, `Blueprint` out.

Everything format-specific about the leanblueprint/plasTeX dialect lives here and nowhere
else. The regexes are carried over unchanged from the original `check_linkage.py`: their
exact behaviour is load-bearing (statement shas are published to the hub, and a
normalization change would move every one of them at once), so this module is a
transliteration, not a rewrite.
"""
from __future__ import annotations

import re
from pathlib import Path

from .config import Config
from .model import Blueprint, Node


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def expand_inputs(entry: Path) -> str:
    """A LaTeX file with its `\\input{...}` includes inlined, recursively.

    Used for two things, and the second is easy to overlook: the blueprint entry file
    (whose nodes live in parts/), and the *macros* file. The macros file is handed to
    pandoc as the render preamble, and pandoc does not follow `\\input` — so once an
    article splits its macros into framework + notation, feeding the unexpanded file
    would silently drop half the definitions and move every rendered_sha at once.
    """
    inp = re.compile(r"^\s*\\input\{([^}]+)\}")

    def expand(path: Path) -> str:
        out = []
        for line in read(path).splitlines(keepends=True):
            m = inp.match(line)
            if m and not line.lstrip().startswith("%"):
                inc = m.group(1)
                if not inc.endswith(".tex"):
                    inc += ".tex"
                out.append(expand(path.parent / inc))
            else:
                out.append(line)
        return "".join(out)

    return expand(entry)


def read_blueprint(entry: Path) -> str:
    """The blueprint entry file, with its parts inlined."""
    return expand_inputs(entry)


def normalize_statement(body: str) -> str:
    """The statement text of a node body, normalized for stable hashing.

    Strips LaTeX comments and the metadata commands (\\label/\\lean/\\uses/\\notes/\\ledger
    with their arguments; the bare \\notready/\\leanok tokens; \\statusT/\\statusA together
    with their trailing \\quad\\emph{...} status annotation — proof-status remarks, not
    statement content, so a status edit does not move the sha), then collapses all whitespace
    runs to single spaces. The mathematical prose and math are kept verbatim, so the text —
    and its sha — changes exactly when the statement's content does. Deterministic: a pure
    function of the body string, no environment input.
    """
    body = re.sub(r"(?<!\\)%[^\n]*", "", body)
    body = re.sub(r"\\(?:label|lean|uses|notes|ledger)\{[^}]*\}", "", body)
    # \statusT / \statusA plus the annotation that follows them: optional \quad / \qquad
    # spacing, then an optional \emph{...} group (balanced to two brace-nesting levels —
    # the annotations contain \texttt{...} / \ref{...}).
    body = re.sub(
        r"\\status[TA]\b(?:\s|\\quad\b|\\qquad\b)*"
        r"(?:\\emph\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\})?",
        "",
        body,
    )
    body = re.sub(r"\\(?:statusT|statusA|notready|leanok)\b", "", body)
    return re.sub(r"\s+", " ", body).strip()


def normalize_for_render(body: str) -> str:
    """The statement/proof source handed to pandoc — normalize_statement's sibling.

    Differs in exactly one way: an *in-prose* ``\\ledger{A2}`` renders as the text
    "ledger A2" (its PDF macro expansion) instead of being deleted — deletion leaves
    dangling punctuation in rendered proofs ("taken as an interface (, the Lean …)",
    found by the H5 migration). Ledger refs on the *status line* still vanish with it
    (the status-strip below tolerates \\ledger tokens between the \\quads). The sha
    fields keep using normalize_statement, so this changes rendered output only.
    """
    body = re.sub(r"(?<!\\)%[^\n]*", "", body)
    body = re.sub(r"\\(?:label|lean|uses|notes)\{[^}]*\}", "", body)
    body = re.sub(
        r"\\status[TA]\b(?:\s|\\quad\b|\\qquad\b|\\ledger\{[^}]*\})*"
        r"(?:\\emph\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\})?",
        "",
        body,
    )
    body = re.sub(r"\\(?:statusT|statusA|notready|leanok)\b", "", body)
    body = re.sub(r"\\ledger\{([^}]*)\}", r"ledger \1", body)
    return re.sub(r"\s+", " ", body).strip()


# The status annotation itself -- the `\emph{...}` that follows \statusT/\statusA (with
# \quad spacing and \ledger{} refs tolerated between). normalize_statement DELETES this
# region, so a status edit never moves a statement sha; check 7 needs it kept, because
# ADR-0011 puts the assignment declaration here. Same brace balancing as the strip.
STATUS_ANNOTATION_RE = re.compile(
    r"\\status[TA]\b(?:\s|\\quad\b|\\qquad\b|\\ledger\{[^}]*\})*"
    r"(\\emph\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\})?"
)


def status_annotation(body: str) -> str:
    m = STATUS_ANNOTATION_RE.search(body)
    return (m.group(1) or "") if m else ""


# a proof environment directly following a statement env (whitespace/comments between);
# non-greedy to the first \end{proof} — the blueprint does not nest proofs
PROOF_AHEAD = re.compile(r"(?:\s|%[^\n]*)*\\begin\{proof\}(.*?)\\end\{proof\}", re.S)


def blueprint_nodes(tex: str, cfg: Config) -> list[Node]:
    """One Node per statement environment (plus its trailing proof, if any)."""
    nodes: list[Node] = []
    for m in re.finditer(
        r"\\begin\{(" + "|".join(cfg.statement_envs) + r")\}(.*?)\\end\{\1\}", tex, re.S
    ):
        body = m.group(2)
        # the environment's optional [human title] is presentation metadata, not statement
        # content — split it out so it neither pollutes the statement text/sha nor renders
        # as escaped brackets; the hub's import renders it in the block header instead
        tm = re.match(r"\s*\[([^\]]*)\]", body)
        title = tm.group(1).strip() if tm else None
        if tm:
            body = body[tm.end():]
        pm = PROOF_AHEAD.match(tex, m.end())
        lab = re.search(r"\\label\{([^}]+)\}", body)
        decls = [
            d.strip()
            for dm in re.finditer(r"\\lean\{([^}]+)\}", body)
            for d in dm.group(1).split(",")
            if d.strip()
        ]
        uses = [
            u.strip()
            for um in re.finditer(r"\\uses\{([^}]+)\}", body)
            for u in um.group(1).split(",")
            if u.strip()
        ]
        nodes.append(
            Node(
                env=m.group(1),
                title=title,
                label=lab.group(1) if lab else None,
                lean=decls,
                uses=uses,
                leanok=r"\leanok" in body,
                notready=r"\notready" in body,
                # [T]/[A] and the node's ledger refs — projected so the hub's generated
                # status line can say "cited interface (ledger A3)" instead of the
                # misleading "proved in Lean" on an accepted axiom (H5 finding)
                status=("T" if r"\statusT" in body
                        else "A" if r"\statusA" in body else None),
                status_note=status_annotation(body),
                # de-duplicated, first-mention order: a node's \ledger{} may now appear
                # twice — once on the status line, once inside the Assignment clause that
                # says what that entry carries (LINKAGE.md rule 7) — and the hub projects
                # this list as the node's sources, where a repeat is noise.
                ledger=list(dict.fromkeys(re.findall(r"\\ledger\{([^}]*)\}", body))),
                statement=normalize_statement(body),
                proof=normalize_statement(pm.group(1)) if pm else None,
                statement_render_src=normalize_for_render(body),
                proof_render_src=normalize_for_render(pm.group(1)) if pm else None,
            )
        )
    return nodes


def ledger_refs(tex: str, cfg: Config) -> set[str]:
    refs = set(re.findall(r"\\ledger\{([^}]+)\}", tex))
    refs |= set(re.findall(r"ledger~?\s*(" + cfg.ledger_key + r")", tex))  # legacy prose
    return refs


def notes_slugs(tex: str) -> set[str]:
    return set(re.findall(r"\\notes\{([^}]+)\}", tex))


def parse(cfg: Config) -> Blueprint:
    """Read and parse the article's blueprint into the format-independent model."""
    tex = read_blueprint(cfg.blueprint)
    return Blueprint(
        nodes=blueprint_nodes(tex, cfg),
        ledger_refs=ledger_refs(tex, cfg),
        notes_slugs=notes_slugs(tex),
    )
