r"""The F7 sweep takes its nodes and proofs from `linkage`'s parser, not a regex of its own.

Two shapes the sweep's old regexes lost: a comment or newline between `\lean{}` and `\leanok`
(the node was not counted), and a statement longer than 400 characters before its proof (the proof's
`\uses{}` was missed, or another node's was taken). The first group pins the parser's side, which
the sweep reads; the second runs the script itself on a fixture article.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

from fixtures.article import statement

SCRIPT = (Path(__file__).resolve().parents[1]
          / ".claude/skills/fidelity-review/scripts/f7sweep.py")

SPLIT_LEAN = r"""
\begin{lemma}
  \label{lem:a}
  \lean{A.a}
  % CHANGED: reproved without the compactness hypothesis
  \leanok
  The kernel is smooth.
\end{lemma}
\begin{proof}\leanok Immediate.\end{proof}
"""

LONG = "The kernel is smooth and its derivatives decay. " * 20  # > 400 characters

LONG_STATEMENT = (
    r"\begin{theorem}" "\n"
    r"  \label{thm:x}" "\n"
    r"  \lean{A.x}" "\n"
    r"  \leanok" "\n"
    f"  {LONG}\n"
    r"\end{theorem}" "\n"
    r"% proof of thm:x" "\n"
    r"\begin{proof}\leanok \uses{lem:a} By \ref{lem:a}.\end{proof}" "\n"
)

NEXT_NODE = (
    r"\begin{lemma}\label{lem:b}\lean{A.b}\leanok \uses{lem:c} Other.\end{lemma}" "\n"
)


def test_a_comment_between_lean_and_leanok_still_makes_a_leanok_node(article):
    article.blueprint(SPLIT_LEAN)
    (node,) = article.parse().nodes
    assert node.lean == ["A.a"] and node.leanok


def test_a_long_statement_keeps_its_own_proofs_uses(article):
    article.blueprint(statement(env="lemma", label="lem:a", lean="A.a", leanok=True)
                      + LONG_STATEMENT + NEXT_NODE)
    got = {n.label: n for n in article.parse().nodes}
    assert got["thm:x"].proof_uses == ["lem:a"]
    assert got["thm:x"].uses == []
    assert got["lem:b"].proof_uses == [] and got["lem:b"].uses == ["lem:c"]


def test_the_sweep_counts_every_leanok_node_and_reads_the_proofs_uses(
        article, monkeypatch, capsys):
    article.blueprint(SPLIT_LEAN + LONG_STATEMENT)
    article.file("Formalization/A.lean", "namespace A\ntheorem a : True := trivial\n")
    article.file("Formalization/B.lean", "namespace A\ntheorem x : True := trivial\n")
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--root", str(article.root)])
    runpy.run_path(str(SCRIPT), run_name="__main__")
    out = capsys.readouterr().out
    assert "2 leanok nodes" in out
    assert "thm:x [B] | uses-not-imported: lem:a→A" in out
