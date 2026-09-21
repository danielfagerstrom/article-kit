"""The pin check: a consumer that calls an article-kit workflow at a branch fails it."""

from __future__ import annotations

from conftest import run_cli
from linkage import pins

WF = "danielfagerstrom/article-kit/.github/workflows"


def _caller(ref: str, linkage_ref: str | None = None, wf: str = "manifest.yml") -> str:
    given = f"      linkage_ref: {linkage_ref}\n" if linkage_ref else ""
    return (
        "name: Blueprint\n"
        "on: [push]\n"
        "jobs:\n"
        "  manifest:\n"
        f"    uses: {WF}/{wf}@{ref}\n"
        "    with:\n"
        "      slug: demo\n"
        f"{given}"
        "    secrets: inherit\n"
    )


def _write(root, name, text):
    d = root / ".github" / "workflows"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text, encoding="utf-8")


def test_a_call_at_main_fails():
    found = pins.check_text(_caller("main", "v0.1.0"), "w.yml")
    assert len(found) == 1
    assert "manifest.yml@main is not a release" in found[0]


def test_a_call_at_a_release_passes():
    assert pins.check_text(_caller("v0.1.0", "v0.1.0"), "w.yml") == []


def test_a_full_commit_sha_passes():
    sha = "a" * 40
    assert pins.check_text(_caller(sha, sha), "w.yml") == []


def test_a_short_sha_or_a_branch_is_not_a_release():
    assert pins.check_text(_caller("abc1234", "v0.1.0"), "w.yml")
    assert pins.check_text(_caller("v0.1", "v0.1.0"), "w.yml")


def test_linkage_ref_left_at_its_default_fails():
    found = pins.check_text(_caller("v0.1.0"), "w.yml")
    assert len(found) == 1
    assert "without `linkage_ref`" in found[0]


def test_linkage_ref_main_fails():
    found = pins.check_text(_caller("v0.1.0", "main"), "w.yml")
    assert len(found) == 1
    assert "linkage_ref 'main'" in found[0]


def test_docs_yml_takes_no_linkage_ref():
    assert pins.check_text(_caller("v0.1.0", wf="docs.yml"), "w.yml") == []


def test_other_actions_and_local_calls_are_ignored():
    text = ("jobs:\n  a:\n    steps:\n      - uses: actions/checkout@main\n"
            "  b:\n    uses: ./.github/workflows/local.yml@main\n")
    assert pins.check_text(text, "w.yml") == []


def test_linkage_ref_of_a_neighbouring_job_is_not_borrowed():
    text = (
        "jobs:\n"
        "  a:\n"
        f"    uses: {WF}/manifest.yml@v0.1.0\n"
        "    with:\n"
        "      slug: demo\n"
        "  b:\n"
        f"    uses: {WF}/lean.yml@v0.1.0\n"
        "    with:\n"
        "      linkage_ref: v0.1.0\n"
    )
    found = pins.check_text(text, "w.yml")
    assert len(found) == 1 and "w.yml:3:" in found[0]


def test_the_command_exits_one_on_a_main_fixture_and_zero_on_a_release_fixture(tmp_path):
    bad, good = tmp_path / "bad", tmp_path / "good"
    _write(bad, "blueprint.yml", _caller("main", "main"))
    _write(good, "blueprint.yml", _caller("v0.1.0", "v0.1.0"))

    rc, out, _ = run_cli("--root", str(bad), "pins")
    assert rc == 1
    assert "PIN CHECK FAILED: 2 call(s)" in out
    assert ".github/workflows/blueprint.yml:5" in out

    rc, out, _ = run_cli("--root", str(good), "pins")
    assert rc == 0
    assert "PIN CHECK OK" in out


def test_a_repository_without_workflows_passes(tmp_path):
    rc, _, _ = run_cli("--root", str(tmp_path), "pins")
    assert rc == 0
