"""A freshly scaffolded article, filled in far enough to be checkable.

`linkage init` writes the framework's half of an article — the LaTeX scaffolding, the
seeded files, `linkage.toml`. It deliberately does not write the article's half (the
blueprint content, the ledger, the Lean sources, the paper), so a scaffolded directory
is not yet something `linkage check` can run on. This module supplies the smallest
article's half that exercises one edge of every kind, and is used two ways:

  * `tests/test_scaffold.py` runs the check over it in-process;
  * CI runs it as a script, then runs the real `linkage check` over the result —
    so a scaffolding change that breaks a *new* article fails here, in the framework's
    own CI, rather than in the next article that starts from it.

Deliberately uses `\\RR` from the scaffolded `macros.tex`: that makes the seeded macro
file part of what the smoke test covers, since fatal check 4 resolves commands against it.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from linkage import scaffold  # noqa: E402

BLUEPRINT = r"""\begin{definition}[The kernel]
  \label{def:kernel}
  A kernel is a map from $\RR$ to $\RR$.
  \statusT
\end{definition}

\begin{theorem}[Smoothness]
  \label{thm:smooth}
  \lean{Smoke.kernel_smooth}
  \leanok
  \uses{def:kernel, prop:interface}
  Every kernel is smooth on $\RR$.
  \statusT
\end{theorem}
\begin{proof}
  \leanok
  \uses{prop:interface}
  Immediate from \ref{prop:interface}.
\end{proof}

\begin{proposition}[The analytic interface]
  \label{prop:interface}
  \uses{def:kernel}
  Every kernel is bounded.
  \statusA\ledger{A1}\quad\emph{\textbf{Assignment.} \ledger{A1} carries boundedness in
  full; nothing here is held as [T].}
\end{proposition}
"""

AXIOMS = """\
# Axiom ledger — the trust boundary

## A1

Boundedness of the kernel, taken as an analytic interface.

**Lean:** `Smoke.kernel_bounded`

**Cite:** @author2020 — Thm 3.1, p. 88
"""

LEAN = """\
namespace Smoke

axiom kernel_bounded : True

theorem kernel_smooth : True := trivial

end Smoke
"""

PAPER = r"""\section{Smoothness}

% shared with blueprint thm:smooth
\begin{theorem}
  \label{thm:smooth}
  Every kernel is smooth on $\RR$.
\end{theorem}
"""


def build(root: Path, slug: str = "smoke") -> Path:
    """Scaffold into `root`, then write the article's own half. Returns `root`."""
    root.mkdir(parents=True, exist_ok=True)
    scaffold.init(root, slug=slug, subs={"TITLE": "Smoke Article"})
    (root / "blueprint" / "src" / "content.tex").write_text(BLUEPRINT, encoding="utf-8")
    (root / "blueprint" / "AXIOMS.md").write_text(AXIOMS, encoding="utf-8")
    (root / "blueprint" / "trust-boundary.txt").write_text(
        "# this article's declared interface axioms\nSmoke.kernel_bounded\n", encoding="utf-8")
    (root / "Formalization").mkdir(parents=True, exist_ok=True)
    (root / "Formalization" / "Smoke.lean").write_text(LEAN, encoding="utf-8")
    (root / "paper").mkdir(parents=True, exist_ok=True)
    (root / "paper" / "smoothness.tex").write_text(PAPER, encoding="utf-8")
    return root


if __name__ == "__main__":
    dest = Path(sys.argv[1] if len(sys.argv) > 1 else "scaffold-smoke").resolve()
    build(dest)
    print(dest)
