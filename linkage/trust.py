"""The trust boundary: which axioms a headline theorem may depend on.

`#print axioms` on the article's proved theorems must reduce to Lean core plus the ledger's
analytic interfaces and nothing else. That list has to be declared *outside* the Lean
sources — deriving it from the `axiom` declarations would let a newly added axiom authorize
itself, which is exactly what the guard exists to prevent.

It is also not derived from `AXIOMS.md`'s `**Lean:**` back-pointers, though that was the
obvious idea. Those segments name proved declarations and downstream consequences alongside
the interfaces (43 identifiers against the 11 real axioms for scale-space-foundations), so
using them would silently widen the boundary.

So the article declares it, one name per line, in `blueprint/trust-boundary.txt` — and this
module *cross-checks* that declaration against the ledger: every name must appear in some
entry's `**Lean:**` segment. That catches the case the old inline-YAML list could not — a
name added to CI that was never reviewed into the ledger.

**Includes** (Q-0298). A module that `require`s another brings the other's trust boundary into
its own *by reference* (hub `RELEASES.md` § "Dependencies between modules"). One line

    include SpatialHemigroup @ v0.1 blueprint/trust-boundary.txt

admits exactly the names that file lists in the required package, read with `git show` at the
commit this article's `lake-manifest.json` pins — never a local copy and never the working tree,
so an edit under `.lake/packages` admits nothing. The revision on the line must be the manifest's
`inputRev` (the tag the lakefile asks for) or its resolved `rev` (the sha, or a prefix of seven or
more hex digits); any other revision, or a package the manifest does not carry, is refused. The
path is relative to the package's repository root (the `.lake/packages/<pkg>` directory, not its
`subDir`) and defaults to `blueprint/trust-boundary.txt`, which is what an article's export ships.
Included names are not cross-checked against *this* article's ledger: the required module's own
`linkage axioms --check` grounded them in its ledger, and copying them here is what the rule
forbids.

An included file may itself include. Lake builds one revision of each package, the one the
*consumer's* manifest pins, so a nested include is resolved against this article's manifest too,
and refused like a direct one when the revision it names is not the one built here. Each
(package, path) is read once, so a cycle terminates.
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from .config import Config

# Lean's own axioms. Present in every trust base; not the article's to declare.
LEAN_CORE = ("propext", "Classical.choice", "Quot.sound")

# What an article's export ships (Paper V's `spatial-hemigroup-scale-space-cone` does at v0.1):
# the trust boundary under the repository root's `blueprint/`. Not the export's `axioms.txt`,
# which is the `#print axioms` output of every declaration -- the boundary's consequence, not
# its declaration.
DEFAULT_INCLUDE_PATH = "blueprint/trust-boundary.txt"

INCLUDE_RE = re.compile(r"^include\s+(?P<pkg>[^\s@]+)\s*@\s*(?P<rev>\S+)(?:\s+(?P<path>\S+))?$")


@dataclass(frozen=True)
class Include:
    """One `include <package> @ <revision> [<path>]` line."""
    package: str
    rev: str
    path: str
    line: int


@dataclass
class Included:
    """An include resolved against the manifest: the names it admits and where they were read."""
    package: str
    rev: str                # as written on the line
    commit: str             # the manifest's resolved `rev`, which is what was read
    path: str
    names: list[str]
    via: str | None = None  # the including package, for a nested include


@dataclass
class Resolution:
    included: list[Included] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def names(self) -> list[str]:
        return list(dict.fromkeys(n for i in self.included for n in i.names))


def _parse(text: str) -> tuple[list[str], list[Include], list[str]]:
    """`(names, includes, malformed)` of a boundary file's non-comment lines."""
    names: list[str] = []
    incs: list[Include] = []
    bad: list[str] = []
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.split(None, 1)[0] != "include":
            names.append(line)
        elif m := INCLUDE_RE.match(line):
            incs.append(Include(m["pkg"], m["rev"], m["path"] or DEFAULT_INCLUDE_PATH, n))
        else:
            bad.append(f"line {n}: `{line}` -- expected `include <package> @ <revision> [<path>]`")
    return names, incs, bad


def declared(cfg: Config) -> list[str]:
    """The article's own declared interface axioms, in file order; include lines excluded."""
    path = trust_file(cfg)
    if not path.exists():
        return []
    return _parse(path.read_text(encoding="utf-8"))[0]


def manifest_packages(cfg: Config) -> tuple[dict[str, dict], Path] | None:
    """The consumer's `lake-manifest.json`: its packages by name, and its packages directory."""
    try:
        data = json.loads((cfg.lean / "lake-manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    pkgs = {p["name"]: p for p in data.get("packages", []) if isinstance(p, dict) and "name" in p}
    return pkgs, cfg.lean / data.get("packagesDir", ".lake/packages")


def read_at(repo: Path, commit: str, path: str) -> str:
    """`git show <commit>:<path>` in a package checkout. Read only; raises `OSError`.

    The commit, not the working tree: what the manifest pins is a commit, and on the author's
    machine `.lake/packages` entries are junctions into a store shared between checkouts.
    """
    try:
        r = subprocess.run(["git", "-C", str(repo), "show", f"{commit}:{path}"],
                           capture_output=True, check=False)
    except (OSError, subprocess.SubprocessError) as e:
        raise OSError(f"git could not run: {e}") from e
    if r.returncode != 0:
        msg = r.stderr.decode("utf-8", "replace").strip().splitlines()
        raise OSError(msg[-1] if msg else f"git show exited {r.returncode}")
    return r.stdout.decode("utf-8")


def required_axioms_path(inc: Included) -> str:
    """The required module's own `AXIOMS.md`, as a path relative to its repository root.

    The sibling of the included `trust-boundary.txt`: the default
    `blueprint/trust-boundary.txt` ships beside `blueprint/AXIOMS.md`, the same
    convention every article's own `Config.axioms` default assumes locally. `PurePosixPath`
    rather than `Path`: `inc.path` is a `git show` path, forward-slashed whatever platform
    this runs on, and stringifying a `Path` would corrupt it with backslashes on Windows.
    """
    return str(PurePosixPath(inc.path).parent / "AXIOMS.md")


def read_required_axioms(cfg: Config, inc: Included) -> str:
    """A required module's own `AXIOMS.md`, read at the commit its include resolved to.

    `inc` must come from a `Resolution.included` list — `resolve()` already confirmed the
    package is pinned to a git revision and fetched, so this only reads a sibling file of
    the one it read there (Q-0374: a qualified `\\ledger{<package>:<id>}` reference resolves
    against this, never against the consuming article's own `AXIOMS.md`). Raises `OSError`,
    as `read_at` does, when the manifest cannot be read or the file is absent at that commit.
    """
    found = manifest_packages(cfg)
    if found is None:
        raise OSError("no readable lake-manifest.json")
    _pkgs, pkg_dir = found
    return read_at(pkg_dir / inc.package, inc.commit, required_axioms_path(inc))


def _rev_matches(written: str, entry: dict) -> bool:
    """The tag the lakefile asks for, or (a prefix of at least 7 of) the sha lake resolved."""
    if written == entry.get("inputRev"):
        return True
    sha = entry.get("rev") or ""
    return (len(written) >= 7 and re.fullmatch(r"[0-9a-f]+", written) is not None
            and sha.startswith(written))


def resolve(cfg: Config) -> Resolution:
    """Every include of the trust boundary, nested ones too, resolved against the manifest."""
    res = Resolution()
    path = trust_file(cfg)
    if not path.exists():
        return res
    _, top, bad = _parse(path.read_text(encoding="utf-8"))
    res.errors += [f"{path.name}: {b}" for b in bad]
    if not top:
        return res
    found = manifest_packages(cfg)
    if found is None:
        rel = (cfg.lean / "lake-manifest.json").relative_to(cfg.root).as_posix()
        res.errors.append(f"{path.name} includes another module's boundary, but there is no "
                          f"readable {rel} to pin it against")
        return res
    pkgs, pkg_dir = found
    seen: set[tuple[str, str]] = set()
    queue: list[tuple[Include, str, str | None]] = [(i, path.name, None) for i in top]
    while queue:
        inc, where, via = queue.pop(0)
        at = f"{where}:{inc.line}: include {inc.package} @ {inc.rev}"
        entry = pkgs.get(inc.package)
        if entry is None:
            res.errors.append(f"{at} -- {inc.package} is not a package of lake-manifest.json; "
                              "only a required module's boundary can be included")
            continue
        if entry.get("type", "git") != "git" or not entry.get("rev"):
            res.errors.append(f"{at} -- lake-manifest.json does not pin {inc.package} to a git "
                              "revision, so there is no release to read its boundary at")
            continue
        if not _rev_matches(inc.rev, entry):
            res.errors.append(f"{at} -- lake-manifest.json pins {inc.package} at "
                              f"{entry.get('inputRev')} ({entry['rev'][:12]}), not {inc.rev}")
            continue
        if (inc.package, inc.path) in seen:
            continue
        seen.add((inc.package, inc.path))
        repo = pkg_dir / inc.package
        if not repo.is_dir():
            res.errors.append(f"{at} -- {inc.package} is pinned but not fetched "
                              f"({repo.relative_to(cfg.root).as_posix()} is missing)")
            continue
        try:
            text = read_at(repo, entry["rev"], inc.path)
        except OSError as e:
            res.errors.append(f"{at} -- cannot read {inc.path} at {entry['rev'][:12]}: {e}")
            continue
        names, nested, bad = _parse(text)
        label = f"{inc.package}:{inc.path}"
        res.errors += [f"{label}: {b}" for b in bad]
        res.included.append(Included(inc.package, inc.rev, entry["rev"], inc.path, names, via))
        queue += [(n, label, inc.package) for n in nested]
    return res


def trust_file(cfg: Config) -> Path:
    return cfg.axioms.parent / "trust-boundary.txt"


def ledger_lean_mentions(cfg: Config) -> set[str]:
    """Short declaration names mentioned in the ledger's `**Lean:**` segments.

    Deliberately over-broad — it is used only to confirm a declared axiom *was* reviewed,
    never to authorize one.
    """
    text = cfg.axioms.read_text(encoding="utf-8")
    out: set[str] = set()
    for m in re.finditer(r"\*\*Lean:\*\*(.*?)(?=\n\s*\n|\*\*Cite:\*\*|\Z)", text, re.S):
        for ident in re.findall(r"`([A-Za-z_][\w'.]*)`", m.group(1)):
            out.add(ident.split(".")[-1])
    return out


def allowlist(cfg: Config, resolution: Resolution | None = None) -> list[str]:
    """Everything a headline theorem may depend on: Lean core + the declared interfaces + the
    names the includes admit.

    An include that does not resolve admits nothing, so a consumer fails closed;
    `linkage axioms` says why.
    """
    res = resolution if resolution is not None else resolve(cfg)
    return list(dict.fromkeys([*LEAN_CORE, *declared(cfg), *res.names]))


def ungrounded(cfg: Config) -> list[str]:
    """Declared axioms that no ledger entry mentions — declared but never reviewed."""
    mentions = ledger_lean_mentions(cfg)
    return [d for d in declared(cfg) if d.split(".")[-1] not in mentions]


def _entries(text: str, key: str) -> dict[str, str]:
    """`AXX` -> the body of its `## AXX` section (same split as `artifacts.ledger_entries`)."""
    return {m.group(1): m.group(2) for m in re.finditer(
        rf"(?ms)^##\s*({key})\b(.*?)(?=^##\s*{key}\b|\Z)", text)}


def missing_verbatim(cfg: Config) -> tuple[list[str], list[str]]:
    """Ledger entries with no transcription of the source's wording (LINKAGE.md rule 5).

    An entry has one if its body carries a `**Verbatim:**` block, or the companion
    (`cfg.axioms_verbatim`) has a section of the same id. Returns `(errors, advisories)`:
    an entry whose `**Lean:**` segment names a declared interface axiom is *admitted* and
    an absent transcription is an error; any other entry only gets an advisory.
    """
    entries = _entries(cfg.axioms.read_text(encoding="utf-8"), cfg.ledger_key)
    companion: set[str] = set()
    if cfg.axioms_verbatim is not None and cfg.axioms_verbatim.is_file():
        companion = set(_entries(cfg.axioms_verbatim.read_text(encoding="utf-8"),
                                 cfg.ledger_key))
    admitted = {d.split(".")[-1] for d in declared(cfg)}
    errors: list[str] = []
    advisories: list[str] = []
    for aid, body in entries.items():
        if "**Verbatim:**" in body or aid in companion:
            continue
        names = {i.split(".")[-1] for m in re.finditer(
                     r"\*\*Lean:\*\*(.*?)(?=\n\s*\n|\*\*Cite:\*\*|\Z)", body, re.S)
                 for i in re.findall(r"`([A-Za-z_][\w'.]*)`", m.group(1))}
        (errors if names & admitted else advisories).append(aid)
    return errors, advisories
