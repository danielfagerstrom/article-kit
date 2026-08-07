#!/usr/bin/env bash
#
# cloud-setup.sh — provision a Claude Code on the web session as a working SSF
# authoring environment (paper/blueprint sessions; NOT Lean proving — see CLOUD.md).
#
# Wired as a SessionStart hook in .claude/settings.json (NOT the environment's
# "Setup script" field — a setup script runs before the repo is checked out, so
# it can't find this file; that was the hub's exit-127 failure). A SessionStart
# hook is part of the clone and runs with $CLAUDE_PROJECT_DIR pointing at the
# checkout. This mirrors the hub's .claude/cloud-setup.sh (notes-wiki repo);
# see the hub's CLOUD.md for the shared background and this repo's CLOUD.md for
# the SSF-specific environment dialog walkthrough.
#
# What it does, idempotently:
#   1. ensure uv is on PATH and resolve a Python 3.13 interpreter (prefer the
#      image's system one; `uv python install` is proxy-blocked in the sandbox)
#   2. locate the attached Notes-vault and librarian checkouts, then
#      editable-install `wiki` (from the vault) and `library` (with .[drive])
#   3. materialise the librarian's Drive config + service account from env vars
#      (schema-agnostic — the librarian owns the shapes)
#   4. install Tectonic (pinned, same release asset as docs.yml) so sessions can
#      compile-check paper/main.tex and blueprint/src/print.tex
#   5. persist WIKI_VAULT for the session and smoke-test the result
#
# ── Environment variables the cloud environment must provide ──────────────────
# Same names and values as the hub environment (they share the account-side
# secrets); see CLOUD.md here and the hub's CLOUD.md for what goes in each:
#   LIBRARY_CONFIG_JSON  the librarian's cloud config.json — the two Drive keys
#                        (gdrive_root_folder_id + gdrive_credentials → the SA
#                        path below, default /root/.config/library/gdrive-sa.json).
#   GDRIVE_SA_JSON       the read-only Google service-account JSON, one line. SECRET.
#   ZOTERO_API_KEY,      read straight from the environment by the librarian
#   ZOTERO_USER_ID       (zotero/api.py) — no file needed. SECRET (read-only key).
#   LIBRARY_ROLE=reader  marks a read-only session (acquire request → git inbox).
#
# Assumptions: Ubuntu 24.04, runs as root (Claude Code web default). The Notes
# vault (danielfagerstrom/notes-wiki) and librarian (danielfagerstrom/library)
# must be ATTACHED as additional source repos on the environment — the GitHub
# proxy will not clone unattached private repos.

# SessionStart hooks fire on BOTH local and cloud sessions; CLAUDE_CODE_REMOTE is
# "true" only in the cloud. Local machines are provisioned by hand (BOOTSTRAP.md
# in the hub), so bail silently everywhere else.
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0

set -euo pipefail

log() { printf '\n\033[1;34m[cloud-setup]\033[0m %s\n' "$*"; }
warn() { printf '\n\033[1;33m[cloud-setup] WARN:\033[0m %s\n' "$*" >&2; }

# This repo's checkout: prefer the hook's $CLAUDE_PROJECT_DIR, else resolve from
# this script's own location (.claude/cloud-setup.sh).
if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
  ARTICLE_DIR="$CLAUDE_PROJECT_DIR"
else
  ARTICLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

TECTONIC_VERSION="0.15.0"   # keep in lockstep with .github/workflows/docs.yml

# ── Locate the attached sibling checkouts ─────────────────────────────────────
# Attached source repos land under /workspace/<name> (or beside this checkout);
# don't hard-code names — detect by marker files. The vault is the directory
# holding wiki/index.md (the wiki CLI itself detects a vault by CLAUDE.md +
# wiki/); the librarian is the directory holding librarian/cli.py.
find_by_marker() {  # find_by_marker MARKER-RELPATH → first match on stdout
  local marker="$1" cand
  for cand in /workspace/*/ "$(dirname "$ARTICLE_DIR")"/*/ "$HOME"/dev/*/; do
    [ -e "$cand$marker" ] || continue
    [ "${cand%/}" = "$ARTICLE_DIR" ] && continue
    printf '%s' "${cand%/}"
    return 0
  done
  return 1
}

if [ -n "${WIKI_VAULT:-}" ] && [ -d "$WIKI_VAULT/wiki" ]; then
  VAULT_DIR="$WIKI_VAULT"
else
  VAULT_DIR="$(find_by_marker wiki/index.md || true)"
fi
if [ -n "${LIBRARY_DIR:-}" ]; then
  LIB_DIR="$LIBRARY_DIR"
else
  LIB_DIR="$(find_by_marker librarian/cli.py || true)"
fi
# The linkage framework. If this session IS the framework repo, use it directly —
# otherwise look for an attached sibling, and fall back to installing from git.
if [ -n "${LINKAGE_DIR:-}" ]; then
  LNK_DIR="$LINKAGE_DIR"
elif [ -f "$ARTICLE_DIR/linkage/cli.py" ]; then
  LNK_DIR="$ARTICLE_DIR"
else
  LNK_DIR="$(find_by_marker linkage/cli.py || true)"
fi

# Clone fallbacks — these only work if the proxy has credentials for the repo,
# i.e. effectively never for an unattached private repo; the warnings say so.
if [ -z "$VAULT_DIR" ]; then
  VAULT_DIR="$HOME/dev/notes-wiki"
  log "no Notes-vault checkout found — trying to clone (likely to fail unless attached)"
  git clone --depth 1 https://github.com/danielfagerstrom/notes-wiki.git "$VAULT_DIR" || {
    warn "could not clone the Notes vault. Durable fix: attach danielfagerstrom/notes-wiki"
    warn "as an additional SOURCE repo on this environment (see CLOUD.md). Continuing"
    warn "without it — wiki gate/show/demands and the writing-style guide are unavailable."
    VAULT_DIR=""
  }
fi
if [ -z "$LIB_DIR" ]; then
  LIB_DIR="$HOME/dev/library"
  log "no librarian checkout found — trying to clone (likely to fail unless attached)"
  git clone --depth 1 https://github.com/danielfagerstrom/library.git "$LIB_DIR" || {
    warn "could not clone the librarian. Durable fix: attach danielfagerstrom/library"
    warn "as an additional SOURCE repo on this environment (see CLOUD.md). Continuing"
    warn "without it — library resolve / citation reads are unavailable."
    LIB_DIR=""
  }
fi
[ -n "$VAULT_DIR" ] && log "Notes vault: $VAULT_DIR"
[ -n "$LIB_DIR" ] && log "librarian:   $LIB_DIR"

CFG_DIR="${LIBRARY_CONFIG_DIR:-$HOME/.config/library}"
SA_PATH="$CFG_DIR/gdrive-sa.json"

smoke_test() {
  log "verifying …"
  set +e
  wiki --version
  WIKI_VAULT="${VAULT_DIR:-}" wiki config
  library config
  linkage --help >/dev/null && echo 'linkage: ok'
  tectonic --version
  set -e
  log "done. Resolve a source with: library resolve <citekey> --json (no G: mount"
  log "means the Drive fallback is live). In an article repo: linkage check."
}

persist_env() {
  # Persist WIKI_VAULT for the session's later Bash calls via the hook env file.
  if [ -n "${CLAUDE_ENV_FILE:-}" ] && [ -n "$VAULT_DIR" ]; then
    printf 'WIKI_VAULT=%s\n' "$VAULT_DIR" >> "$CLAUDE_ENV_FILE"
  fi
}

# Fast path: on a resumed session everything may already be installed. Skip the
# heavy work (SessionStart hooks aren't cached, so this keeps warm restarts quick).
if command -v wiki >/dev/null 2>&1 && command -v library >/dev/null 2>&1 \
   && command -v linkage >/dev/null 2>&1 \
   && command -v tectonic >/dev/null 2>&1 && [ -f "$CFG_DIR/config.json" ]; then
  log "already provisioned — skipping install."
  persist_env
  smoke_test
  exit 0
fi

# ── 1. Toolchain: uv + Python 3.13, installed where every shell can see them ──
export UV_INSTALL_DIR=/usr/local/bin
export UV_TOOL_BIN_DIR=/usr/local/bin
export INSTALLER_NO_MODIFY_PATH=1

if ! command -v uv >/dev/null 2>&1; then
  log "installing uv → /usr/local/bin"
  command -v curl >/dev/null 2>&1 || { apt-get update -qq && apt-get install -y -qq curl; }
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="/usr/local/bin:$PATH"
else
  log "uv already present: $(command -v uv)"
fi

# Resolve a Python 3.13 interpreter. `uv python install 3.13` downloads a pinned
# CPython build from GitHub releases, which the cloud's agent proxy 403s — the
# Ubuntu 24.04 cloud image already ships /usr/bin/python3.13, so prefer an
# interpreter that's already here and only fall back to the download.
log "resolving a Python 3.13 interpreter"
PYTHON313="$(command -v python3.13 || true)"
if [ -n "$PYTHON313" ]; then
  log "using existing Python 3.13: $PYTHON313 ($("$PYTHON313" --version 2>&1))"
else
  log "no system python3.13 — asking uv to fetch one (may be proxy-blocked)"
  if uv python install 3.13; then
    PYTHON313="$(uv python find 3.13 || true)"
  fi
  if [ -z "$PYTHON313" ]; then
    warn "could not obtain Python 3.13 — the download is likely proxy-blocked."
    warn "install one at the OS level (apt-get install -y python3.13) and re-run."
    PYTHON313=3.13   # last resort: let each uv tool call do its own resolution
  fi
fi

# ── 2. Install the CLIs (editable, so a `git pull` updates them in place) ─────
if [ -n "$LIB_DIR" ] && [ -d "$LIB_DIR" ]; then
  log "installing library (with the .[drive] Drive-API extra)"
  ( cd "$LIB_DIR" && uv tool install --editable ".[drive]" --python "$PYTHON313" --force )
fi
if [ -n "$VAULT_DIR" ] && [ -d "$VAULT_DIR" ]; then
  log "installing wiki (from the Notes-vault checkout)"
  uv tool install --editable "$VAULT_DIR" --python "$PYTHON313" --force
fi
# linkage: editable from a checkout when one is attached (so a `git pull` updates it),
# else straight from git — it is stdlib-only, so this always works when the network does.
if [ -n "$LNK_DIR" ] && [ -d "$LNK_DIR" ]; then
  log "installing linkage (editable, from $LNK_DIR)"
  uv tool install --editable "$LNK_DIR" --python "$PYTHON313" --force
else
  log "no linkage checkout found — installing from git"
  uv tool install "git+https://github.com/danielfagerstrom/article-kit" --python "$PYTHON313" --force \
    || warn "could not install linkage — \`linkage check\` unavailable this session."
fi

# ── 3. Materialise librarian config + service account from env (schema-agnostic) ──
mkdir -p "$CFG_DIR"
write_if_set() {  # write_if_set VALUE DEST MODE VARNAME
  if [ -n "$1" ]; then
    printf '%s' "$1" > "$2"; chmod "$3" "$2"
    log "wrote $2"
  else
    warn "\$$4 is empty — skipped $2 (set it in the environment's variables)"
  fi
}
# Zotero creds (ZOTERO_API_KEY / ZOTERO_USER_ID) and LIBRARY_ROLE are read from
# the environment directly — no file to write. Only the config.json (Drive keys)
# and the service-account JSON need materialising.
write_if_set "${LIBRARY_CONFIG_JSON:-}" "$CFG_DIR/config.json" 644 LIBRARY_CONFIG_JSON
write_if_set "${GDRIVE_SA_JSON:-}"      "$SA_PATH"             600 GDRIVE_SA_JSON
log "service-account path (point LIBRARY_CONFIG_JSON's gdrive_credentials here): $SA_PATH"

# ── 4. Tectonic — the LaTeX toolchain (pinned; same asset as docs.yml) ────────
# A single static binary; it fetches TeX packages on demand from the bundle CDN
# (relay.fullyjustified.net → data1/data2.fullyjustified.net — allowlisted, see
# CLOUD.md) and caches them under ~/.cache/Tectonic.
if command -v tectonic >/dev/null 2>&1; then
  log "tectonic already present: $(tectonic --version 2>&1)"
else
  log "installing Tectonic ${TECTONIC_VERSION} → /usr/local/bin"
  TMPD="$(mktemp -d)"
  if curl -fsSL -o "$TMPD/tectonic.tar.gz" \
      "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%40${TECTONIC_VERSION}/tectonic-${TECTONIC_VERSION}-x86_64-unknown-linux-musl.tar.gz"; then
    tar -xzf "$TMPD/tectonic.tar.gz" -C "$TMPD" tectonic
    mv "$TMPD/tectonic" /usr/local/bin/tectonic
    chmod +x /usr/local/bin/tectonic
  else
    warn "Tectonic download failed — is release-assets.githubusercontent.com allowlisted?"
    warn "LaTeX compile checks will be unavailable this session."
  fi
  rm -rf "$TMPD"
fi

# ── 5. Persist env + smoke test (non-fatal — report, don't abort the session) ─
persist_env
smoke_test
