"""linkage — the blueprint <-> Lean <-> ledger <-> paper linkage framework.

One article repo per deliverable; this package is the shared machinery they all run:
the checks, the manifest the wiki hub reads, and the scaffolding a new article starts from.

The stages are deliberately separable — `parse_latex` turns one blueprint dialect into the
`model.Node` IR, and `checks` / `manifest` / `demand` consume only the IR. A second dialect
is a second parser, not a rewrite.
"""

__version__ = "0.1.0"
