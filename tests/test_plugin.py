"""The Claude Code plugin and its marketplace ([`docs/PLUGIN.md`](../docs/PLUGIN.md)).

Three things can rot silently here, and none of them is caught by anything else in the suite:

1. a **component path** in `plugin.json`. The manifest points at `.claude/skills/…` and
   `.claude/agents/…` rather than holding copies (one source of truth, hub ADR-0008), so a
   renamed or deleted skill leaves the manifest naming a path that is not there — and a plugin
   with a missing component is only discovered by a session that wanted it;
2. the **version**, which appears in three files (`pyproject.toml`, `plugin.json`,
   `marketplace.json`). Detectable divergence is what ADR-0008 asks of a copy that cannot be
   generated;
3. the **scaffolded `settings.json`**, which is what makes an article see the plugin at all, and
   which also carries the two `SessionStart` hooks (Q-0121). It is JSON an article inherits
   verbatim; a trailing comma or a dropped hook would reach every new repository.

These read this checkout, not a scaffolded article, so `conftest`'s "never read a real article
repo" rule is untouched: the files under test are the framework's own.
"""

from __future__ import annotations

import json
import tomllib

import pytest

from conftest import REPO
from linkage import scaffold

PLUGIN_DIR = REPO / ".claude-plugin"
MARKETPLACE = "article-kit"
PLUGIN = "article-kit"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def manifest():
    return load(PLUGIN_DIR / "plugin.json")


@pytest.fixture
def marketplace():
    return load(PLUGIN_DIR / "marketplace.json")


@pytest.fixture
def settings():
    return load(scaffold.scaffold_dir() / "claude" / "settings.json")


def test_the_plugin_manifest_names_the_plugin(manifest):
    assert manifest["name"] == PLUGIN
    assert manifest["description"].strip()
    assert manifest["version"]


def test_every_component_the_manifest_declares_exists(manifest):
    declared = [*manifest["skills"], *manifest["agents"]]
    assert declared, "the plugin ships nothing"
    for rel in declared:
        assert rel.startswith("./"), f"{rel} is not a plugin-relative path"
        target = REPO / rel[2:]
        assert target.exists(), f"{rel} is declared but absent"
    for rel in manifest["skills"]:
        assert (REPO / rel[2:] / "SKILL.md").is_file(), f"{rel} has no SKILL.md"
    for rel in manifest["agents"]:
        assert rel.endswith(".md"), rel


def test_the_shared_skills_and_agent_are_the_ones_shipped(manifest):
    """The set is documented in PLUGIN.md and PROCESS.md; adding to it is a documented act.

    In particular the hub-owned agents (`draft-reviewer`, `archivist`) and the librarian's
    must NOT appear here — they stay owned by their repositories and arrive through the hub's
    sync table, not as a copy in this one.
    """
    skills = {rel.rsplit("/", 1)[-1] for rel in manifest["skills"]}
    agents = {rel.rsplit("/", 1)[-1].removesuffix(".md") for rel in manifest["agents"]}
    assert skills == {"fidelity-review", "tighten"}
    assert agents == {"mathematician"}


def test_the_marketplace_offers_this_plugin(marketplace):
    assert marketplace["name"] == MARKETPLACE
    assert marketplace["owner"]["name"].strip()
    entries = {p["name"]: p for p in marketplace["plugins"]}
    assert set(entries) == {PLUGIN}
    assert entries[PLUGIN]["source"] == "./"


def test_the_versions_do_not_drift(manifest, marketplace):
    pkg = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    version = pkg["project"]["version"]
    assert manifest["version"] == version
    assert marketplace["metadata"]["version"] == version
    assert marketplace["plugins"][0]["version"] == version


# --- what a scaffolded article declares -------------------------------------------------


def test_the_scaffolded_settings_declare_the_marketplace(settings):
    source = settings["extraKnownMarketplaces"][MARKETPLACE]["source"]
    assert source == {"source": "github", "repo": "danielfagerstrom/article-kit"}


def test_the_scaffolded_settings_enable_the_plugin(settings):
    assert settings["enabledPlugins"] == {f"{PLUGIN}@{MARKETPLACE}": True}


def test_the_scaffolded_settings_still_run_both_session_start_hooks(settings):
    (entry,) = settings["hooks"]["SessionStart"]
    commands = [h["command"] for h in entry["hooks"]]
    assert any("cloud-setup.sh" in c for c in commands)
    assert any("sync-agents-hook.sh" in c for c in commands)


def test_a_scaffolded_article_gets_the_declaration(tmp_path):
    """End to end: `linkage init` is what puts it in the article, and it is seeded, not owned."""
    root = tmp_path / "new-article"
    root.mkdir()
    scaffold.init(root, slug="fresh")
    written = load(root / ".claude" / "settings.json")
    assert written["enabledPlugins"] == {f"{PLUGIN}@{MARKETPLACE}": True}
    assert ".claude/settings.json" in scaffold.SEEDED.values()
