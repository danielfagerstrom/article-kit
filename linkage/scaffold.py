"""Scaffolding a new article, and keeping the copied framework files honest.

An article repo needs a handful of the framework's LaTeX files physically present, because
TeX resolves `\\input` relative to the source tree. That makes them copies, and hub ADR-0008
is explicit about what a copy owes: *wherever the same content must exist in two places,
either make one of them generated, or make the divergence detectable.* These are generated
by `linkage init` and their divergence is detected by `linkage check`.

Two tiers:

**Framework-owned** — `blueprint.sty`, `theorems.tex`, `linkage-macros.tex`, `latexmkrc`.
Editing the article's copy is a mistake; `linkage check` reports it as an advisory naming
the file. Change them in the framework and re-run `linkage init --sync`.

**Seeded** — `plastex.cfg`, `extra_styles.css`, `render-allowlist.txt`, and the rendered
templates (`web.tex`, `print.tex`, `macros.tex`, `linkage.toml`). Copied once as a starting
point and then owned by the article: the allowlist grows with the article's vocabulary, the
split-level depends on its chapter shape, the macros hold its notation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

STAMP = ".linkage-scaffold.json"

# framework-owned file -> destination relative to the article root
FRAMEWORK_OWNED = {
    "blueprint/blueprint.sty": "blueprint/src/blueprint.sty",
    "blueprint/theorems.tex": "blueprint/src/theorems.tex",
    "blueprint/linkage-macros.tex": "blueprint/src/linkage-macros.tex",
    "blueprint/latexmkrc": "blueprint/src/latexmkrc",
}

# seeded once, then the article's
SEEDED = {
    "blueprint/plastex.cfg": "blueprint/src/plastex.cfg",
    "blueprint/extra_styles.css": "blueprint/src/extra_styles.css",
    "blueprint/render-allowlist.txt": "blueprint/render-allowlist.txt",
}

# template -> destination; rendered with @@NAME@@ substitution, never overwritten
TEMPLATES = {
    "blueprint/web.tex.in": "blueprint/src/web.tex",
    "blueprint/print.tex.in": "blueprint/src/print.tex",
    "blueprint/macros.tex.in": "blueprint/src/macros.tex",
    "linkage.toml.in": "linkage.toml",
}


def scaffold_dir() -> Path:
    """The packaged scaffold tree — `scaffold/` in a checkout, `scaffold_data/` in a wheel."""
    here = Path(__file__).resolve().parent
    for cand in (here / "scaffold_data", here.parent / "scaffold"):
        if cand.is_dir():
            return cand
    raise RuntimeError(f"scaffold tree not found next to {here}")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def render(text: str, subs: dict[str, str]) -> str:
    for k, v in subs.items():
        text = text.replace(f"@@{k}@@", v)
    return text


def init(root: Path, slug: str, subs: dict[str, str] | None = None,
         sync: bool = False) -> int:
    """Write the scaffolding into `root`. Existing seeded/template files are left alone."""
    src = scaffold_dir()
    subs = {"SLUG": slug, "TITLE": slug, "HOME": "", "GITHUB": "", "DOCHOME": "", **(subs or {})}
    stamp: dict[str, str] = {}
    wrote, kept = [], []

    for rel, dest_rel in FRAMEWORK_OWNED.items():
        dest = root / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        content = _read(src / rel)
        if dest.exists() and _read(dest) == content:
            kept.append(dest_rel)
        else:
            dest.write_text(content, encoding="utf-8")
            wrote.append(dest_rel)
        stamp[dest_rel] = sha(content)

    for rel, dest_rel in SEEDED.items():
        dest = root / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            kept.append(dest_rel)
            continue
        dest.write_text(_read(src / rel), encoding="utf-8")
        wrote.append(dest_rel)

    if not sync:
        for rel, dest_rel in TEMPLATES.items():
            dest = root / dest_rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                kept.append(dest_rel)
                continue
            dest.write_text(render(_read(src / rel), subs), encoding="utf-8")
            wrote.append(dest_rel)

    (root / "blueprint").mkdir(parents=True, exist_ok=True)
    (root / "blueprint" / STAMP).write_text(
        json.dumps({"framework_owned": stamp}, indent=2) + "\n", encoding="utf-8")

    print(f"scaffold: wrote {len(wrote)}, left {len(kept)} in place")
    for w in wrote:
        print(f"  + {w}")
    if not sync and not (root / "blueprint" / "AXIOMS.md").exists():
        print("\nNext: write blueprint/AXIOMS.md (the axiom ledger) and "
              "blueprint/src/content.tex (\\input-ing your parts), then `linkage check`.")
    return 0


def drift(root: Path) -> list[str]:
    """Framework-owned files whose article copy no longer matches the framework's."""
    src = scaffold_dir()
    out = []
    for rel, dest_rel in FRAMEWORK_OWNED.items():
        dest = root / dest_rel
        if not dest.exists():
            continue
        if _read(dest) != _read(src / rel):
            out.append(dest_rel)
    return out
