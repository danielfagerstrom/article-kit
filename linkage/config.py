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

    statement_envs: tuple[str, ...] = DEFAULT_STATEMENT_ENVS
    label_prefixes: tuple[str, ...] = DEFAULT_LABEL_PREFIXES
    statement_kinds: tuple[str, ...] = DEFAULT_STATEMENT_KINDS
    ledger_key: str = DEFAULT_LEDGER_KEY

    pandoc_pin: str = DEFAULT_PANDOC_PIN
    pandoc_target: str = DEFAULT_PANDOC_TARGET

    _label_re: re.Pattern = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._label_re = re.compile(r"^(?:" + "|".join(self.label_prefixes) + r"):")

    def is_statement_label(self, label: str) -> bool:
        return bool(self._label_re.match(label))

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


def load(root: Path | None = None) -> Config:
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
        statement_envs=tuple(bp.get("statement_envs", DEFAULT_STATEMENT_ENVS)),
        label_prefixes=tuple(bp.get("statement_label_prefixes", DEFAULT_LABEL_PREFIXES)),
        statement_kinds=tuple(bp.get("statement_kinds", DEFAULT_STATEMENT_KINDS)),
        ledger_key=bp.get("ledger_key", DEFAULT_LEDGER_KEY),
        pandoc_pin=rd.get("pandoc_pin", DEFAULT_PANDOC_PIN),
        pandoc_target=rd.get("pandoc_target", DEFAULT_PANDOC_TARGET),
    )
    if missing := cfg.missing():
        raise ConfigError(
            f"{CONFIG_NAME} points at paths that do not exist: {'; '.join(missing)}"
        )
    return cfg
