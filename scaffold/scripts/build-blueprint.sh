#!/bin/sh
# Rebuild every view of the blueprint, in dependency order, from one command.
#
# There are three views of the same source, and nothing in the framework rebuilds them
# together -- the shared docs workflow builds the PDFs only, and the plasTeX web build is
# still listed as future work in article-kit's LINKAGE.md ("activate the full leanblueprint
# web/dep-graph build"). So this script is the local answer: run it at each round boundary
# and the three cannot drift apart.
#
#   check     `linkage check`           the gate -- statuses, ledger refs, \uses closure,
#                                       and the clean-render rule. Runs FIRST and stops the
#                                       build, because a render-breaking node should fail
#                                       here rather than silently lose a command downstream.
#   print     blueprint/src/print.pdf   statements and proofs as typeset mathematics
#   web       blueprint/web/            the same PLUS the dependency graph and [T]/[A] tags
#   manifest  .manifest-preview.json    what the hub would transclude (pandoc-rendered)
#
# Owner: article-kit's scaffold/scripts/build-blueprint.sh. The copy in an article is a delivery
# of it by `linkage init --sync`; change it there, not in the article.
#
# Usage:
#   scripts/build-blueprint.sh              everything (~30s)
#   scripts/build-blueprint.sh --quick      skip the web build (~13s) -- the inner loop
#   scripts/build-blueprint.sh --web        the web build only
#   scripts/build-blueprint.sh --serve      everything, then serve the graph on :8000
#
# The dependency graph needs a server: file:// URLs cannot fetch the graph's JSON.

set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

DO_CHECK=1; DO_PRINT=1; DO_WEB=1; DO_MANIFEST=1; DO_SERVE=0

case "${1:-}" in
  --quick) DO_WEB=0 ;;
  --web)   DO_CHECK=0; DO_PRINT=0; DO_MANIFEST=0 ;;
  --serve) DO_SERVE=1 ;;
  "")      ;;
  *) echo "usage: $0 [--quick|--web|--serve]" >&2; exit 2 ;;
esac

step() { printf '\n\033[1m== %s\033[0m\n' "$1"; }

if [ "$DO_CHECK" = 1 ]; then
  # Cheap and first: a stray control character makes latexmk fail hundreds of lines later with a
  # message that names the character rather than the cause. See the script's docstring.
  step "control characters"
  python scripts/check-control-chars.py

  step "linkage check"
  linkage check

  # `linkage check` counts statement-level \leanok only, and leanblueprint colours the graph from
  # two flags: statement \leanok gives a green border, proof \leanok a green background. A node
  # with the first and not the second paints as "proof ready, not done" while the check passes.
  # Six nodes were wrong that way before a reader noticed a blue box; two of the six were
  # introduced by the author who had just fixed the other four. Local until article-kit's
  # WISHLIST entry lands.
  step "leanok statement/proof agreement"
  python scripts/audit-leanok.py --check
fi

if [ "$DO_PRINT" = 1 ]; then
  step "print.pdf (latexmk)"
  # latexmk reads blueprint/src/latexmkrc: pdflatex, -synctex=1, default file print.tex.
  ( cd blueprint/src && latexmk -pdf -interaction=nonstopmode print.tex >/dev/null ) \
    || { echo "latexmk failed -- see blueprint/src/print.log" >&2; exit 1; }
  echo "  blueprint/src/print.pdf"
fi

if [ "$DO_WEB" = 1 ]; then
  step "web build (plasTeX + dependency graph)"
  # plastex.cfg sets directory=../web/, so this must run from blueprint/src.
  # Two warnings are expected and harmless: "default renderer for newtheorem" (the extra
  # environments declared in theorems-extra.tex) and "default renderer for bigskip".
  # PYTHONUTF8=1 on this one command: plasTeX writes the \lean-tag declaration list with
  # Python's default encoding, which is cp1252 on Windows, and dies on a non-ASCII Lean
  # declaration name such as `b₀` (U+2080). The symptom is Windows-only; Linux CI defaults
  # to UTF-8 and never sees it.
  ( cd blueprint/src && PYTHONUTF8=1 plastex -c plastex.cfg web.tex >/dev/null 2>&1 ) \
    || { echo "plastex failed -- rerun without >/dev/null to see why" >&2; exit 1; }
  echo "  blueprint/web/index.html"
  echo "  blueprint/web/dep_graph_document.html"
fi

if [ "$DO_MANIFEST" = 1 ]; then
  step "manifest preview (pandoc render gate)"
  # --require-render turns a missing/wrong pandoc, or any per-label render failure, into a
  # hard error. That is the point: the hub byte-compares rendered_sha, so a node that fails
  # to render must fail here and not at import time. Pandoc is pinned at 3.10.
  linkage manifest .manifest-preview.json --require-render
fi

if [ "$DO_SERVE" = 1 ]; then
  step "serving blueprint/web on http://localhost:8000"
  echo "  graph: http://localhost:8000/dep_graph_document.html   (ctrl+c to stop)"
  ( cd blueprint/web && python -m http.server 8000 )
fi

printf '\n\033[1mdone.\033[0m\n'
