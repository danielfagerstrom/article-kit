"""`linkage` — the article-repo command line.

    linkage check [--wiki PATH] [--emit-manifest PATH] [--require-render]
    linkage manifest [PATH] [--require-render]
    linkage demand [--wiki PATH]
    linkage init [--slug SLUG]

Run from anywhere inside an article repo; the config is found by walking up to
`linkage.toml`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import artifacts, checks, config, manifest as manifest_mod, parse_latex


def _warn(msg: str) -> None:
    print(f"  warning: {msg}", file=sys.stderr)


def _load(root: Path | None):
    cfg = config.load(root)
    bp = parse_latex.parse(cfg)
    return cfg, bp


def _emit_manifest(cfg, bp, dest: Path, require_render: bool) -> int:
    lean_names = artifacts.lean_declared_names(cfg)
    ledger = artifacts.ledger_entries(cfg)
    try:
        doc = manifest_mod.build(
            bp, cfg, lean_names, ledger, require_render=require_render, warn=_warn)
    except manifest_mod.ManifestError as e:
        print(f"MANIFEST EMIT FAILED: {e}", file=sys.stderr)
        return 2
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    n_lab = len(doc["labels"])
    n_proof = sum(1 for e in doc["labels"].values() if e["proof"] is not None)
    rendered = "rendered" if doc["render"] else "NOT rendered"
    print(f"Wrote manifest v{doc['manifest_version']} ({n_lab} labels, {n_proof} proofs, "
          f"{len(lean_names)} Lean decls, markdown {rendered}) → {dest}")
    return 0


def cmd_check(args) -> int:
    cfg, bp = _load(args.root)

    if args.emit_manifest:
        rc = _emit_manifest(cfg, bp, args.emit_manifest, args.require_render)
        if rc:
            return rc

    f = checks.run(
        bp, cfg,
        lean_names=artifacts.lean_declared_names(cfg),
        ledger=artifacts.ledger_entries(cfg),
        markers=artifacts.paper_markers(cfg),
        safe_commands=artifacts.render_safe_commands(cfg),
        wiki=args.wiki,
    )

    # Framework-owned scaffolding must exist in the article tree (TeX resolves \input
    # against the source dir), so it is a copy; ADR-0008 says a copy owes detectable
    # divergence. Advisory, not fatal — an edited copy still builds, it just silently
    # stops tracking the framework.
    from . import scaffold
    for rel in scaffold.drift(cfg.root):
        f.advisory.append(
            f"[scaffold] {rel} differs from the framework's copy — edit it in the linkage "
            "repo and re-run `linkage init --sync`, or the change is lost on the next sync"
        )

    s = f.stats
    print(f"Blueprint: {s['nodes']} statement nodes ({s['leanok']} \\leanok), "
          f"{s['ledger_refs']} ledger refs, {s['paper_shared']} paper shared-statements.")
    print(f"Dependency closure: {s['reached_unproved']} statement(s) proved nowhere reached "
          f"by a \\leanok node, {s['reached_on_paper']} proved on paper only; "
          f"{len(s['unproved'])} [T] statement(s) proved nowhere in all "
          f"({', '.join(s['unproved']) or 'none'}).")
    print("  (the fatal walk traverses [A] nodes; the advisory's dependent counts stop at "
          "them -- LINKAGE.md rule 8)")
    for a in f.advisory:
        print("  advisory " + a)
    if f.fatal:
        print(f"\nLINKAGE CHECK FAILED: {len(f.fatal)} problem(s)\n")
        for p in f.fatal:
            print("  FAIL " + p)
        return 1
    print("\nLINKAGE CHECK OK: all in-repo Lean / ledger / paper edges are consistent.")
    return 0


def cmd_manifest(args) -> int:
    cfg, bp = _load(args.root)
    dest = args.path or (cfg.root / manifest_mod.default_filename(cfg.slug))
    return _emit_manifest(cfg, bp, dest, args.require_render)


def cmd_demand(args) -> int:
    from . import demand
    return demand.main(args)


def cmd_axioms(args) -> int:
    """Print the trust-boundary allowlist; verify each entry is grounded in the ledger."""
    from . import trust
    cfg = config.load(args.root)
    names = trust.declared(cfg)
    if not names:
        print(f"no {trust.trust_file(cfg).name} — the trust-boundary guard has nothing to "
              "check; create it naming this article's interface axioms", file=sys.stderr)
        return 0 if not args.check else 1
    if bad := trust.ungrounded(cfg):
        print(f"TRUST BOUNDARY: {len(bad)} declared axiom(s) that no {cfg.axioms.name} entry "
              f"mentions in a **Lean:** segment — declared but never reviewed:", file=sys.stderr)
        for b in bad:
            print(f"  {b}", file=sys.stderr)
        return 1
    if args.check:
        print(f"trust boundary OK: {len(names)} interface axiom(s), all grounded in "
              f"{cfg.axioms.name}.", file=sys.stderr)
    for n in trust.allowlist(cfg):
        print(n)
    return 0


def cmd_packages(args) -> int:
    """Report the shared Lake packages this article needs, for a toolchain-free fetch."""
    cfg = config.load(args.root)
    rows = artifacts.lake_package_sources(cfg)
    if not rows:
        return 0
    missing = 0
    for r in rows:
        if args.missing_only and r["present"]:
            continue
        if not r["present"]:
            missing += 1
        if not r["url"] or not r["rev"]:
            print(f"{r['name']}: not resolved in lake-manifest.json — run `lake update "
                  f"{r['name']}`", file=sys.stderr)
            return 1
        print(f"{r['name']}	{r['url']}	{r['rev']}	{r['dest']}")
    if args.missing_only and missing:
        print(f"{missing} shared package(s) not checked out", file=sys.stderr)
    return 0


def cmd_prose_extract(args) -> int:
    """Dump the prose extraction. Config-free: it takes bare paths, so it also runs
    over the baseline corpus, which lives outside any article repo."""
    from .prose import show
    return show.main(args)


def cmd_prose_baseline(args) -> int:
    from .prose import corpus, measure
    bases, stats = corpus.build(warn=_warn)
    for b in bases:
        f = b.features
        print(f"{b.name:<8} {len(b.sources):>2} sources  {f.words:>7}w  "
              f"{f.sentences:>5} sentences   carries: {', '.join(b.supports)}")
        for s in stats[b.name]:
            note = ""
            if s.repaired.get("reflow", {}).get("blocks joined"):
                r = s.repaired
                note = (f"  [repaired: {sum(r['running heads'].values())} heads, "
                        f"{sum(r['dehyphenated'].values())} hyphens, "
                        f"{r['reflow']['blocks joined']} rejoins]")
            print(f"    {s.key[:44]:<46}{s.words:>7}w  residue {s.residue:>5.1%}{note}")
    for k, why in corpus.GENRE_REJECTED.items():
        print(f"  rejected  {k[:44]:<46}{why}")
    measure.save(bases, args.out)
    print(f"\nwrote {args.out}")
    return 0


def cmd_prose_stats(args) -> int:
    from .prose import measure, report
    if not args.baseline.exists():
        print(f"no baseline at {args.baseline} — run `linkage prose baseline` first",
              file=sys.stderr)
        return 2
    bases = measure.load(args.baseline)
    paths = [Path(p) for p in args.paths]
    if args.instances:
        if args.instances not in measure.FAMILIES:
            print(f"unknown family {args.instances!r}; one of: "
                  f"{', '.join(measure.FAMILIES)}", file=sys.stderr)
            return 2
        print("\n".join(report.instances(paths, args.instances)))
        return 0
    from .prose.extract import extract
    blocks = [b for p in paths for b in extract(p).blocks]
    f = measure.features(blocks)
    print(f"  {f.words} words of connective prose, {f.sentences} sentences, "
          f"over {len(paths)} file(s)\n")
    print("\n".join(report.compare(f, bases)))
    print("\n".join(report.sentence_shape(f, bases)))
    print("\n".join(report.per_section(paths, bases)))
    return 0


def cmd_init(args) -> int:
    from . import scaffold
    root = args.root or Path.cwd()
    slug = args.slug
    if slug is None:
        # --sync inside an existing article: take the slug from its config
        slug = config.load(root).slug
    subs = {k: v for k, v in (
        ("TITLE", args.title), ("GITHUB", args.github),
        ("HOME", args.home), ("DOCHOME", args.dochome)) if v}
    return scaffold.init(root, slug=slug, subs=subs, sync=args.sync)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="linkage", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=None,
                    help="article repo root (default: walk up to linkage.toml)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="verify every blueprint/Lean/ledger/paper edge")
    c.add_argument("--wiki", type=Path,
                   help="path to the Notes wiki (enables \\notes{} checking)")
    c.add_argument("--emit-manifest", type=Path, metavar="PATH",
                   help="also write the blueprint manifest the wiki reads")
    c.add_argument("--require-render", action="store_true",
                   help="fail (exit 2) unless the pinned pandoc renders every label — for "
                        "CI, where a manifest without transclusion fields must never reach "
                        "the hub")
    c.set_defaults(func=cmd_check)

    m = sub.add_parser("manifest", help="write the manifest only")
    m.add_argument("path", nargs="?", type=Path, default=None,
                   help="destination (default: ./blueprint-manifest-<slug>.json)")
    m.add_argument("--require-render", action="store_true")
    m.set_defaults(func=cmd_manifest)

    d = sub.add_parser("demand", help="unproved blueprint nodes the hub is asking for")
    d.add_argument("--wiki", type=Path, help="path to the Notes wiki")
    d.add_argument("--json", action="store_true", help="machine-readable output")
    d.set_defaults(func=cmd_demand)

    x = sub.add_parser("axioms", help="the trust-boundary allowlist (Lean core + interfaces)")
    x.add_argument("--check", action="store_true",
                   help="also report the grounding verdict on stderr; fail if the "
                        "declaration file is missing")
    x.set_defaults(func=cmd_axioms)

    k = sub.add_parser("packages", help="shared Lake packages: name, url, rev, destination")
    k.add_argument("--missing-only", action="store_true",
                   help="only those not already checked out")
    k.set_defaults(func=cmd_packages)

    p = sub.add_parser("prose", help="prose measurement over the paper sources")
    psub = p.add_subparsers(dest="prose_cmd", required=True)
    pe = psub.add_parser("extract", help="dump the extraction, for auditing it")
    pe.add_argument("paths", nargs="+", help=".tex sources")
    pe.add_argument("--kind", action="append",
                    help="only these block kinds (prose, statement, proof, "
                         "remark, abstract, list, heading); repeatable")
    pe.add_argument("--long-at", type=int, default=45,
                    help="mark sentences at or above this word count (default 45)")
    pe.set_defaults(func=cmd_prose_extract)

    pb = psub.add_parser("baseline", help="build the author + genre baseline profiles")
    pb.add_argument("--out", type=Path, default=Path("prose-baseline.json"))
    pb.set_defaults(func=cmd_prose_baseline)

    ps = psub.add_parser("stats", help="the report: rates against both baselines")
    ps.add_argument("paths", nargs="+", help=".tex sources")
    ps.add_argument("--baseline", type=Path, default=Path("prose-baseline.json"))
    ps.add_argument("--instances", metavar="FAMILY",
                    help="drill down: located occurrences of one family")
    ps.set_defaults(func=cmd_prose_stats)

    i = sub.add_parser("init", help="scaffold linkage.toml + blueprint skeleton here")
    i.add_argument("--slug", help="satellite id, e.g. 'hcs' (omit with --sync)")
    i.add_argument("--sync", action="store_true",
                   help="refresh the framework-owned files only; leave article files alone")
    i.add_argument("--title", help="document title for the rendered web/print templates")
    i.add_argument("--github", help="the article repo's URL")
    i.add_argument("--home", help="published site URL")
    i.add_argument("--dochome", help="published API-docs URL")
    i.set_defaults(func=cmd_init)

    return ap


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except config.ConfigError as e:
        print(f"CONFIG ERROR: {e}", file=sys.stderr)
        return 2
    except artifacts.MissingLeanPackage as e:
        print(f"CONFIG ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
