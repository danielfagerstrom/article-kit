"""Scaffolding a new article, and keeping the copied framework files honest.

An article repo needs a handful of the framework's LaTeX files physically present, because
TeX resolves `\\input` relative to the source tree. That makes them copies, and hub ADR-0008
is explicit about what a copy owes: *wherever the same content must exist in two places,
either make one of them generated, or make the divergence detectable.* These are generated
by `linkage init` and their divergence is detected by `linkage check`.

Two tiers:

**Framework-owned** — `blueprint.sty`, `theorems.tex`, `linkage-macros.tex`, `latexmkrc`,
`scripts/build-blueprint.sh` (the article's one-command rebuild of every blueprint view), and
the session rules under `.claude/rules/article-kit/` (ADR-0001: the process reaches every
article session through them). Editing the article's copy is a mistake; `linkage check` reports
it as an advisory naming the file. Change them in article-kit and re-run `linkage init --sync`.

**Seeded** — `plastex.cfg`, `extra_styles.css`, `render-allowlist.txt`, the `adr/` and
`records/` READMEs, and the rendered templates (`web.tex`, `print.tex`, `macros.tex`,
`linkage.toml`, `CLAUDE.md`, `README.md`, `CHANGELOG.md`, `notes/HANDOFF.md`). Copied once as a
starting point and then owned by the article: the allowlist grows with the article's vocabulary,
the split-level depends on its chapter shape, the macros hold its notation.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

STAMP = ".linkage-scaffold.json"

# framework-owned file -> destination relative to the article root
FRAMEWORK_OWNED = {
    "blueprint/blueprint.sty": "blueprint/src/blueprint.sty",
    "blueprint/theorems.tex": "blueprint/src/theorems.tex",
    "blueprint/linkage-macros.tex": "blueprint/src/linkage-macros.tex",
    "blueprint/latexmkrc": "blueprint/src/latexmkrc",
    "scripts/build-blueprint.sh": "scripts/build-blueprint.sh",
    "scripts/check-swallowed-prose.py": "scripts/check-swallowed-prose.py",
    "scripts/check-control-chars.py": "scripts/check-control-chars.py",
    "claude/rules/core.md": ".claude/rules/article-kit/core.md",
    "claude/rules/writing.md": ".claude/rules/article-kit/writing.md",
    "claude/rules/blueprint.md": ".claude/rules/article-kit/blueprint.md",
    "claude/rules/ledger.md": ".claude/rules/article-kit/ledger.md",
    "claude/rules/lean.md": ".claude/rules/article-kit/lean.md",
}

# seeded once, then the article's
SEEDED = {
    # cloud-setup.sh is the BOOTSTRAP: it is what finds the sibling checkouts and installs
    # the CLIs, so it cannot itself be fetched through the framework it installs. Each
    # article therefore carries its own copy, seeded here.
    "claude/cloud-setup.sh": ".claude/cloud-setup.sh",
    "claude/sync-agents-hook.sh": ".claude/sync-agents-hook.sh",
    "claude/settings.json": ".claude/settings.json",
    "blueprint/plastex.cfg": "blueprint/src/plastex.cfg",
    "blueprint/extra_styles.css": "blueprint/src/extra_styles.css",
    "blueprint/render-allowlist.txt": "blueprint/render-allowlist.txt",
    "repo/adr-README.md": "adr/README.md",
    "repo/records-README.md": "records/README.md",
    # the draft part's directory, which `[article] phase = "draft"` requires (ADR-0002)
    "repo/draft-README.md": "draft/README.md",
}

# the licence texts the Lean headers and the README name; written by `init` only, never by
# `--sync`, and never over a file that exists
LICENSES = {
    "licenses/Apache-2.0.txt": "LICENSES/Apache-2.0.txt",
    "licenses/CC-BY-4.0.txt": "LICENSES/CC-BY-4.0.txt",
}

# template -> destination; rendered with @@NAME@@ substitution, never overwritten
TEMPLATES = {
    "blueprint/web.tex.in": "blueprint/src/web.tex",
    "blueprint/print.tex.in": "blueprint/src/print.tex",
    "blueprint/macros.tex.in": "blueprint/src/macros.tex",
    "linkage.toml.in": "linkage.toml",
    "repo/CLAUDE.md.in": "CLAUDE.md",
    "repo/README.md.in": "README.md",
    "repo/CHANGELOG.md.in": "CHANGELOG.md",
    "repo/HANDOFF.md.in": "notes/HANDOFF.md",
    # the one caller of the reusable workflows, following the [article] table (ADR-0002);
    # pinned to the article-kit release that wrote it
    "repo/article.yml.in": ".github/workflows/article.yml",
}


def scaffold_dir() -> Path:
    """The packaged scaffold tree — `scaffold/` in a checkout, `scaffold_data/` in a wheel."""
    here = Path(__file__).resolve().parent
    for cand in (here / "scaffold_data", here.parent / "scaffold"):
        if cand.is_dir():
            return cand
    raise RuntimeError(f"scaffold tree not found next to {here}")


def kit_tag() -> str:
    """The article-kit release this package is, as the tag the seeded workflows pin."""
    from importlib.metadata import PackageNotFoundError, version
    try:
        return "v" + version("linkage")
    except PackageNotFoundError:
        return "v0.0.0"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def render(text: str, subs: dict[str, str]) -> str:
    for k, v in subs.items():
        text = text.replace(f"@@{k}@@", v)
    return text


def _absent_artifacts(root: Path) -> set[str]:
    """`--sync` in a repository lacking an artifact skips what belongs to it.

    The path-scoped rules load only when a matching file is read, so copying them would be
    harmless, but the `blueprint/` build files would litter a paper-only repo (its stamp goes at
    the repository root instead).
    """
    from . import config
    try:
        cfg = config.load(root, validate=False)
    except config.ConfigError:
        return set()
    # By the parts `config.load` found absent, the same reading `linkage check` uses, so a
    # repository's sync and its check never disagree about what it has (LINKAGE.md, "Absent
    # parts"). A declared path that does not exist yet still skips here: `--sync` runs
    # mid-adoption, before the files are written.
    gone = set()
    if not cfg.has("blueprint") or not cfg.blueprint.exists():
        gone |= {"blueprint", "scripts/build-blueprint.sh",
                 "claude/rules/blueprint.md", "claude/rules/ledger.md"}
    if not cfg.has("lean") or not cfg.lean.exists():
        gone.add("claude/rules/lean.md")
    if not cfg.listed("draft"):
        gone.add("repo/draft-README.md")
    return gone


def _skipped(rel: str, absent: set[str]) -> bool:
    return rel in absent or ("blueprint" in absent and rel.startswith("blueprint/"))


def init(root: Path, slug: str, subs: dict[str, str] | None = None,
         sync: bool = False) -> int:
    """Write the scaffolding into `root`. Existing seeded/template files are left alone."""
    src = scaffold_dir()
    subs = {"SLUG": slug, "TITLE": slug, "HOME": "", "GITHUB": "", "DOCHOME": "",
            "KIT_TAG": kit_tag(), **(subs or {})}
    stamp: dict[str, str] = {}
    wrote, kept = [], []
    absent = _absent_artifacts(root) if sync else set()

    for rel, dest_rel in FRAMEWORK_OWNED.items():
        if _skipped(rel, absent):
            continue
        dest = root / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        content = _read(src / rel)
        if dest.exists() and _read(dest) == content:
            kept.append(dest_rel)
        else:
            # bytes, not write_text: on Windows text mode would turn the shell script's LF
            # into CRLF, and `sh` then reads `set -eu\r`.
            dest.write_bytes(content.encode("utf-8"))
            wrote.append(dest_rel)
        stamp[dest_rel] = sha(content)

    for rel, dest_rel in SEEDED.items():
        if _skipped(rel, absent):
            continue
        dest = root / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            kept.append(dest_rel)
            continue
        dest.write_text(_read(src / rel), encoding="utf-8")
        wrote.append(dest_rel)

    if not sync:
        for rel, dest_rel in LICENSES.items():
            dest = root / dest_rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                kept.append(dest_rel)
                continue
            dest.write_bytes((src / rel).read_bytes())
            wrote.append(dest_rel)
        for rel, dest_rel in TEMPLATES.items():
            dest = root / dest_rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                kept.append(dest_rel)
                continue
            dest.write_text(render(_read(src / rel), subs), encoding="utf-8")
            wrote.append(dest_rel)

    stamp_path = root / STAMP if "blueprint" in absent else root / "blueprint" / STAMP
    stamp_path.parent.mkdir(parents=True, exist_ok=True)
    stamp_path.write_text(
        json.dumps({"framework_owned": stamp}, indent=2) + "\n", encoding="utf-8")

    print(f"scaffold: wrote {len(wrote)}, left {len(kept)} in place")
    for w in wrote:
        print(f"  + {w}")
    if not sync and not (root / "blueprint" / "AXIOMS.md").exists():
        print("\nNext: write blueprint/AXIOMS.md (the axiom ledger) and "
              "blueprint/src/content.tex (\\input-ing your parts), then `linkage check`.")
    return 0


PLUGIN_KEY = "article-kit@article-kit"


def plugin_enabled(root: Path) -> bool:
    """Whether the article's project settings enable the article-kit plugin, which is what makes
    the skills its rules name (`/article-kit:write`, `:release`, `:gate`) visible to its sessions.
    `settings.local.json` overrides `settings.json`, as in Claude Code. A file that is absent or
    not JSON counts as not enabling it; a user-level enablement is not visible from here."""
    return plugin_setting(root)[0]


def plugin_setting(root: Path) -> tuple[bool, str]:
    """(enabled, the settings file that decided it, or "" when none names the plugin)."""
    found, where = None, ""
    for name in ("settings.json", "settings.local.json"):
        path = root / ".claude" / name
        try:
            doc = json.loads(path.read_text(encoding="utf-8-sig"))   # a Windows editor's BOM
        except (OSError, ValueError):
            continue
        plugins = doc.get("enabledPlugins") if isinstance(doc, dict) else None
        if isinstance(plugins, dict) and PLUGIN_KEY in plugins:
            found, where = plugins[PLUGIN_KEY] is True, f".claude/{name}"
    return bool(found), where


Reader = Callable[[str], "str | None"]   # a path relative to the article root -> its text, or None if absent


def tree_reader(root: Path) -> Reader:
    """The article's working tree: the default reader."""
    def read(rel: str) -> str | None:
        p = root / rel
        return _read(p) if p.exists() else None
    return read


class RevError(Exception):
    """`git` could not read the revision."""


def git_reader(root: Path, rev: str) -> Reader:
    """The article as committed at `rev`, through `git -C root show rev:path`. A path absent at
    `rev` reads as None; an unknown `rev`, or git failing, raises RevError. Writes nothing."""
    def git(*argv: str) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(["git", "-C", str(root), *argv], capture_output=True)
        except OSError as e:
            raise RevError(f"git failed: {e}") from e

    probe = git("rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}")
    if probe.returncode != 0:
        raise RevError(f"cannot read revision {rev!r} in {root}: "
                       + (probe.stderr.decode("utf-8", "replace").strip() or "unknown revision"))

    def read(rel: str) -> str | None:
        r = git("show", f"{rev}:{rel}")
        if r.returncode == 0:
            return r.stdout.decode("utf-8")
        if git("cat-file", "-e", f"{rev}:{rel}").returncode != 0:
            return None   # the path is not in that revision: absent, as a missing file is
        raise RevError(f"git show {rev}:{rel} failed: " + r.stderr.decode("utf-8", "replace").strip())
    return read


def drift(root: Path, read: Reader | None = None) -> list[str]:
    """Framework-owned files whose article copy no longer matches the framework's."""
    read = read or tree_reader(root)
    src = scaffold_dir()
    out = []
    for rel, dest_rel in FRAMEWORK_OWNED.items():
        theirs = read(dest_rel)
        if theirs is None:
            continue
        if theirs != _read(src / rel):
            out.append(dest_rel)
    return out


def last_sync(root: Path, read: Reader | None = None) -> dict[str, str]:
    """The hashes `init` recorded, per framework-owned destination, of the scaffold copy the
    article last received. Empty when there is no stamp or it is unreadable."""
    read = read or tree_reader(root)
    for rel in (f"blueprint/{STAMP}", STAMP):
        try:
            text = read(rel)
            if text is None:
                continue
            recorded = json.loads(text)["framework_owned"]
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if isinstance(recorded, dict):
            return recorded
    return {}


def drift_directions(root: Path, read: Reader | None = None) -> list[tuple[str, str]]:
    """Each drifted framework-owned file with whose change it is.

    Compared with the hash recorded at the last sync: `scaffold` when the article's copy is
    still what it received (the framework changed since), `article` when the framework's copy
    is still what it sent (the article edited its copy), `both` when each moved, `unrecorded`
    when the stamp does not name the file (synced before the stamp existed).
    """
    read = read or tree_reader(root)
    src = scaffold_dir()
    recorded = last_sync(root, read)
    rels = {dest_rel: rel for rel, dest_rel in FRAMEWORK_OWNED.items()}
    out = []
    for dest_rel in drift(root, read):
        theirs, ours = sha(read(dest_rel) or ""), sha(_read(src / rels[dest_rel]))
        then = recorded.get(dest_rel)
        if then is None:
            direction = "unrecorded"
        elif theirs == then:
            direction = "scaffold"
        elif ours == then:
            direction = "article"
        else:
            direction = "both"
        out.append((dest_rel, direction))
    return out


DIRECTION_TEXT = {
    "scaffold": "the scaffold changed since the last sync: `linkage init --sync` brings it in",
    "article": "the article edited its copy: move the edit into article-kit first, or a sync loses it",
    "both": "the scaffold changed and the article edited its copy: reconcile in article-kit, then sync",
    "unrecorded": "no record of the last sync names it: compare the two by hand",
}


def check(root: Path, rev: str | None = None) -> int:
    """`init --sync --check`: print what a sync would change and whose change it is; write nothing.
    Exit 1 when any framework-owned file differs. With `rev`, the article side is read from that
    git revision, not the working tree; an unreadable revision exits 2."""
    try:
        found = drift_directions(root, git_reader(root, rev) if rev else None)
    except RevError as e:
        print(f"linkage init: {e}", file=sys.stderr)
        return 2
    for rel, direction in found:
        print(f"{rel}: {direction} \u2014 {DIRECTION_TEXT[direction]}")
    if not found:
        print("scaffold: every framework-owned file matches the framework's copy")
        return 0
    print(f"scaffold: {len(found)} framework-owned file(s) differ")
    return 1
