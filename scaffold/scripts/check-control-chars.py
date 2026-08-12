#!/usr/bin/env python3
"""Reject stray control characters in source files.

Why this exists: writing LaTeX or Lean through a non-raw Python string literal silently turns
`\\begin` into U+0008, `\\texttt` into a TAB and `\\ref` into a CR. The result still looks almost
right in a diff, and LaTeX fails several hundred lines later with a message that names the
character rather than the cause. This ran three times in one session before being caught.

Legal control characters in these sources are LF and (on Windows checkouts) CR immediately before
LF. Anything else -- a bare TAB, a lone CR, a backspace -- is corruption.

Usage: python scripts/check-control-chars.py [paths...]   (default: the tracked source trees)
"""

from __future__ import annotations

import sys
from pathlib import Path

DEFAULT_GLOBS = [
    "blueprint/src/**/*.tex",
    "blueprint/*.md",
    "draft/*.md",
    "*.md",
    "Formalization/**/*.lean",
]

LF = 0x0A
CR = 0x0D


def offenders(data: bytes) -> list[tuple[int, int]]:
    """Return (offset, byte) for each illegal control character."""
    bad = []
    for i, c in enumerate(data):
        if c >= 0x20 or c == LF:
            continue
        if c == CR and i + 1 < len(data) and data[i + 1] == LF:
            continue  # CRLF line ending
        bad.append((i, c))
    return bad


def line_of(data: bytes, offset: int) -> int:
    return data.count(bytes([LF]), 0, offset) + 1


def main(argv: list[str]) -> int:
    root = Path(".")
    if len(argv) > 1:
        paths = [Path(a) for a in argv[1:]]
    else:
        paths = []
        for pattern in DEFAULT_GLOBS:
            paths.extend(sorted(root.glob(pattern)))

    failed = False
    for path in paths:
        if not path.is_file():
            continue
        data = path.read_bytes()
        for offset, char in offenders(data):
            failed = True
            snippet = data[max(0, offset - 40):offset + 40]
            print(
                f"{path}:{line_of(data, offset)}: illegal control character "
                f"U+{char:04X} -- near {snippet!r}",
                file=sys.stderr,
            )

    if failed:
        print(
            "\nThis is almost always a non-raw Python string literal writing LaTeX or Lean:\n"
            "  \\b -> U+0008, \\t -> TAB, \\r -> CR, \\f -> U+000C.\n"
            "Use the Edit tool, a raw string, or bytes([92]) for the backslash.",
            file=sys.stderr,
        )
        return 1

    print(f"control-char check OK ({len(paths)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
