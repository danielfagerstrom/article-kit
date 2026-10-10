r"""A shared-library statement has one home (check 15; docs/LINKAGE.md rule 15).

The shared library has no blueprint of its own (hub ADR-0026, amended 2026-10-10): a
statement's prose lives in its **home**, the blueprint node of the article that first needed
it, and a later article cites the home instead of stating the lemma again. The library says
where each module's home is in its `site/library/data.json` (`scale-space-lean`, Q-0391):
per module a `home` of kind `home` (an article and its labels), `none` (standard material no
blueprint states) or `owed` (a home is expected and not yet written); per declaration its
module. This module reads that record and classifies every node whose `\lean{}` names one of
the library's declarations.

**The record is read at the pin**, the way an `include` line and a qualified `\ledger{}` are
(trust.py): `git show <rev>:site/library/data.json` in the checkout of each package the
article's `lake-manifest.json` pins, never the working tree. A package without the file is
not a shared library for this check; a file whose modules carry no `home` predates the
record, and nothing is checked against it. `--library-record PATH` reads a record from a
file instead, standing for the package its `source_dir` names: for a run against a library
revision no article pins yet, and for tests.

**Tagging is not always stating.** `lem:isotropic-marginal-family` (Paper VII) tags
`ScaleSpace.CascadeFamily` because it constructs one; `def:cascade-family` (Paper V) is the
definition's home. What tells the two apart is the citation the author writes, not a guess
from the node: `\statedin{<article>:<label>}` says "this node uses that statement, which is
stated there", `\restates{<article>:<label>}` says "this node repeats it", and only the
second is compared with the home's text. The kinds (a definition node against a claim, a
structure against a theorem) are read only to word the advisory for a node that carries
neither.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from . import trust
from .config import Config
from .model import Blueprint, Node
from .parse_latex import blueprint_nodes

RECORD_PATH = "site/library/data.json"
ENV_RECORD = "LINKAGE_LIBRARY_RECORD"
ENV_ARTICLE = "LINKAGE_LIBRARY_ARTICLE"
# Where a required article's blueprint starts, relative to its repository root: the
# framework's default `paths.blueprint`, which an export ships unchanged.
HOME_BLUEPRINT = "blueprint/src/content.tex"

# `[<article>:]<label>[@<sha12>]`. A label carries a colon of its own (`def:cascade-family`),
# so the article is whatever precedes the label, not whatever precedes the first colon.
REF_RE = re.compile(
    r"^(?:(?P<article>[^:@\s]+):)?(?P<label>[A-Za-z]+:[^:@\s]+)(?:@(?P<sha>[0-9a-f]{12}))?$")

_THEOREM_KINDS = ("theorem", "lemma")


@dataclass(frozen=True)
class Ref:
    article: str | None
    """The home's article as written (`line`, `line/cone`); None for this article."""
    label: str
    sha: str | None = None
    """The `shared_sha` of the home's statement a `\\restates` was written against."""

    def member(self, me: str) -> str:
        return _member(self.article) if self.article else me


def parse_ref(ref: str) -> Ref | None:
    m = REF_RE.match(ref)
    return Ref(m["article"], m["label"], m["sha"]) if m else None


def _member(article: str) -> str:
    """The constellation member of a home's article: `line` for `line/cone`. One repository
    holds a member's modules under one blueprint, so labels are unique per member."""
    return article.split("/", 1)[0]


@dataclass
class Record:
    """One shared library's `data.json`, reduced to what this check reads."""
    package: str
    source: str
    """Where it was read from, as the summary prints it."""
    homes: dict[str, dict] = field(default_factory=dict)
    """module -> its `home` table."""
    decls: dict[str, tuple[str, str]] = field(default_factory=dict)
    """declaration name -> (module, kind)."""


@dataclass
class Loaded:
    records: list[Record] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    """Lines for the summary: a library without a record, a record that predates `home`."""


def _record(package: str, source: str, data: object) -> Record | None:
    """None when the file is not a record that carries homes."""
    if not isinstance(data, dict) or not isinstance(data.get("modules"), dict):
        return None
    homes = {name: m["home"] for name, m in data["modules"].items()
             if isinstance(m, dict) and isinstance(m.get("home"), dict)}
    if not homes:
        return None
    decls = {d["name"]: (d.get("module", ""), d.get("kind", ""))
             for d in data.get("declarations", ())
             if isinstance(d, dict) and d.get("name")}
    return Record(package, source, homes, decls)


def load(cfg: Config, override: Path | None = None) -> Loaded:
    """The record of every required package that carries one at its pinned revision."""
    out = Loaded()
    replaced: str | None = None
    if override is not None:
        try:
            data = json.loads(override.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            out.notes.append(f"cannot read the library record {override}: {e}")
            data = None
        if data is not None:
            package = str(data.get("source_dir") or override.stem) \
                if isinstance(data, dict) else override.stem
            rec = _record(package, f"{override} (given by path, not read at the pin)", data)
            if rec is None:
                out.notes.append(f"{override} carries no module `home`: it predates the "
                                 "record of homes, and nothing is checked against it")
            else:
                out.records.append(rec)
            replaced = package
    found = trust.manifest_packages(cfg)
    if found is None:
        return out
    pkgs, pkg_dir = found
    without: list[str] = []
    for name, entry in pkgs.items():
        if name == replaced or entry.get("type", "git") != "git" or not entry.get("rev"):
            continue
        repo = pkg_dir / name
        if not repo.is_dir():
            continue
        at = f"{name} @ {entry.get('inputRev') or entry['rev'][:12]} ({entry['rev'][:12]})"
        try:
            text = trust.read_at(repo, entry["rev"], RECORD_PATH)
        except OSError:
            # Not a shared library for this check.
            if name in cfg.lean_packages:
                without.append(at)
            continue
        try:
            data = json.loads(text)
        except ValueError as e:
            out.notes.append(f"{at}: {RECORD_PATH} is not readable JSON ({e})")
            continue
        rec = _record(name, at, data)
        if rec is None:
            out.notes.append(f"{at}: the pinned library predates the record of homes (its "
                             f"{RECORD_PATH} has no module `home`), and nothing is checked "
                             "against it")
        else:
            out.records.append(rec)
    if without and not out.records and not out.notes:
        # Said aloud only when the article names shared packages (`paths.lean_packages`)
        # and none of them has a record: silence there would read as "clean".
        out.notes.append(f"no shared package carries {RECORD_PATH} at its pinned revision "
                         f"({', '.join(without)}): there is no record of homes, and nothing "
                         "is checked")
    return out


# --- the home's text, where it is reachable -------------------------------------------------


def _expand_at(repo: Path, commit: str, path: str) -> str:
    r"""`parse_latex.expand_inputs` over `git show`: a blueprint entry file of a pinned
    package with its `\input{}`s inlined. Raises `OSError` when a file is absent there."""
    inp = re.compile(r"^\s*\\input\{([^}]+)\}")
    out = []
    for line in trust.read_at(repo, commit, path).splitlines(keepends=True):
        m = inp.match(line)
        if m and not line.lstrip().startswith("%"):
            inc = m.group(1) if m.group(1).endswith(".tex") else m.group(1) + ".tex"
            out.append(_expand_at(repo, commit, str(PurePosixPath(path).parent / inc)))
        else:
            out.append(line)
    return "".join(out)


class _Reach:
    """The blueprints of the packages this article requires, each parsed once, at its pin.

    A home in another article is reachable when a required package ships that article's
    blueprint: an export does, under `blueprint/src`. The record names a home by article and
    the manifest names a package by its Lake name, and nothing maps one to the other (an
    export carries no `linkage.toml`), so the node is looked up by label in every required
    package that has a blueprint, and the finding says which package it was read from. An
    article requires only its predecessors, which keeps a chance match of labels unlikely;
    a home in an article this one does not require is not reachable, and is said to be
    uncompared.
    """

    def __init__(self, cfg: Config, skip: set[str]) -> None:
        self.cfg = cfg
        self.skip = skip
        self._nodes: list[tuple[str, dict[str, Node]]] | None = None

    def _load(self) -> list[tuple[str, dict[str, Node]]]:
        out: list[tuple[str, dict[str, Node]]] = []
        found = trust.manifest_packages(self.cfg)
        if found is None:
            return out
        pkgs, pkg_dir = found
        for name, entry in pkgs.items():
            repo = pkg_dir / name
            if (name in self.skip or entry.get("type", "git") != "git"
                    or not entry.get("rev") or not repo.is_dir()):
                continue
            try:
                tex = _expand_at(repo, entry["rev"], HOME_BLUEPRINT)
            except OSError:
                continue
            at = f"{name} @ {entry.get('inputRev') or entry['rev'][:12]}"
            out.append((at, {n.label: n for n in blueprint_nodes(tex, self.cfg) if n.label}))
        return out

    def find(self, label: str) -> tuple[str, Node] | None:
        if self._nodes is None:
            self._nodes = self._load()
        for at, by_label in self._nodes:
            if label in by_label:
                return at, by_label[label]
        return None


# --- the check ------------------------------------------------------------------------------


@dataclass
class Result:
    advisory: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


def _first_difference(mine: str, home: str, width: int = 72) -> str:
    i = next((k for k in range(min(len(mine), len(home))) if mine[k] != home[k]),
             min(len(mine), len(home)))
    return (f"differs from the home after {i} chars\n"
            f"             here : {mine[i:i + width]}\n"
            f"             home : {home[i:i + width]}")


def check(bp: Blueprint, cfg: Config, loaded: Loaded, article: str | None = None) -> Result:
    """Classify every node that tags a shared-library declaration. Advisory throughout."""
    from .checks import uses_paths  # checks imports this module

    res = Result(notes=list(loaded.notes))
    me = _member(article or cfg.library_article or cfg.slug)
    counts = dict.fromkeys(
        ("home", "cited", "standard", "owed", "uncited", "restated", "verbatim", "tracked",
         "differing", "uncompared", "unresolved"), 0)
    res.stats = {"article": me, "records": [r.source for r in loaded.records], **counts}
    if not loaded.records:
        return res
    s = res.stats
    by_label = bp.by_label
    known_homes = {(_member(h["article"]), lab)
                   for r in loaded.records for h in r.homes.values()
                   if h.get("kind") == "home" for lab in h.get("labels", ())}
    reach = _Reach(cfg, skip={r.package for r in loaded.records})
    owed: dict[tuple[str, str], list[str]] = {}

    for n in bp.nodes:
        if not n.label:
            continue
        refs: list[tuple[str, Ref]] = []
        for macro, raw in [("statedin", r) for r in n.stated_in] + \
                          [("restates", r) for r in n.restates]:
            ref = parse_ref(raw)
            if ref is None:
                res.advisory.append(
                    f"[home]   {n.label}: \\{macro}{{{raw}}} is not `[<article>:]<label>`"
                    + ("`[@<sha12>]`" if macro == "restates" else "")
                    + " (LINKAGE.md rule 15)")
                s["unresolved"] += 1
            elif (ref.member(me), ref.label) not in known_homes:
                # "Resolves" means the record knows the target as a home; a label that
                # merely exists somewhere is `\uses`' business, not this macro's.
                res.advisory.append(
                    f"[home]   {n.label}: \\{macro}{{{raw}}} does not resolve -- the "
                    f"library's record names no home {ref.member(me)}:{ref.label}")
                s["unresolved"] += 1
            else:
                refs.append((macro, ref))
        cited = {(ref.member(me), ref.label) for _, ref in refs}

        # One classification per (node, home), however many declarations of however many
        # modules with that home the node tags.
        targets: dict[tuple[str, tuple[str, ...]], list[tuple[str, str]]] = {}
        standard = False
        for d in n.lean:
            for rec in loaded.records:
                if d not in rec.decls:
                    continue
                module, kind = rec.decls[d]
                home = rec.homes.get(module, {})
                if home.get("kind") == "none":
                    standard = True
                elif home.get("kind") == "owed":
                    owed.setdefault((rec.package, module), []).append(n.label)
                elif home.get("kind") == "home":
                    key = (home["article"], tuple(home.get("labels", ())))
                    targets.setdefault(key, []).append((d, kind))
        s["standard"] += standard
        reached: set[str] | None = None
        for (art, labels), decls in targets.items():
            same = _member(art) == me
            if same and n.label in labels:
                s["home"] += 1
                continue
            if cited & {(_member(art), lab) for lab in labels}:
                s["cited"] += 1
                continue
            if same:
                # Inside one blueprint the citation already exists: a `\uses` edge to the
                # home, direct or through other nodes, as rule 14 reads an interface node.
                if reached is None:
                    reached = set(uses_paths(n.label, by_label))
                if reached & set(labels):
                    s["cited"] += 1
                    continue
            s["uncited"] += 1
            where = ", ".join(f"{art}:{lab}" for lab in labels)
            first = f"{art}:{labels[0]}" if labels else art
            tags = ", ".join(f"\\lean{{{d}}}" for d, _ in decls[:3]) + (
                f", +{len(decls) - 3} more" if len(decls) > 3 else "")
            is_claim = n.kind in cfg.statement_kinds
            states = any((kind in _THEOREM_KINDS) == is_claim for _, kind in decls)
            if states:
                res.advisory.append(
                    f"[home]   {n.label}: tags {tags}, whose home is {where}, and states it "
                    f"again unmarked -- cite the home and drop the statement "
                    f"(\\statedin{{{first}}}), or mark the repetition "
                    f"(\\restates{{{first}}}) so that it is compared with the home "
                    "(LINKAGE.md rule 15)")
            else:
                res.advisory.append(
                    f"[home]   {n.label}: uses {tags}, whose home is {where}, without "
                    f"citing it -- add \\statedin{{{first}}}"
                    + (f" or a \\uses{{{labels[0]}}} edge" if same and labels else "")
                    + " (LINKAGE.md rule 15)")

        # A marked restatement is compared with the home's text where that is reachable.
        for macro, ref in refs:
            if macro != "restates":
                continue
            s["restated"] += 1
            name = f"{ref.member(me)}:{ref.label}"
            if ref.member(me) == me:
                got = ("this blueprint", by_label[ref.label]) if ref.label in by_label else None
            else:
                got = reach.find(ref.label)
            if got is None:
                s["uncompared"] += 1
                res.advisory.append(
                    f"[home]   {n.label}: restates {name} -- uncompared: the home's text is "
                    "not reachable (no package this article requires ships that node at "
                    "its pinned revision)")
                continue
            at, home_node = got
            if n.shared_statement == home_node.shared_statement:
                s["verbatim"] += 1
            elif ref.sha == home_node.shared_sha:
                s["tracked"] += 1
            elif ref.sha:
                s["differing"] += 1
                res.advisory.append(
                    f"[home]   {n.label}: the home {name} ({at}) changed since this "
                    f"restatement was pinned to it -- re-read it against the home, then pin "
                    f"\\restates{{{name}@{home_node.shared_sha}}}")
            else:
                s["differing"] += 1
                res.advisory.append(
                    f"[home]   {n.label}: restates {name} ({at}) and "
                    + _first_difference(n.shared_statement, home_node.shared_statement)
                    + f"\n             if it is meant to differ, pin it: "
                      f"\\restates{{{name}@{home_node.shared_sha}}}")

    for (package, module), labels in sorted(owed.items()):
        rec = next(r for r in loaded.records if r.package == package)
        home = rec.homes[module]
        s["owed"] += len(set(labels))
        res.advisory.append(
            f"[home]   {package}.{module}: a home is owed by {home.get('article', '?')} "
            f"({home.get('missing') or 'no reason recorded'}); tagged here by "
            f"{', '.join(dict.fromkeys(labels))}")
    return res


def summary(stats: dict) -> str | None:
    """The line `linkage check` prints; None when no record with homes was read."""
    if not stats.get("records"):
        return None
    s = stats
    line = (f"Library homes ({'; '.join(s['records'])}; this article is `{s['article']}`): "
            f"{s['home']} home(s), {s['cited']} citation(s), {s['uncited']} uncited use(s); "
            f"{s['standard']} node(s) on standard material, {s['owed']} on a module whose "
            "home is owed")
    if s["restated"]:
        line += (f"; {s['restated']} marked restatement(s): {s['verbatim']} verbatim, "
                 f"{s['tracked']} tracked by sha, {s['differing']} to re-read, "
                 f"{s['uncompared']} uncompared")
    if s["unresolved"]:
        line += f"; {s['unresolved']} citation(s) that do not resolve"
    return line + " (LINKAGE.md rule 15)."
