"""The node model — the intermediate representation every other stage speaks.

This is the seam that makes the rest of the package format-independent. A parser
(`parse_latex`) turns *one* blueprint dialect into `list[Node]`; `checks`, `manifest`
and `demand` consume `Node` and never look at LaTeX. Adding a second dialect means
adding a second parser, not touching the checks.

Field names are deliberately the ones the manifest projects, so the emitter is a
near-transliteration and the wire format cannot drift from the model by accident.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Node:
    """One statement environment of the blueprint, plus its trailing proof if any."""

    env: str
    """The environment it was stated in (definition/lemma/proposition/theorem/corollary)."""

    label: str | None
    """Canonical label, e.g. `thm:causal-galilean`. Every other artifact references this."""

    title: str | None
    """The environment's optional [human title] — presentation metadata, not content."""

    lean: list[str] = field(default_factory=list)
    """Declaration names this node claims to be formalised by."""

    uses: list[str] = field(default_factory=list)
    """Labels this node's statement/proof depends on — the dependency-graph edges."""

    leanok: bool = False
    """The node asserts it is proved in Lean."""

    notready: bool = False
    """The node asserts it is not ready to formalise."""

    status: str | None = None
    """`T` (proved-target) or `A` (analytic interface); None means undeclared (check 5)."""

    status_note: str = ""
    """The `\\emph{...}` annotation trailing the status tag — check 7 reads the
    Assignment clause out of it. Deliberately excluded from `statement`, so a status
    edit never moves a statement sha."""

    ledger: list[str] = field(default_factory=list)
    """Axiom-ledger entry ids this node is grounded in, de-duplicated, first-mention order."""

    statement: str = ""
    """Statement text normalized for stable hashing."""

    proof: str | None = None
    """Proof-of-record text, normalized the same way. None when there is no proof."""

    statement_render_src: str = ""
    """Statement source normalized for the renderer — differs from `statement` only in
    keeping in-prose ledger refs as text."""

    proof_render_src: str | None = None
    """Proof source normalized for the renderer."""

    @property
    def kind(self) -> str | None:
        """The label's prefix — `thm`, `prop`, `def`, … — as the manifest projects it.

        The label, not the environment: `thm:receptive-field` is stated in a `proposition`
        environment, and the label is what every other artifact references.
        """
        return self.label.split(":", 1)[0] if self.label else None

    def proof_of_record(self) -> str:
        """The node's blueprint proof, or "" — a proof environment with content in it."""
        return (self.proof or "").strip()


@dataclass
class LedgerEntry:
    """One `## AXX` entry of the axiom ledger."""

    id: str
    citekey: str | None = None
    anchor: str | None = None
    has_cite_line: bool = False
    """False when the entry carries no `**Cite:**` line at all — fatal check 6."""

    def projection(self) -> dict:
        """What the manifest carries for a node grounded in this entry."""
        return {"id": self.id, "citekey": self.citekey, "anchor": self.anchor}


@dataclass
class PaperMarker:
    """A `% shared with blueprint <label>` marker found in the paper."""

    file: str
    blueprint_label: str
    nearest_label: str | None
    """The paper's own nearest preceding `\\label{}` — label equality is the target form."""


@dataclass
class Blueprint:
    """A parsed blueprint: the nodes, plus the whole-document facts the checks need."""

    nodes: list[Node]
    ledger_refs: set[str]
    """Every ledger id referenced anywhere in the document, including legacy prose form."""
    notes_slugs: set[str]
    """Every wiki content-note slug referenced by the document."""

    @property
    def labels(self) -> set[str]:
        return {n.label for n in self.nodes if n.label}

    @property
    def by_label(self) -> dict[str, Node]:
        return {n.label: n for n in self.nodes if n.label}
