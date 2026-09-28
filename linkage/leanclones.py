"""`linkage lean clones` — declarations copied between the constellation's Lean members.

The trunk (`scale-space-lean`) is extended *on second demand*: a result moves there when a
second article needs it. Nothing computed second demand until the engineer's survey of
2026-09-19 (hub `offices/engineer/experiments/lean_overlap.py`), which found 73 clones between
two articles by hand where the queue had three. This is that survey as a standing check.

The members are found through the hub's `constellation.json` (`--wiki`, else `$WIKI_VAULT`,
the same convention as `linkage demand`); every member that is a git checkout with tracked
`.lean` files is compared with every other. The parser and the method are the survey's: the
*tracked* files only (`git ls-files`, so `.lake/` and agent worktrees are never read), comments
blanked, each declaration cut at its top-level `:=` / `where` into a statement and a body, and
every one-letter lowercase identifier collapsed to one marker (*alpha normalization*), which is
what separates real divergence from the causal-to-spatial rename `t, r -> x, y`. No Lean is
compiled.

What changes is the anchor. The survey indexed declarations by name and compared those that
shared one, so renaming a declaration made its clone vanish. Here the index is the **statement
text** (alpha-normalized); names are only reported. A pair of declarations, one in each member,
is

- a **clone** when the whole declaration -- modifiers, statement and body -- is the same text
  up to renaming, whatever the two are called;
- a **same-statement** match otherwise: two theorems that say the same thing and prove it
  differently.

`renamed` counts the matches whose two names differ: the number a rename would move, and the
one to read before believing a drop in the clone count.

Four departures from the survey. The first is a repair to its parser, the rest follow from
anchoring on the statement, where the survey had the name to fall back on.

1. A declaration ends at the next top-level command that is not part of it (`end Foo`, `open`,
   `variable`, `@[attr]`, ...), not only at the next declaration. The survey read that line as
   the tail of the proof, so a clone that was the last declaration of its namespace differed
   from its copy by the `end` line and was missed: 6 of the 86 clones on the checkouts of
   2026-09-28. `COMMAND_RE` is the whole change.
2. A theorem's statement is what it *says*; a definition's is only its signature (`: R -> R`),
   which a hundred unrelated definitions share. So a definition, structure, class, instance or
   inductive is anchored on its whole text and can only be a clone.
3. A theorem statement of fewer than `--min-tokens` tokens (`: True`) is too short to be
   evidence of anything, so that theorem is anchored on its whole text too.
4. A declaration's own name is blanked out of its text before the whole-text comparison, so a
   renamed recursive declaration is still a clone.

The check exits 1 when the clones not named in the exception list exceed `--max-clones`
(default 0), 2 when it could not answer (no vault, no constellation, fewer than two Lean
members checked out). A comparison that silently compared nothing would be a check that never
fails.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from . import config

DECL_KINDS = ("theorem", "lemma", "def", "abbrev", "structure", "class",
              "instance", "inductive", "example")
MODIFIERS = (r"(?:@\[[^\]]*\]\s*)*"
             r"(?:private\s+|protected\s+|noncomputable\s+|nonrec\s+|partial\s+|unsafe\s+|scoped\s+)*")
DECL_RE = re.compile(r"^(?P<mods>" + MODIFIERS + r")(?P<kind>" + "|".join(DECL_KINDS) + r")\b")
NAME_RE = re.compile(r"^\s*(?P<name>[^\s(){}\[\]:]+)")
TOKEN_RE = re.compile(r"[A-Za-z_α-ωΑ-Ω][A-Za-z0-9_'α-ωΑ-Ω]*|\S")
OPEN, CLOSE = "([{⟨⦃", ")]}⟩⦄"
VARS = set("abcdefghijklmnopqrstuvwxyz")
# A top-level command that is not a declaration. The survey's parser ended a declaration only
# at the next declaration, so the `end Foo`, `open`, `variable` or `@[attr]` line after it was
# read as the tail of its proof; two copies of one lemma followed by different such lines were
# then "the same statement, a different proof". On today's checkouts that hid 6 of 86 clones.
COMMAND_RE = re.compile(
    r"^(?:end|namespace|section|noncomputable\s+section|open|variable|universe|set_option|"
    r"attribute|local|scoped|export|import|omit|include|notation|infix[lr]?|prefix|postfix|"
    r"macro|syntax|elab|mutual|initialize|@\[|#)")

DEFAULT_MIN_TOKENS = 4
SELF = "«self»"


# ---------------------------------------------------------------- the survey's parser

def strip_comments(text: str) -> str:
    """Blank out `/- ... -/` (incl. `/-!`, `/--`) and `--` comments, keeping line structure."""
    out, i, n, depth = [], 0, len(text), 0
    while i < n:
        c = text[i]
        if text.startswith("/-", i):
            depth += 1
            i += 2
            continue
        if text.startswith("-/", i) and depth:
            depth -= 1
            i += 2
            continue
        if depth:
            out.append("\n" if c == "\n" else " ")
            i += 1
            continue
        if text.startswith("--", i):
            j = text.find("\n", i)
            if j < 0:
                break
            out.append(" " * (j - i))
            i = j
            continue
        out.append(c)
        i += 1
    return "".join(out)


def split_statement(body: str, kind: str) -> tuple[str, str]:
    """(statement, proof/value): everything before the top-level `:=` or `where`."""
    depth, i, n = 0, 0, len(body)
    while i < n:
        c = body[i]
        if c in OPEN:
            depth += 1
        elif c in CLOSE:
            depth -= 1
        elif depth == 0:
            if body.startswith(":=", i):
                return body[:i], body[i + 2:]
            if kind in ("structure", "class", "inductive") and body.startswith("where", i):
                prev = body[i - 1] if i else " "
                nxt = body[i + 5] if i + 5 < n else " "
                if not (prev.isalnum() or prev == "_") and not (nxt.isalnum() or nxt == "_"):
                    return body[:i], body[i + 5:]
        i += 1
    return body, ""


def tokens(s: str) -> list[str]:
    return TOKEN_RE.findall(s)


def alpha_tokens(s: str) -> list[str]:
    return ["ν" if (len(t) == 1 and t in VARS) else t for t in tokens(s)]


def alpha(s: str) -> str:
    return " ".join(alpha_tokens(s))


def parse_file(path: Path, root: Path) -> list[dict]:
    """Every named declaration of one `.lean` file, as a record of its text and place."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    rawlines = raw.split("\n")
    lines = strip_comments(raw).split("\n")
    starts = [(i, m) for i, ln in enumerate(lines)
              if ln and not ln[0].isspace() and (m := DECL_RE.match(ln))]
    ns_events = []
    for i, ln in enumerate(lines):
        if m := re.match(r"^namespace\s+(\S+)", ln):
            ns_events.append((i, "+" + m.group(1)))
        elif m := re.match(r"^end\s+(\S+)\s*$", ln):
            ns_events.append((i, "-" + m.group(1)))

    def ns_at(i: int) -> str:
        st: list[str] = []
        for at, ev in ns_events:
            if at > i:
                break
            if ev[0] == "+":
                st.append(ev[1:])
            elif st and st[-1] == ev[1:]:
                st.pop()
        return ".".join(st)

    out = []
    for k, (i, m) in enumerate(starts):
        end = starts[k + 1][0] if k + 1 < len(starts) else len(lines)
        end = next((j for j in range(i + 1, end) if COMMAND_RE.match(lines[j])), end)
        block = "\n".join(lines[i:end]).rstrip()
        after = block[m.end("mods") + len(m.group("kind")):]
        nm = NAME_RE.match(after)
        if not nm:
            continue
        stmt, proof = split_statement(after[nm.end():], m.group("kind"))
        # real source span, backing up over an attached docstring
        s0, j = i, i - 1
        while j >= 0 and rawlines[j].strip() == "":
            j -= 1
        if j >= 0 and rawlines[j].rstrip().endswith("-/"):
            depth = 0
            while j >= 0:
                if rawlines[j].rstrip().endswith("-/"):
                    depth += 1
                if rawlines[j].lstrip().startswith("/-"):
                    depth -= 1
                    if depth <= 0:
                        break
                j -= 1
            s0 = max(0, j)
        e0 = max((q for q in range(i, min(end, len(rawlines))) if rawlines[q].strip()),
                 default=i)
        out.append({
            "file": path.relative_to(root).as_posix(),
            "kind": m.group("kind"), "mods": " ".join(m.group("mods").split()),
            "name": nm.group("name"), "ns": ns_at(i),
            "stmt": " ".join(stmt.split()), "proof": " ".join(proof.split()),
            "line": i + 1, "src_lines": e0 - s0 + 1,
        })
    return out


# ---------------------------------------------------------------- statement-anchored keys

def _blank_self(text: str, name: str) -> str:
    return re.sub(r"(?<![\w'.])" + re.escape(name) + r"(?![\w'])", SELF, text)


def _norm_kind(kind: str) -> str:
    return "theorem" if kind == "lemma" else kind


@dataclass(frozen=True)
class Decl:
    member: str
    file: str
    line: int
    kind: str
    name: str
    ns: str
    src_lines: int
    anchor: tuple
    whole: tuple

    @property
    def qualified(self) -> str:
        return f"{self.ns}.{self.name}" if self.ns else self.name

    def where(self) -> dict:
        return {"member": self.member, "name": self.name, "qualified": self.qualified,
                "kind": self.kind, "file": self.file, "line": self.line,
                "src_lines": self.src_lines}


def make_decl(member: str, rec: dict, min_tokens: int) -> Decl:
    kind = _norm_kind(rec["kind"])
    whole = (kind, alpha(rec["mods"]), alpha(_blank_self(rec["stmt"], rec["name"])),
             alpha(_blank_self(rec["proof"], rec["name"])))
    stmt = alpha_tokens(rec["stmt"])
    # A theorem's statement is its content; a definition's is a signature, its content is the
    # value. See the module docstring, guards (1) and (2).
    by_statement = kind == "theorem" and len(stmt) >= min_tokens
    anchor = ("stmt", " ".join(stmt)) if by_statement else ("whole", *whole)
    return Decl(member, rec["file"], rec["line"], rec["kind"], rec["name"], rec["ns"],
                rec["src_lines"], anchor, whole)


# ---------------------------------------------------------------- finding the members

@dataclass(frozen=True)
class Member:
    slug: str
    root: Path


class CloneInputError(config.ConfigError):
    """The check could not be run at all (exit 2), as against finding clones (exit 1)."""


def resolve_vault(explicit: Path | None) -> Path:
    if explicit:
        return Path(explicit)
    if env := os.environ.get("WIKI_VAULT"):
        return Path(env)
    raise CloneInputError(
        "no wiki vault — pass --wiki PATH or set $WIKI_VAULT to the Notes vault, whose "
        "constellation.json names the members")


def _expand(p: str) -> Path:
    return Path(os.path.expanduser(p))


def read_constellation(vault: Path, dev_root: Path | None) -> tuple[list[tuple[str, Path]], Path]:
    """(slug, directory) of every member, and the workspace root the relative ones sit under."""
    f = vault / "constellation.json"
    if not f.is_file():
        raise CloneInputError(f"no constellation.json under {vault}")
    try:
        doc = json.loads(f.read_text(encoding="utf-8"))
        root = dev_root or _expand(doc.get("workspace", {}).get("root", "~/dev"))
        rows = [(m["slug"], _expand(m["dir"])) for m in doc["members"]]
    except (ValueError, KeyError, TypeError) as e:
        raise CloneInputError(f"{f} is not a constellation manifest: {e!r}") from e
    return [(slug, d if d.is_absolute() else root / d) for slug, d in rows], root


def tracked_lean(repo: Path) -> list[Path]:
    """The `.lean` files git tracks in `repo`; empty when it is not a checkout."""
    if not repo.is_dir():
        return []
    r = subprocess.run(["git", "ls-files", "-z", "--", "*.lean"], cwd=repo,
                       capture_output=True, text=True, encoding="utf-8", check=False)
    if r.returncode != 0:
        return []
    return [repo / p for p in r.stdout.split("\0") if p]


def find_members(vault: Path, dev_root: Path | None = None
                 ) -> tuple[list[Member], dict[str, list[str]]]:
    """The Lean members that are checked out, and the slugs set aside, by reason."""
    rows, _ = read_constellation(vault, dev_root)
    members: list[Member] = []
    skipped: dict[str, list[str]] = {"not checked out": [], "no Lean": []}
    for slug, d in rows:
        if not d.is_dir():
            skipped["not checked out"].append(slug)
        elif tracked_lean(d):
            members.append(Member(slug, d))
        else:
            skipped["no Lean"].append(slug)
    return members, skipped


def collect(member: Member, min_tokens: int) -> list[Decl]:
    return [make_decl(member.slug, rec, min_tokens)
            for f in tracked_lean(member.root) for rec in parse_file(f, member.root)]


# ---------------------------------------------------------------- comparing a pair

@dataclass(frozen=True)
class Match:
    a: Decl
    b: Decl
    clone: bool

    @property
    def renamed(self) -> bool:
        return self.a.name != self.b.name


def _pair_up(As: list[Decl], Bs: list[Decl]) -> list[Match]:
    """One match per declaration on the shorter side: whole-text equals first, and among
    those the same name first, so a rename is reported as a rename only when it must be."""
    left, right = list(As), list(Bs)
    out: list[Match] = []
    for want_whole, want_name in ((True, True), (True, False), (False, True), (False, False)):
        for a in list(left):
            for b in right:
                if ((not want_whole or a.whole == b.whole)
                        and (not want_name or a.name == b.name)):
                    out.append(Match(a, b, a.whole == b.whole))
                    left.remove(a)
                    right.remove(b)
                    break
    return out


def compare(A: list[Decl], B: list[Decl]) -> list[Match]:
    byA, byB = defaultdict(list), defaultdict(list)
    for d in A:
        byA[d.anchor].append(d)
    for d in B:
        byB[d.anchor].append(d)
    out: list[Match] = []
    for anchor in byA.keys() & byB.keys():
        out.extend(_pair_up(byA[anchor], byB[anchor]))
    return sorted(out, key=lambda m: (m.a.file, m.a.line))


# ---------------------------------------------------------------- exceptions

def read_allow(path: Path) -> list[str]:
    """One declaration name per line; `#` starts a comment (say why it is allowed)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise CloneInputError(f"cannot read the exception list {path}: {e}") from e
    return [s for ln in text.splitlines() if (s := ln.split("#", 1)[0].strip())]


def excepted_by(m: Match, allow: set[str]) -> str | None:
    """The exception entry that names this match: the short or the namespaced name, either side."""
    for d in (m.a, m.b):
        for entry in (d.name, d.qualified):
            if entry in allow:
                return entry
    return None


# ---------------------------------------------------------------- the report

@dataclass
class Report:
    members: list[dict]
    skipped: dict[str, list[str]]
    pairs: list[dict]
    max_clones: int
    allow: list[str]
    stale_allow: list[str]
    min_tokens: int

    @property
    def counted(self) -> int:
        return sum(p["counted"] for p in self.pairs)

    @property
    def ok(self) -> bool:
        return self.counted <= self.max_clones

    def totals(self) -> dict:
        keys = ("statement_matches", "clones", "same_statement", "renamed",
                "renamed_clones", "excepted", "counted", "clone_src_lines")
        return {k: sum(p[k] for p in self.pairs) for k in keys}

    def to_json(self) -> dict:
        return {"ok": self.ok, "max_clones": self.max_clones, "min_tokens": self.min_tokens,
                "totals": self.totals(), "members": self.members, "skipped": self.skipped,
                "allow": self.allow, "stale_allow": self.stale_allow, "pairs": self.pairs}


def run(members: list[Member], *, max_clones: int = 0, allow: list[str] | None = None,
        min_tokens: int = DEFAULT_MIN_TOKENS,
        skipped: dict[str, list[str]] | None = None) -> Report:
    if len(members) < 2:
        raise CloneInputError(
            f"{len(members)} Lean member(s) checked out; there is no pair to compare"
            + (f" (set aside: {skipped})" if skipped else ""))
    allow = list(allow or [])
    allowed = set(allow)
    decls = {m.slug: collect(m, min_tokens) for m in members}
    used: set[str] = set()
    pairs = []
    for ma, mb in combinations(members, 2):
        matches = compare(decls[ma.slug], decls[mb.slug])
        rows = []
        for m in matches:
            entry = excepted_by(m, allowed)
            if entry:
                used.add(entry)
            rows.append({"clone": m.clone, "renamed": m.renamed, "excepted_by": entry,
                         "a": m.a.where(), "b": m.b.where()})
        clones = [r for r in rows if r["clone"]]
        pairs.append({
            "a": ma.slug, "b": mb.slug,
            "statement_matches": len(rows),
            "clones": len(clones),
            "same_statement": len(rows) - len(clones),
            "renamed": sum(r["renamed"] for r in rows),
            "renamed_clones": sum(r["renamed"] for r in clones),
            "excepted": sum(1 for r in clones if r["excepted_by"]),
            "counted": sum(1 for r in clones if not r["excepted_by"]),
            "clone_src_lines": sum(min(r["a"]["src_lines"], r["b"]["src_lines"])
                                   for r in clones),
            "matches": rows,
        })
    return Report(
        members=[{"slug": m.slug, "root": str(m.root), "declarations": len(decls[m.slug])}
                 for m in members],
        skipped=skipped or {}, pairs=pairs, max_clones=max_clones, allow=allow,
        stale_allow=sorted(allowed - used), min_tokens=min_tokens)


def render(rep: Report) -> list[str]:
    out = ["Lean members compared: " + ", ".join(
        f"{m['slug']} ({m['declarations']} decls)" for m in rep.members)]
    for why, slugs in rep.skipped.items():
        if slugs:
            out.append(f"  set aside, {why}: {', '.join(slugs)}")
    out.append("")
    out.append(f"{'pair':44s} {'stmt':>5s} {'clone':>5s} {'other proof':>11s} "
               f"{'renamed':>7s} {'excepted':>8s}")
    for p in rep.pairs:
        out.append(f"{p['a'] + ' / ' + p['b']:44s} {p['statement_matches']:5d} "
                   f"{p['clones']:5d} {p['same_statement']:11d} {p['renamed']:7d} "
                   f"{p['excepted']:8d}")
    t = rep.totals()
    out.append(f"{'total':44s} {t['statement_matches']:5d} {t['clones']:5d} "
               f"{t['same_statement']:11d} {t['renamed']:7d} {t['excepted']:8d}")
    out.append("")
    out.append(f"  {t['statement_matches']} declaration pair(s) share a statement text; "
               f"{t['renamed']} under different names ({t['renamed_clones']} of them clones) "
               f"-- the number a rename would move.")
    out.append(f"  {t['clones']} are clones (whole declaration the same up to renaming), "
               f"{t['clone_src_lines']} source lines duplicated; {t['excepted']} named in the "
               f"exception list, {t['counted']} counted against the {rep.max_clones} allowed.")
    for p in rep.pairs:
        rows = [r for r in p["matches"] if r["clone"]]
        if not rows:
            continue
        out.append(f"\nclones, {p['a']} / {p['b']}:")
        for r in rows:
            a, b = r["a"], r["b"]
            names = a["qualified"] if a["name"] == b["name"] else f"{a['qualified']} = {b['qualified']}"
            tag = f"  [excepted: {r['excepted_by']}]" if r["excepted_by"] else ""
            out.append(f"  {names}  ({a['kind']}, {min(a['src_lines'], b['src_lines'])} lines)"
                       f"{tag}\n      {p['a']}: {a['file']}:{a['line']}"
                       f"\n      {p['b']}: {b['file']}:{b['line']}")
    for entry in rep.stale_allow:
        out.append(f"  advisory exception `{entry}` names no statement match -- remove it")
    return out
