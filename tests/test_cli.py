"""The command line's contract: the exit codes CI binds to, and the reports it prints.

Three codes, and they mean different things: **0** every edge holds, **1** the article
has a linkage defect, **2** the tooling could not answer (bad config, no pinned pandoc
under `--require-render`). A CI step that collapsed 1 and 2 would report a broken
`linkage.toml` as a broken article.
"""

from __future__ import annotations

from conftest import run_cli
from fixtures.article import statement


def test_a_clean_article_exits_zero_and_says_so(article):
    article.blueprint(statement(label="thm:x"))
    rc, out, _ = run_cli("--root", str(article.root), "check")
    assert rc == 0
    assert "LINKAGE CHECK OK" in out


def test_a_fatal_finding_exits_one_and_is_printed(article):
    article.blueprint(statement(label="thm:x", status=None))
    rc, out, _ = run_cli("--root", str(article.root), "check")
    assert rc == 1
    assert "LINKAGE CHECK FAILED: 1 problem(s)" in out
    assert "FAIL [status] thm:x" in out


def test_an_advisory_alone_does_not_fail_the_check(article):
    article.blueprint(statement(label="thm:x", leanok=True))
    rc, out, _ = run_cli("--root", str(article.root), "check")
    assert rc == 0
    assert "advisory [lean]" in out


def test_a_root_with_no_config_exits_two_rather_than_traceback(article):
    """`--root` does no walking, so nothing else establishes that the file is there."""
    article.root.joinpath("linkage.toml").unlink()
    rc, _, err = run_cli("--root", str(article.root), "check")
    assert rc == 2
    assert err.startswith("CONFIG ERROR")
    assert "point --root at an article repo root" in err


def test_a_missing_shared_lake_package_exits_two(article):
    article.file("linkage.toml", article.root.joinpath("linkage.toml").read_text("utf-8")
                 + '\nlean_packages = ["shared"]\n')
    rc, _, err = run_cli("--root", str(article.root), "check")
    assert rc == 2
    assert "CONFIG ERROR" in err and "lake build" in err


def test_help_lists_every_subcommand():
    rc, out, _ = run_cli("--help")
    assert rc == 0
    for cmd in ("check", "manifest", "demand", "axioms", "packages", "prose", "init"):
        assert cmd in out


def test_packages_reports_url_rev_and_destination(article):
    import json

    article.file("linkage.toml", article.root.joinpath("linkage.toml").read_text("utf-8")
                 + '\nlean_packages = ["shared"]\n')
    article.file("Formalization/lake-manifest.json", json.dumps({"packages": [
        {"name": "shared", "url": "https://example.invalid/shared", "rev": "deadbeef"}]}))
    rc, out, _ = run_cli("--root", str(article.root), "packages", "--missing-only")
    assert rc == 0
    assert out.split("\t")[:3] == ["shared", "https://example.invalid/shared", "deadbeef"]


def test_packages_refuses_an_unresolved_package(article):
    import json

    article.file("linkage.toml", article.root.joinpath("linkage.toml").read_text("utf-8")
                 + '\nlean_packages = ["shared"]\n')
    article.file("Formalization/lake-manifest.json",
                 json.dumps({"packages": [{"name": "shared"}]}))
    rc, _, err = run_cli("--root", str(article.root), "packages")
    assert rc == 1
    assert "lake update shared" in err
