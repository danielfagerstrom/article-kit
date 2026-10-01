#!/usr/bin/env python3
"""Find prose swallowed by a comment: text that was prose at a base revision and now sits at the
end of a `%` line.

Why this exists: the session rule (`docs/PROCESS.md`, `.claude/rules/article-kit/lean.md`) has
every changed statement carry a `% CHANGED` marker. When an edit's replacement ends with that
marker and the text it matched stopped mid-source-line, the rest of that line becomes comment. The
build stays clean, and `linkage check` stays clean too -- it strips comments on both sides of a
shared statement before comparing them -- so only a reader of the rendered PDF sees the sentence
broken. `spatial-hemigroup-scale-space` module C carried thirteen such broken sentences through two
external review rounds and a blind summary pass; its round 3 presentation referee found three by
eye before this detector (ported from that repository's `scripts/check-swallowed-prose.py`) found
the rest.

Usage: python scripts/check-swallowed-prose.py <base-revision>
Compares every changed `.tex` under the article's configured paper directories (`linkage.toml`'s
`paths.paper`, default `paper`) and `blueprint/src/parts` with the base revision. A hit is an added
comment line, followed directly by prose, whose tail plus that prose occurs as unbroken prose in
the base version and does not end its own sentence. A comment that quotes old wording can still
match; read each hit. Exit 1 if there is any hit.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tomllib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_NAME = "linkage.toml"


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True,
                          encoding="utf-8").stdout


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def paper_dirs() -> list[str]:
    """The module's configured paper directories -- `linkage.toml`'s `paths.paper`, one
    directory or a list of them (`linkage.config.Config.papers`). No config file, or no
    `paths.paper` key, falls back to the framework default, `paper`."""
    config_path = os.path.join(REPO, CONFIG_NAME)
    if not os.path.isfile(config_path):
        return ["paper"]
    with open(config_path, "rb") as f:
        raw = tomllib.load(f)
    paper = raw.get("paths", {}).get("paper", "paper")
    return [paper] if isinstance(paper, str) else list(paper)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    base = sys.argv[1]
    dirs = [*paper_dirs(), "blueprint/src/parts"]
    files = [f for f in git("diff", "--name-only", base, "--", *dirs).split()
            if f.endswith(".tex")]
    hits = 0
    for f in files:
        path = os.path.join(REPO, f)
        if not os.path.exists(path):
            continue
        old = git("show", f"{base}:{f}")
        prose = norm(" ".join(ln for ln in old.splitlines() if not ln.lstrip().startswith("%")))
        oldlines = {ln.rstrip() for ln in old.splitlines()}
        with open(path, encoding="utf-8") as fh:
            cur = fh.read().splitlines()
        for i, line in enumerate(cur):
            if not line.lstrip().startswith("%") or line.rstrip() in oldlines:
                continue
            nxt = cur[i + 1] if i + 1 < len(cur) else ""
            if nxt.lstrip().startswith("%") or not nxt.strip():
                continue
            words = line.lstrip()[1:].strip().split(" ")
            for j in range(1, len(words)):
                tail = norm(" ".join(words[j:]))
                # A swallowed tail breaks off mid-sentence; a comment that ends its own sentence
                # (".") or is commented-out code ("}") and happens to match old prose is not one.
                if tail.endswith((".", "}")):
                    break
                if norm(tail + " " + nxt)[:60] in prose:
                    print(f"{f}:{i + 1}: comment ends {tail!r}, prose resumes {nxt.strip()[:40]!r}")
                    hits += 1
                    break
    print(f"{hits} candidate(s)" if hits else "no swallowed prose")
    sys.exit(1 if hits else 0)


if __name__ == "__main__":
    main()
