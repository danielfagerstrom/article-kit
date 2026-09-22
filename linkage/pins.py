"""The pin check: a consumer calls article-kit's reusable workflows at a release, not at a branch.

A framework change reaches every article that calls it at `@main` the moment it is pushed, so a
defect here breaks all of them at once (docs/RELEASE.md, "Versioning the framework"). Consumers
call `docs.yml`, `lean.yml` and `manifest.yml` at a tag (`vX.Y.Z`) or a full commit sha, and pass
the same tag as `linkage_ref` so the CLI they install matches the workflow that installs it.

Line-based on purpose: the package has no dependencies, and a workflow's `uses:` and `with:`
lines are regular enough that a YAML parser would add a dependency for no extra precision.
"""

from __future__ import annotations

import re
from pathlib import Path

_USES = re.compile(
    r"^\s*(?:-\s+)?uses:\s*['\"]?[\w.-]+/article-kit/\.github/workflows/"
    r"(?P<wf>[\w.-]+)@(?P<ref>[^\s'\"#]+)")
_LINKAGE_REF = re.compile(r"^\s*linkage_ref:\s*['\"]?(?P<ref>[^\s'\"#]*)")
_RELEASE = re.compile(r"^v\d+\.\d+\.\d+$")
_SHA = re.compile(r"^[0-9a-f]{40}$")

# The workflows that install the linkage CLI and so take `linkage_ref`; its default is `main`.
_INSTALLS_LINKAGE = {"lean.yml", "manifest.yml"}


def _pinned(ref: str) -> bool:
    return bool(_RELEASE.match(ref) or _SHA.match(ref))


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _given_linkage_ref(lines: list[str], i: int) -> str | None:
    """The `linkage_ref` passed by the job whose `uses:` is on line `i`, if any.

    The job is every neighbouring line indented at least as deep as its `uses:` key; the
    `with:` block follows the `uses:` line, but a caller may write `with:` first.
    """
    base = _indent(lines[i])
    if lines[i].lstrip().startswith("- "):
        base += 2
    for follow in lines[i + 1:]:
        if follow.strip() and _indent(follow) < base:
            break
        m = _LINKAGE_REF.match(follow)
        if m:
            return m["ref"]
    for prev in reversed(lines[:i]):
        if prev.strip() and _indent(prev) < base:
            break
        m = _LINKAGE_REF.match(prev)
        if m:
            return m["ref"]
    return None


def check_text(text: str, rel: str) -> list[str]:
    """The pin defects of one workflow file, as messages naming `rel:line`."""
    lines = text.splitlines()
    found: list[str] = []
    for i, line in enumerate(lines):
        m = _USES.match(line)
        if not m:
            continue
        wf, ref = m["wf"], m["ref"]
        where = f"{rel}:{i + 1}"
        if not _pinned(ref):
            found.append(f"{where}: article-kit/.github/workflows/{wf}@{ref} is not a release "
                         "-- call it at a tag (vX.Y.Z) or a full commit sha")
        if wf not in _INSTALLS_LINKAGE:
            continue
        given = _given_linkage_ref(lines, i)
        if given is None:
            found.append(f"{where}: {wf} is called without `linkage_ref`, which defaults to "
                         "main -- pass the same tag the workflow is called at")
        elif not _pinned(given):
            found.append(f"{where}: linkage_ref {given!r} is not a release -- pass a tag "
                         "(vX.Y.Z) or a full commit sha")
    return found


def check(root: Path) -> list[str]:
    """Every pin defect under `root`'s `.github/workflows/`."""
    found: list[str] = []
    wf_dir = root / ".github" / "workflows"
    if not wf_dir.is_dir():
        return found
    for path in sorted([*wf_dir.glob("*.yml"), *wf_dir.glob("*.yaml")]):
        rel = path.relative_to(root).as_posix()
        found.extend(check_text(path.read_text(encoding="utf-8"), rel))
    return found
