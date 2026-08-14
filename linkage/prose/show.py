"""Human-readable dump of an extraction — for auditing the extractor itself.

Not the review report. This exists so the sentence splitting and the environment
classification can be *looked at* before anything is counted on top of them.
"""
from __future__ import annotations

from pathlib import Path

from .extract import Extraction, extract

KIND_MARK = {"prose": " ", "statement": "S", "proof": "P", "remark": "R",
             "abstract": "A", "list": "-", "heading": "#"}


def summarize(ex: Extraction) -> list[str]:
    by_kind: dict[str, list[int]] = {}
    for b in ex.blocks:
        by_kind.setdefault(b.kind, []).append(b.words)
    out = ["", "  kind        blocks    words   words/block"]
    for kind, ws in sorted(by_kind.items(), key=lambda kv: -sum(kv[1])):
        tot = sum(ws)
        out.append(f"  {kind:<10} {len(ws):>7} {tot:>8} {tot / len(ws):>13.0f}")
    return out


def audit(ex: Extraction) -> list[str]:
    out = []
    if ex.unknown:
        out.append("")
        out.append("  unrecognised commands (argument kept as prose — check for "
                   "anything whose argument is NOT prose):")
        for cmd, cnt in sorted(ex.unknown.items(), key=lambda kv: -kv[1]):
            out.append(f"    \\{cmd:<20} {cnt:>4}   {ex.unknown_ctx.get(cmd, '')[:90]}")
    if ex.dropped_envs:
        out.append("")
        out.append("  environments skipped wholesale:")
        for env, cnt in sorted(ex.dropped_envs.items(), key=lambda kv: -kv[1]):
            out.append(f"    {env:<25} {cnt}")
    return out


def dump(path: Path, *, kinds: set[str] | None = None, long_at: int = 45) -> str:
    ex = extract(path)
    lines = [f"{path}  —  {len(ex.blocks)} blocks, {ex.words} prose words"]
    lines += summarize(ex)
    lines += audit(ex)
    lines.append("")
    lines.append("  " + "-" * 76)

    seen = None
    for b in ex.blocks:
        if kinds and b.kind not in kinds:
            continue
        head = b.section + (f" › {b.subsection}" if b.subsection else "")
        if head != seen:
            lines.append("")
            lines.append(f"  §  {head}")
            seen = head
        if b.kind == "heading":
            lines.append(f"     [#] {b.text}")
            continue
        tag = KIND_MARK.get(b.kind, "?")
        meta = f"L{b.line}"
        if b.env and b.kind != "prose":
            meta += f" {b.env}"
        if b.emdashes:
            meta += f" em×{b.emdashes}"
        if b.title:
            meta += f"  [{b.title}]"
        lines.append(f"     [{tag}] {meta}")
        for s in b.sentences:
            mark = "!" if s.words >= long_at else (
                "0" if s.words == 0 else " ")
            extra = []
            if s.math:
                extra.append(f"m{s.math}")
            if s.cites:
                extra.append(f"c{s.cites}")
            if s.refs:
                extra.append(f"r{s.refs}")
            note = ("/" + ",".join(extra)) if extra else ""
            lines.append(f"       {mark}{s.words:>3}w{note:<10} {s.text}")
        if b.emphases:
            lines.append(f"          emph: {'; '.join(b.emphases)}")
    return "\n".join(lines)


def main(args) -> int:
    for p in args.paths:
        print(dump(Path(p), kinds=set(args.kind) if args.kind else None,
                   long_at=args.long_at))
        print()
    return 0
