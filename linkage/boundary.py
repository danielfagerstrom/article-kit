r"""The boundary harness: four checks the repository-wide axiom guard cannot do.

`blueprint/trust-boundary.txt` plus `linkage axioms --check` already fail CI when a
declaration's axioms fall outside the declared boundary. That guard reads the *union* of
what the guard file prints, which leaves four holes. This module closes them, and every
check here is deliberately **source-text only** — no Lean, no toolchain, no network — so
it runs in the same offline job the manifest emitter runs in.

The division of labour is the point, so state it once:

| hole | what Lean enforces | what `linkage boundary` enforces |
|---|---|---|
| 1. a theorem silently gains an axiom | `#guard_msgs` fails the build when the printed axiom set differs from the pin | the pin *exists* for every headline declaration, names the right declaration, and its axioms are inside the reviewed boundary |
| 2. a theorem weakened into vacuity | the probe file builds, so the probe really holds | a probe exists per headline result, is `sorry`-free, and is not stated as `True` |
| 3. the development goes unsound | nothing — the file is never built | every adversarial goal is *still* a `sorry`, and nothing imports the file |
| 4. a local redefinition shadows a standard notion | nothing | the name collision is reported unless the article has acknowledged it with a reason |

Hole 1 is worth spelling out, because the two halves only work together. `#guard_msgs`
alone would let an author widen a pin by hand to whatever the build now prints; the
allowlist alone sees the union, so a theorem that gained `Classical.choice`-plus-one hides
behind a sibling that legitimately has it. Pinned per declaration *and* cross-checked
against `trust-boundary.txt`, a new axiom can only land by editing the pin, and the edit
only passes if a reviewed ledger entry already grounds that axiom.

Everything is opt-in: an article with no `[boundary]` table in `linkage.toml` is reported
as unconfigured and exits 0, so adopting the harness is a per-article decision.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import trust
from .config import Config

# --- reading Lean source ------------------------------------------------------

# Same shape as `artifacts.DECL_RE`, widened with `example` (a probe is usually one) and
# made to tolerate an anonymous declaration. Kept here rather than shared because the two
# want different things: `artifacts` wants the set of names, this wants the blocks.
DECL_RE = re.compile(
    r"(?m)^(?:@\[[^\]]*\]\s*)?"
    r"(?:(?:private|protected|noncomputable|scoped|local|partial|unsafe)\s+)*"
    r"(?P<kind>theorem|lemma|def|abbrev|structure|instance|axiom|example)"
    r"(?:\s+(?P<name>[A-Za-z_][\w'.]*))?\b"
)

# A real `sorry` term or tactic, not the backtick-wrapped prose `sorry` of a docstring.
# Same pattern the `lean.yml` sorry guard greps with, so the two agree on what counts.
SORRY_RE = re.compile(r"(?:^|[^`\w])sorry(?:[^`\w-]|$)")

IMPORT_RE = re.compile(r"(?m)^\s*import\s+([\w'.]+)")


@dataclass(frozen=True)
class Decl:
    """One top-level declaration, with the source from its keyword to the next one."""
    name: str | None
    kind: str
    line: int
    text: str
    doc: str
    """The comment block immediately above it (`/-- … -/`, `/-! … -/` or `--` lines)."""

    @property
    def head(self) -> str:
        """The statement: everything before the proof's `:=`."""
        return self.text.split(":=", 1)[0]

    @property
    def is_sorry(self) -> bool:
        return bool(SORRY_RE.search(self.text))

    @property
    def is_vacuous(self) -> bool:
        r"""Stated as `: True`, i.e. proving nothing about anything.

        The cheapest vacuity there is, and the one a probe degenerates into when its
        subject is deleted from under it. Deeper vacuity (a hypothesis nothing can
        satisfy) is not a source-text question and is the fidelity review's job.
        """
        return bool(re.search(r":\s*True\s*\Z", self.head.rstrip()))


def declarations(text: str) -> list[Decl]:
    """Every top-level declaration in one Lean file, in source order.

    A declaration's `text` runs to the start of the next one — good enough to ask whether
    a proof is a `sorry` or a statement mentions a name, which is all any check here asks.
    """
    out: list[Decl] = []
    ms = list(DECL_RE.finditer(text))
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        prev = ms[i - 1].end() if i else 0
        out.append(Decl(
            name=m.group("name"),
            kind=m.group("kind"),
            line=text.count("\n", 0, m.start()) + 1,
            text=text[m.start():end],
            doc=_trailing_comment(text[prev:m.start()]),
        ))
    return out


def _trailing_comment(gap: str) -> str:
    """The comment block that ends the gap before a declaration, if any."""
    g = gap.rstrip()
    if g.endswith("-/"):
        start = max(g.rfind("/--"), g.rfind("/-!"), g.rfind("/-"))
        return g[start:] if start >= 0 else ""
    lines: list[str] = []
    for line in reversed(g.splitlines()):
        if line.strip().startswith("--"):
            lines.insert(0, line.strip())
        elif line.strip():
            break
    return "\n".join(lines)


def module_name(cfg: Config, path: Path) -> str:
    """`Formalization/Hemigroup/Adversarial.lean` -> `Hemigroup.Adversarial`."""
    rel = path.relative_to(cfg.lean)
    return ".".join(rel.with_suffix("").parts)


def lean_sources(cfg: Config) -> list[Path]:
    """The article's own Lean sources; build artifacts excluded."""
    return sorted(p for p in cfg.lean.rglob("*.lean") if ".lake" not in p.parts)


# --- the axiom pins -----------------------------------------------------------

PRINT_RE = re.compile(r"(?m)^[ \t]*#print\s+axioms\s+(?P<decl>[\w'.]+)")
# What must sit immediately before a pinned `#print axioms`: the expected output as a
# doc comment, then `#guard_msgs in`. `#guard_msgs` takes options (`(info)`, `(drop
# warning)`, …) before its `in`, so the middle is matched loosely.
# The expectation may not run over a `-/`: with `.*?` it could, and a file with several
# pins then matched from the FIRST doc comment to the LAST `#guard_msgs in` — every pin
# after the first was read against the first one's expected axioms.
GUARD_RE = re.compile(
    r"/--(?P<expect>(?:(?!-/)[\s\S])*)-/\s*#guard_msgs\b[^\n]*\bin\s*\Z")
BARE_GUARD_RE = re.compile(r"#guard_msgs\b[^\n]*\bin\s*\Z", re.S)
# `info: 'Foo.bar' depends on axioms: [propext, Classical.choice]`
EXPECT_RE = re.compile(
    r"'(?P<decl>[\w'.]+)'\s+(?:depends on axioms:\s*\[(?P<axioms>[^\]]*)\]"
    r"|(?P<none>does not depend on any axioms))", re.S)


@dataclass(frozen=True)
class Pin:
    """One `#print axioms` line in the guard file, with whatever pins it."""
    decl: str
    line: int
    guarded: bool
    """Under a `#guard_msgs in`, i.e. Lean itself fails when the output changes."""
    expect_decl: str | None = None
    axioms: tuple[str, ...] | None = None
    """The pinned axiom set — `()` for a declaration pinned as axiom-free, `None` when
    nothing was pinned or the expectation could not be read."""


def pins(text: str) -> list[Pin]:
    """Every `#print axioms` in the guard file, pinned or not."""
    out: list[Pin] = []
    for m in PRINT_RE.finditer(text):
        before = text[:m.start()]
        g = GUARD_RE.search(before)
        line = text.count("\n", 0, m.start()) + 1
        if g is None:
            out.append(Pin(decl=m.group("decl"), line=line,
                           guarded=bool(BARE_GUARD_RE.search(before))))
            continue
        e = EXPECT_RE.search(g.group("expect"))
        if e is None:
            out.append(Pin(decl=m.group("decl"), line=line, guarded=True))
            continue
        axioms = () if e.group("none") else tuple(
            a.strip() for a in (e.group("axioms") or "").split(",") if a.strip())
        out.append(Pin(decl=m.group("decl"), line=line, guarded=True,
                       expect_decl=e.group("decl"), axioms=axioms))
    return out


# --- definition scrutiny ------------------------------------------------------

# Standard notions whose silent local redefinition is a real hazard: a name from Lean
# core, Mathlib or the common analysis/probability vocabulary that a reader — and an
# agent — will assume means the standard thing. Curated rather than derived, because the
# derived alternative is scanning Mathlib on every run (thousands of files) and because
# most of Mathlib's names nobody would ever collide with. Extend per article with
# `[boundary] standard_notions_extra`, or consult a checked-out Mathlib with
# `--with-mathlib`.
STANDARD_NOTIONS: tuple[str, ...] = (
    # measure theory
    "Measure", "MeasurableSet", "Measurable", "AEMeasurable", "Integrable",
    "IntegrableOn", "integral", "lintegral", "setIntegral", "withDensity",
    "IsFiniteMeasure", "IsProbabilityMeasure", "IsFiniteMeasureOnCompacts",
    "SigmaFinite", "ae", "volume", "rnDeriv", "Density", "convolution", "conv",
    # probability
    "Kernel", "kernel", "pdf", "cdf", "variance", "evariance", "mgf", "cgf",
    "charFun", "IndepFun", "Indep", "condexp", "Martingale", "stoppedValue",
    "law", "Law", "expectation",
    # analysis
    "deriv", "fderiv", "HasDerivAt", "HasFDerivAt", "Differentiable", "Continuous",
    "ContinuousAt", "ContinuousOn", "UniformContinuous", "Tendsto", "limsup",
    "liminf", "Summable", "tsum", "exp", "log", "sin", "cos", "rpow", "nnorm",
    "norm", "dist", "edist", "Gamma", "Beta", "fourier", "mellin", "laplace",
    "LipschitzWith", "Isometry", "Homeomorph",
    # order and topology
    "IsOpen", "IsClosed", "IsCompact", "Convex", "ConvexOn", "Monotone", "Antitone",
    "StrictMono", "StrictAnti", "iSup", "iInf", "closure", "interior", "frontier",
    # sets, functions, algebra
    "Injective", "Surjective", "Bijective", "comp", "inv", "id", "Equiv", "Quotient",
    "Setoid", "Subgroup", "Submonoid", "Ideal", "LinearMap", "ContinuousLinearMap",
    "Group", "Monoid", "Semigroup", "Ring", "Field", "Module", "Algebra",
    "Polynomial", "Matrix",
)


def mathlib_names(cfg: Config) -> set[str]:
    """Short declaration names from a checked-out Mathlib, or an empty set.

    Opt-in (`--with-mathlib`): it reads several thousand files, which is fine for a
    deliberate run and wrong for a check CI runs on every push.
    """
    from .artifacts import DECL_RE as NAME_RE
    from .artifacts import read

    root = cfg.lean / ".lake" / "packages" / "mathlib" / "Mathlib"
    if not root.is_dir():
        return set()
    names: set[str] = set()
    for f in root.rglob("*.lean"):
        names |= set(NAME_RE.findall(read(f)))
    return names


# --- the report ---------------------------------------------------------------

@dataclass
class Report:
    fatal: list[str] = field(default_factory=list)
    advisory: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def __bool__(self) -> bool:  # pragma: no cover - convenience only
        return not self.fatal


def run(cfg: Config, *, strict_shadows: bool = False,
        with_mathlib: bool = False) -> Report:
    """The four checks, over one article's declared boundary manifest."""
    rep = Report()
    b = cfg.boundary
    if not b.configured:
        rep.stats["configured"] = False
        return rep
    rep.stats["configured"] = True

    texts: dict[str, str] = {}

    def source(kind: str, path: Path | None, *, required: bool) -> str | None:
        if path is None:
            if required:
                rep.fatal.append(
                    f"[{kind}] `[boundary] {kind}` is not set — the harness needs the file "
                    f"that holds the {kind}")
            return None
        if not path.is_file():
            rep.fatal.append(
                f"[{kind}] {path.relative_to(cfg.root).as_posix()} does not exist — "
                f"`[boundary] {kind}` points at nothing")
            return None
        texts[kind] = path.read_text(encoding="utf-8")
        return texts[kind]

    guard = source("guard", b.guard, required=True)
    probes = source("probes", b.probes, required=bool(b.headline))
    adversarial = source("adversarial", b.adversarial, required=False)

    declared = {n for p in lean_sources(cfg) for n in _names(p)}

    _check_pins(cfg, rep, guard, declared)
    _check_probes(cfg, rep, probes)
    _check_adversarial(cfg, rep, adversarial)
    _check_shadows(cfg, rep, strict=strict_shadows, with_mathlib=with_mathlib)
    return rep


def _names(path: Path) -> set[str]:
    from .artifacts import DECL_RE as NAME_RE
    return set(NAME_RE.findall(path.read_text(encoding="utf-8")))


def _short(name: str) -> str:
    return name.split(".")[-1]


def _check_pins(cfg: Config, rep: Report, guard: str | None,
                declared: set[str]) -> None:
    """Check 1 — one `#guard_msgs`-pinned `#print axioms` per headline declaration."""
    b = cfg.boundary
    rep.stats["headline"] = len(b.headline)
    if guard is None:
        return
    found = pins(guard)
    rep.stats["pins"] = sum(1 for p in found if p.guarded and p.axioms is not None)
    rel = b.guard.relative_to(cfg.root).as_posix()
    allowed = set(trust.allowlist(cfg))
    by_decl = {p.decl: p for p in found if p.guarded and p.axioms is not None}

    for p in found:
        where = f"{rel}:{p.line}"
        if not p.guarded:
            rep.fatal.append(
                f"[axiom-pin] {where}: `#print axioms {p.decl}` is not under a "
                f"`#guard_msgs in` — its output is read as part of the repository-wide "
                f"union, so this declaration can gain an axiom another one already has "
                f"and nothing fails. Pin it: `/-- info: … -/ #guard_msgs in`")
            continue
        if p.axioms is None:
            rep.fatal.append(
                f"[axiom-pin] {where}: `#guard_msgs` with no readable expectation above "
                f"`{p.decl}` — the doc comment must carry Lean's own line, "
                f"`info: '{p.decl}' depends on axioms: [...]`")
            continue
        if p.expect_decl != p.decl:
            rep.fatal.append(
                f"[axiom-pin] {where}: the pin expects output for `{p.expect_decl}` but "
                f"prints `{p.decl}` — one of the two was copied and not edited")
        if _short(p.decl) not in declared:
            rep.fatal.append(
                f"[axiom-pin] {where}: `{p.decl}` is pinned but declared nowhere under "
                f"{cfg.lean.name}/ — a stale pin guards nothing")
        for a in p.axioms:
            if a == "sorryAx":
                rep.fatal.append(
                    f"[axiom-pin] {where}: `{p.decl}` is pinned as depending on `sorryAx` "
                    f"— a `sorry` is inside a headline result's trust base")
            elif a not in allowed:
                rep.fatal.append(
                    f"[axiom-pin] {where}: `{p.decl}` is pinned on `{a}`, which "
                    f"{trust.trust_file(cfg).name} does not declare — widening the trust "
                    f"base is a review decision: add a grounded {cfg.axioms.name} entry "
                    f"and the name to the boundary, or do not accept the pin")

    for h in b.headline:
        if h not in by_decl:
            rep.fatal.append(
                f"[axiom-pin] headline `{h}` has no pinned `#print axioms` block in {rel} "
                f"— the repository-wide axiom check sees the union and would not notice "
                f"this one theorem gaining an axiom")

    extra = sorted(set(by_decl) - set(b.headline))
    if extra:
        rep.stats["pins_unlisted"] = len(extra)


def _check_probes(cfg: Config, rep: Report, probes: str | None) -> None:
    """Check 2 — a cheap should-hold consequence per headline result, kept holding."""
    b = cfg.boundary
    if probes is None:
        return
    rel = b.probes.relative_to(cfg.root).as_posix()
    decls = [d for d in declarations(probes) if d.kind != "structure"]
    rep.stats["probes"] = len(decls)

    if not decls:
        rep.fatal.append(
            f"[probe] {rel} declares no probes — an empty probe file passes every build "
            f"and witnesses nothing")

    for d in decls:
        what = d.name or f"example at line {d.line}"
        if d.kind == "axiom":
            rep.fatal.append(
                f"[probe] {rel}:{d.line}: `{what}` is an `axiom` — a probe must be proved "
                f"from the development, not assumed alongside it")
            continue
        if d.is_sorry:
            rep.fatal.append(
                f"[probe] {rel}:{d.line}: `{what}` is a `sorry` — a probe that is not "
                f"proved tests nothing")
        if d.is_vacuous:
            rep.fatal.append(
                f"[probe] {rel}:{d.line}: `{what}` is stated as `True` — it holds "
                f"whatever happened to the result it is supposed to probe")

    for h in b.headline:
        if not any(_mentions(d.text, h) for d in decls):
            rep.fatal.append(
                f"[probe] headline `{h}` has no positive probe in {rel} — nothing would "
                f"catch it being weakened into a statement that still type-checks")


def _mentions(text: str, decl: str) -> bool:
    """Does this probe use that declaration — by full name or by its short one?

    The short name counts because a probe file usually sits inside the namespace and
    writes `main_construction`, not `Hemigroup.main_construction`.
    """
    for name in (decl, _short(decl)):
        if re.search(rf"(?<![\w'.]){re.escape(name)}(?![\w'])", text):
            return True
    return False


def _check_adversarial(cfg: Config, rep: Report, adversarial: str | None) -> None:
    """Check 3 — known-false goals must stay unprovable, and stay isolated."""
    b = cfg.boundary
    if adversarial is None:
        if b.adversarial is None:
            rep.advisory.append(
                "[adversarial] no `[boundary] adversarial` file — nothing would notice the "
                "development becoming able to prove a statement known to be false")
        return
    rel = b.adversarial.relative_to(cfg.root).as_posix()
    decls = [d for d in declarations(adversarial) if d.kind not in ("structure", "def")]
    rep.stats["adversarial"] = len(decls)

    if not decls:
        rep.advisory.append(
            f"[adversarial] {rel} states no goals — the file is a placeholder")

    for d in decls:
        what = d.name or f"example at line {d.line}"
        if not d.is_sorry:
            rep.fatal.append(
                f"[adversarial] {rel}:{d.line}: `{what}` is no longer a `sorry` — a "
                f"statement kept here because it is FALSE has become provable. Something "
                f"in the development is unsound, or the goal was mis-stated; do not "
                f"'fix' this by deleting the line")
        if not d.doc:
            rep.advisory.append(
                f"[adversarial] {rel}:{d.line}: `{what}` carries no comment saying why it "
                f"is false — an unexplained goal is deleted by the next reader")

    # Isolation. The file is never built as part of the library, so a `sorry` in it must
    # not be reachable from anything that is -- and the `sorry` guard's scan directory
    # must not cover it either, or CI fails on the file's whole reason to exist.
    module = module_name(cfg, b.adversarial)
    for p in lean_sources(cfg):
        if p == b.adversarial:
            continue
        if module in IMPORT_RE.findall(p.read_text(encoding="utf-8")):
            rep.fatal.append(
                f"[adversarial] {p.relative_to(cfg.root).as_posix()} imports `{module}` — "
                f"the adversarial goals are `sorry`s and must reach nothing")


def _check_shadows(cfg: Config, rep: Report, *, strict: bool,
                   with_mathlib: bool) -> None:
    """Check 4 — a local declaration sharing a name with a standard notion."""
    b = cfg.boundary
    standard = set(STANDARD_NOTIONS) | set(b.standard_notions_extra)
    # A shared package the article builds on is a second source of standard names, and a
    # free one: those files are already read for check 1 of `linkage check`.
    for pkg in cfg.lean_packages:
        root = cfg.lean / ".lake" / "packages" / pkg
        if root.is_dir():
            standard |= {n for f in root.rglob("*.lean")
                         if ".lake" not in f.relative_to(root).parts
                         for n in _names(f)}
    if with_mathlib:
        standard |= mathlib_names(cfg)

    acknowledged = {_short(k): v for k, v in b.shadows.items()}
    hits: list[str] = []
    seen: set[str] = set()
    for p in lean_sources(cfg):
        if b.adversarial is not None and p == b.adversarial:
            continue
        text = p.read_text(encoding="utf-8")
        for d in declarations(text):
            if d.name is None or d.name in seen:
                continue
            short = _short(d.name)
            if short not in standard or short in acknowledged:
                continue
            seen.add(d.name)
            hits.append(
                f"[shadow] {p.relative_to(cfg.root).as_posix()}:{d.line}: `{d.kind} "
                f"{d.name}` shares its name with a standard notion — a reader, and an "
                f"agent reading the proof, will take it for the standard one. `unfold` "
                f"or `#print` both and either rename it, or record it under "
                f"`[boundary.shadows]` in linkage.toml with what differs")
    rep.stats["shadows"] = len(hits)
    (rep.fatal if strict else rep.advisory).extend(hits)

    live = {_short(n) for n in seen} | {
        _short(d.name) for p in lean_sources(cfg)
        for d in declarations(p.read_text(encoding="utf-8")) if d.name}
    for name, why in b.shadows.items():
        if not str(why).strip():
            rep.fatal.append(
                f"[shadow] `[boundary.shadows]` accepts `{name}` with an empty reason — "
                f"the entry is the review record, so it has to say what differs")
        elif _short(name) not in live:
            rep.advisory.append(
                f"[shadow] `[boundary.shadows]` still accepts `{name}`, which this "
                f"article no longer declares — drop the entry")
