"""A synthetic article repository, built under `tmp_path`.

Every test builds the article it needs and nothing else. That is the whole isolation
story for this suite: `linkage` reads an article tree through `Config`, so a fixture
that *is* an article tree exercises the real code path — parser, artifact readers and
checks together — without a real repository, a Lean toolchain, pandoc, or the network.

The defaults are the smallest tree `config.load()` accepts (all six configured paths
must exist). A test overwrites the one or two files its rule is about.
"""

from __future__ import annotations

from pathlib import Path

from linkage import artifacts, checks, config, parse_latex

DEFAULT_TOML = """\
slug = "test"

[paths]
blueprint = "blueprint/src/content.tex"
axioms    = "blueprint/AXIOMS.md"
macros    = "blueprint/src/macros.tex"
allowlist = "blueprint/render-allowlist.txt"
lean      = "Formalization"
paper     = "paper"
"""

# The framework's own vocabulary is stripped by `normalize_statement`, so it needs no
# entry here; these are an article's notation, i.e. what fatal check 4 reads.
DEFAULT_MACROS = r"""
\newcommand{\RR}{\mathbb{R}}
\newcommand{\kernel}[1]{K_{#1}}
"""

DEFAULT_ALLOWLIST = """\
# vetted standard LaTeX
emph
in
mathbb
text
textbf
texttt
ref
"""


def statement(
    body: str = "The kernel is smooth.",
    *,
    env: str = "theorem",
    label: str | None = "thm:x",
    title: str | None = None,
    lean: str | None = None,
    leanok: bool = False,
    notready: bool = False,
    uses: tuple[str, ...] = (),
    ledger: tuple[str, ...] = (),
    notes: str | None = None,
    status: str | None = "T",
    note: str | None = None,
    proof: str | None = None,
) -> str:
    r"""One blueprint statement environment (plus a trailing proof), as LaTeX source.

    Written the way the blueprint dialect writes it — metadata commands first, the
    `\statusT`/`\statusA` tag and its `\emph{}` annotation last — so a test's fixture
    differs from a real node only in being short.
    """
    lines = [f"\\begin{{{env}}}" + (f"[{title}]" if title else "")]
    if label:
        lines.append(f"  \\label{{{label}}}")
    if lean:
        lines.append(f"  \\lean{{{lean}}}")
    if leanok:
        lines.append(r"  \leanok")
    if notready:
        lines.append(r"  \notready")
    if uses:
        lines.append("  \\uses{" + ",".join(uses) + "}")
    if notes:
        lines.append(f"  \\notes{{{notes}}}")
    lines.append("  " + body)
    if status:
        tag = f"  \\status{status}"
        for a in ledger:
            tag += f"\\ledger{{{a}}}"
        if note:
            tag += r"\quad\emph{" + note + "}"
        lines.append(tag)
    lines.append(f"\\end{{{env}}}")
    if proof is not None:
        lines.append(r"\begin{proof}" + proof + r"\end{proof}")
    return "\n".join(lines) + "\n"


def assignment(clause: str = r"\ledger{A1} carries the tail bound; the mode is [T].") -> str:
    r"""A rule-7 `\textbf{Assignment.}` clause, for the `note=` argument."""
    return r"\textbf{Assignment.} " + clause


def ledger_entry(aid: str = "A1", cite: str | None = "@author2020 — Thm 3.1, p. 88",
                 lean: str | None = None) -> str:
    """One `## AXX` ledger entry, optionally with its `**Lean:**` back-pointer."""
    out = [f"## {aid}", "", "Some analytic interface.", ""]
    if lean:
        out += [f"**Lean:** `{lean}`", ""]
    if cite is not None:
        out += [f"**Cite:** {cite}", ""]
    return "\n".join(out)


class Article:
    """A tiny article repo. Every writer returns `self`, so a fixture is one expression."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.file("linkage.toml", DEFAULT_TOML)
        self.blueprint("")
        self.axioms("# Axiom ledger\n")
        self.macros(DEFAULT_MACROS)
        self.allowlist(DEFAULT_ALLOWLIST)
        self.lean("")
        self.paper("")

    # --- writers ---------------------------------------------------------------
    def file(self, rel: str, text: str) -> Article:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")
        return self

    def blueprint(self, tex: str) -> Article:
        return self.file("blueprint/src/content.tex", tex)

    def part(self, name: str, tex: str) -> Article:
        return self.file(f"blueprint/src/{name}", tex)

    def axioms(self, text: str) -> Article:
        return self.file("blueprint/AXIOMS.md", text)

    def macros(self, text: str) -> Article:
        return self.file("blueprint/src/macros.tex", text)

    def allowlist(self, text: str) -> Article:
        return self.file("blueprint/render-allowlist.txt", text)

    def lean(self, text: str, name: str = "Main.lean") -> Article:
        return self.file(f"Formalization/{name}", text)

    def paper(self, text: str, name: str = "paper.tex") -> Article:
        return self.file(f"paper/{name}", text)

    # --- readers ---------------------------------------------------------------
    @property
    def cfg(self) -> config.Config:
        return config.load(self.root)

    def parse(self):
        return parse_latex.parse(self.cfg)

    def check(self, **kw) -> checks.Findings:
        """The whole in-repo check, end to end over this fixture."""
        cfg = self.cfg
        return checks.run(
            self.parse(),
            cfg,
            lean_names=artifacts.lean_declared_names(cfg),
            ledger=artifacts.ledger_entries(cfg),
            markers=artifacts.paper_markers(cfg),
            safe_commands=artifacts.render_safe_commands(cfg),
            control_chars=artifacts.control_chars(cfg),
            **kw,
        )
