r"""The inferred half of the `\uses` edge: what a node's Lean declaration actually cites.

`checks.py` verifies the **declared** dependency graph — the `\uses{}` edges an author
wrote, and what they imply (check 8: no `\leanok` node reaches a `[T]` statement proved
nowhere). Nothing verified that the declared graph resembles the *real* one. A blueprint
node says "this is proved, and here is what it rests on"; the Lean declaration it points at
knows the second half for a fact, and the two were never compared.

This module computes the second half and diffs it both ways. It is **advisory and audit
only**: authorship stays blueprint-first — the LaTeX is the deliverable, `\uses{}` is written
by the author for the reader and for leanblueprint's graph, and nothing here ever proposes,
still less writes, a `\uses{}` edge. The output is a worklist for a person.

**The two routes.** An exact answer needs Lean's environment, which needs a build, which this
package deliberately does not have (`manifest.yml` runs on source text alone, offline, with no
elan). So:

*export* — if the article carries a `lean-uses.json` export (`paths.lean_uses`, written by a
meta program that walks each declaration's `ConstantInfo.value` in a built environment), that
is read and believed. It is the exact constant set, elaborated: instances, `simp` sets and
notation are all resolved by then.

*source scan* — otherwise the declaration's source text is scanned for identifier tokens, in
the spirit of `.claude/skills/fidelity-review/scripts/f7sweep.py`, which does the coarser
file-level version of this by hand (a `\uses` target whose declaration is not in the Lean
file's transitive *import* closure). Tokens are resolved only against this article's own
declarations, so Mathlib names, tactic names and keywords fall away by not matching. This is
the default route and is what the tests exercise.

**What the source scan cannot see**, i.e. the false positives of the `[declared]` direction:

- a lemma pulled in by a `simp` set (`@[simp]` at the lemma, `simp` at the use site) —
  the use site names nothing;
- a fact used through **notation**, a `macro`/`syntax` expansion, or an `abbrev`;
- an **instance** found by typeclass resolution, which is the whole point of instances;
- anything reached by `omega`, `aesop`, `positivity`, `gcongr`, `fun_prop`, or by
  `exact?`-style automation that elaborates to a name the source never spells;
- defeq unfolding: `rfl` can consume a definition without naming it.

Each of those makes a `\uses{}` label look unsupported when it is used. That is why this
direction is reported, never failed, and why the *export* route exists for an article that
wants the exact answer. The `[inferred]` direction (a declaration cites a node the blueprint
does not) has the opposite profile: a token match is evidence of a real citation, and its own
false positive is a name collision with a Mathlib declaration of the same short name.

**Direct versus transitive, deliberately asymmetric** — the same asymmetry as check 8's two
walks, for the same reason. A `\uses{}` label counts as supported if its declaration is
anywhere in the **transitive** inferred closure: the Lean proof may reach a cited ingredient
through a private helper the blueprint has no node for, and that is not a finding. An
inferred dependency counts as missing only when the node's **transitive `\uses` closure**
does not reach it at all: the blueprint records direct edges, so an indirect dependency is
legitimately absent from `\uses{}`, but a node the blueprint cannot reach by any path is a
route the blueprint does not tell the reader about.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .checks import uses_paths
from .config import Config
from .model import Blueprint, Node

# A Lean identifier: ASCII/Greek head, then word characters, primes and subscripts, with
# dotted components for a fully qualified name. `\w` is unicode-aware in Python, which covers
# the Greek letters Lean sources are full of; subscript digits are category No and are added
# by hand.
_ID = r"[A-Za-z_Ͱ-Ͽᴀ-ᶿ][\w'Ͱ-Ͽ₀-₉]*"
TOKEN_RE = re.compile(rf"{_ID}(?:\.{_ID})*")

DECL_KEYWORDS = ("theorem", "lemma", "def", "abbrev", "structure", "instance", "axiom",
                 "example")
# A declaration head, as `artifacts.DECL_RE` matches it, but line-anchored and keeping the
# keyword: the scan needs to know where one declaration's body ends, not only that a name
# was declared.
DECL_LINE_RE = re.compile(
    r"^\s*(?:@\[[^\]]*\]\s*)?"
    r"(?:(?:private|protected|noncomputable|scoped|local|partial|unsafe)\s+)*"
    r"(?:" + "|".join(DECL_KEYWORDS) + r")\s+(" + _ID + r")")
NAMESPACE_RE = re.compile(r"^\s*namespace\s+(\S+)")
END_RE = re.compile(r"^\s*end\s+(\S+)")

BLOCK_COMMENT_RE = re.compile(r"/-.*?-/", re.S)
LINE_COMMENT_RE = re.compile(r"--[^\n]*")
STRING_RE = re.compile(r'"(?:[^"\\]|\\.)*"')


def strip_noise(text: str) -> str:
    """Lean source with comments and string literals blanked, line structure preserved.

    Blanked rather than removed: the namespace/declaration scan is line-based, so a block
    comment must not swallow the lines it spans.
    """
    def blank(m: re.Match) -> str:
        return re.sub(r"[^\n]", " ", m.group(0))

    text = BLOCK_COMMENT_RE.sub(blank, text)
    text = STRING_RE.sub(blank, text)
    return LINE_COMMENT_RE.sub(blank, text)


@dataclass
class DeclIndex:
    """This article's declarations and what each one's source mentions."""

    module: dict[str, str] = field(default_factory=dict)
    """full declaration name -> the module it is declared in (dotted, `cfg.lean`-relative)."""

    direct: dict[str, set[str]] = field(default_factory=dict)
    """full declaration name -> the full names its own source cites (self excluded)."""

    short: dict[str, set[str]] = field(default_factory=dict)
    """final component -> the full names carrying it, for resolving an unqualified token."""

    def resolve(self, name: str) -> str | None:
        """The full declaration name a `\\lean{}` tag or a source token denotes, if ours.

        Exact match first, then by final component — the same suffix rule the rest of the
        package uses for `\\lean{}` tags (`checks.py` compares `d.split(".")[-1]`), because a
        blueprint tag is written the way a reader would write it and a source token is
        written under whatever `open`/namespace is in scope. Ambiguity (two declarations of
        the same short name in different namespaces) resolves to nothing: guessing would
        invent an edge, which is the one thing an audit must not do.
        """
        if name in self.module:
            return name
        cands = self.short.get(name.split(".")[-1], set())
        return next(iter(cands)) if len(cands) == 1 else None

    def closure(self, start: str) -> set[str]:
        """Everything `start` reaches through `direct`, transitively (start excluded)."""
        seen: set[str] = set()
        stack = [start]
        while stack:
            cur = stack.pop()
            for nxt in self.direct.get(cur, ()):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        seen.discard(start)
        return seen


def scan_lean(cfg: Config) -> DeclIndex:
    """Index every declaration under `cfg.lean`, with the names each one's source cites.

    Build output (`.lake/`) is skipped, so a shared Lake package's declarations are *not*
    indexed: a node whose `\\lean{}` points into one is reported as unlocatable rather than
    silently scored as citing nothing. Whole-file scanning, one pass, no toolchain.
    """
    index = DeclIndex()
    bodies: dict[str, list[str]] = {}
    for f in sorted(cfg.lean.rglob("*.lean")):
        if ".lake" in f.parts:
            continue
        mod = f.relative_to(cfg.lean).with_suffix("").as_posix().replace("/", ".")
        ns: list[str] = []
        cur: str | None = None
        for line in strip_noise(f.read_text(encoding="utf-8")).splitlines():
            if m := NAMESPACE_RE.match(line):
                ns.append(m.group(1))
                cur = None
                continue
            if m := END_RE.match(line):
                if ns and ns[-1] == m.group(1):
                    ns.pop()
                cur = None
                continue
            if m := DECL_LINE_RE.match(line):
                cur = ".".join([*ns, m.group(1)])
                index.module.setdefault(cur, mod)
                index.short.setdefault(cur.split(".")[-1], set()).add(cur)
                bodies.setdefault(cur, []).append(line[m.end(1):])
                continue
            if cur is not None:
                bodies[cur].append(line)

    for name, lines in bodies.items():
        tokens = {t for line in lines for t in TOKEN_RE.findall(line)}
        index.direct[name] = tokens  # resolved below, once every name is known
    for name, tokens in index.direct.items():
        index.direct[name] = {r for t in tokens
                              if (r := index.resolve(t)) is not None and r != name}
    return index


def apply_export(index: DeclIndex, export: dict) -> DeclIndex:
    r"""Replace the scanned `direct` sets with an exported constant map.

    The export is `{"Decl.Name": ["Const.One", …]}` — what a Lean meta program can write out
    of a built environment, where instances, `simp` sets and notation have all been
    elaborated away. Names outside this article are dropped: the audit compares against
    blueprint nodes, and a Mathlib constant maps to no node. An exported declaration this
    package's scan never saw is indexed too (module unknown), so an article may export names
    the source scan cannot locate.
    """
    if not isinstance(export, dict):
        raise ExportError("the export must be a JSON object mapping declaration names to "
                          "the list of constants each one uses")
    for name, consts in export.items():
        if not isinstance(consts, list):
            raise ExportError(f"{name}: expected a list of constant names, got "
                              f"{type(consts).__name__}")
        index.short.setdefault(name.split(".")[-1], set()).add(name)
    for name, consts in export.items():
        index.direct[name] = {r for c in consts
                              if (r := index.resolve(str(c))) is not None and r != name}
    return index


class ExportError(RuntimeError):
    pass


def load_export(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise ExportError(f"{path}: {e}") from e


def build_index(cfg: Config, export: Path | None = None) -> tuple[DeclIndex, str]:
    """The index and the name of the route that produced it, for the report's header."""
    index = scan_lean(cfg)
    path = export or cfg.lean_uses
    if path is not None and path.is_file():
        return apply_export(index, load_export(path)), f"export ({path.name})"
    if export is not None:
        raise ExportError(f"{export}: no such file")
    return index, "source scan"


# --- the audit ---------------------------------------------------------------------------


@dataclass
class Audit:
    advisory: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


def _decl_owner(bp: Blueprint, index: DeclIndex) -> dict[str, str]:
    r"""full declaration name -> the blueprint label whose `\lean{}` claims it.

    First claimant wins, so two nodes tagging one declaration do not make the mapping depend
    on parse order; the duplicate is not this audit's finding to make.
    """
    out: dict[str, str] = {}
    for n in bp.nodes:
        for d in n.lean:
            if (full := index.resolve(d)) is not None and n.label:
                out.setdefault(full, n.label)
    return out


def _node_decls(node: Node, index: DeclIndex) -> tuple[list[str], list[str]]:
    """The node's `\\lean{}` tags, split into (resolved full names, unlocatable tags)."""
    found, missing = [], []
    for d in node.lean:
        (found if (full := index.resolve(d)) is not None else missing).append(full or d)
    return found, missing


def audit(bp: Blueprint, cfg: Config, index: DeclIndex) -> Audit:
    r"""Diff each `\leanok` node's inferred constant closure against its `\uses{}`.

    Four advisories, in the order a reader wants them: the two directions of the diff, then
    the two whole-node flags (see the module docstring for what each direction can get
    wrong).
    """
    a = Audit()
    by_label = bp.by_label
    owner = _decl_owner(bp, index)
    decls: dict[str, list[str]] = {}
    unlocatable: list[str] = []

    audited = [n for n in sorted(bp.nodes, key=lambda n: n.label or "")
               if n.leanok and n.label and n.lean]
    for n in audited:
        found, missing = _node_decls(n, index)
        decls[n.label] = found
        if missing:
            unlocatable.append(n.label)
            a.advisory.append(
                f"[closure] {n.label}: \\lean{{{', '.join(missing)}}} names no declaration "
                f"under {cfg.lean.name}/ that this audit can read — a shared Lake package, "
                f"or a declaration this scan does not parse; its uses are not inferred")

    empty: list[str] = []
    declared_gaps = inferred_gaps = 0
    for n in audited:
        if not decls[n.label]:
            continue
        inferred = set().union(*(index.closure(d) for d in decls[n.label]))
        direct = set().union(*(index.direct.get(d, set()) for d in decls[n.label]))

        # Flag 1: proved, its declarations were read, and they cite nothing of this
        # article's *while the blueprint says the node rests on formalised nodes of ours*.
        # Either the tag points at the wrong declaration, or the proof is carried entirely
        # by automation, or (the case worth catching) the Lean statement is not the one the
        # blueprint node thinks it is. Its per-label lines are suppressed: this is the total
        # version of direction 1 below, and one finding per node beats one per `\uses`
        # target when they have a single cause.
        #
        # "Implausibly empty" needs that second condition. A leaf lemma proved from Mathlib
        # alone cites nothing of ours and is the ordinary case, not a finding; what is
        # implausible is a node whose two accounts of its dependencies -- the blueprint's
        # list and the declaration's body -- have nothing whatever in common.
        formalised_uses = [u for u in n.uses
                           if (un := by_label.get(u)) is not None and un.lean]
        if not inferred and n.kind in cfg.statement_kinds and formalised_uses:
            empty.append(n.label)
            a.advisory.append(
                f"[empty]   {n.label}: \\leanok, but {', '.join(decls[n.label])} cites no "
                f"declaration of this article, while the node \\uses "
                f"{len(formalised_uses)} formalised node(s) ({', '.join(formalised_uses)}) "
                "— check the tag names the intended declaration, and that the proof is not "
                "carried entirely by automation")
            continue

        # Direction 1 (declared, not inferred): a `\uses{}` target whose own declaration is
        # nowhere in the inferred closure. The noisy direction — see the module docstring.
        for u in n.uses:
            un = by_label.get(u)
            if un is None or not un.lean:
                continue  # an [A] or untagged node has no declaration to look for
            targets, _ = _node_decls(un, index)
            if not targets or any(t in inferred for t in targets):
                continue
            declared_gaps += 1
            a.advisory.append(
                f"[declared] {n.label}: \\uses{{{u}}}, but {', '.join(targets)} is not in "
                f"the inferred closure of {', '.join(decls[n.label])} ({len(inferred)} "
                f"declaration(s)) — the blueprint cites it and the Lean proof appears not "
                f"to; a `simp` set, an instance or notation would hide a real use")

        # Direction 2 (inferred, not declared): a declaration this node's Lean proof cites
        # DIRECTLY, owned by a node the blueprint's `\uses` graph cannot reach from here by
        # any path. Indirect inferred uses are not reported: `\uses{}` records direct edges.
        reach = set(uses_paths(n.label, by_label))
        for d in sorted(direct):
            lab = owner.get(d)
            if lab is None or lab == n.label or lab in reach:
                continue
            inferred_gaps += 1
            a.advisory.append(
                f"[inferred] {n.label}: {', '.join(decls[n.label])} cites {d} ({lab}), which "
                f"no \\uses path from {n.label} reaches — add \\uses{{{lab}}} if the "
                f"blueprint proof really rests on it, or record why the routes differ")

    # Flag 2: a lemma nothing depends on, in either graph. Kind `lem` only: a `thm`, `prop`
    # or `cor` that nothing uses is the ordinary shape of a headline result, while a lemma
    # exists to be used — one that is not is either dead weight, a `\uses` edge someone
    # forgot, or a result that has quietly become the headline and should be re-kinded.
    used_labels = {u for n in bp.nodes for u in n.uses}
    cited_decls = set().union(*index.direct.values()) if index.direct else set()
    orphans: list[str] = []
    for n in sorted(bp.nodes, key=lambda n: n.label or ""):
        if n.kind != "lem" or not n.label or n.label in used_labels:
            continue
        mine, _ = _node_decls(n, index)
        if any(d in cited_decls for d in mine):
            continue
        orphans.append(n.label)
        a.advisory.append(
            f"[orphan]  {n.label}: no blueprint node \\uses it"
            + (f" and no declaration cites {', '.join(mine)}" if mine
               else " and it names no Lean declaration")
            + " — an unused lemma, a missing \\uses edge, or a result that has become a "
              "theorem in its own right")

    a.stats = {
        "audited": len(audited),
        "unlocatable": unlocatable,
        "declared_gaps": declared_gaps,
        "inferred_gaps": inferred_gaps,
        "empty": empty,
        "orphans": orphans,
        "declarations": len(index.module),
    }
    return a
