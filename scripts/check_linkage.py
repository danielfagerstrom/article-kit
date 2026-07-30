#!/usr/bin/env python3
"""Blueprint <-> Lean <-> ledger <-> paper linkage checker.

The blueprint (blueprint/src/content.tex) is the source of truth. Each statement
node carries a canonical \\label, a \\lean{} pointer (with \\leanok / \\notready),
\\ledger{} grounding for [A] nodes, and \\notes{} for its wiki content note. This
script verifies the edges that live *inside this repository*:

  FATAL (exit 1 if any fail)
    1. every \\leanok node's \\lean{Decl} names a declaration that exists in Formalization/
    2. every \\ledger{AXX} (and legacy "ledger AXX" prose) resolves to an AXIOMS.md entry
    3. every paper "% shared with blueprint <label>" names a real blueprint statement label
    4. every \\command in a statement/proof is render-safe: defined in macros.tex or vetted
       in blueprint/render-allowlist.txt (the clean-render gate — pandoc silently DROPS
       unknown commands, argument and all, so this must be caught source-side)
    5. every statement node declares \\statusT or \\statusA (the hub's confidence grading
       keys on the projected status; WISHLIST 2026-07-26)
    6. every \\ledger-referenced AXIOMS.md entry carries a **Cite:** line (the manifest
       projects each entry's primary citekey + page anchor; WISHLIST 2026-07-26)
    7. every \\statusA node declares its assignment -- a "\\textbf{Assignment.}" clause in
       its status annotation naming at least one ledger entry (ADR-0011, 2026-07-30)

  ADVISORY (reported, non-fatal)
    - a *labelled* paper statement that shares a blueprint node but uses a different label
      (rename to the blueprint label for true single-sourcing). Prose that merely references a
      blueprint node -- nearest preceding label is a section, not a statement -- is a valid
      weaker link and is not advised.
    - a \\leanok node with no \\lean{}, or a node marked both \\leanok and \\notready

The wiki edge (\\notes{slug} <-> a Notes content note) is cross-repo; it is checked
only when --wiki PATH is given.

Usage
    python scripts/check_linkage.py                 # in-repo edges
    python scripts/check_linkage.py --wiki ~/Documents/Notes   # also the wiki edge

See blueprint/LINKAGE.md for the spec this enforces.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BLUEPRINT = REPO / "blueprint" / "src" / "content.tex"
AXIOMS = REPO / "blueprint" / "AXIOMS.md"
LEAN_DIR = REPO / "Formalization"
PAPER_DIR = REPO / "paper"

STMT_ENVS = ("definition", "lemma", "proposition", "theorem", "corollary")
# label prefixes that denote a statement (as opposed to a section/equation)
STMT_LABEL_RE = re.compile(r"^(?:thm|prop|def|lem|cor):")
# a Lean declaration keyword, allowing leading attributes / modifiers
DECL_RE = re.compile(
    r"(?m)^\s*(?:@\[[^\]]*\]\s*)?"
    r"(?:(?:private|protected|noncomputable|scoped|local|partial|unsafe)\s+)*"
    r"(?:theorem|lemma|def|abbrev|structure|instance|axiom)\s+([A-Za-z_][\w']*)"
)


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def read_blueprint() -> str:
    """content.tex, with `\\input{...}` includes inlined (the nodes live in parts/)."""
    inp = re.compile(r"^\s*\\input\{([^}]+)\}")

    def expand(path: Path) -> str:
        out = []
        for line in read(path).splitlines(keepends=True):
            m = inp.match(line)
            if m and not line.lstrip().startswith("%"):
                inc = m.group(1)
                if not inc.endswith(".tex"):
                    inc += ".tex"
                out.append(expand(path.parent / inc))
            else:
                out.append(line)
        return "".join(out)

    return expand(BLUEPRINT)


# --- Rendering (the transclusion fields; LINKAGE.md § cross-repo channel, ROADMAP #7 T1) ---
#
# The manifest carries, per label, an Obsidian-flavoured markdown rendering of the
# normalized statement/proof source, produced by a version-PINNED pandoc so the output is
# deterministic (`wiki lint` byte-compares transcluded blocks against it; a version drift
# would move every rendered_sha at once). Macro expansion is pandoc's own `latex_macros`
# extension, fed blueprint/src/macros.tex as a preamble — macros expand inside math too, so
# the output contains no unexpanded custom commands. `\ref{X}` is pre-passed to \texttt{X}
# (a code span — the way wiki notes write labels). Rendering degrades gracefully: no pandoc,
# or a version other than the pin, emits the manifest without rendered fields and warns;
# --require-render (CI) turns that, or any per-label render failure, into a hard error.

PANDOC_PIN = "3.10"
PANDOC_TARGET = "commonmark+tex_math_dollars"
MACROS = REPO / "blueprint" / "src" / "macros.tex"


def pandoc_version() -> str | None:
    try:
        r = subprocess.run(["pandoc", "--version"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=30)
        m = re.match(r"pandoc(?:\.exe)?\s+(\S+)", r.stdout) if r.returncode == 0 else None
        return m.group(1) if m else None
    except (OSError, subprocess.SubprocessError):
        return None


ALLOWLIST = REPO / "blueprint" / "render-allowlist.txt"


def render_safe_commands() -> set[str]:
    """Commands the render pipeline handles: macros.tex definitions + the vetted allowlist."""
    defined = set(re.findall(r"\\(?:new|provide|renew)command\{?\\([A-Za-z]+)", read(MACROS)))
    vetted = {
        line.strip()
        for line in read(ALLOWLIST).splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    return defined | vetted


def unknown_commands(src: str, known: set[str]) -> list[str]:
    """Commands in normalized statement/proof source the pipeline cannot render (gate 4)."""
    return sorted(set(re.findall(r"\\([A-Za-z]+)", src)) - known)


# math ($$…$$ then $…$) and code spans — regions where backslash commands are legitimate
_MATH_OR_CODE = re.compile(r"\$\$.*?\$\$|\$[^$\n]*?\$|`[^`\n]*`", re.S)


def render_residue(md: str) -> list[str]:
    """Raw LaTeX commands surviving outside math/code spans — the clean-render gate (T2).

    The preamble expands every custom macro and pandoc converts every standard construct,
    so a `\\command` in rendered prose means a node uses something the pipeline does not
    handle — it must fail CI (via --require-render) rather than reach the hub, where the
    transcluded block would show literal LaTeX to a reader."""
    return sorted(set(re.findall(r"\\[A-Za-z]+", _MATH_OR_CODE.sub(" ", md))))


def render_markdown(src: str, preamble: str) -> str:
    """Normalized statement/proof LaTeX -> markdown with $/$$ math (Obsidian dialect)."""
    src = re.sub(r"\\ref\{([^}]+)\}", r"\\texttt{\1}", src)
    r = subprocess.run(
        ["pandoc", "-f", "latex", "-t", PANDOC_TARGET, "--wrap=none"],
        input=preamble + "\n" + src + "\n",
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or f"pandoc exit {r.returncode}")
    return r.stdout.replace("\r\n", "\n").strip()


def normalize_statement(body: str) -> str:
    """The statement text of a node body, normalized for stable hashing.

    Strips LaTeX comments and the metadata commands (\\label/\\lean/\\uses/\\notes/\\ledger
    with their arguments; the bare \\notready/\\leanok tokens; \\statusT/\\statusA together
    with their trailing \\quad\\emph{...} status annotation — proof-status remarks, not
    statement content, so a status edit does not move the sha), then collapses all whitespace
    runs to single spaces. The mathematical prose and math are kept verbatim, so the text —
    and its sha — changes exactly when the statement's content does. Deterministic: a pure
    function of the body string, no environment input.
    """
    body = re.sub(r"(?<!\\)%[^\n]*", "", body)
    body = re.sub(r"\\(?:label|lean|uses|notes|ledger)\{[^}]*\}", "", body)
    # \statusT / \statusA plus the annotation that follows them: optional \quad / \qquad
    # spacing, then an optional \emph{...} group (balanced to two brace-nesting levels —
    # the annotations contain \texttt{...} / \ref{...}).
    body = re.sub(
        r"\\status[TA]\b(?:\s|\\quad\b|\\qquad\b)*"
        r"(?:\\emph\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\})?",
        "",
        body,
    )
    body = re.sub(r"\\(?:statusT|statusA|notready|leanok)\b", "", body)
    return re.sub(r"\s+", " ", body).strip()


def normalize_for_render(body: str) -> str:
    """The statement/proof source handed to pandoc — normalize_statement's sibling.

    Differs in exactly one way: an *in-prose* ``\\ledger{A2}`` renders as the text
    "ledger A2" (its PDF macro expansion) instead of being deleted — deletion leaves
    dangling punctuation in rendered proofs ("taken as an interface (, the Lean …)",
    found by the H5 migration). Ledger refs on the *status line* still vanish with it
    (the status-strip below tolerates \\ledger tokens between the \\quads). The sha
    fields keep using normalize_statement, so this changes rendered output only.
    """
    body = re.sub(r"(?<!\\)%[^\n]*", "", body)
    body = re.sub(r"\\(?:label|lean|uses|notes)\{[^}]*\}", "", body)
    body = re.sub(
        r"\\status[TA]\b(?:\s|\\quad\b|\\qquad\b|\\ledger\{[^}]*\})*"
        r"(?:\\emph\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\})?",
        "",
        body,
    )
    body = re.sub(r"\\(?:statusT|statusA|notready|leanok)\b", "", body)
    body = re.sub(r"\\ledger\{([^}]*)\}", r"ledger \1", body)
    return re.sub(r"\s+", " ", body).strip()


# The status annotation itself -- the `\emph{...}` that follows \statusT/\statusA (with
# \quad spacing and \ledger{} refs tolerated between). normalize_statement DELETES this
# region, so a status edit never moves a statement sha; check 7 needs it kept, because
# ADR-0011 puts the assignment declaration here. Same brace balancing as the strip.
STATUS_ANNOTATION_RE = re.compile(
    r"\\status[TA]\b(?:\s|\\quad\b|\\qquad\b|\\ledger\{[^}]*\})*"
    r"(\\emph\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\})?"
)
# ADR-0011: an [A] node declares, in that annotation, what its citation carries and what
# it does not. The marker is fixed so the checker can find it; the clause after it must
# name at least one ledger entry, since a declaration that names nothing declares nothing.
ASSIGNMENT_MARKER = r"\textbf{Assignment.}"


def status_annotation(body: str) -> str:
    m = STATUS_ANNOTATION_RE.search(body)
    return (m.group(1) or "") if m else ""


# a proof environment directly following a statement env (whitespace/comments between);
# non-greedy to the first \end{proof} — the blueprint does not nest proofs
PROOF_AHEAD = re.compile(r"(?:\s|%[^\n]*)*\\begin\{proof\}(.*?)\\end\{proof\}", re.S)


def blueprint_nodes(tex: str):
    """One dict per statement environment (plus its trailing proof, if any)."""
    nodes = []
    for m in re.finditer(
        r"\\begin\{(" + "|".join(STMT_ENVS) + r")\}(.*?)\\end\{\1\}", tex, re.S
    ):
        body = m.group(2)
        # the environment's optional [human title] is presentation metadata, not statement
        # content — split it out so it neither pollutes the statement text/sha nor renders
        # as escaped brackets; the hub's import renders it in the block header instead
        tm = re.match(r"\s*\[([^\]]*)\]", body)
        title = tm.group(1).strip() if tm else None
        if tm:
            body = body[tm.end():]
        pm = PROOF_AHEAD.match(tex, m.end())
        lab = re.search(r"\\label\{([^}]+)\}", body)
        decls = [
            d.strip()
            for dm in re.finditer(r"\\lean\{([^}]+)\}", body)
            for d in dm.group(1).split(",")
            if d.strip()
        ]
        uses = [
            u.strip()
            for um in re.finditer(r"\\uses\{([^}]+)\}", body)
            for u in um.group(1).split(",")
            if u.strip()
        ]
        nodes.append(
            {
                "env": m.group(1),
                "title": title,
                "label": lab.group(1) if lab else None,
                "lean": decls,
                "uses": uses,
                "leanok": r"\leanok" in body,
                "notready": r"\notready" in body,
                # [T]/[A] and the node's ledger refs — projected so the hub's generated
                # status line can say "cited interface (ledger A3)" instead of the
                # misleading "proved in Lean" on an accepted axiom (H5 finding)
                "status": ("T" if r"\statusT" in body
                           else "A" if r"\statusA" in body else None),
                "status_note": status_annotation(body),
                # de-duplicated, first-mention order: a node's \ledger{} may now appear
                # twice — once on the status line, once inside the Assignment clause that
                # says what that entry carries (LINKAGE.md rule 7) — and the hub projects
                # this list as the node's sources, where a repeat is noise.
                "ledger": list(dict.fromkeys(re.findall(r"\\ledger\{([^}]*)\}", body))),
                "statement": normalize_statement(body),
                "proof": normalize_statement(pm.group(1)) if pm else None,
                "statement_render_src": normalize_for_render(body),
                "proof_render_src": normalize_for_render(pm.group(1)) if pm else None,
            }
        )
    return nodes


def ledger_refs(tex: str) -> set[str]:
    refs = set(re.findall(r"\\ledger\{([^}]+)\}", tex))
    refs |= set(re.findall(r"ledger~?\s*(A\d+)", tex))  # legacy prose
    return refs


def notes_slugs(tex: str) -> set[str]:
    return set(re.findall(r"\\notes\{([^}]+)\}", tex))


def lean_declared_names() -> set[str]:
    names: set[str] = set()
    for f in LEAN_DIR.rglob("*.lean"):
        if ".lake" in f.parts:
            continue
        names |= set(DECL_RE.findall(read(f)))
    return names


def ledger_keys() -> set[str]:
    return set(re.findall(r"(?m)^##\s*(A\d+)\b", read(AXIOMS)))


def ledger_cites() -> dict[str, dict | None]:
    """AXX -> {citekey, anchor} from each entry's ``**Cite:**`` line.

    The line's grammar (AXIOMS.md, backfilled 2026-07-26): ``**Cite:** @citekey — anchor``,
    optionally more ``·``-separated segments (corroborations); the FIRST segment is the
    primary and is what the manifest projects. ``**Cite:** — pending (…)`` yields null
    citekey/anchor; a missing line yields None (fatal check 6 flags it)."""
    out: dict[str, dict | None] = {}
    for m in re.finditer(r"(?ms)^##\s*(A\d+)\b(.*?)(?=^##\s*A\d+\b|\Z)", read(AXIOMS)):
        aid, body = m.group(1), m.group(2)
        cm = re.search(r"\*\*Cite:\*\*\s*(.+)", body)
        if not cm:
            out[aid] = None
            continue
        first = cm.group(1).split("·")[0].strip()
        km = re.match(r"@([\w:-]+)\s*[—–-]+\s*(.+)", first)
        out[aid] = ({"citekey": km.group(1), "anchor": km.group(2).strip()} if km
                    else {"citekey": None, "anchor": None})
    return out


def _git_provenance() -> dict:
    """The freshness stamp for the manifest: the short HEAD SHA and whether the working tree was
    dirty at emit time. Best-effort — degrades to a null commit if git is unavailable, so a
    manifest can still be emitted outside a checkout. `source_dirty` is whole-repo on purpose: the
    manifest projects labels, Lean decls, and scripts, so a change anywhere may not be captured by
    HEAD's SHA, and the honest signal is "this did not come from a clean commit." See the freshness
    note in blueprint/LINKAGE.md § "The cross-repo channel"."""
    def _git(*args: str) -> str | None:
        try:
            r = subprocess.run(["git", "-C", str(REPO), *args],
                               capture_output=True, text=True, timeout=10)
            return r.stdout.strip() if r.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            return None

    return {"source_commit": _git("rev-parse", "--short", "HEAD"),
            "source_dirty": bool(_git("status", "--porcelain"))}


def _sha12(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]


def build_manifest(nodes, lean_names: set[str], require_render: bool = False) -> dict:
    """Projection of the blueprint the wiki reads to resolve `claim/…` proof-refs.

    Same role as the librarian's library.json (citekeys): a generated, single-writer
    manifest another repo reads. `kind` is the label prefix (thm|prop|def|lem|cor) —
    exactly the token a wiki claim ref uses. `lean_decls` are short declaration names
    (matched on final component, as the in-repo \\lean{} check does). See blueprint/LINKAGE.md.

    Carries a freshness stamp (`generated_at`, `source_commit`, `source_dirty`) so the wiki can
    report where the manifest came from and how old it is, and never silently validate a note
    against a stale view.

    Each label also carries `uses` (the node's \\uses{} dependency labels, so blueprint-internal
    edges are verifiable vault-side), the normalized `statement` text, and `statement_sha` (a
    short sha256 of it) — the wiki's lint diffs mirrored statement blocks against the hash to
    catch silent drift. The normalization (`normalize_statement`) is deterministic, so the sha
    changes exactly when the statement's mathematical content does.

    Manifest v2 (ROADMAP #7 T1) adds the transclusion fields: per label, the normalized `proof`
    source + `proof_sha` (null when the node has no proof environment), and — when the pinned
    pandoc is available — `statement_md` / `proof_md` (Obsidian-dialect markdown, custom macros
    expanded) + `rendered_sha` over both, which is what the hub's `wiki import`/lint will
    byte-compare. Top-level `render` records the renderer provenance (null when rendering was
    skipped); `manifest_version` lets the hub detect the schema.
    """
    ver = pandoc_version()
    rendering = ver == PANDOC_PIN
    render_errors: list[str] = []
    if not rendering:
        msg = (f"pandoc {ver} found but pin is {PANDOC_PIN}" if ver
               else "pandoc not found on PATH")
        if require_render:
            raise RuntimeError(f"--require-render: {msg}")
        print(f"  warning: {msg} — manifest emitted without rendered fields", file=sys.stderr)
    preamble = read(MACROS) if rendering else ""
    cites = ledger_cites()

    labels: dict[str, dict] = {}
    for n in nodes:
        lab = n["label"]
        if not lab:
            continue
        entry = {
            "kind": lab.split(":", 1)[0],
            "env": n["env"],
            "title": n["title"],
            "status": n["status"],
            # each ledger ref carries the entry's primary citation (WISHLIST 2026-07-26),
            # so the hub can cross-check the citekey against library.json and show the
            # source in claim chips / block status lines
            "ledger": [
                {"id": a, **(cites.get(a) or {"citekey": None, "anchor": None})}
                for a in n["ledger"]
            ],
            "leanok": n["leanok"],
            "notready": n["notready"],
            "lean": n["lean"],
            "uses": n["uses"],
            "statement": n["statement"],
            "statement_sha": _sha12(n["statement"]),
            "proof": n["proof"],
            "proof_sha": _sha12(n["proof"]) if n["proof"] is not None else None,
            "statement_md": None,
            "proof_md": None,
            "rendered_sha": None,
        }
        if rendering:
            try:
                entry["statement_md"] = render_markdown(n["statement_render_src"], preamble)
                if n["proof"] is not None:
                    entry["proof_md"] = render_markdown(n["proof_render_src"], preamble)
                # titles are block-header text too — render them when they carry LaTeX
                # (accents, em-dashes); plain titles pass through without a pandoc call
                title = n["title"]
                entry["title_md"] = (
                    render_markdown(title, preamble)
                    if title and re.search(r"[\\{}]|--", title) else title
                )
                # rendered_sha covers EVERY input of the hub's block derivation (header,
                # status line, statement, proof) — so any change that alters the derived
                # block moves the sha, and the hub's lint reads it as *stale* (mechanical
                # refresh) rather than misclassifying it as a hand-edit. A leanok flip or
                # a title fix must never look like a violation.
                entry["rendered_sha"] = _sha12(json.dumps(
                    [entry["env"], entry["title_md"], entry["status"], entry["ledger"],
                     entry["lean"], entry["leanok"], entry["notready"],
                     entry["statement_md"], entry["proof_md"]],
                    ensure_ascii=False))
                residue = render_residue(
                    entry["statement_md"] + "\n" + (entry["proof_md"] or "")
                )
                if residue:
                    render_errors.append(
                        f"{lab}: raw LaTeX outside math/code: {', '.join(residue)}"
                    )
            except RuntimeError as e:
                render_errors.append(f"{lab}: {e}")
        labels[lab] = entry
    if render_errors:
        for e in render_errors:
            print(f"  warning: render failed for {e}", file=sys.stderr)
        if require_render:
            raise RuntimeError(
                f"--require-render: {len(render_errors)} label(s) failed to render"
            )
    scripts = (
        sorted(p.relative_to(REPO).as_posix() for p in (REPO / "scripts").glob("*.py"))
        if (REPO / "scripts").is_dir()
        else []
    )
    return {
        "generated_by": "scripts/check_linkage.py",
        "note": "Projection of blueprint/src/content.tex — generated, do not hand-edit.",
        "manifest_version": 2,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **_git_provenance(),
        "render": (
            {"renderer": "pandoc", "version": PANDOC_PIN,
             "target": PANDOC_TARGET, "wrap": "none"}
            if rendering else None
        ),
        "labels": labels,
        "lean_decls": sorted(lean_names),
        "scripts": scripts,
    }


def paper_shared():
    """(file, blueprint_key, nearest_preceding_paper_label)."""
    out = []
    for f in sorted(PAPER_DIR.glob("*.tex")):
        t = read(f)
        for m in re.finditer(
            r"%[^\n]*?shared[^\n]*?with blueprint\s+([a-z]+:[\w-]+)", t
        ):
            key = m.group(1)
            labs = re.findall(r"\\label\{([^}]+)\}", t[: m.start()])
            out.append((f.name, key, labs[-1] if labs else None))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--wiki", type=Path, help="Path to the Notes wiki (enables \\notes{} checking)"
    )
    ap.add_argument(
        "--emit-manifest",
        type=Path,
        metavar="PATH",
        help="Write the blueprint manifest (labels + leanok + Lean decls + uses + statement hashes) the wiki reads "
        "to resolve claim proof-refs, e.g. --emit-manifest ~/Documents/Notes/blueprint-manifest.json",
    )
    ap.add_argument(
        "--require-render",
        action="store_true",
        help="Fail (exit 2) unless the pinned pandoc renders every label's markdown fields — "
        "for CI, where a manifest without transclusion fields must never reach the hub.",
    )
    args = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    tex = read_blueprint()
    nodes = blueprint_nodes(tex)
    labels = {n["label"] for n in nodes if n["label"]}
    lean_names = lean_declared_names()
    axk = ledger_keys()

    if args.emit_manifest:
        try:
            manifest = build_manifest(nodes, lean_names, require_render=args.require_render)
        except RuntimeError as e:
            print(f"MANIFEST EMIT FAILED: {e}", file=sys.stderr)
            return 2
        args.emit_manifest.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        n_lab = sum(1 for n in nodes if n["label"])
        n_proof = sum(1 for n in nodes if n["label"] and n["proof"] is not None)
        rendered = "rendered" if manifest["render"] else "NOT rendered"
        print(f"Wrote manifest v2 ({n_lab} labels, {n_proof} proofs, {len(lean_names)} Lean decls, "
              f"markdown {rendered}) → {args.emit_manifest}")

    fatal: list[str] = []
    advisory: list[str] = []

    # 1. Lean decls of proved nodes exist
    for n in nodes:
        if n["leanok"] and not n["lean"]:
            advisory.append(f"[lean]   node '{n['label']}' is \\leanok but has no \\lean{{}}")
        if n["leanok"] and n["notready"]:
            advisory.append(f"[lean]   node '{n['label']}' marked both \\leanok and \\notready")
        if not n["leanok"]:
            continue  # \notready nodes may not have a Lean decl yet
        for d in n["lean"]:
            last = d.split(".")[-1]
            if last not in lean_names:
                fatal.append(
                    f"[lean]   {n['label']}: \\lean{{{d}}} not declared in {LEAN_DIR.name}/"
                )

    # 4. the clean-render gate: every command in a statement/proof is render-safe
    known = render_safe_commands()
    for n in nodes:
        for part, src in (("statement", n["statement"]), ("proof", n["proof"])):
            if not src:
                continue
            for c in unknown_commands(src, known):
                fatal.append(
                    f"[render] {n['label'] or n['env']}: \\{c} in {part} is not render-safe "
                    f"— add a \\newcommand to macros.tex or vet it in {ALLOWLIST.name}"
                )

    # 2. ledger refs resolve
    cites = ledger_cites()
    for a in sorted(ledger_refs(tex)):
        if a not in axk:
            fatal.append(f"[ledger] {a}: no '## {a}' entry in AXIOMS.md")
        elif cites.get(a) is None:
            # 6. the manifest projects each entry's primary citation — a referenced entry
            # without a **Cite:** line would emit an unverifiable bare id (WISHLIST 2026-07-26)
            fatal.append(f"[ledger] {a}: no '**Cite:**' line in AXIOMS.md "
                         "(format: '**Cite:** @citekey — anchor')")

    # 5. every node declares its [T]/[A] status — the hub's grading keys on it
    for n in nodes:
        if n["label"] and n["status"] is None:
            fatal.append(f"[status] {n['label']}: no \\statusT/\\statusA — every statement "
                         "node must declare one (WISHLIST 2026-07-26)")

    # 7. every [A] node declares its assignment (ADR-0011, hub adr/0011). The checker can
    # require that the judgement be written; it cannot make it, and it cannot tell a wrong
    # declaration from a right one. What it removes is the silent case -- an [A] statement
    # whose split between citation and [T] exists only in someone's head, which is how all
    # three defects of the 2026-07 ledger passes survived.
    for n in nodes:
        if n["status"] != "A" or not n["label"]:
            continue
        note = n["status_note"]
        head, _, clause = note.partition(ASSIGNMENT_MARKER)
        if not _:
            fatal.append(
                f"[assign] {n['label']}: [A] node with no '{ASSIGNMENT_MARKER}' clause in its "
                "status annotation -- say what the citation carries and what it does not "
                "(ADR-0011; blueprint/LINKAGE.md rule 7)"
            )
        elif not re.search(r"A\d+", clause):
            fatal.append(
                f"[assign] {n['label']}: the Assignment clause names no ledger entry -- it must "
                "say which entry carries which part of this statement (ADR-0011)"
            )

    # 3. paper shared statements
    for fn, key, nearest in paper_shared():
        if key not in labels:
            fatal.append(
                f"[paper]  {fn}: 'shared with blueprint {key}' but no such blueprint label"
            )
        elif nearest != key and nearest and STMT_LABEL_RE.match(nearest):
            advisory.append(
                f"[paper]  {fn}: labelled statement '{nearest}' shares blueprint '{key}' "
                f"(rename to the blueprint label for single-sourcing)"
            )

    # optional: wiki notes
    if args.wiki:
        for slug in sorted(notes_slugs(tex)):
            if not list(args.wiki.rglob(slug + ".md")):
                fatal.append(f"[notes]  \\notes{{{slug}}}: no {slug}.md under {args.wiki}")

    n_lean = sum(1 for n in nodes if n["leanok"])
    print(
        f"Blueprint: {len(nodes)} statement nodes ({n_lean} \\leanok), "
        f"{len(ledger_refs(tex))} ledger refs, {len(paper_shared())} paper shared-statements."
    )
    for a in advisory:
        print("  advisory " + a)
    if fatal:
        print(f"\nLINKAGE CHECK FAILED: {len(fatal)} problem(s)\n")
        for p in fatal:
            print("  FAIL " + p)
        return 1
    print("\nLINKAGE CHECK OK: all in-repo Lean / ledger / paper edges are consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
