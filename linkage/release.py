r"""The verification export of a release: `linkage release export`.

The Lean modules a release's blueprint nodes rest on, the paper, the ledger and the reviews,
into a separate repository, without the chapters that belong to later modules.

    linkage release export --module line --out ../<article>-v0.1
    linkage release export --module line --out ... --build   # then lake build + the guard there

Ported from `spatial-hemigroup-scale-space`'s `scripts/export-release.py` (ADR-0001 step 5),
with every module-specific constant — chapters, paper directory, tag, roots, headline
declaration, records directory, title, repository URL, the Lake libraries of the tree — read
from `linkage.toml`'s `[[modules]]` and `[release]` tables instead.

What goes out:

  Formalization/   lakefile.toml, lake-manifest.json, lean-toolchain verbatim; the transitive
                   import closure of every module a blueprint node's `\lean{}` tag names, over
                   the module's chapters and the nodes its paper shares from other chapters;
                   generated library roots; CIAxiomGuard.lean restricted to exported
                   declarations.
  blueprint/       trust-boundary.txt, AXIOMS.md (and AXIOMS-verbatim.md where it exists), the
                   sources of the module's chapters, and everything needed to BUILD them;
                   content.tex and web.tex are generated — the chapters are a subset, and the
                   export's web build must link readers at the export.
  paper/, figures/ the article's sources and the built PDF.
  notes/           the process account, the response plans and the reviews, from the module's
                   records directory.
  CHANGELOG.md     the release entry only; README.md generated; LICENSES/ copied.

The closure is computed from the blueprint, so the export follows the tags: a node moved out of
the release's chapters leaves the export at the next run. Every run also regenerates
`<lean>/INDEX.md`, the map from blueprint nodes to declarations to modules over all chapters.
"""
from __future__ import annotations

import collections
import datetime
import io
import json
import re
import shutil
import subprocess
import tarfile
from dataclasses import dataclass
from pathlib import Path

from .config import Config, Module

# The blueprint files the export needs in order to BUILD, not merely to be read: print.tex is
# the pdflatex driver, plastex.cfg and the style files the web driver that renders the
# dependency graph. Both drivers \input content.tex, and the web driver is web.tex; those two
# are GENERATED rather than copied — the first because the export carries a subset of the
# chapters, the second because its \home/\github/\dochome must name the export repository.
BLUEPRINT_SUPPORT = [
    "macros.tex",
    "theorems.tex",
    "theorems-extra.tex",
    "linkage-macros.tex",
    "blueprint.sty",
    "extra_styles.css",
    "plastex.cfg",
    "print.tex",
    "latexmkrc",
]

GUARD_NAME = "CIAxiomGuard.lean"
LOGICAL_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}

LABEL_RE = re.compile(r"\\label\{([^}]*)\}")
USES_RE = re.compile(r"\\(?:uses|proves)\{([^}]*)\}")
URL_MACROS = ("home", "github", "dochome")
URL_MACRO_RE = re.compile(r"^\\(" + "|".join(URL_MACROS) + r")\{[^}]*\}", re.M)
LEAN_RE = re.compile(r"\\lean\{([^}]*)\}", re.S)
IMPORT_RE = re.compile(r"^import\s+(\S+)", re.M)

# linkage's marker grammar (artifacts.MARKER_RE): labels, optionally pinned to a sha, comma-separated.
_REF = r"[a-z]+:[\w-]+(?:@[0-9a-f]{12})?"
SHARED_RE = re.compile(
    r"%[^\n]*?shared[^\n]*?with blueprint\s+(" + _REF + r"(?:\s*,\s*" + _REF + r")*)")

DRAFT_MARKS = ("working draft", "not yet released")

# A module's own tags: an optional module prefix (empty for the first module's plain `vX.Y`,
# `cone-` or `selection-` for the others) before the `vMAJOR.MINOR` the export's tag carries.
TAG_RE = re.compile(r"^(?P<prefix>[a-z]+-)?v(?P<major>\d+)\.(?P<minor>\d+)$")


class ReleaseError(RuntimeError):
    """A fault the run cannot go on from; the CLI prints it and exits 2."""


def strip_comments(text: str) -> str:
    out = []
    for line in text.splitlines():
        if line.lstrip().startswith("%"):
            out.append("")
        else:
            out.append(line.split("%", 1)[0])
    return "\n".join(out)


def decl_pattern(short: str) -> re.Pattern[str]:
    return re.compile(
        r"^\s*(?:@\[[^\]]*\]\s*)?(?:noncomputable\s+)?(?:protected\s+)?(?:private\s+)?"
        r"(?:theorem|lemma|def|abbrev|structure|class|axiom|instance|opaque)\s+"
        + re.escape(short) + r"\b", re.M)


def find_modules(name: str, mods: dict[str, str], libraries: tuple[str, ...] = (),
                 shared_packages: tuple[str, ...] = ()) -> list[str]:
    """Modules defining the declaration's short name.

    A library prefix on the tag restricts the hits to that library (the interface axioms are
    declared in both the real library and the skeleton). A prefix naming a *shared* Lake
    package (`paths.lean_packages`) names a declaration that is not in this tree at all.
    """
    for pkg in shared_packages:
        if name.startswith(pkg + "."):
            return []
    short = name.split(".")[-1]
    pat = decl_pattern(short)
    hits = [m for m, t in mods.items() if pat.search(t)]
    for lib in libraries:
        if name.startswith(lib + "."):
            narrowed = [m for m in hits if m.startswith(lib + ".")]
            return narrowed or hits
    return hits


def closure_of(roots: list[str], mods: dict[str, str]) -> tuple[set[str], dict[str, str | None]]:
    parent: dict[str, str | None] = dict.fromkeys(roots)
    seen: set[str] = set()
    queue = collections.deque(roots)
    while queue:
        m = queue.popleft()
        if m in seen or m not in mods:
            continue
        seen.add(m)
        for i in IMPORT_RE.findall(mods[m]):
            if i in mods and i not in parent:
                parent[i] = m
                queue.append(i)
    return seen, parent


# ---- the release gate ------------------------------------------------------------------------

def earlier_release_tag(tag: str, root: Path) -> str | None:
    """The module's own first-release tag, if `tag` names a later release of it (`cone-v0.1`
    for `cone-v0.2`) — the earliest git tag that shares `tag`'s module prefix and names a lower
    version. None if `tag` itself is the module's first release, or names no earlier tag (git
    has none to read, or the tag does not parse as <module->vX.Y)."""
    m = TAG_RE.match(tag)
    if not m:
        return None
    prefix, this = m.group("prefix") or "", (int(m.group("major")), int(m.group("minor")))
    try:
        out = subprocess.run(["git", "tag", "-l"], cwd=root, capture_output=True,
                             text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    earlier = []
    for t in out.split():
        tm = TAG_RE.match(t)
        if tm and (tm.group("prefix") or "") == prefix:
            v = (int(tm.group("major")), int(tm.group("minor")))
            if v < this:
                earlier.append((v, t))
    return min(earlier)[1] if earlier else None


def first_release_line(first_tag: str, root: Path) -> tuple[str, str | None]:
    """(version, date) naming the module's first release the way a later date line should read
    it: version as `vX.Y`, date as `Month D, YYYY`. The date is read from CHANGELOG.md's entry
    headed `## <first_tag> — YYYY-MM-DD — ...`, or, where the changelog carries none, the tag's
    own commit date."""
    version = "v" + first_tag.rsplit("v", 1)[-1]
    iso = None
    changelog = root / "CHANGELOG.md"
    if changelog.exists():
        m = re.search(r"(?m)^## " + re.escape(first_tag) + r" — (\d{4}-\d{2}-\d{2}) —",
                      changelog.read_text(encoding="utf-8"))
        if m:
            iso = m.group(1)
    if iso is None:
        try:
            iso = subprocess.run(["git", "log", "-1", "--format=%as", first_tag], cwd=root,
                                 capture_output=True, text=True,
                                 check=True).stdout.strip() or None
        except (OSError, subprocess.CalledProcessError):
            iso = None
    if iso is None:
        return version, None
    d = datetime.datetime.strptime(iso, "%Y-%m-%d").date()
    return version, f"{d:%B} {d.day}, {d:%Y}"


def version_history_text(paper: Path) -> str | None:
    r"""The text of the paper's `\section*{Version history}` (RELEASE.md rule 6; comments
    stripped, so a template's commented worked example never counts as an entry), from the
    marker to the end of the file that carries it; None if no source file has the section."""
    for f in sorted(paper.glob("*.tex")):
        text = strip_comments(f.read_text(encoding="utf-8"))
        m = re.search(r"\\section\*\{Version history\}", text)
        if m:
            return text[m.end():]
    return None


def release_gate(paper: Path, tag: str, root: Path, doi: str | None = None) -> list[str]:
    r"""What keeps a build from being a release: the faults of the paper's date line and PDF.

    A release PDF prints its date and version (RELEASE.md rule 5) and, where the DOI was
    reserved first (`linkage release zenodo reserve`), its DOI. Two first tags went on builds
    that still said "working draft", so this is checked by the tooling and not left to a
    checklist.

    **Rule 6 (RELEASE.md), the later-release gate:** a release after the module's first also
    names that first release in the date line — its version and its date — and closes with a
    version-history entry for the version being exported. A first release is exempt from both,
    the same way it is exempt from having a version history section at all; and a date line
    still marked as a draft is faulted on its own terms rather than piling rule 6 on top.

    An empty list means the build can be released.
    """
    faults = []
    main = paper / "main.tex"
    version = "v" + tag.rsplit("v", 1)[-1]
    name = paper.name
    if not main.exists():
        return [f"{name}/main.tex does not exist"]
    # The last \date{...} outside a comment, with its braces matched, so that the release form,
    # which carries the DOI on a second line, is read whole.
    date = None
    live = "\n".join("" if ln.lstrip().startswith("%") else ln
                     for ln in main.read_text(encoding="utf-8").splitlines())
    for m in re.finditer(r"\\date\{", live):
        depth, i = 1, m.end()
        while i < len(live) and depth:
            depth += {"{": 1, "}": -1}.get(live[i], 0)
            i += 1
        if depth == 0:
            date = " ".join(live[m.end():i - 1].split())
    if date is None:
        faults.append(f"{main.name} has no \\date line")
    else:
        draft_marked = any(k in date.lower() for k in DRAFT_MARKS)
        if draft_marked:
            faults.append(f"the date line of {name}/main.tex still reads \"{date}\": set the "
                          f"release date and the version, e.g. \\date{{September 19, 2026 "
                          f"({version})}}, with the DOI if one is reserved, and keep the draft "
                          f"line in a comment")
        elif version not in date:
            faults.append(f"the date line \"{date}\" does not name the version {version}")
        if doi and doi not in main.read_text(encoding="utf-8"):
            faults.append(f"--doi {doi} is not printed by {name}/main.tex")
        if not draft_marked:
            first_tag = earlier_release_tag(tag, root)
            if first_tag is not None:
                first_version, first_date = first_release_line(first_tag, root)
                if first_version not in date:
                    faults.append(f"the date line does not name the first release's version "
                                  f"{first_version} (this release, {version}, is a later "
                                  f"release of the module first released as {first_tag})")
                if first_date and first_date not in date:
                    faults.append(f"the date line does not name the first release's date "
                                  f"{first_date} (first released as {first_tag})")
                vh = version_history_text(paper)
                if vh is None:
                    faults.append(f"{name} has no \"Version history\" section: required for a "
                                  f"release after the module's first ({first_tag}); "
                                  f"article-kit's scaffold/paper/version-history.tex.in is "
                                  f"the template")
                elif version not in vh:
                    faults.append(f"the \"Version history\" section names no entry for {version}")
    pdf = paper / "main.pdf"
    if not pdf.exists():
        faults.append(f"{name}/main.pdf does not exist: build the paper into its own directory "
                      f"(tectonic {name}/main.tex)")
        return faults
    sources = [f for f in paper.iterdir() if f.suffix in {".tex", ".bib", ".sty", ".cls"}]
    newest = max(sources, key=lambda f: f.stat().st_mtime)
    if newest.stat().st_mtime > pdf.stat().st_mtime:
        faults.append(f"{name}/main.pdf is older than {newest.name}: rebuild it")
    try:
        first = subprocess.run(["pdftotext", "-l", "1", str(pdf), "-"], capture_output=True,
                               text=True, encoding="utf-8", errors="replace",
                               check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        faults.append("pdftotext is not available, so the PDF's first page could not be read")
        return faults
    flat = " ".join(first.split()).lower()
    if any(k in flat for k in DRAFT_MARKS):
        faults.append(f"the first page of {name}/main.pdf says it is a working draft")
    elif version not in flat:
        faults.append(f"the first page of {name}/main.pdf does not print the version {version}")
    if doi and doi.lower() not in flat:
        faults.append(f"the first page of {name}/main.pdf does not print the DOI {doi}")
    return faults


# ---- reading the paper and the changelog -------------------------------------------------------

def plain_abstract(paper: Path, macros: dict[str, str] | None = None) -> str:
    """The paper's abstract as plain text, for the deposit's description. The article's own
    no-argument macros are expanded through `modules.abstract_macros`; one not named there is
    dropped, as `\\emph{}`-style wrappers are unwrapped."""
    main = paper / "main.tex"
    if not main.exists():
        return ""
    m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", main.read_text(encoding="utf-8"),
                  re.S)
    if not m:
        return ""
    t = "\n".join(ln for ln in m.group(1).splitlines() if not ln.lstrip().startswith("%"))
    for name, text in (macros or {}).items():
        t = re.sub(r"\\" + re.escape(name) + r"\{\}", text, t)
    for a, b in (("~", " "), (r"\\emph\{([^}]*)\}", r"\1"), (r"\$([^$]*)\$", r"\1"),
                 (r"\\[a-zA-Z]+\{\}", ""), (r"\\,", " ")):
        t = re.sub(a, b, t)
    return re.sub(r"\s+", " ", t).strip()


def paper_axiom_block(paper: Path, headline: str) -> str:
    """The `#print axioms` line for the headline declaration as the paper prints it in a
    verbatim block, whitespace-normalized; empty if the paper prints none."""
    for f in sorted(paper.glob("*.tex")):
        for m in re.finditer(r"\\begin\{verbatim\}(.*?)\\end\{verbatim\}",
                             f.read_text(encoding="utf-8"), re.S):
            if f"'{headline}'" in m.group(1):
                return re.sub(r"\s+", " ", m.group(1)).strip()
    return ""


def figure_files(paper: Path) -> list[Path]:
    r"""The files the paper's `\includegraphics` lines name, resolved through `\graphicspath`."""
    dirs = [paper]
    names: list[str] = []
    for f in sorted(paper.glob("*.tex")):
        t = f.read_text(encoding="utf-8")
        for m in re.finditer(r"\\graphicspath\{((?:\{[^}]*\})+)\}", t):
            dirs += [paper / d for d in re.findall(r"\{([^}]*)\}", m.group(1))]
        names += re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]*)\}", t)
    out = []
    for n in names:
        for d in dirs:
            if (d / n).is_file():
                out.append((d / n).resolve())
                break
    return sorted(set(out))


def changelog_entry(src: Path, tag: str, warn=print) -> str:
    """The '## ' section whose heading names the tag (the release entry). One changelog serves
    every module of a repository, so the entry is not always the first section."""
    text = src.read_text(encoding="utf-8")
    parts = re.split(r"(?m)^## ", text)
    head = parts[0]
    for sec in parts[1:]:
        if tag in sec.splitlines()[0]:
            return head.rstrip() + "\n\n## " + sec.rstrip() + "\n"
    warn(f"changelog: no '## ' heading names {tag}; the export carries the header alone")
    return head.rstrip() + "\n"


def cited_doi(tag: str, root: Path) -> str | None:
    """The concept DOI the changelog records for the release tagged `tag`; None if there is no
    such section or it names no concept DOI. The export's README cites this DOI beside the tag."""
    changelog = root / "CHANGELOG.md"
    if not changelog.exists():
        return None
    parts = re.split(r"(?m)^## ", changelog.read_text(encoding="utf-8"))
    for sec in parts[1:]:
        if tag in sec.splitlines()[0]:
            m = re.search(r"concept DOI\s+(10\.\d{4,9}/[^\s*]+)", sec)
            return m.group(1) if m else None
    return None


# ---- generated files ---------------------------------------------------------------------------

def export_content_tex(files: list[str], tag: str) -> str:
    r"""The export's blueprint/src/content.tex: the release's chapters, in order.

    The chapter counter is set before every part rather than once at the top as the
    development's content.tex does. The development inputs its chapters consecutively, so a
    single \setcounter suffices there; an export may carry a gap, and a gap would renumber
    every chapter after it. Numbering must not drift: the paper cites its statements by number,
    and the README's table names blueprint nodes by chapter."""
    lines = [
        "% GENERATED by `linkage release export` in the development repository. Do not edit.",
        "%",
        f"% The chapters of release {tag}, in reading order. The counter is set before each part",
        "% so the numbers match the development's blueprint exactly, whatever subset is exported.",
        "",
        "\\input{theorems-extra.tex}",
        "",
    ]
    for name in files:
        lines.append(f"\\setcounter{{chapter}}{{{int(name[:2]) - 1}}}")
        lines.append(f"\\input{{parts/{name}}}")
    return "\n".join(lines) + "\n"


def export_web_tex(source: Path, repo_url: str) -> str:
    """The export's blueprint/src/web.tex: the development's, with the three repository URLs
    repointed at the export. Rewritten rather than templated so that the original's comments —
    chiefly the load-order warning about macros.tex after the package — travel with it."""
    text = source.read_text(encoding="utf-8")
    seen = set()

    def repoint(m: re.Match) -> str:
        seen.add(m.group(1))
        return f"\\{m.group(1)}{{{repo_url}}}"

    text = URL_MACRO_RE.sub(repoint, text)
    missing = [m for m in URL_MACROS if m not in seen]
    if missing:
        named = ", ".join("\\" + m for m in missing)
        raise ReleaseError(
            f"web.tex: no {named} to repoint at the export — the export would "
            f"link readers into the private development repository")
    return ("% GENERATED by `linkage release export` from the development's web.tex, with the\n"
            "% repository URLs repointed at this export. Do not edit.\n" + text)


def root_file(original: Path, exported: set[str], prefix: str) -> str:
    """The library root: the original's import order, restricted to exported modules."""
    header, imports = [], []
    for line in original.read_text(encoding="utf-8").splitlines():
        m = IMPORT_RE.match(line)
        if m:
            if m.group(1) in exported:
                imports.append(line)
        elif not imports:
            header.append(line)
    listed = {ln.split()[1] for ln in imports}
    for m in sorted(exported):
        if m.startswith(prefix + ".") and m not in listed:
            imports.append(f"import {m}")
    return "\n".join(header + imports) + "\n"


def copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def write(dst: Path, text: str) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding="utf-8", newline="\n")


def _normalize_eol(s: str) -> str:
    return s.replace("\r\n", "\n").replace("\r", "\n")


def compare_to_cited(exported: set[str], mods: dict[str, str], cited_exported: set[str],
                     cited_mods: dict[str, str]) -> tuple[list[str], list[str]]:
    """(cited, differing) for one `--cites` tag: of THIS export's own closure, the modules the
    cited tag's export also carries — a module the cited export does not carry is not treated as
    cited, whatever import edge brought it into this closure — are `cited` when byte-identical to
    the cited tag's file (line endings normalized), and `differing` otherwise. A non-empty
    `differing` must fail the run."""
    cited, differing = [], []
    for m in sorted(exported):
        if m not in cited_exported:
            continue
        if _normalize_eol(mods[m]) == _normalize_eol(cited_mods[m]):
            cited.append(m)
        else:
            differing.append(m)
    return cited, differing


# ---- the export ---------------------------------------------------------------------------------

@dataclass
class Exporter:
    """One run of `linkage release export`, over one module of one article repository."""
    cfg: Config
    mod: Module
    out: Path | None = None
    tag: str = ""
    doi: str | None = None
    draft: bool = False
    shared_nodes: str = "omit"
    cites: tuple[str, ...] = ()
    log: object = print

    @property
    def root(self) -> Path:
        return self.cfg.root

    @property
    def form(self) -> Path:
        return self.cfg.lean

    @property
    def parts(self) -> Path:
        return self.cfg.blueprint.parent / "parts"

    @property
    def paper(self) -> Path:
        return self.root / self.mod.paper

    def libraries(self) -> tuple[str, ...]:
        """The tree's own Lake libraries: configured, or inferred as a directory `X/` under the
        Lean root beside a root file `X.lean`."""
        if self.cfg.lean_libraries:
            return self.cfg.lean_libraries
        return tuple(sorted(
            d.name for d in self.form.iterdir()
            if d.is_dir() and (self.form / f"{d.name}.lean").is_file()))

    # -- reading the blueprint ---------------------------------------------------------------

    def chapter_files(self, chapters: list[str]) -> list[str]:
        """`02` -> `02-preliminaries.tex`; a chapter with no file is an error."""
        out = []
        for ch in chapters:
            hits = sorted(self.parts.glob(f"{ch}-*.tex"))
            if len(hits) != 1:
                raise ReleaseError(
                    f"chapter {ch}: {len(hits)} files match "
                    f"{self.parts.relative_to(self.root).as_posix()}/{ch}-*.tex")
            out.append(hits[0].name)
        return out

    def label_chapters(self) -> dict[str, str]:
        """blueprint label -> chapter file, over every chapter."""
        out: dict[str, str] = {}
        for part in sorted(self.parts.glob("*.tex")):
            for m in LABEL_RE.finditer(strip_comments(part.read_text(encoding="utf-8"))):
                out.setdefault(m.group(1), part.name)
        return out

    def paper_shared_labels(self, paper: Path) -> list[str]:
        """The blueprint labels the paper's `% shared with blueprint` markers name (rule 4)."""
        labels: list[str] = []
        for f in sorted(paper.glob("*.tex")) if paper.is_dir() else []:
            for m in SHARED_RE.finditer(f.read_text(encoding="utf-8")):
                for ref in m.group(1).split(","):
                    labels.append(ref.strip().partition("@")[0])
        return labels

    def harvest_tags(self, chapters: list[str],
                     paper: Path) -> collections.OrderedDict[str, tuple[str, str]]:
        """declaration -> (chapter file, node label) for the release's nodes: every node of the
        release's chapters, and every node of another chapter that the paper shares; the paper's
        markers are the record of the latter, not a table here."""
        decls: collections.OrderedDict[str, tuple[str, str]] = collections.OrderedDict()

        def one(ch: str, only: set[str] | None):
            text = strip_comments((self.parts / ch).read_text(encoding="utf-8"))
            for label, d in _tagged(text, only):
                decls.setdefault(d, (ch, label))

        files = self.chapter_files(chapters)
        for ch in files:
            one(ch, None)
        where = self.label_chapters()
        outside: dict[str, set[str]] = collections.defaultdict(set)
        for label in self.paper_shared_labels(paper):
            ch = where.get(label)
            if ch is not None and ch not in files:
                outside[ch].add(label)
        for ch, labels in sorted(outside.items()):
            one(ch, labels)
        return decls

    def harvest_all_tags(self) -> collections.OrderedDict[str, list[tuple[str, str]]]:
        """declaration -> [(chapter file, node label)] over every chapter (for the index)."""
        decls: collections.OrderedDict[str, list[tuple[str, str]]] = collections.OrderedDict()
        for part in sorted(self.parts.glob("*.tex")):
            text = strip_comments(part.read_text(encoding="utf-8"))
            for label, d in _tagged(text, None):
                decls.setdefault(d, []).append((part.name, label))
        return decls

    def dangling_uses(self, files: list[str]) -> dict[str, list[str]]:
        """Labels the exported chapters depend on that the export does not define, as
        {label: [chapter files that reference it]}. These are not an error — a restricted export
        of a larger development is expected to reference what it does not carry — but they are
        edges the published dependency graph cannot draw, so the run says so out loud."""
        inside, refs = set(), collections.defaultdict(list)
        for name in files:
            text = strip_comments((self.parts / name).read_text(encoding="utf-8"))
            inside.update(m.group(1) for m in LABEL_RE.finditer(text))
        for name in files:
            text = strip_comments((self.parts / name).read_text(encoding="utf-8"))
            for m in USES_RE.finditer(text):
                for ref in m.group(1).split(","):
                    ref = ref.strip()
                    if ref:
                        refs[ref].append(name)
        return {ref: sorted(set(where)) for ref, where in sorted(refs.items()) if ref not in inside}

    # -- reading the Lean tree ---------------------------------------------------------------

    def module_path(self, m: str) -> Path:
        return self.form / (m.replace(".", "/") + ".lean")

    def lean_modules(self) -> dict[str, str]:
        mods = {}
        for lib in self.libraries():
            for f in (self.form / lib).glob("**/*.lean"):
                rel = f.relative_to(self.form).with_suffix("")
                mods[".".join(rel.parts)] = f.read_text(encoding="utf-8", errors="replace")
        return mods

    def find(self, name: str, mods: dict[str, str]) -> list[str]:
        return find_modules(name, mods, self.libraries(), self.cfg.lean_packages)

    def closure_for(self, chapters: list[str], paper: Path, roots: list[str],
                    mods: dict[str, str]):
        tags = self.harvest_tags(chapters, paper)
        root_mods: collections.OrderedDict[str, list[str]] = collections.OrderedDict()
        missing = []
        for d in tags:
            hits = self.find(d, mods)
            if not hits:
                missing.append(d)
            for h in hits:
                root_mods.setdefault(h, []).append(d)
        for m in roots:
            root_mods.setdefault(m, [])
        exported, parent = closure_of(list(root_mods), mods)
        return tags, root_mods, missing, exported, parent

    # -- a cited release's closure, as it stood at its tag ------------------------------------

    def read_tree(self, tag: str) -> dict[str, str]:
        """path -> text, for every regular file at `tag` (`git archive`, read entirely in
        memory: no checkout, nothing left on disk)."""
        r = subprocess.run(["git", "archive", tag], cwd=self.root, capture_output=True, check=True)
        tree: dict[str, str] = {}
        with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tf:
            for member in tf.getmembers():
                if member.isfile():
                    data = tf.extractfile(member)
                    if data is not None:
                        tree[member.name] = data.read().decode("utf-8", errors="replace")
        return tree

    def tag_closure(self, tag: str, chapters: tuple[str, ...], paper_dir: str,
                    roots: tuple[str, ...]) -> tuple[set[str], dict[str, str]]:
        """A module's own import closure as it stood at `tag`: the same harvest/closure pipeline
        the working tree gets, over that module's OWN parameters, but every file read from
        `tag`'s git tree instead of disk."""
        tree = self.read_tree(tag)
        parts_rel = self.parts.relative_to(self.root).as_posix()
        lean_rel = self.form.relative_to(self.root).as_posix()

        def chapter_file(ch: str) -> str:
            hits = sorted(p for p in tree
                          if re.fullmatch(rf"{re.escape(parts_rel)}/{ch}-[^/]*\.tex", p))
            if len(hits) != 1:
                raise ReleaseError(f"--cites {tag}: chapter {ch}: {len(hits)} files match "
                                   f"{parts_rel}/{ch}-*.tex at {tag}")
            return hits[0]

        chapter_names = [Path(chapter_file(c)).name for c in chapters]

        label_chapter: dict[str, str] = {}
        for p, text in tree.items():
            if p.startswith(parts_rel + "/") and p.endswith(".tex"):
                for m in LABEL_RE.finditer(strip_comments(text)):
                    label_chapter.setdefault(m.group(1), Path(p).name)

        shared_labels: list[str] = []
        for p, text in tree.items():
            if p.startswith(paper_dir + "/") and p.endswith(".tex"):
                for m in SHARED_RE.finditer(text):
                    for ref in m.group(1).split(","):
                        shared_labels.append(ref.strip().partition("@")[0])

        decls: collections.OrderedDict[str, tuple[str, str]] = collections.OrderedDict()

        def harvest(ch_name: str, only: set[str] | None) -> None:
            text = strip_comments(tree[f"{parts_rel}/{ch_name}"])
            for label, d in _tagged(text, only):
                decls.setdefault(d, (ch_name, label))

        for ch_name in chapter_names:
            harvest(ch_name, None)
        outside: dict[str, set[str]] = collections.defaultdict(set)
        for label in shared_labels:
            ch_name = label_chapter.get(label)
            if ch_name is not None and ch_name not in chapter_names:
                outside[ch_name].add(label)
        for ch_name, labels in sorted(outside.items()):
            harvest(ch_name, labels)

        libs = self.libraries()
        mods: dict[str, str] = {}
        for p, text in tree.items():
            if p.endswith(".lean") and any(p.startswith(f"{lean_rel}/{lib}/") for lib in libs):
                rel = Path(p[len(lean_rel) + 1:])
                mods[".".join(rel.with_suffix("").parts)] = text

        root_mods: collections.OrderedDict[str, list[str]] = collections.OrderedDict()
        for d in decls:
            for h in self.find(d, mods):
                root_mods.setdefault(h, []).append(d)
        for m in roots:
            root_mods.setdefault(m, [])
        exported, _ = closure_of(list(root_mods), mods)
        return exported, mods

    def cites_closure(self, tag: str) -> tuple[set[str], dict[str, str]]:
        """`tag_closure`, with that release's own chapters/paper/roots: the module whose tag
        prefix the tag carries, as its parameters stood at the tag (`modules.releases`)."""
        cited_mod = self.cfg.module_of_tag(tag)
        chapters, paper_dir, roots = cited_mod.parameters_at(tag)
        return self.tag_closure(tag, chapters, paper_dir, roots)

    def cites_report(self, tags: tuple[str, ...], exported: set[str], mods: dict[str, str]):
        """{tag: [cited modules, identical]} over every `--cites` tag, and the failure lines for
        every module that differs from what its cited tag ships."""
        cited: collections.OrderedDict[str, list[str]] = collections.OrderedDict()
        failures: list[str] = []
        for tag in tags:
            cited_exported, cited_mods = self.cites_closure(tag)
            hits, diffs = compare_to_cited(exported, mods, cited_exported, cited_mods)
            cited[tag] = hits
            failures += [f"{m} differs from its file at {tag}" for m in diffs]
        return cited, failures

    # -- the index ---------------------------------------------------------------------------

    def write_index(self, path: Path, mods: dict[str, str], marked: set[str],
                    marked_name: str) -> tuple[int, int, int]:
        """INDEX.md: statements to declarations to modules, and modules to statements."""
        tags = self.harvest_all_tags()
        rows, unfound, ambiguous = [], [], []
        by_module: dict[str, list[str]] = collections.defaultdict(list)
        for d, places in tags.items():
            hits = self.find(d, mods)
            if not hits:
                unfound.append((d, places))
                where = "*not found*"
            else:
                if len(hits) > 1:
                    ambiguous.append((d, hits))
                where = ", ".join(f"`{h}`" for h in sorted(hits))
            for ch, label in places:
                rows.append((ch, label, d, where))
                for h in hits:
                    if f"`{label}`" not in by_module[h]:
                        by_module[h].append(f"`{label}`")
        rows.sort(key=lambda r: (r[0], r[1], r[2]))
        shared = ", ".join(f"`{p}`" for p in self.cfg.lean_packages)
        out = [
            "# Index of the Lean development",
            "",
            f"Generated by `linkage release export --dry-run` on {datetime.date.today()} from "
            "the blueprint's `\\lean{}` tags and the files that define the tagged declarations; "
            "do not edit by",
            f"hand. A `●` marks a module in the import closure of module {marked_name}'s "
            "statements; the other modules' closures are printed by their own dry runs.",
            "Untagged helper declarations are not listed; use the language server for those.",
            "",
            "## Statements to declarations",
            "",
            "| chapter | node | declaration | module |",
            "|---|---|---|---|",
        ]
        out += [f"| {ch[:2]} | `{label}` | `{d}` | {where} |" for ch, label, d, where in rows]
        out += ["", "## Modules to statements", "",
                "| module | release | statements served |", "|---|---|---|"]
        for m in sorted(mods):
            served = ", ".join(by_module.get(m, [])) or "—"
            out.append(f"| `{m}` | {'●' if m in marked else ''} | {served} |")
        if unfound:
            out += ["", "## Tagged declarations found in no module of this tree", "",
                    (f"Names in {shared} live in a shared package; anything else is a"
                     if shared else "A name here is a"),
                    "skeleton name that moved when proved, or a typo. `linkage check` is the "
                    "authority.", ""]
            out += [f"- `{d}` ({', '.join(f'{ch[:2]} {label}' for ch, label in places)})"
                    for d, places in unfound]
        if ambiguous:
            out += ["", "## Declarations whose short name is defined in more than one module", "",
                    "The tag names one of them; the table above lists all, so read the "
                    "namespace.", ""]
            out += [f"- `{d}`: " + ", ".join(f"`{h}`" for h in hits) for d, hits in ambiguous]
        write(path, "\n".join(out) + "\n")
        return len(rows), len(unfound), len(ambiguous)

    # -- generated Lean and metadata ---------------------------------------------------------

    def guard_file(self, exported: set[str], mods: dict[str, str]) -> tuple[str, int, int]:
        """The development's axiom guard, restricted to the exported declarations."""
        src_path = self.form / GUARD_NAME
        if not src_path.exists():
            raise ReleaseError(f"{src_path} does not exist: the export has no axiom guard to "
                               f"restrict (RELEASE.md checklist item 5)")
        kept, dropped = [], 0
        exported_text = {m: mods[m] for m in exported}
        for line in src_path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"#print axioms\s+(\S+)", line)
            if not m:
                continue
            name = m.group(1)
            hits = self.find(name, exported_text)
            inner = name.split(".")[1:-1]      # namespaces between the library and the short name
            if inner:
                # A qualified name must not be kept because some exported module defines a
                # top-level declaration of the same short name: ask for the qualified
                # declaration, or for the short one inside the innermost namespace.
                qualified = decl_pattern(".".join(inner) + "." + name.split(".")[-1])
                ns = re.compile(r"^namespace\s+(?:\S+\.)?" + re.escape(inner[-1]) + r"\s*$", re.M)
                short_pat = decl_pattern(name.split(".")[-1])
                hits = [h for h, t in exported_text.items()
                        if qualified.search(t) or (ns.search(t) and short_pat.search(t))]
            if hits:
                kept.append(line)
            else:
                dropped += 1
        libs = [lib for lib in self.libraries()
                if any(m.startswith(lib + ".") for m in exported)]
        imports = "\n".join(f"import {lib}" for lib in libs) or ""
        head = (
            f"/-\nCopyright (c) {self.copyright_line()}. All rights reserved.\n"
            "Released under the Apache 2.0 license as described in the file "
            "LICENSES/Apache-2.0.txt.\n"
            f"Authors: {self.author_line()}\n-/\n{imports}\n/-!\n"
            "# The trust-boundary guard (release export)\n\n"
            f"`lake env lean {GUARD_NAME}` prints the axiom usage of every named declaration of "
            "this\nexport. Every axiom that appears must be one of Lean's three logical axioms "
            "or a name declared\nin `blueprint/trust-boundary.txt` (the interface names of the "
            f"full development; the paper's\nsection {self.mod.axioms_section} says which of "
            "them its theorems rest on). The list is the development\nrepository's guard "
            "restricted to the exported declarations; see README.md.\n-/\n\n")
        return head + "\n".join(kept) + "\n", len(kept), dropped

    def author_line(self) -> str:
        """The authors as a Lean header prints them, given name first."""
        names = []
        for c in self.cfg.release.creators:
            family, _, given = c["name"].partition(",")
            names.append(f"{given.strip()} {family.strip()}".strip() if given else c["name"])
        return ", ".join(names)

    def copyright_line(self) -> str:
        return self.cfg.release.copyright or f"{datetime.date.today():%Y} {self.author_line()}"

    def citation_files(self, out: Path) -> None:
        """CITATION.cff (GitHub's citation box) and .zenodo.json (the deposit's metadata, read by
        `linkage release zenodo` and by Zenodo's GitHub integration). Both are generated, so that
        the title, the version and the related identifiers cannot drift from the release."""
        rel, mod = self.cfg.release, self.mod
        version = self.tag.rsplit("v", 1)[-1]
        today = datetime.date.today().isoformat()
        related = []
        for item in mod.related:
            ident, _, relation = item.partition(":")
            related.append({"identifier": ident, "relation": relation or "references",
                            "scheme": "doi"})
        if mod.repo_url:
            related.append({"identifier": mod.repo_url, "relation": "isSupplementedBy",
                            "scheme": "url"})
        zen = {
            "title": mod.title,
            "upload_type": rel.upload_type,
            "publication_type": rel.publication_type,
            "description": "<p>" + plain_abstract(self.paper, mod.abstract_macros)
                           + "</p><p>This deposit is the article's verification export: the PDF, "
                             "its LaTeX source, the Lean 4 modules its statements rest on, the "
                             "trust boundary with the ledger of cited facts, the blueprint "
                             "chapters, the process account and the external reviews.</p>",
            "creators": [dict(c) for c in rel.creators],
            "version": version,
            "publication_date": today,
            "license": rel.license,
            "keywords": list(mod.keywords),
            "related_identifiers": related,
        }
        write(out / ".zenodo.json", json.dumps(zen, indent=2, ensure_ascii=False) + "\n")
        cff = ["cff-version: 1.2.0",
               "message: \"If you use this work, please cite it as below.\"",
               "title: \"" + mod.title.replace('"', "'") + "\"",
               "version: \"" + version + "\"", "date-released: " + today, "authors:"]
        for c in rel.creators:
            family, _, given = c["name"].partition(",")
            cff.append("  - family-names: " + (family.strip() or c["name"]))
            if given.strip():
                cff.append("    given-names: " + given.strip())
            if c.get("orcid"):
                cff.append("    orcid: \"https://orcid.org/" + c["orcid"] + "\"")
        if self.doi:
            cff.append("doi: \"" + self.doi + "\"")
        if mod.repo_url:
            cff.append("repository-code: \"" + mod.repo_url + "\"")
        cff.append("license: " + rel.license.upper().replace("-", "-"))
        write(out / "CITATION.cff", "\n".join(cff) + "\n")

    def git_rev(self) -> str:
        try:
            return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=self.root,
                                  capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return "unknown"


def _tagged(text: str, only: set[str] | None):
    r"""(label, declaration) for every `\lean{}` tag of a chapter's source, in reading order,
    each attached to the label that precedes it; `only` restricts to those labels."""
    events = [(m.start(), "label", m.group(1)) for m in LABEL_RE.finditer(text)]
    events += [(m.start(), "lean", m.group(1)) for m in LEAN_RE.finditer(text)]
    events.sort()
    label = None
    for _, kind, val in events:
        if kind == "label":
            label = val
            continue
        if only is not None and label not in only:
            continue
        for d in val.replace("\n", " ").split(","):
            d = d.strip()
            if d:
                yield label or "?", d


# ---- the run ------------------------------------------------------------------------------------

def export(cfg: Config, args) -> int:
    """`linkage release export`: the whole run, reports included. Returns the exit code."""
    mod = cfg.module(args.module)
    tag = args.tag or mod.tag
    if not tag:
        raise ReleaseError(
            f"module {mod.name!r} declares no `tag` in linkage.toml and none was given with "
            f"--tag; the tag names the changelog entry and the export's PDF")
    chapters = ([c.strip() for c in args.chapters.split(",") if c.strip()]
                if args.chapters else list(mod.chapters))
    if not chapters:
        raise ReleaseError(f"module {mod.name!r} names no `chapters` — the export would carry "
                           f"no blueprint source")
    ex = Exporter(cfg=cfg, mod=mod, out=Path(args.out).resolve() if args.out else None,
                  tag=tag, doi=args.doi, draft=args.draft,
                  shared_nodes=args.shared_nodes or mod.shared_nodes,
                  cites=tuple(args.cites or ()))
    out, paper = ex.out, ex.paper
    roots = ([r.strip() for r in args.roots.split(",") if r.strip()]
             if args.roots else list(mod.roots))
    first = cfg.modules[0]
    is_first = mod.name == first.name
    if not paper.is_dir():
        print(f"paper directory {mod.paper} does not exist yet: no shared markers, nothing to "
              f"export but the Lean")

    mods = ex.lean_modules()
    tags, root_mods, missing, exported, parent = ex.closure_for(chapters, paper, roots, mods)
    # The index marks the first module's release on every run, so the one generated file in the
    # development tree does not flip its marks with the module last exported.
    marked = exported if is_first else ex.closure_for(
        list(first.chapters), cfg.root / first.paper, list(first.roots), mods)[3]

    def chain(m: str) -> str:
        c = [m]
        while parent.get(c[-1]) is not None:
            c.append(parent[c[-1]])  # type: ignore[arg-type]
        return " <- ".join(c)

    print(f"chapters {', '.join(chapters)}, paper {mod.paper}: {len(tags)} tagged declarations, "
          f"{len(root_mods)} root modules, closure {len(exported)} of {len(mods)} modules")
    if missing:
        print("tagged declarations found in no module (skeleton names that moved, or typos):")
        for d in missing:
            print(f"  {d}  ({tags[d][0]} {tags[d][1]})")
    import_only = sorted(m for m in exported if m not in root_mods)
    print(f"import-only modules ({len(import_only)}):")
    for m in import_only:
        print(f"  {chain(m)}")

    # Which chapters each module of the closure serves, from every chapter's tags: a module whose
    # tagged statements all lie outside the module's chapters is a leak from another module; an
    # import-only module with no tag at all is judged by its name and its chain.
    served: dict[str, set[str]] = collections.defaultdict(set)
    for d, places in ex.harvest_all_tags().items():
        for m in ex.find(d, mods):
            for ch, _ in places:
                served[m].add(ch[:2])
    chset = set(chapters)
    cited_by_tag: collections.OrderedDict[str, list[str]] = collections.OrderedDict()
    cite_failures: list[str] = []
    if ex.cites:
        cited_by_tag, cite_failures = ex.cites_report(ex.cites, exported, mods)
        for t, ms in cited_by_tag.items():
            print(f"cited from {t} ({len(ms)}, identical): {', '.join(ms) if ms else '-'}")
        if cite_failures:
            print(f"--cites: {len(cite_failures)} module(s) do not match the tag they cite:")
            for f in cite_failures:
                print("  -", f)
    all_cited = {m for ms in cited_by_tag.values() for m in ms}
    # A root module defines a tagged declaration of the release (a shared node from another
    # chapter counts), so only import-only modules can leak; one cited and identical is reported
    # above instead of here.
    leaks = sorted(m for m in exported if m not in root_mods and served.get(m)
                   and not (served[m] & chset) and m not in all_cited)
    print(f"import-only modules whose tagged statements all lie outside chapters "
          f"{','.join(chapters)} ({len(leaks)}):")
    for m in leaks:
        print(f"  {m}  serves {','.join(sorted(served[m]))}  via {chain(m)}")
    untagged = sorted(m for m in exported if m not in served)
    print(f"modules of the closure with no tagged statement at all ({len(untagged)}): "
          f"{', '.join(untagged) or '-'}")
    if not is_first:
        beyond = sorted(exported - marked)
        print(f"beyond module {first.name}'s closure ({len(marked)} modules): "
              f"{len(beyond)} modules")
        for m in beyond:
            print(f"  {m}  serves {','.join(sorted(served.get(m, set()))) or '-'}")
        print(f"of module {first.name}'s closure, not in this one: {len(marked - exported)}")

    n_rows, n_unfound, n_amb = ex.write_index(ex.form / "INDEX.md", mods, marked, first.name)
    print(f"index: {(ex.form / 'INDEX.md').relative_to(cfg.root).as_posix()} written "
          f"({n_rows} node-declaration rows, {n_unfound} not found, {n_amb} ambiguous)")
    faults = release_gate(paper, tag, cfg.root, ex.doi) if paper.is_dir() else []
    if faults:
        print("release gate: this build is NOT a release"
              + (" (--draft: exported all the same)" if ex.draft else ""))
        for f in faults:
            print("    -", f)
    else:
        print("release gate: the date line and the PDF's first page carry the version"
              + (" and the DOI" if ex.doi else "; no --doi given, so no DOI was checked"))
    if args.dry_run:
        return 1 if cite_failures else 0
    if cite_failures:
        print("nothing exported: repair the --cites mismatch(es) above")
        return 1
    if faults and not ex.draft:
        print("nothing exported; repair the above, or pass --draft for a build that is not a "
              "release")
        return 1
    if out is None:
        raise ReleaseError("--out is required unless --dry-run")
    if faults:
        write(out / "DRAFT", "This export was written with --draft and is not a release:\n"
              + "".join(f"- {f}\n" for f in faults))
    elif (out / "DRAFT").exists():
        (out / "DRAFT").unlink()

    # ---- the Lean tree
    lean_name = ex.form.name
    for m in exported:
        copy(ex.module_path(m), out / lean_name / (m.replace(".", "/") + ".lean"))
    for name in ["lakefile.toml", "lakefile.lean", "lake-manifest.json", "lean-toolchain"]:
        if (ex.form / name).exists():
            copy(ex.form / name, out / lean_name / name)
    for lib in ex.libraries():
        if any(m.startswith(lib + ".") for m in exported) and (ex.form / f"{lib}.lean").exists():
            write(out / lean_name / f"{lib}.lean",
                  root_file(ex.form / f"{lib}.lean", exported, lib))
    guard, kept, dropped = ex.guard_file(exported, mods)
    write(out / lean_name / GUARD_NAME, guard)
    print(f"guard: {kept} #print axioms lines kept, {dropped} dropped (declarations of later "
          f"modules)")

    # ---- blueprint/
    # AXIOMS-verbatim.md is the ledger's companion: the sources' own wording beside each
    # paraphrase. It ships whenever it exists.
    bp_dir = cfg.blueprint.parent.parent          # blueprint/, above src/
    for src in (cfg.root / "blueprint" / "trust-boundary.txt", cfg.axioms, cfg.axioms_verbatim):
        if src and src.exists():
            copy(src, out / "blueprint" / src.name)

    # The release's OWN chapters, and — under --shared-nodes whole — the chapters that hold a
    # node the paper transcribes from elsewhere. `whole` is not the default: a chapter that
    # merely contains a shared node also contains everything else in that chapter, so the
    # artifact would render with broken references and would show material of a module that is
    # not released. The right answer is to extract the shared node alone, keeping its number;
    # that is not built yet, so the default omits them and says which.
    own = ex.chapter_files(chapters)
    exported_chapters = list(own)
    if ex.shared_nodes == "whole":
        extra = sorted({ch for ch, _ in tags.values()} - set(own))
        if extra:
            print(f"--shared-nodes whole: also exporting {', '.join(extra)} — check their prose "
                  "references resolve inside the export before releasing")
            exported_chapters += extra
    for ch in exported_chapters:
        copy(ex.parts / ch, out / "blueprint" / "src" / "parts" / ch)

    # Everything the two drivers need, then the two generated drivers themselves.
    for name in BLUEPRINT_SUPPORT:
        src = bp_dir / "src" / name
        if src.exists():
            copy(src, out / "blueprint" / "src" / name)
        else:
            print(f"blueprint/src/{name} is absent — the export's blueprint may not build")
    write(out / "blueprint" / "src" / "content.tex", export_content_tex(exported_chapters, tag))
    write(out / "blueprint" / "src" / "web.tex",
          export_web_tex(bp_dir / "src" / "web.tex", mod.repo_url))

    # Not an error: a restricted export is expected to rest on statements it does not carry.
    # But each one is an edge the published dependency graph cannot draw, and a reader of the
    # graph should not have to discover that by noticing an absence.
    outside = ex.dangling_uses(exported_chapters)
    if outside:
        print(f"{len(outside)} dependency edge(s) leave the export and will be absent from the "
              f"graph:")
        for ref, where in outside.items():
            print(f"    {ref}  (used in {', '.join(where)})")

    # ---- paper/, figures/ (the export keeps the directory name `paper/` whatever the source's)
    stem = mod.stem or cfg.slug
    if paper.is_dir():
        for f in paper.iterdir():
            if f.suffix in {".tex", ".bib", ".sty", ".cls"}:
                copy(f, out / "paper" / f.name)
        if (paper / "main.pdf").exists():
            copy(paper / "main.pdf", out / "paper" / "main.pdf")
            copy(paper / "main.pdf", out / f"{stem}-{tag}.pdf")
        figs = figure_files(paper)
        for f in figs:
            copy(f, out / "figures" / f.name)
        stems = {f.stem for f in figs}
        for f in (cfg.root / "scripts").glob("make-fig-*.py"):
            if f.stem.removeprefix("make-") in stems or not stems:
                copy(f, out / "scripts" / f.name)

    # ---- notes/, licences, changelog
    # The response plan may be several files, one per review round: the first is exported as
    # PLAN-review-response.md, the n-th as PLAN-review-response-round<n>.md.
    named = [(mod.process_file(), "PROCESS.md")] + [
        (q, "PLAN-review-response.md" if i == 0 else f"PLAN-review-response-round{i + 1}.md")
        for i, q in enumerate(mod.response_plan_files())]
    for src, name in named:
        if src is None:
            continue
        if (cfg.root / src).exists():
            copy(cfg.root / src, out / "notes" / name)
        else:
            print(f"notes: {src} does not exist; not exported")
    # The archive here is verbatim, and agents' reports name files by their path on the author's
    # machine. The public copy replaces those paths and says so at its head; nothing else in a
    # report is touched. The frozen review builds are local PDFs; the export carries the text.
    quoted = re.compile(r"`[A-Za-z]:[\\/](?:Users|My Drive)[^`\n]*`")
    bare = re.compile(r"[A-Za-z]:[\\/](?:Users|My Drive)[^\s`,;)]*")
    n_redacted = 0
    reviews = mod.reviews_dir()
    for f in (cfg.root / reviews).glob("*") if reviews else []:
        if not f.is_file() or f.suffix.lower() == ".pdf":
            continue
        dst = out / "notes" / "reviews" / f.name
        if f.suffix.lower() not in {".md", ".txt"}:
            copy(f, dst)
            continue
        text = f.read_text(encoding="utf-8")
        text, n1 = quoted.subn("`<local path>`", text)
        text, n2 = bare.subn("<local path>", text)
        if n1 + n2:
            note = (f"<!-- Export note: {n1 + n2} file path(s) on the author's machine were "
                    "replaced by <local path> in this public copy; nothing else was changed. "
                    "-->\n")
            n_redacted += n1 + n2
            write(dst, note + text)
        else:
            copy(f, dst)               # byte for byte, line endings included
    if n_redacted:
        print(f"reviews: {n_redacted} local path(s) replaced in the exported copies")
    for f in (cfg.root / "LICENSES").glob("*"):
        copy(f, out / "LICENSES" / f.name)
    if (cfg.root / "CHANGELOG.md").exists():
        write(out / "CHANGELOG.md", changelog_entry(cfg.root / "CHANGELOG.md", tag))
    write(out / ".gitignore", f"{lean_name}/.lake/\n*.olean\npaper/*.aux\npaper/*.log\n"
                              "paper/*.bbl\npaper/*.blg\npaper/*.out\n")

    # ---- CITATION.cff and .zenodo.json
    ex.citation_files(out)

    # ---- README.md
    write(out / "README.md", readme(ex, chapters, tags, exported, mods, cited_by_tag))
    print(f"exported to {out}")

    if not args.build:
        return 0
    return build_in_place(ex, out, paper)


def readme(ex: Exporter, chapters: list[str], tags, exported: set[str], mods: dict[str, str],
           cited_by_tag) -> str:
    """The export's README: what is here, how to verify it, and the statement-to-declaration
    table — generated, so that it cannot drift from the closure just computed."""
    mod, cfg = ex.mod, ex.cfg
    by_node: collections.OrderedDict[str, list[str]] = collections.OrderedDict()
    for d, (ch, label) in tags.items():
        if ex.find(d, {m: mods[m] for m in exported}):
            by_node.setdefault(f"{label} ({ch[:2]})", []).append(d)
    rows = "\n".join(f"| `{label}` | " + ", ".join(f"`{d}`" for d in ds) + " |"
                     for label, ds in by_node.items())
    headline = mod.headline or ""
    block = paper_axiom_block(ex.paper, headline) if headline else ""
    names = re.findall(r"[A-Za-z_][\w.]*", block.partition("[")[2]) if block else []
    ledger_names = [n for n in names if n not in LOGICAL_AXIOMS]
    section = mod.axioms_section
    if ledger_names:
        rest = (f"The last command prints, for `{headline}`, Lean's three logical axioms and\n"
                + ", ".join(f"`{n}`" for n in ledger_names)
                + f", and nothing else (the block printed in section {section}).")
        on = (f"The headline theorem, `{headline}`, rests on {len(ledger_names)} of them, and "
              f"section {section} of the paper says what the other results rest on.")
    elif headline:
        rest = (f"The last command prints, for `{headline}`, the axioms it rests on: Lean's "
                f"three\nlogical axioms and the interface names section {section} of the paper "
                f"lists.")
        on = (f"Section {section} of the paper says which of them the article's theorems rest "
              f"on.")
    else:
        rest = "The last command prints the axiom usage of every named declaration."
        on = f"Section {section} of the paper says which of them the article's theorems rest on."
    boundary_file = cfg.root / "blueprint" / "trust-boundary.txt"
    boundary = ([ln.strip() for ln in boundary_file.read_text(encoding="utf-8").splitlines()
                 if ln.strip() and not ln.lstrip().startswith("#")]
                if boundary_file.exists() else [])
    nums = [int(c) for c in chapters]
    sections = (f"sections {nums[0]}–{nums[-1]}"
                if nums == list(range(nums[0], nums[-1] + 1))
                else "sections " + ", ".join(str(n) for n in nums))
    cites_block = ""
    if ex.cites:
        lines = ["## Cited releases", "",
                 "Lean modules of another module's release, carried unchanged and checked "
                 "identical to it at export time (`--cites`); listed here rather than above, "
                 "since this module does not own them.", ""]
        for tag in ex.cites:
            doi = cited_doi(tag, cfg.root)
            lines.append(f"### `{tag}`" + (f" — DOI {doi}" if doi else ""))
            lines.append("")
            ms = cited_by_tag.get(tag, [])
            lines.append(", ".join(f"`{m}`" for m in ms) if ms else "*(none)*")
            lines.append("")
        cites_block = "\n".join(lines)
    lean_name = ex.form.name
    return f"""# {mod.title} — release {ex.tag}

This repository is the verification artifact of the article of the same name (the PDF is at the
root). It is an export of the development repository at revision `{ex.git_rev()}`, restricted to
what the article's statements rest on; the development repository also holds the material of
other modules of the same theory and stays private until they are released.

## What is here

- `{lean_name}/` — the Lean 4 development: the transitive import closure of every module that a
  numbered statement of the article names ({len(exported)} modules), with the toolchain pinned
  in-tree (`lean-toolchain`, `lake-manifest.json`).
- `{lean_name}/{GUARD_NAME}` — prints the axiom usage of every named declaration.
- `blueprint/trust-boundary.txt`, `blueprint/AXIOMS.md` — the {len(boundary)} interface names of
  the full development, each with the page-verified citation it rests on and the step it carries
  beyond its source; `blueprint/AXIOMS-verbatim.md`, where it is present, sets the sources' own
  wording beside each entry. {on}
- `blueprint/src/parts/` — the statements and proofs of record of the article's {sections} (the
  blueprint's chapters of the same numbers), with the `\\lean{{}}` tag naming the declaration
  behind each statement; a chapter of another module is included where the article transcribes a
  statement from it.
- `paper/`, `figures/` — the article's sources.
- `notes/` — the process account, the external reviews verbatim, and the response plan.

## Verifying

    cd {lean_name}
    lake exe cache get        # Mathlib's prebuilt oleans
    lake build
    lake env lean {GUARD_NAME}

{rest}

## Statements and declarations

| blueprint node (chapter) | declarations |
|---|---|
{rows}

{cites_block}## Licence

Lean sources under Apache 2.0, text under CC BY 4.0 (`LICENSES/`).
"""


def build_in_place(ex: Exporter, out: Path, paper: Path) -> int:
    """`--build`: link the shared package store, `lake build`, run the guard, and check the
    paper's printed `#print axioms` block against the guard's output."""
    print("linking the shared package store …", flush=True)
    # `lake-store` is a shell script with a `.cmd` wrapper beside it; Python's `subprocess` finds
    # neither by bare name on Windows, so the wrapper is named explicitly there.
    store = shutil.which("lake-store") or shutil.which("lake-store.cmd")
    if store is None:
        print("lake-store not on PATH; link the shared package store by hand before building")
    else:
        subprocess.run([store, "link", out.name], check=False)
    form = out / ex.form.name
    print("lake build …", flush=True)
    r = subprocess.run(["lake", "build"], cwd=form)
    if r.returncode != 0:
        print("lake build FAILED")
        return r.returncode
    print("guard …", flush=True)

    def run_guard():
        return subprocess.run(["lake", "env", "lean", GUARD_NAME], cwd=form,
                              capture_output=True, text=True, encoding="utf-8", errors="replace")

    r = run_guard()
    # The guard file is restricted by the declarations' SHORT names, so a line can survive whose
    # qualified name lives in a module the export does not carry. Lean names such a line exactly;
    # it is removed, reported, and the guard is run once more.
    unknown = re.findall(r"Unknown constant `([^`]+)`", r.stdout + r.stderr)
    if r.returncode != 0 and unknown:
        gpath = form / GUARD_NAME
        lines = gpath.read_text(encoding="utf-8").splitlines()
        drop = {f"#print axioms {u}" for u in unknown}
        write(gpath, "\n".join(ln for ln in lines if ln.strip() not in drop) + "\n")
        print(f"guard: {len(unknown)} line(s) named a declaration outside the export and were "
              f"removed: " + ", ".join(unknown))
        r = run_guard()
    write(out / "axioms.txt", r.stdout)
    if r.returncode != 0:
        errs = [ln for ln in (r.stdout + "\n" + r.stderr).splitlines() if "error" in ln]
        print("guard FAILED:\n" + "\n".join(errs[-20:]))
        return r.returncode
    headline = ex.mod.headline
    if not headline:
        print("the module names no headline declaration; the guard's output is in axioms.txt")
        return 0
    want = paper_axiom_block(paper, headline)
    got_m = re.search(r"'" + re.escape(headline) + r"' depends on axioms: \[[^\]]*\]", r.stdout)
    got = re.sub(r"\s+", " ", got_m.group(0)).strip() if got_m else ""
    if not want:
        print(f"the paper prints no #print axioms block for {headline}; the guard's line is\n"
              f" {got}")
        return 0
    print("paper block matches the guard" if want == got
          else f"MISMATCH\n paper: {want}\n guard: {got}")
    return 0 if want == got else 1
