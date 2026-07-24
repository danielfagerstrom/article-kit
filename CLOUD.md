# CLOUD — running SSF sessions on Claude Code on the web

How to run **paper/blueprint authoring sessions** for this repo as Claude Code on the web cloud
sessions. This is the SSF instance of the hub's phase-3 recipe — the shared background (why a
committed `SessionStart` hook and not the environment's Setup-script field, the secrets-visibility
caveat, the obsidian-git replica model) lives in the **hub's `CLOUD.md`** (`notes-wiki` repo, root)
and is not duplicated here. Repo-side provisioning is already committed:

- [`.claude/settings.json`](.claude/settings.json) — the `SessionStart` hook (matcher `startup|resume`).
- [`.claude/cloud-setup.sh`](.claude/cloud-setup.sh) — installs `wiki` + `library[.drive]` from the
  attached checkouts, materialises the librarian's Drive config/secrets from env vars, installs
  **Tectonic** (pinned to `docs.yml`'s version), persists `WIKI_VAULT`, and smoke-tests. Fast no-op
  on local sessions (gated on `CLAUDE_CODE_REMOTE=true`) and on warm restarts.

**Scope.** Cloud SSF sessions are for paper/blueprint work and *statement-level* Lean edits (push a
branch, let `lean.yml` be the checker — ~5–10 min/iteration). **Not for Lean proving**: SessionStart
hooks aren't cached, so every cold session would re-download the multi-GB Mathlib cache. Real
proving stays local (fast language server).

---

## One-time: create the cloud environment

At [claude.ai/code](https://claude.ai/code), connect `danielfagerstrom/scale-space-foundations` and
create/edit its environment.

### 1. Attach the sibling repos — required

Add **two additional source repositories** to the environment (phase-3 lesson: the GitHub proxy will
**not** clone unattached private repos, so the hook cannot fetch them itself):

- `danielfagerstrom/notes-wiki` — the vault (`$WIKI_VAULT`): `wiki gate/show/demands`, the outline,
  the source digests, the private writing-style guide.
- `danielfagerstrom/library` — the librarian: `library resolve`/`page` via the Drive-API fallback.

They land under `/workspace/<name>`; the hook detects them by marker files, not by name.

### 2. Network access → Custom

Keep **"include default list of common package managers"** checked, then add (the hub's three plus
the Tectonic hosts):

```
api.zotero.org
*.googleapis.com
astral.sh
release-assets.githubusercontent.com
relay.fullyjustified.net
data1.fullyjustified.net
data2.fullyjustified.net
```

The first three are the hub's list (Zotero metadata; Drive API; uv installer). The rest are
Tectonic: `release-assets.githubusercontent.com` is where `github.com` release-asset downloads
redirect (the pinned binary; verified 2026-07-24), and `relay.fullyjustified.net` is Tectonic's
default package-bundle relay, redirecting to `data1`/`data2.fullyjustified.net` (verified: the
relay 302s to `data1`). If the dialog accepts wildcards, `*.fullyjustified.net` covers the three.

### 3. Environment variables

**Identical to the hub environment** — same five names, same values (the environments share the
account-side secrets; paste the same block). See the hub's `CLOUD.md` § "Environment variables" for
what each is and the no-secrets-store caveat:

```dotenv
ZOTERO_API_KEY=…        # read-only Zotero key
ZOTERO_USER_ID=…
LIBRARY_ROLE=reader
LIBRARY_CONFIG_JSON={"gdrive_root_folder_id":"…","gdrive_credentials":"/root/.config/library/gdrive-sa.json"}
GDRIVE_SA_JSON=…        # read-only service-account JSON, minified to one line
```

### 4. Setup script — leave it blank

Provisioning is the committed `SessionStart` hook; the dialog's Setup-script field runs **before
checkout** and would exit 127. (The hook also runs on local sessions but no-ops instantly unless
`CLAUDE_CODE_REMOTE=true`.)

---

## Smoke test — first session checklist

The hook runs most of this itself and reports; re-run by hand to accept the environment:

```bash
wiki config                                           # resolves the attached vault via $WIKI_VAULT
wiki gate --worklist                                  # the drafting gate reads across both repos
library config                                        # config.json + SA materialised from env
library resolve fagerstrom2007spatiotemporal --json   # pdf available, no G:\ (Drive fallback live)
tectonic --version                                    # pinned binary on PATH
tectonic paper/main.tex                               # paper compiles (first run fetches packages)
tectonic blueprint/src/print.tex                      # blueprint compiles
```

If all seven pass, the environment is live. Lean is deliberately absent from this list — see Scope.

---

## Manifest projection — one-time account setup

[`.github/workflows/manifest.yml`](.github/workflows/manifest.yml) regenerates
`blueprint-manifest.json` on every `main` push touching `blueprint/**`, `Formalization/**`, or the
generator, and commits it into the hub (`danielfagerstrom/notes-wiki`) — the theorem channel's
satellite-owned "check" projection, with a semantic diff-guard so stamp-only changes never produce a
commit. This CI is the *only* writer of that hub file (single-writer preserved). It needs one
account-side credential:

1. **Create a fine-grained PAT** (github.com → Settings → Developer settings → Personal access
   tokens → Fine-grained tokens): repository access **only `danielfagerstrom/notes-wiki`**,
   repository permission **Contents: Read and write**, nothing else. Set an expiry you will
   actually renew.
2. **Add it as an Actions secret on this repo** named **`NOTES_WIKI_TOKEN`**
   (scale-space-foundations → Settings → Secrets and variables → Actions → New repository secret).
3. **Seed the first projection:** run the workflow once by hand (Actions → *Manifest projection* →
   Run workflow) — the hub has no committed manifest until this runs.

The workflow fails with an explicit error (never silently skips) if the secret is missing. For the
security-conscious alternative: a write-enabled **deploy key** on notes-wiki (private half as an SSF
secret, SSH-based push) scopes even tighter than a fine-grained PAT and never expires silently.
