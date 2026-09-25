"""Per-article configuration — `linkage.toml` at the article repo root.

What is configurable and what is not is a deliberate line.

**Configurable:** where the artifacts live, the satellite slug, which environments and
label prefixes count as statements, the ledger-id shape, the pandoc pin. These genuinely
differ between articles.

**Not configurable: the linkage macro names** (`\\ledger`, `\\statusT`, `\\statusA`,
`\\notes`, plus the leanblueprint set `\\lean` / `\\leanok` / `\\uses` / `\\notready`).
They are the *framework's* vocabulary, defined once in `scaffold/blueprint/linkage-macros.tex`
and inputted by every article. Letting an article rename them would make the manifest schema
article-dependent — the hub reads every satellite's manifest with one reader — and would buy
nothing, since the article does not own those macros in the first place. This is a
deliberate narrowing of the original plan, which listed them in `linkage.toml`.
"""
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_NAME = "linkage.toml"

DEFAULT_LICENSE = "cc-by-4.0"
DEFAULT_UPLOAD_TYPE = "publication"
DEFAULT_PUBLICATION_TYPE = "preprint"
DEFAULT_SHARED_NODES = "omit"
DEFAULT_AXIOMS_SECTION = "1.1"

DEFAULT_STATEMENT_ENVS = ("definition", "lemma", "proposition", "theorem", "corollary")
# Label prefixes that denote a statement (as opposed to a section/equation).
DEFAULT_LABEL_PREFIXES = ("thm", "prop", "def", "lem", "cor")
# Of those, the ones that are *claims* — definitions are vocabulary, exempt from check 8.
DEFAULT_STATEMENT_KINDS = ("thm", "prop", "lem", "cor")
DEFAULT_LEDGER_KEY = r"A\d+"
DEFAULT_PANDOC_PIN = "3.10"
DEFAULT_PANDOC_TARGET = "commonmark+tex_math_dollars"


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Boundary:
    r"""The `[boundary]` table: the boundary harness's manifest (`linkage boundary`).

    Absent, `configured` is False and the harness reports nothing — adopting it is a
    per-article decision, so every existing article keeps passing untouched.

    The paths are **not** validated by `load()`. A repository mid-adoption has the table
    before it has the files, and `linkage check` must keep working meanwhile; the harness
    itself reports a missing file, where the message can say what the file is for.
    """
    configured: bool = False
    guard: Path | None = None
    """The Lean file CI elaborates, holding one `#guard_msgs`-pinned `#print axioms` per
    headline declaration."""
    probes: Path | None = None
    """Positive probes: cheap should-hold consequences of the headline results."""
    adversarial: Path | None = None
    """Known-false, in-domain statements kept as isolated `sorry`s."""
    headline: tuple[str, ...] = ()
    """The declarations whose axiom set is pinned per declaration and which each need a
    probe — fully qualified, spelled exactly as the guard file prints them."""
    shadows: dict[str, str] = field(default_factory=dict)
    """Declarations deliberately sharing a name with a standard notion, each mapped to
    what differs. The entry is the review record, so an empty reason is an error."""
    standard_notions_extra: tuple[str, ...] = ()
    """Names this article adds to the standard-notion list (`boundary.STANDARD_NOTIONS`)."""


@dataclass
class Release:
    """`[release]`: what every deposit of this repository says, whichever module it is.

    The creators, the licence and the copyright line are the repository's, not a module's —
    a second module of the same repository does not get a second author list. What differs
    per module (title, keywords, related identifiers) lives in `[[modules]]`.
    """
    creators: tuple[dict[str, str], ...] = ()
    license: str = DEFAULT_LICENSE
    upload_type: str = DEFAULT_UPLOAD_TYPE
    publication_type: str = DEFAULT_PUBLICATION_TYPE
    copyright: str | None = None
    """The copyright line of generated Lean files, e.g. `2026 Daniel Fagerström`; the first
    creator's name with the current year when absent."""


@dataclass
class Module:
    r"""`[[modules]]`: one releasable module of this repository.

    A module is what gets a tag, an export and a DOI: its blueprint chapters, its paper
    directory, the Lean modules its paper names directly, the records that travel with it.
    A single-paper article declares one; `spatial-hemigroup-scale-space` declares three
    (the line paper, module B, module C), which is why every one of these was a constant
    in that repository's `scripts/export-release.py` before the move here (ADR-0001 step 5).
    """
    name: str
    chapters: tuple[str, ...] = ()
    paper: str = "paper"
    """The paper directory, relative to the root — one of `paths.paper`'s entries."""
    tag: str | None = None
    roots: tuple[str, ...] = ()
    r"""Lean modules the paper names directly, exported whatever the `\lean{}` tags say."""
    headline: str | None = None
    r"""The declaration whose `#print axioms` block the paper prints."""
    stem: str | None = None
    """Stem of the PDF at the export's root; `<stem>-<tag>.pdf`."""
    title: str = ""
    repo_url: str = ""
    """The EXPORT repository's URL — never the development repository's."""
    records: str | None = None
    """The module's records directory; the default process account, response plan and
    reviews are read from it."""
    process: str | None = None
    response_plans: tuple[str, ...] = ()
    reviews: str | None = None
    shared_nodes: str = DEFAULT_SHARED_NODES
    keywords: tuple[str, ...] = ()
    related: tuple[str, ...] = ()
    """Related identifiers for the deposit, each `DOI:relation` (Zenodo's relations)."""
    abstract_macros: dict[str, str] = field(default_factory=dict)
    r"""Article macros the plain-text abstract expands, e.g. `Matern = "Matérn"`; a macro
    not named here and taking no argument is dropped."""
    axioms_section: str = DEFAULT_AXIOMS_SECTION
    """The paper section that says what the theorems rest on, named by the export's README."""
    releases: dict[str, dict] = field(default_factory=dict)
    """Per-tag overrides of `chapters`/`paper`/`roots`, for a release whose parameters have
    since moved: `linkage release export --cites <tag>` recomputes *that* release's closure,
    so it must read the parameters as they stood, not today's."""

    def records_path(self, name: str) -> str | None:
        return f"{self.records}/{name}" if self.records else None

    def process_file(self) -> str | None:
        return self.process or self.records_path("PROCESS.md")

    def response_plan_files(self) -> tuple[str, ...]:
        if self.response_plans:
            return self.response_plans
        one = self.records_path("PLAN-review-response.md")
        return (one,) if one else ()

    def reviews_dir(self) -> str | None:
        return self.reviews or self.records_path("reviews")

    def parameters_at(self, tag: str) -> tuple[tuple[str, ...], str, tuple[str, ...]]:
        """(chapters, paper, roots) as they stood at `tag` — the `releases` override where
        the module declares one, today's parameters otherwise."""
        over = self.releases.get(tag, {})
        return (
            tuple(over.get("chapters", self.chapters)),
            over.get("paper", self.paper),
            tuple(over.get("roots", self.roots)),
        )


def module_prefix(tag: str) -> str:
    """The module prefix of a tag: `cone-` for `cone-v0.1`, empty for `v0.1`."""
    head, sep, _ = tag.rpartition("v")
    return head if sep else ""


@dataclass
class Config:
    root: Path
    slug: str

    blueprint: Path
    axioms: Path
    macros: Path
    allowlist: Path
    lean: Path
    papers: tuple[Path, ...]
    r"""The paper directories, in the order `linkage.toml` lists them.

    **A tuple, because one repository can hold several papers.** `paths.paper` takes a
    string or a list of strings; the string form is a one-element tuple, so an article
    that has one paper reads exactly as before. The second form exists because an
    article may publish a line paper and its modules from one repository, each with its
    own release tag and verification export (requested by `spatial-hemigroup-scale-space`,
    WISHLIST 2026-09-15, whose Paper V holds three). Everything that reads the paper --
    `artifacts.paper_markers`, `artifacts.pin_shared`, `missing()` -- iterates this tuple,
    so a second directory is checked, pinned and counted the same as the first.
    """
    axioms_verbatim: Path | None = None
    """The verbatim companion of the ledger (`paths.axioms_verbatim`, default
    `blueprint/AXIOMS-verbatim.md`): one `## AXX` section per entry holding the source's
    wording. It need not exist -- an article may keep every transcription in its entries --
    so it is not in `missing()`."""
    lean_uses: Path | None = None
    r"""An exported constant map for `linkage closure` (`paths.lean_uses`, default
    `lean-uses.json` inside `paths.lean`): `{"Decl.Name": ["Const.One", …]}`, written by a Lean
    meta program out of a built environment. It need not exist -- the audit falls back to
    scanning the declaration sources -- so it is not in `missing()`."""

    lean_packages: tuple[str, ...] = ()
    r"""Lake packages whose sources also count as "declared here".

    A shared library holds results this article's blueprint legitimately points `\lean{}` at.
    Named explicitly rather than scanning every dependency: scanning Mathlib would make any
    Mathlib name satisfy check 1, and would read thousands of files on every run.
    """

    boundary: Boundary = field(default_factory=Boundary)

    statement_envs: tuple[str, ...] = DEFAULT_STATEMENT_ENVS
    label_prefixes: tuple[str, ...] = DEFAULT_LABEL_PREFIXES
    statement_kinds: tuple[str, ...] = DEFAULT_STATEMENT_KINDS
    ledger_key: str = DEFAULT_LEDGER_KEY

    pandoc_pin: str = DEFAULT_PANDOC_PIN
    pandoc_target: str = DEFAULT_PANDOC_TARGET

    lean_libraries: tuple[str, ...] = ()
    """The Lake libraries of this repository's own tree (`paths.lean_libraries`). Empty
    means: infer them — a directory `X/` under `paths.lean` beside a root file `X.lean`."""
    shared_namespaces: tuple[str, ...] = ()
    r"""Namespace prefixes of declarations that live in a shared package rather than this
    tree (`paths.shared_namespaces`; default: `lean_packages`). A `\lean{}` tag naming one
    is not looked for here, so a local declaration that happens to share its short name is
    not mistaken for it. The package's *name* and its *namespace* need not agree —
    `ScaleSpaceCore` declares `ScaleSpace.*` — which is why this is its own key."""
    modules: tuple[Module, ...] = ()
    release: Release = field(default_factory=Release)

    _label_re: re.Pattern = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._label_re = re.compile(r"^(?:" + "|".join(self.label_prefixes) + r"):")

    def is_statement_label(self, label: str) -> bool:
        return bool(self._label_re.match(label))

    def module(self, name: str | None = None) -> Module:
        """The named module, or the only one there is.

        A repository with one module need not name it on every release command; one with
        several must, because picking for the author would pick the wrong tag.
        """
        if not self.modules:
            raise ConfigError(
                f"{CONFIG_NAME} declares no `[[modules]]` table — a release command needs "
                f"the module's chapters, paper directory, tag, roots and headline "
                f"declaration; see docs/RELEASE.md")
        if name is None:
            if len(self.modules) > 1:
                raise ConfigError(
                    f"{CONFIG_NAME} declares {len(self.modules)} modules "
                    f"({', '.join(m.name for m in self.modules)}) — name one with --module")
            return self.modules[0]
        for m in self.modules:
            if m.name == name:
                return m
        raise ConfigError(
            f"{CONFIG_NAME} declares no module {name!r} (known: "
            f"{', '.join(m.name for m in self.modules) or '-'})")

    def module_of_tag(self, tag: str) -> Module:
        """The module a released tag belongs to, by tag prefix: `cone-v0.1` is the module
        whose own `tag` is prefixed `cone-`. `--cites` resolves a cited tag this way, so
        that the cited release's closure is recomputed with ITS parameters, never the
        citing module's."""
        prefix = module_prefix(tag)
        hits = [m for m in self.modules if m.tag and module_prefix(m.tag) == prefix]
        if len(hits) != 1:
            raise ConfigError(
                f"the tag {tag!r} names no single module of {CONFIG_NAME}: "
                f"{len(hits)} module(s) carry the tag prefix {prefix or '(none)'!r}. "
                f"Give the module a `tag` in its `[[modules]]` table")
        return hits[0]

    def missing(self) -> list[str]:
        """Configured paths that do not exist — reported together, not one at a time."""
        return [
            f"{name} = {p.relative_to(self.root).as_posix()}"
            for name, p in (
                ("blueprint", self.blueprint), ("axioms", self.axioms),
                ("macros", self.macros), ("allowlist", self.allowlist),
                ("lean", self.lean),
                *(("paper", d) for d in self.papers),
            )
            if not p.exists()
        ]


def find_root(start: Path | None = None) -> Path:
    """Walk up from `start` (default: cwd) to the directory holding `linkage.toml`."""
    cur = (start or Path.cwd()).resolve()
    for cand in (cur, *cur.parents):
        if (cand / CONFIG_NAME).is_file():
            return cand
    raise ConfigError(
        f"no {CONFIG_NAME} found in {cur} or any parent — run from an article repo, "
        f"or scaffold one with `linkage init`"
    )


def load(root: Path | None = None, *, validate: bool = True) -> Config:
    root = (root or find_root()).resolve()
    # An explicit `--root` does no walking, so nothing has established that the file is
    # there: without this, a mistyped path reached tomllib as a FileNotFoundError and the
    # CLI printed a traceback instead of its own "CONFIG ERROR ... exit 2".
    if not (root / CONFIG_NAME).is_file():
        raise ConfigError(
            f"no {CONFIG_NAME} in {root} — point --root at an article repo root, or omit "
            f"it to walk up from the current directory"
        )
    raw = tomllib.loads((root / CONFIG_NAME).read_text(encoding="utf-8"))

    paths = raw.get("paths", {})
    bp = raw.get("blueprint", {})
    rd = raw.get("render", {})

    def p(key: str, default: str) -> Path:
        return root / paths.get(key, default)

    def paper_dirs() -> tuple[Path, ...]:
        """`paths.paper`: one directory, or a list of them.

        A list is rejected when it is empty or repeats a directory. Neither is a
        harmless no-op: an empty list would silently check no paper at all, and a
        repeat would collect every marker twice and let `--pin-shared` rewrite the
        same file twice in one pass.
        """
        raw_paper = paths.get("paper", "paper")
        if isinstance(raw_paper, str):
            raw_paper = [raw_paper]
        if (not isinstance(raw_paper, list)
                or not all(isinstance(d, str) for d in raw_paper)):
            raise ConfigError(
                f"{CONFIG_NAME}: `paths.paper` must be a directory or a list of "
                f"directories, not {raw_paper!r}")
        if not raw_paper:
            raise ConfigError(
                f"{CONFIG_NAME}: `paths.paper` is an empty list — name at least one "
                f"paper directory, or omit the key for the default 'paper'")
        seen: dict[str, None] = {}
        for d in raw_paper:
            if d in seen:
                raise ConfigError(
                    f"{CONFIG_NAME}: `paths.paper` lists {d!r} twice — every marker in "
                    f"it would be read, reported and pinned twice")
            seen[d] = None
        return tuple(root / d for d in raw_paper)

    def release_table() -> Release:
        rel = raw.get("release", {})
        if not isinstance(rel, dict):
            raise ConfigError(f"{CONFIG_NAME}: `[release]` must be a table")
        creators = []
        for c in rel.get("creators", ()):
            if not isinstance(c, dict) or not c.get("name"):
                raise ConfigError(
                    f"{CONFIG_NAME}: every `release.creators` entry is a table with a "
                    f"`name` (surname first, as a deposit prints it), not {c!r}")
            creators.append({k: str(v) for k, v in c.items()})
        return Release(
            creators=tuple(creators),
            license=rel.get("license", DEFAULT_LICENSE),
            upload_type=rel.get("upload_type", DEFAULT_UPLOAD_TYPE),
            publication_type=rel.get("publication_type", DEFAULT_PUBLICATION_TYPE),
            copyright=rel.get("copyright"),
        )

    def modules_table() -> tuple[Module, ...]:
        rows = raw.get("modules", [])
        if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
            raise ConfigError(f"{CONFIG_NAME}: `[[modules]]` must be a list of tables")
        out: list[Module] = []
        seen: set[str] = set()
        for r in rows:
            name = r.get("name")
            if not name:
                raise ConfigError(
                    f"{CONFIG_NAME}: every `[[modules]]` table needs a `name` — it is what "
                    f"`--module` selects and what the export's reports call the module")
            if name in seen:
                raise ConfigError(f"{CONFIG_NAME}: two `[[modules]]` tables named {name!r}")
            seen.add(name)
            releases = r.get("releases", {})
            if not isinstance(releases, dict) or not all(
                    isinstance(v, dict) for v in releases.values()):
                raise ConfigError(
                    f"{CONFIG_NAME}: module {name!r}: `releases` maps a tag to the "
                    f"parameters as they stood at it, e.g. "
                    f"[modules.releases.\"{name}-v0.1\"] chapters = [...]")
            shared = r.get("shared_nodes", DEFAULT_SHARED_NODES)
            if shared not in ("omit", "whole"):
                raise ConfigError(
                    f"{CONFIG_NAME}: module {name!r}: `shared_nodes` is 'omit' or 'whole', "
                    f"not {shared!r}")
            out.append(Module(
                name=str(name),
                chapters=tuple(str(c) for c in r.get("chapters", ())),
                paper=r.get("paper", "paper"),
                tag=r.get("tag"),
                roots=tuple(r.get("roots", ())),
                headline=r.get("headline"),
                stem=r.get("stem"),
                title=r.get("title", ""),
                repo_url=r.get("repo_url", ""),
                records=r.get("records"),
                process=r.get("process"),
                response_plans=tuple(r.get("response_plans", ())),
                reviews=r.get("reviews"),
                shared_nodes=shared,
                keywords=tuple(r.get("keywords", ())),
                related=tuple(r.get("related", ())),
                abstract_macros=dict(r.get("abstract_macros", {})),
                axioms_section=str(r.get("axioms_section", DEFAULT_AXIOMS_SECTION)),
                releases={str(k): dict(v) for k, v in releases.items()},
            ))
        return tuple(out)

    def boundary() -> Boundary:
        bt = raw.get("boundary")
        if bt is None:
            return Boundary()
        if not isinstance(bt, dict):
            raise ConfigError(f"{CONFIG_NAME}: `[boundary]` must be a table")

        def f(key: str) -> Path | None:
            v = bt.get(key)
            if v is None:
                return None
            if not isinstance(v, str):
                raise ConfigError(
                    f"{CONFIG_NAME}: `[boundary] {key}` must be a path, not {v!r}")
            return root / v

        def strs(key: str) -> tuple[str, ...]:
            v = bt.get(key, [])
            if not isinstance(v, list) or not all(isinstance(s, str) for s in v):
                raise ConfigError(
                    f"{CONFIG_NAME}: `[boundary] {key}` must be a list of strings")
            return tuple(v)

        shadows = bt.get("shadows", {})
        if not isinstance(shadows, dict):
            raise ConfigError(
                f"{CONFIG_NAME}: `[boundary.shadows]` must be a table mapping a "
                f"declaration to what makes it differ from the standard notion")
        return Boundary(
            configured=True,
            guard=f("guard"),
            probes=f("probes"),
            adversarial=f("adversarial"),
            headline=strs("headline"),
            shadows={k: str(v) for k, v in shadows.items()},
            standard_notions_extra=strs("standard_notions_extra"),
        )

    slug = raw.get("slug")
    if not slug:
        raise ConfigError(f"{CONFIG_NAME}: `slug` is required — it is the satellite id the "
                          f"hub keys claim refs and the manifest filename on")

    cfg = Config(
        root=root,
        slug=slug,
        blueprint=p("blueprint", "blueprint/src/content.tex"),
        axioms=p("axioms", "blueprint/AXIOMS.md"),
        macros=p("macros", "blueprint/src/macros.tex"),
        allowlist=p("allowlist", "blueprint/render-allowlist.txt"),
        lean=p("lean", "Formalization"),
        papers=paper_dirs(),
        axioms_verbatim=p("axioms_verbatim", "blueprint/AXIOMS-verbatim.md"),
        # Defaulted *inside the Lean directory* rather than at a fixed path: it is written by
        # a Lean meta program alongside the sources it describes, and `paths.lean` is
        # configurable, so a hard-coded "Formalization/…" would miss it in any article that
        # names its Lean project something else.
        lean_uses=p("lean_uses", f"{paths.get('lean', 'Formalization')}/lean-uses.json"),
        lean_packages=tuple(paths.get("lean_packages", ())),
        boundary=boundary(),
        statement_envs=tuple(bp.get("statement_envs", DEFAULT_STATEMENT_ENVS)),
        label_prefixes=tuple(bp.get("statement_label_prefixes", DEFAULT_LABEL_PREFIXES)),
        statement_kinds=tuple(bp.get("statement_kinds", DEFAULT_STATEMENT_KINDS)),
        ledger_key=bp.get("ledger_key", DEFAULT_LEDGER_KEY),
        pandoc_pin=rd.get("pandoc_pin", DEFAULT_PANDOC_PIN),
        pandoc_target=rd.get("pandoc_target", DEFAULT_PANDOC_TARGET),
        lean_libraries=tuple(paths.get("lean_libraries", ())),
        shared_namespaces=tuple(paths.get("shared_namespaces",
                                          paths.get("lean_packages", ()))),
        modules=modules_table(),
        release=release_table(),
    )
    if validate and (missing := cfg.missing()):
        raise ConfigError(
            f"{CONFIG_NAME} points at paths that do not exist: {'; '.join(missing)}"
        )
    return cfg
