"""The reusable docs workflow: one job (GitHub bills each job to a whole minute), and a
`workflow_call` interface that no caller's `with:` has to follow a change of."""

from __future__ import annotations

import re
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "docs.yml"

INPUTS = {
    "slug", "bucket", "source_ref", "channel", "dry_run", "push_artifacts", "build_blueprint",
    "paper_tex", "blueprint_tex", "extra_papers", "build_web", "blueprint_web_dir",
    "blueprint_web_out", "plastex_requirements", "tectonic_version",
}
SECRETS = {"R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "CLOUDFLARE_ACCOUNT_ID"}


def _keys_under(header: str, indent: int) -> list[str]:
    """Keys at `indent` spaces inside the block opened by the line `header` (no YAML parser)."""
    keys, inside = [], False
    for line in DOCS.read_text(encoding="utf-8").splitlines():
        if not inside:
            inside = line.rstrip() == header
            continue
        if line.strip() and not line.startswith(" " * indent):
            if not line.lstrip().startswith("#") or not line.startswith(" "):
                break
        m = re.fullmatch(" " * indent + r"([A-Za-z0-9_]+):\s*", line)
        if m:
            keys.append(m.group(1))
    return keys


def test_the_docs_run_is_one_job():
    assert _keys_under("jobs:", 2) == ["docs"]


def test_the_interface_is_unchanged():
    assert set(_keys_under("    inputs:", 6)) == INPUTS
    assert set(_keys_under("    secrets:", 6)) == SECRETS


def test_a_failed_build_still_fails_the_run_and_blocks_the_deploy():
    text = DOCS.read_text(encoding="utf-8")
    # the PDF builds continue on error so the others still run, and the closing step fails
    assert text.count("continue-on-error: true") == 4  # paper, extra, blueprint, artifacts push
    assert "Fail the run if a build or the artifacts push failed" in text
    deploy = re.search(r"id: deploy\n\s+if: (.*)", text)
    assert deploy
    for need in ("success()", "steps.paper.outcome == 'success'",
                 "steps.blueprint.outcome == 'success'", "steps.extra.outcome != 'failure'"):
        assert need in deploy.group(1)
