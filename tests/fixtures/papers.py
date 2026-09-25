"""The paper fixtures `linkage paper` is tested against.

Two things live here. `install()` copies one of the two fixture *papers* under
`tests/fixtures/paper/` into an `Article` tree — `clean`, which every check passes, and
`seeded`, which is the same paper with one defect per check, each marked `% SEED: <tag>`
in the source. They are a pair on purpose: a check that stops firing is caught by the
seeded paper, and a check that starts firing where it should not is caught by the clean
one.

`document()` builds a one-file paper instead, for the per-check tests: the whole
front matter a real paper needs (an in-range abstract, all four declarations) around
whatever body the test is about, so a test that seeds a dangling `\\ref` reports that and
nothing else.
"""

from __future__ import annotations

from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "paper"

# 150 words exactly, the floor of PUBLICATION-TEMPLATE § A's range — so a test that wants
# an out-of-range abstract shortens or lengthens it deliberately.
ABSTRACT = " ".join(["word"] * 150)

DECLARATIONS = r"""
\section*{Author contributions}
The author wrote the paper.

\section*{Competing interests}
The author declares none.

\section*{Data availability}
No data were generated.

\section*{Funding}
This work received no funding.
"""


def install(article, name: str = "clean", dir: str = "paper"):
    """Copy the `clean` or `seeded` fixture paper into `article`'s paper directory."""
    for p in sorted((FIXTURES / name).iterdir()):
        if p.is_file():
            article.file(f"{dir}/{p.name}", p.read_text(encoding="utf-8"))
    return article


def document(body: str, *, abstract: str | None = ABSTRACT,
             declarations: str = DECLARATIONS, bib: str | None = None) -> str:
    r"""A whole small paper around `body`: a main document with front matter.

    `abstract=None` omits the abstract environment; `declarations=""` omits the four
    declaration headings; `bib` names the bibliography (`\bibliography{<bib>}`), which
    the caller writes as a sibling file.
    """
    head = r"""\documentclass{article}
\begin{document}
"""
    if abstract is not None:
        head += "\\begin{abstract}\n" + abstract + "\n\\end{abstract}\n"
    tail = declarations
    if bib:
        tail += f"\n\\bibliography{{{bib}}}\n"
    return head + "\n" + body + "\n" + tail + "\n\\end{document}\n"
