"""`linkage.toml` — what an article may configure, and what it may not.

The line is deliberate (see the module docstring of `linkage/config.py`): paths, slug,
environments, label shapes and the pandoc pin are per-article; the framework's macro
names are not configurable at all.
"""

from __future__ import annotations

import pytest

from linkage import config


def test_the_root_is_found_by_walking_up(article):
    deep = article.root / "blueprint" / "src"
    assert config.find_root(deep) == article.root


def test_no_config_anywhere_is_a_config_error(tmp_path):
    with pytest.raises(config.ConfigError, match="no linkage.toml found"):
        config.find_root(tmp_path)


def test_the_slug_is_required(article):
    article.file("linkage.toml", '[paths]\nblueprint = "blueprint/src/content.tex"\n')
    with pytest.raises(config.ConfigError, match="`slug` is required"):
        config.load(article.root)


def test_every_missing_path_is_reported_at_once(article):
    article.root.joinpath("blueprint/AXIOMS.md").unlink()
    article.root.joinpath("blueprint/render-allowlist.txt").unlink()
    with pytest.raises(config.ConfigError) as e:
        config.load(article.root)
    assert "axioms = blueprint/AXIOMS.md" in str(e.value)
    assert "allowlist = blueprint/render-allowlist.txt" in str(e.value)


def test_the_defaults_are_the_frameworks(article):
    cfg = article.cfg
    assert cfg.slug == "test"
    assert cfg.statement_envs == config.DEFAULT_STATEMENT_ENVS
    assert cfg.statement_kinds == config.DEFAULT_STATEMENT_KINDS
    assert cfg.ledger_key == config.DEFAULT_LEDGER_KEY
    assert cfg.pandoc_pin == config.DEFAULT_PANDOC_PIN
    assert cfg.lean_packages == ()


def test_an_article_may_override_the_blueprint_shapes(article):
    article.file("linkage.toml", """
slug = "other"

[blueprint]
statement_envs = ["theorem", "claim"]
statement_label_prefixes = ["thm", "claim"]
statement_kinds = ["thm"]
ledger_key = "L-[a-z]+"

[render]
pandoc_pin = "3.9"
pandoc_target = "gfm"
""")
    cfg = config.load(article.root)
    assert cfg.statement_envs == ("theorem", "claim")
    assert cfg.ledger_key == "L-[a-z]+"
    assert cfg.pandoc_pin == "3.9" and cfg.pandoc_target == "gfm"


def test_is_statement_label_keys_on_the_configured_prefixes(article):
    cfg = article.cfg
    assert cfg.is_statement_label("thm:x")
    assert cfg.is_statement_label("def:x")
    assert not cfg.is_statement_label("eq:x")
    assert not cfg.is_statement_label("sec:thm:x")


def test_paths_are_resolved_against_the_article_root(article):
    cfg = article.cfg
    assert cfg.blueprint == article.root / "blueprint/src/content.tex"
    assert cfg.lean == article.root / "Formalization"
    assert cfg.missing() == []
