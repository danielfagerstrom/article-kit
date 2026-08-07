"""The linkage checks — blueprint <-> Lean <-> ledger <-> paper.

The blueprint is the source of truth. Each statement node carries a canonical label, a
\\lean{} pointer (with \\leanok / \\notready), \\ledger{} grounding for [A] nodes, and
\\notes{} for its wiki content note. This module verifies the edges that live *inside one
article repository*.

  FATAL (exit 1 if any fail)
    1. every \\leanok node's \\lean{Decl} names a declaration that exists in the Lean sources
    2. every \\ledger{AXX} (and legacy "ledger AXX" prose) resolves to an AXIOMS.md entry
    3. every paper "% shared with blueprint <label>" names a real blueprint statement label
    4. every \\command in a statement/proof is render-safe: defined in the article's macros
       or vetted in its render allowlist (the clean-render gate — pandoc silently DROPS
       unknown commands, argument and all, so this must be caught source-side)
    5. every statement node declares \\statusT or \\statusA (the hub's confidence grading
       keys on the projected status)
    6. every \\ledger-referenced AXIOMS.md entry carries a **Cite:** line (the manifest
       projects each entry's primary citekey + page anchor)
    7. every \\statusA node declares its assignment -- a "\\textbf{Assignment.}" clause in
       its status annotation naming at least one ledger entry (ADR-0011)
    8. no \\leanok node reaches, through the transitive \\uses closure, a [T] statement node
       that is proved nowhere -- neither \\leanok nor carrying a blueprint proof of record
       (the dependency invariant; [A] nodes and definitions are exempt as targets, but the
       fatal walk does traverse *through* [A] nodes: an [A] node's own statement may not be
       phrased in terms of an unproved one either)

  ADVISORY (reported, non-fatal)
    - a *labelled* paper statement that shares a blueprint node but uses a different label
      (rename to the blueprint label for true single-sourcing). Prose that merely references
      a blueprint node -- nearest preceding label is a section, not a statement -- is a valid
      weaker link and is not advised.
    - a \\leanok node with no \\lean{}, or a node marked both \\leanok and \\notready
    - a statement reached by a \\leanok node that is proved on paper but not in Lean: a
      formalisation debt (permitted -- ADR-0010 rule 2), and the list to read when choosing
      what to formalise next. Its dependent count stops at [A] nodes, unlike the fatal walk
      above -- a node that reaches the statement only through a cited interface would gain
      nothing from formalising it -- and both counts are printed

The wiki edge (\\notes{slug} <-> a Notes content note) is cross-repo; it is checked only
when a vault path is supplied.

See docs/LINKAGE.md for the spec this enforces.
"""
from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from .config import Config
from .model import Blueprint, LedgerEntry, Node, PaperMarker
from .render import unknown_commands

# ADR-0011: an [A] node declares, in its status annotation, what its citation carries and
# what it does not. The marker is fixed so the checker can find it; the clause after it must
# name at least one ledger entry, since a declaration that names nothing declares nothing.
ASSIGNMENT_MARKER = r"\textbf{Assignment.}"


@dataclass
class Findings:
    fatal: list[str] = field(default_factory=list)
    advisory: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.fatal


# --- The dependency invariant (check 8; docs/LINKAGE.md rule 8) -------------------------
#
# What a \leanok node means to a reader -- and to the hub, which grades a note
# `confidence: verified` off the projected flag -- is "this is proved". That claim is only
# as good as what the node rests on, so the structural property behind it is: nothing a
# proved node depends on may be *ours and unproved*, i.e. a statement of our own with no
# argument anywhere.
#
# Two exemptions, both principled rather than pragmatic. **[A] nodes** are the trust
# boundary itself: they are accepted on a page-anchored citation, reviewed in AXIOMS.md,
# and depending on one is the whole point of the "verified core, axiomatized analysis"
# split. **Definitions** are vocabulary, not claims; a proved node legitimately names an
# unformalised definition.
#
# And one distinction the naive form of this check gets wrong -- it produced sixteen false
# hits when prop:conservative went [A] \leanok -> [T] \notready while *gaining* a proof of
# record. "Not \leanok" is not "unproved": ADR-0010 rule 2 permits a node whose blueprint
# proof is complete but which Lean does not state (Lean models symbols where the proof needs
# operators, or formalisation is simply pending). Depending on such a node is a *proof debt*,
# reported as an advisory, not a defect. Only a node with no argument anywhere -- no \leanok,
# no proof environment -- is a violation.
#
# What the checker cannot do is judge whether a proof of record is a real proof; that is the
# blueprint's register rule ("see Lean" is not a proof), enforced by review. It prints the
# proof's size so a stub is visible in the advisory.
#
# The two walks differ, on purpose (2026-07-31). The FATAL walk traverses *through* [A] nodes:
# it is the strictly stronger reading, and it catches the case where an [A] node's own
# STATEMENT is phrased in terms of an unproved node. Not hypothetical -- [A] nodes do \uses our
# own nodes (pre-split thm:covariant-lamperti: \uses{def:covariant-memory,thm:memory-family}),
# and the A15 split happened because that node had absorbed an unproved clause of ours.
# The ADVISORY walk stops at [A]. It answers a different question -- "which proved nodes would
# gain if this statement were formalised?" -- and a node that reaches the statement only
# through an [A] interface would gain nothing: its trust already passes through the ledger at
# that point, and whether that is sound is AXIOMS.md's review, not a formalisation task. So
# counting it inflates the number and points formalisation effort at the wrong place. Both
# numbers are printed, because the gap is itself informative: it says how much of the debt is
# already covered by an axiom.


def is_unproved_statement(node: Node, cfg: Config) -> bool:
    """Ours and unproved: a [T] statement with no Lean proof and no proof of record."""
    return (
        node.kind in cfg.statement_kinds
        and node.status == "T"
        and not node.leanok
        and not node.proof_of_record()
    )


def is_paper_proved_statement(node: Node, cfg: Config) -> bool:
    """Ours and proved on paper: a [T] statement Lean does not prove but the blueprint does."""
    return (
        node.kind in cfg.statement_kinds
        and node.status == "T"
        and not node.leanok
        and bool(node.proof_of_record())
    )


def uses_paths(
    start: str, by_label: dict[str, Node], stop_at_axiom: bool = False
) -> dict[str, list[str]]:
    """Shortest \\uses path from `start` to each label transitively reachable from it.

    Breadth-first, so the reported path is a shortest one; the visited set makes the walk
    terminate whatever the edges do. The blueprint DAG has no cycles today, but a naive
    recursion would hang rather than fail on the day one is introduced by mistake.

    `stop_at_axiom` closes the walk at the trust boundary: an `[A]` node reached along the
    way is recorded but not expanded, so the result holds exactly what `start` depends on
    *ahead of* the ledger. `start` itself is expanded whatever its status — an `[A]` node's
    own `\\uses` are the labels its statement is phrased in terms of, which is a real
    dependency of that node even though nothing above it inherits it. See the two-walk note
    above, and docs/LINKAGE.md rule 8."""
    paths: dict[str, list[str]] = {}
    seen = {start}
    queue = deque([start])
    while queue:
        cur = queue.popleft()
        if stop_at_axiom and cur != start and getattr(by_label.get(cur), "status", None) == "A":
            continue
        node = by_label.get(cur)
        for nxt in (node.uses if node else []):
            if nxt in seen:
                continue
            seen.add(nxt)
            paths[nxt] = paths.get(cur, [start]) + [nxt]
            queue.append(nxt)
    return paths


def _who(reachers: list[str]) -> str:
    shown = ", ".join(reachers[:4])
    return shown + (f", +{len(reachers) - 4} more" if len(reachers) > 4 else "")


def run(
    bp: Blueprint,
    cfg: Config,
    lean_names: set[str],
    ledger: dict[str, LedgerEntry],
    markers: list[PaperMarker],
    safe_commands: set[str],
    wiki: Path | None = None,
) -> Findings:
    """Every in-repo edge, plus the wiki edge when a vault path is given."""
    f = Findings()
    fatal, advisory = f.fatal, f.advisory
    nodes = bp.nodes

    # 1. Lean decls of proved nodes exist
    for n in nodes:
        if n.leanok and not n.lean:
            advisory.append(f"[lean]   node '{n.label}' is \\leanok but has no \\lean{{}}")
        if n.leanok and n.notready:
            advisory.append(f"[lean]   node '{n.label}' marked both \\leanok and \\notready")
        if not n.leanok:
            continue  # \notready nodes may not have a Lean decl yet
        for d in n.lean:
            last = d.split(".")[-1]
            if last not in lean_names:
                fatal.append(
                    f"[lean]   {n.label}: \\lean{{{d}}} not declared in {cfg.lean.name}/"
                )

    # 4. the clean-render gate: every command in a statement/proof is render-safe
    for n in nodes:
        for part, src in (("statement", n.statement), ("proof", n.proof)):
            if not src:
                continue
            for c in unknown_commands(src, safe_commands):
                fatal.append(
                    f"[render] {n.label or n.env}: \\{c} in {part} is not render-safe "
                    f"— add a \\newcommand to {cfg.macros.name} or vet it in "
                    f"{cfg.allowlist.name}"
                )

    # 2. ledger refs resolve / 6. and carry a citation
    for a in sorted(bp.ledger_refs):
        entry = ledger.get(a)
        if entry is None:
            fatal.append(f"[ledger] {a}: no '## {a}' entry in {cfg.axioms.name}")
        elif not entry.has_cite_line:
            # the manifest projects each entry's primary citation — a referenced entry
            # without a **Cite:** line would emit an unverifiable bare id
            fatal.append(f"[ledger] {a}: no '**Cite:**' line in {cfg.axioms.name} "
                         "(format: '**Cite:** @citekey — anchor')")

    # 5. every node declares its [T]/[A] status — the hub's grading keys on it
    for n in nodes:
        if n.label and n.status is None:
            fatal.append(f"[status] {n.label}: no \\statusT/\\statusA — every statement "
                         "node must declare one")

    # 7. every [A] node declares its assignment (ADR-0011). The checker can require that the
    # judgement be written; it cannot make it, and it cannot tell a wrong declaration from a
    # right one. What it removes is the silent case -- an [A] statement whose split between
    # citation and [T] exists only in someone's head, which is how all three defects of the
    # 2026-07 ledger passes survived.
    for n in nodes:
        if n.status != "A" or not n.label:
            continue
        head, marker, clause = n.status_note.partition(ASSIGNMENT_MARKER)
        if not marker:
            fatal.append(
                f"[assign] {n.label}: [A] node with no '{ASSIGNMENT_MARKER}' clause in its "
                "status annotation -- say what the citation carries and what it does not "
                "(ADR-0011; LINKAGE.md rule 7)"
            )
        elif not re.search(cfg.ledger_key, clause):
            fatal.append(
                f"[assign] {n.label}: the Assignment clause names no ledger entry -- it must "
                "say which entry carries which part of this statement (ADR-0011)"
            )

    # 8. the dependency invariant: no proved node rests on a statement proved nowhere.
    # Held by hand all through July 2026 and by no control; this is that control. Fatal
    # because it is the one structural property the trust story rests on -- and because a
    # violation is non-local: adding a \uses edge in one node can break the guarantee of a
    # \leanok node nobody touched, which is precisely the kind of defect a person does not
    # re-derive by reading a diff.
    by_label = bp.by_label
    unproved = {lab for lab, n in by_label.items() if is_unproved_statement(n, cfg)}
    on_paper = {lab for lab, n in by_label.items() if is_paper_proved_statement(n, cfg)}
    # target -> the \leanok nodes reaching it, and a shortest path to it. The fatal buckets
    # come from the through-[A] walk; `direct_on_paper` repeats the walk with the trust
    # boundary closed, giving the advisory's headline count (see the two-walk note above).
    reached_unproved: dict[str, tuple[list[str], list[str]]] = {}
    reached_on_paper: dict[str, tuple[list[str], list[str]]] = {}
    direct_on_paper: dict[str, list[str]] = {}
    for n in sorted(nodes, key=lambda n: n.label or ""):
        if not n.leanok or not n.label:
            continue
        for tgt, path in uses_paths(n.label, by_label).items():
            bucket = (reached_unproved if tgt in unproved
                      else reached_on_paper if tgt in on_paper else None)
            if bucket is None:
                continue
            reachers, best = bucket.setdefault(tgt, ([], path))
            reachers.append(n.label)
            if len(path) < len(best):
                bucket[tgt] = (reachers, path)
        for tgt in uses_paths(n.label, by_label, stop_at_axiom=True):
            if tgt in on_paper:
                direct_on_paper.setdefault(tgt, []).append(n.label)

    for tgt, (reachers, path) in sorted(reached_unproved.items()):
        fatal.append(
            f"[depend] {tgt} is proved nowhere ([T], no \\leanok, no proof of record) but "
            f"{len(reachers)} \\leanok node(s) depend on it: {_who(reachers)} "
            f"(path: {' -> '.join(path)}) -- prove it, write its blueprint proof of record, "
            f"or drop the \\uses edge (LINKAGE.md rule 8)"
        )
    for tgt, (reachers, _path) in sorted(reached_on_paper.items()):
        direct = sorted(direct_on_paper.get(tgt, []))
        head = (
            f"[depend] {tgt}: proved on paper only "
            f"({len(by_label[tgt].proof_of_record())}-char proof, not \\leanok), reached by "
            f"{len(direct) if direct else 'no'} \\leanok node(s) ahead of the trust boundary "
            f"({len(reachers)} counting paths through an [A] interface)"
        )
        advisory.append(
            f"{head}: {_who(direct)} -- a formalisation debt (permitted, ADR-0010 rule 2), not a "
            f"defect; formalising it would discharge the debt for those {len(direct)}"
            if direct else
            f"{head}: {_who(sorted(reachers))} -- every dependent reaches it behind a cited "
            "interface, so formalising it discharges no debt today; whether the interface is "
            "sound is AXIOMS.md's review (permitted, ADR-0010 rule 2)"
        )

    # 3. paper shared statements
    labels = bp.labels
    for mk in markers:
        if mk.blueprint_label not in labels:
            fatal.append(
                f"[paper]  {mk.file}: 'shared with blueprint {mk.blueprint_label}' but no such "
                "blueprint label"
            )
        elif (mk.nearest_label != mk.blueprint_label and mk.nearest_label
              and cfg.is_statement_label(mk.nearest_label)):
            advisory.append(
                f"[paper]  {mk.file}: labelled statement '{mk.nearest_label}' shares blueprint "
                f"'{mk.blueprint_label}' (rename to the blueprint label for single-sourcing)"
            )

    # optional: wiki notes
    if wiki:
        for slug in sorted(bp.notes_slugs):
            if not list(wiki.rglob(slug + ".md")):
                fatal.append(f"[notes]  \\notes{{{slug}}}: no {slug}.md under {wiki}")

    f.stats = {
        "nodes": len(nodes),
        "leanok": sum(1 for n in nodes if n.leanok),
        "ledger_refs": len(bp.ledger_refs),
        "paper_shared": len(markers),
        "reached_unproved": len(reached_unproved),
        "reached_on_paper": len(reached_on_paper),
        "unproved": sorted(unproved),
    }
    return f
