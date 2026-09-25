#!/usr/bin/env bash
#
# sync-agents-hook.sh — keep the constellation's shared sub-agents current from an article session.
#
# Shared agents (librarian, mathematician, draft-reviewer, …) are installed user-level and derived
# from the repo that owns them by the hub's .claude/sync-agents.sh (hub adr/0008). That script ran
# only when a *hub* session started, so an author working in an article repo for a week kept
# whatever the last hub session installed. This hook finds the hub and runs its script.
#
# Silent when everything is current (the hub script's own contract), and never fails a session
# start: every path here exits 0. No hub found is not an error — say nothing.
#
# Seeded once into .claude/ by `linkage init`; it is the article's own after that.

hub_dir() {
  local project="${CLAUDE_PROJECT_DIR:-$PWD}" cand
  # $WIKI_VAULT first, then the sweep cloud-setup.sh uses: attached repos, siblings, ~/dev,
  # and the hub's usual home. The marker is the script itself, so a stale $WIKI_VAULT is skipped.
  for cand in "${WIKI_VAULT:-}" /workspace/*/ "$(dirname "$project")"/*/ "$HOME"/dev/*/ "$HOME/Documents/Notes"; do
    cand="${cand%/}"
    [ -n "$cand" ] && [ -f "$cand/.claude/sync-agents.sh" ] || continue
    [ "$cand" = "${project%/}" ] && continue
    printf '%s' "$cand"
    return 0
  done
  return 1
}

hub="$(hub_dir 2>/dev/null)" || exit 0
# The hub script resolves hub-owned agents (`.`) and its siblings from CLAUDE_PROJECT_DIR, so
# point that at the hub, not at this article.
CLAUDE_PROJECT_DIR="$hub" bash "$hub/.claude/sync-agents.sh" || true
exit 0
