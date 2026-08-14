"""Prose measurement — the language-review floor.

The deterministic half of the AI-prose pass: extract reviewable prose from a LaTeX
(or pandoc-markdown) source, classify it by environment, and count. It never judges
and never edits; the report is input to a human triage step.

`extract.py` is the only format-aware module, the same rule `parse_latex.py` follows
for the blueprint.
"""
