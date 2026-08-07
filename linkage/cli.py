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


def cmd_init(args) -> int:
    from . import scaffold
    return scaffold.init(Path.cwd(), slug=args.slug)


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

    i = sub.add_parser("init", help="scaffold linkage.toml + blueprint skeleton here")
    i.add_argument("--slug", required=True, help="satellite id, e.g. 'hcs'")
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


if __name__ == "__main__":
    sys.exit(main())
