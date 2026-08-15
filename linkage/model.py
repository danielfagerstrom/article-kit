"""The node model — the intermediate representation every other stage speaks.

This is the seam that makes the rest of the package format-independent. A parser
(`parse_latex`) turns *one* blueprint dialect into `list[Node]`; `checks`, `manifest`
and `demand` consume `Node` and never look at LaTeX. Adding a second dialect means
adding a second parser, not touching the checks.

Field names are deliberately the ones the manifest projects, so the emitter is a
near-transliteration and the wire format cannot drift from the model by accident.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


def sha12(s: str) -> str:
    """The short digest the manifest publishes and the paper marker pins."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]


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

    shared_statement: str = ""
    """The statement reduced to what the paper is supposed to share: content before the
    [T]/[A] status tag, with the environment word the paper writes before a `\\ref`
    removed. A comparison key for check 3, never projected — the hub reads
    `statement`/`statement_sha` and those must not move."""

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

    @property
    def shared_sha(self) -> str:
        """Digest of `shared_statement` — what a paper marker pins itself to.

        Deliberately not `statement_sha`: that one covers the formalisation notes as
        well, so editing a note would report the paper as stale when nothing the paper
        shares has moved.
        """
        return sha12(self.shared_statement)

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
    """A `% shared with blueprint <label>[@sha][, <label>[@sha]]…` marker.

    **Several labels, because the relationship is n:1.** The blueprint is deliberately
    finer-grained than the paper: it splits statements to make Lean progress legible,
    and the paper renders the pieces as one readable statement. In the first article 25
    of 87 nodes are marked by no paper marker at all, being halves of something the
    paper states whole. A one-label marker cannot say that, so it reported five correct
    statements as drifted.

    **And an optional pinned sha per label**, which is what makes the split case
    checkable at all. A merged statement cannot be compared byte-for-byte — the paper
    rewrites when it merges — but it *can* record which version of each node it was
    written against, so that a later blueprint edit shows up as stale rather than
    silently diverging. That matters because the blueprint changes for two different
    reasons: splitting (the paper stays correct) and new mathematical learning (the
    paper must follow). Only the sha distinguishes them.
    """

    file: str
    blueprint_labels: list[str]
    statement_label: str | None
    """The `\\label{}` *inside* the statement the marker marks — label equality with
    `blueprint_label` is the target form. Read forwards, not backwards: the marker is a
    comment ABOVE its environment, so the nearest *preceding* label is the previous
    statement's, and comparing against that reported 47 of 62 markers as mismatched when
    every one of them in fact matched."""

    line: int = 0
    """1-indexed line of the marker, so a drift report can be opened."""

    pinned: dict[str, str] = field(default_factory=dict)
    """label -> the `shared_sha` the paper was written against, for labels that carry
    one. Empty when the marker is unpinned."""

    shared_statement: str | None = None
    """The paper's own statement under the same reduction applied to the blueprint node.
    None when no statement environment follows the marker — itself a finding."""

    raw: str = ""
    """The marker's own text, so `--pin-shared` can rewrite it in place."""

    @property
    def blueprint_label(self) -> str:
        """The first label — the node the paper's statement is principally shared with."""
        return self.blueprint_labels[0]


@dataclass
class ControlChar:
    """One illegal control character in a source file."""

    path: str
    """Repo-relative, so the message is the same wherever the checker was invoked."""
    line: int
    char: int
    """The code point, reported as U+XXXX — naming it is half the diagnosis."""
    context: str
    """Printable rendering of the surrounding bytes."""


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
