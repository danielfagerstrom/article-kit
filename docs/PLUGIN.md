# article-kit as a Claude Code plugin

The shared skills and the shared agent this repository owns used to reach a session by hand: the
skills through a user-level junction (`~/.claude/skills/fidelity-review → <this repo>/.claude/skills/fidelity-review`;
`tighten`'s was never installed on the author's machine), the `mathematician` through the hub's
`.claude/sync-agents.sh`, which copies it into `~/.claude/agents/` and runs only when a *hub*
session starts. Both are per-machine acts that nothing checks, and neither happens in a cloud
session at all.

This repository is therefore also a **Claude Code plugin** in a **marketplace of its own**, which
each article declares in its checked-in `.claude/settings.json`. An article session — local or
cloud, this machine or another — then gets the skills and the agent from the repository that owns
them, at the revision the marketplace resolves, with nothing installed by hand.

ADR-0001 step 6 is the decision; `WISHLIST.md` § "process: skills and agents as a Claude Code
plugin" is the request.

## What the plugin ships

| component | plugin name in a session | source of truth |
|---|---|---|
| `fidelity-review` skill | `/article-kit:fidelity-review` | `.claude/skills/fidelity-review/` |
| `tighten` skill | `/article-kit:tighten` | `.claude/skills/tighten/` |
| `mathematician` agent | `mathematician` | `.claude/agents/mathematician.md` |

Nothing else. The session **rules** are not in the plugin: they reach an article as
framework-owned copies under `.claude/rules/article-kit/`, written by `linkage init` and checked
for drift by `linkage check` (ADR-0001), because path-scoped rules must be in the project to be
scoped to its files. The `linkage` CLI stays a `uv tool install`.

## The layout, and why the files stay under `.claude/`

```
.claude-plugin/plugin.json        the plugin manifest — points at the components below
.claude-plugin/marketplace.json   the marketplace manifest — one plugin, source "./"
.claude/skills/<name>/            the skills, unmoved
.claude/agents/mathematician.md   the agent, unmoved
```

A plugin's default layout is `skills/` and `agents/` at the plugin root; the manifest's `skills`
and `agents` arrays may instead name paths, and that is what is used here. The reason is the rule
this constellation keeps everywhere (hub ADR-0008): *no second copy of a file another place owns.*
A session **in article-kit** resolves `.claude/skills/` and `.claude/agents/` as project
components — that is how the framework's own sessions run the fidelity review and dispatch the
mathematician — so moving the files to `skills/` and `agents/` at the root would either break that
or require a copy. Pointing the manifest at them keeps exactly one copy of each file, serving both
readers.

The consequence to know: inside article-kit these components are *also* project components, so a
session here that has the plugin enabled sees each skill twice — once as `fidelity-review`
(project) and once as `article-kit:fidelity-review` (plugin). Same file, same behaviour. Article
sessions, which have no `.claude/skills/`, see only the namespaced names.

The versions in `plugin.json` and `marketplace.json` track `pyproject.toml`'s; `tests/test_plugin.py`
fails if they drift, which is the "make the divergence detectable" half of ADR-0008.

## What an article declares

`scaffold/claude/settings.json` — seeded into a new article as `.claude/settings.json` by
`linkage init` — now carries:

```json
{
  "extraKnownMarketplaces": {
    "article-kit": {
      "source": {
        "source": "github",
        "repo": "danielfagerstrom/article-kit"
      }
    }
  },
  "enabledPlugins": {
    "article-kit@article-kit": true
  }
}
```

The marketplace is named by its `.claude-plugin/marketplace.json` (`article-kit`) and the plugin by
its `.claude-plugin/plugin.json` (`article-kit`), which is why the enabled key reads
`article-kit@article-kit` — plugin first, marketplace second.

## Migration

The plugin does not replace the old paths until the old paths are removed, and while both exist the
**old one wins**: project agents outrank user-level agents, which outrank plugin agents, so a stale
`~/.claude/agents/mathematician.md` would silently keep defining the agent. In order:

1. **Enable it** in one article repo and confirm the components appear (below).
2. **Remove this machine's junction** `~/.claude/skills/fidelity-review`. Until it goes, the skill
   is offered twice from one session — unnamespaced from the junction, namespaced from the plugin.
   `tighten` has no junction to remove. *(The author's: an unattended session may not write under
   `~/.claude/`.)*
3. **Retire the `mathematician` row of the hub's sync table.** `.claude/sync-agents.sh`'s `AGENTS`
   table has one row `mathematician|ARTICLE_KIT_DIR|article-kit`; the plugin makes it redundant, and
   the copy it installs *outranks* the plugin's. Delete the row and delete
   `~/.claude/agents/mathematician.md`. The script's "installed but no table row claims it" warning
   is what will tell you if the file is still there. *(The hub's change, and the author's.)*
4. **Existing article repos** (`spatial-hemigroup-scale-space`, `spatial-hemigroup-affine`,
   `spatial-hemigroup-pyramids`, `hemigroup-kernels-ssvm`, …): `.claude/settings.json` is *seeded*,
   not framework-owned, so `linkage init --sync` will not touch it. Merge the two keys above into
   each by hand. A repo scaffolded before Q-0121 also lacks `.claude/sync-agents-hook.sh`; copy it
   from `scaffold/claude/` if the hook line is wanted (see below).
5. **Cloud sessions**: see "In the cloud".

### The hook and the plugin coexist

Q-0121's scaffolded `SessionStart` hook (`.claude/sync-agents-hook.sh` → the hub's
`sync-agents.sh`) stays. It is not a duplicate of the plugin: after step 3 the two mechanisms
carry disjoint sets of agents.

- **article-kit's own** components — `mathematician`, `fidelity-review`, `tighten` — come from this
  plugin.
- **The hub's own** shared agents — `draft-reviewer`, `archivist` — and the **librarian's**
  `librarian` stay owned by their repositories and keep arriving through the hub's sync table. This
  repository does **not** carry copies of them; a `draft-reviewer.md` under article-kit's `agents/`
  would be exactly the second source of truth ADR-0008 forbids, and it would go stale the way the
  installed `librarian` once did (12 days, 228 lines).

How a hub-owned agent reaches a session *as a plugin*, when that is wanted, is the same move one
repository down: the hub declares its own `.claude-plugin/` over the agent files it already owns,
publishes it as the marketplace `notes-wiki` (or whatever it calls itself), and an article's
`settings.json` grows a second marketplace and a second enabled plugin. The file stays in the hub
and stays single. Nothing in this plugin has to change for that, and nothing here should be held up
waiting for it — that is why the hook is still here.

### In the cloud

`article-kit` is a **private** repository, so a `github` marketplace source needs credentials.
Locally the author's git credentials serve. In a cloud session the agent proxy will not clone an
unattached private repo — the failure mode `cloud-setup.sh` already documents for the vault and the
librarian — so a cloud environment that wants the plugin must **attach `danielfagerstrom/article-kit`
as an additional source repository** ([`CLOUD.md`](CLOUD.md)); it is worth attaching anyway, since
`cloud-setup.sh` then installs `linkage` editable from the checkout instead of from git.

If the marketplace still fails to resolve there, the fallback is a path source pointing at the
attached checkout, in the *environment's* settings rather than the repository's (the repository's
one file has to be true on both this machine and in the cloud):

```json
{
  "extraKnownMarketplaces": {
    "article-kit": { "source": { "source": "directory", "path": "/workspace/article-kit" } }
  }
}
```

## Verifying it — the pilot

The pilot repository is `spatial-hemigroup-scale-space` (ADR-0001). What this change verified, and
what is left for the author, is recorded here rather than in a session note.

**Verified in CI and by `pytest`** (`tests/test_plugin.py`):

- `plugin.json` and `marketplace.json` are valid JSON with the required fields, the marketplace's
  single plugin entry names this plugin, and the three component paths the manifest declares exist
  (a renamed or deleted skill fails the test);
- the manifest versions match `pyproject.toml`'s;
- `scaffold/claude/settings.json` is valid JSON, declares the marketplace and enables
  `article-kit@article-kit`, and still carries both `SessionStart` hooks;
- a fresh `linkage init` writes that declaration into the new article's `.claude/settings.json`.

**Verified against the pilot, 2026-09-25**, as a dry run outside the repository (the change that
introduced the plugin was allowed to edit article-kit only): the two keys merged into
`spatial-hemigroup-scale-space`'s existing `.claude/settings.json` give valid JSON with its
`cloud-setup.sh` hook intact. That repository was scaffolded before Q-0121, so it has **one**
`SessionStart` hook and no `.claude/sync-agents-hook.sh`; it needs the file copied from
`scaffold/claude/` and the second hook line added if the hub-owned agents are to stay current from
its sessions (step 4 above), and until then `draft-reviewer` and `librarian` there are whatever a
hub session last installed.

**Left for the author** — these need the `claude` binary, which an unattended session may not run,
and a cloud environment, which it cannot reach:

```bash
claude plugin validate .                         # in this checkout: the manifest loads
claude plugin marketplace add C:/Users/danie/dev/article-kit    # local source, for the pilot
claude                                           # then: /plugin  → article-kit listed, enabled
```

Then in `spatial-hemigroup-scale-space`, after steps 2–4 above:

- `/article-kit:fidelity-review` and `/article-kit:tighten` are offered, and the unnamespaced names
  are gone;
- a `mathematician` dispatch resolves to the plugin's file (check the agent's own contents, not just
  the name — the point of step 3);
- the same repository in a cloud session, with article-kit attached, offers the same three.

Record the outcome in this section; if the `github` source does not resolve in the cloud, record
which fallback was used.
