"""The reusable docs workflow: one job (GitHub bills each job to a whole minute), and a
`workflow_call` interface that no caller's `with:` has to follow a change of."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

from fixtures.shell import find_bash

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
        if (line.strip() and not line.startswith(" " * indent)
                and (not line.lstrip().startswith("#") or not line.startswith(" "))):
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


# --- a paper of several TeX roots (a paper with a supplement) -----------------------------

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "supplement"

# On Windows (CI runs there on push to `main`) this is Git's bash, not WSL's launcher; every script handed to it
# is written with LF endings and every path in POSIX form (`C:/…`), which Git's bash reads.
BASH = find_bash()
JQ = shutil.which("jq")

needs_shell = pytest.mark.skipif(JQ is None or BASH is None,
                                 reason="needs bash and jq, as the runner has")


def _script(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def _helper(tmp_path: Path) -> Path:
    """The build helper the workflow writes to $RUNNER_TEMP/papers.sh, as a file."""
    m = re.search(r"""cat > "\$RUNNER_TEMP/papers.sh" <<'EOF'\n(.*?)\n\s*EOF\n""",
                  DOCS.read_text(encoding="utf-8"), re.S)
    assert m, "docs.yml no longer writes $RUNNER_TEMP/papers.sh"
    return _script(tmp_path / "papers.sh", textwrap.dedent(m.group(1)) + "\n")


def _jq_shim(tmp_path: Path) -> Path:
    """A `jq` that drops the CR a native Windows jq.exe writes before each LF, as the
    runner's jq does not write one."""
    shimdir = tmp_path / "jq-shim"
    shimdir.mkdir(exist_ok=True)   # _run makes it once per step, and a test may run several
    tool = _script(shimdir / "jq", f'#!/usr/bin/env bash\nset -o pipefail\n'
                                   f'"{Path(JQ).as_posix()}" "$@" | tr -d \'\\r\'\n')
    tool.chmod(0o755)
    return shimdir


def _run(run, tmp_path: Path, script: str, paper_tex: str, extra: str = "[]",
         bindir: Path | None = None, **env: str) -> subprocess.CompletedProcess[str]:
    """Source the helper and run `script` in tmp_path, as a step of the workflow would."""
    env = {**os.environ, "PAPER_TEX": paper_tex, "EXTRA_PAPERS": extra, **env}
    dirs = [bindir] if bindir is not None else []
    if os.name == "nt":
        dirs.append(_jq_shim(tmp_path))
    if dirs:
        env["PATH"] = os.pathsep.join([*map(str, dirs), env["PATH"]])
    return run(
        [BASH, "-c", f'set -eo pipefail; . "{_helper(tmp_path).as_posix()}"; {script}'],
        cwd=tmp_path, env=env, capture_output=True, text=True, check=False)


def _step(tmp_path: Path, name: str) -> Path:
    """The `run:` script of the step `name`, as a file, its `${{ }}` expressions blanked."""
    m = re.search(rf"\n      - name: {re.escape(name)}\n(?:        .*\n)*?        run: \|\n"
                  r"((?:          .*\n|\s*\n)+)", DOCS.read_text(encoding="utf-8"))
    assert m, f"docs.yml has no step {name!r}"
    return _script(tmp_path / "step.sh", re.sub(r"\$\{\{.*?\}\}", "X", textwrap.dedent(m.group(1))))


def _bin(tmp_path: Path, body: str) -> Path:
    """A directory holding a `tectonic` script with `body`, to put first on PATH."""
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    tool = _script(bindir / "tectonic", "#!/usr/bin/env bash\n" + body)
    tool.chmod(0o755)
    return bindir


# Logs its arguments and the .aux files beside its input, and writes the PDF (and, with
# --keep-intermediates, the .aux) as Tectonic does.
FAKE = r"""tex="${@: -1}"; base="${tex%.tex}"
seen=$(cd "$(dirname "$tex")" && ls -- *.aux 2>/dev/null | tr '\n' ' ')
echo "$* | aux: $seen" >> "$CALLS"
printf '%%PDF-1.5 %s\n' "$tex" > "$base.pdf"
[ "$1" != "--keep-intermediates" ] || : > "$base.aux"
"""


def _sources(tmp_path: Path, *names: str) -> None:
    (tmp_path / "paper").mkdir()
    for name in names:
        (tmp_path / "paper" / name).write_text("x", encoding="utf-8")


@needs_shell
def test_roots_name_each_pdf(tmp_path, real_run):
    extra = json.dumps([
        {"name": "cone", "tex": "paper-b/main.tex", "title": "B"},
        {"name": "iso", "tex": ["paper-iso/main.tex", "paper-iso/supplement.tex"], "title": "I"},
    ])
    out = _run(real_run, tmp_path, "roots; echo ---; further_roots; echo ---; first_root iso",
               "paper/main.tex paper/supplement.tex", extra)
    assert out.returncode == 0, out.stderr
    every, further, first = out.stdout.split("---\n")
    assert first == "paper-iso/main.tex\n"
    assert every.splitlines() == [
        "paper\tpaper.pdf\tpaper/main.tex",
        "paper\tpaper.supplement.pdf\tpaper/supplement.tex",
        "cone\tcone.pdf\tpaper-b/main.tex",
        "iso\tiso.pdf\tpaper-iso/main.tex",
        "iso\tiso.supplement.pdf\tpaper-iso/supplement.tex",
    ]
    assert further.splitlines() == [
        "paper\tpaper.supplement.pdf\tpaper/supplement.tex",
        "iso\tiso.supplement.pdf\tpaper-iso/supplement.tex",
    ]


@needs_shell
def test_one_root_builds_as_it_always_did(tmp_path, real_run):
    _sources(tmp_path, "main.tex")
    calls = tmp_path / "calls"
    out = _run(real_run, tmp_path, "build_paper paper paper-pdf", "paper/main.tex",
               bindir=_bin(tmp_path, FAKE), CALLS=calls.as_posix())
    assert out.returncode == 0, out.stderr
    assert calls.read_text(encoding="utf-8").splitlines() == ["paper/main.tex | aux: "]
    assert sorted(p.name for p in (tmp_path / "paper-pdf").iterdir()) == ["paper.pdf"]


@needs_shell
def test_two_roots_build_twice_in_order_and_publish_both(tmp_path, real_run):
    _sources(tmp_path, "main.tex", "supplement.tex")
    calls = tmp_path / "calls"
    out = _run(real_run, tmp_path, "build_paper paper paper-pdf", "paper/main.tex paper/supplement.tex",
               bindir=_bin(tmp_path, FAKE), CALLS=calls.as_posix())
    assert out.returncode == 0, out.stderr
    # the second pass of each root finds the other's .aux
    assert calls.read_text(encoding="utf-8").splitlines() == [
        "--keep-intermediates paper/main.tex | aux: ",
        "--keep-intermediates paper/supplement.tex | aux: main.aux ",
        "--keep-intermediates paper/main.tex | aux: main.aux supplement.aux ",
        "--keep-intermediates paper/supplement.tex | aux: main.aux supplement.aux ",
    ]
    built = tmp_path / "paper-pdf"
    assert sorted(p.name for p in built.iterdir()) == ["paper.pdf", "paper.supplement.pdf"]
    assert "paper/supplement.tex" in (built / "paper.supplement.pdf").read_text(encoding="utf-8")


@needs_shell
def test_a_failed_root_fails_the_build(tmp_path, real_run):
    _sources(tmp_path, "main.tex", "supplement.tex")
    out = _run(real_run, tmp_path, "build_paper paper paper-pdf", "paper/main.tex paper/supplement.tex",
               bindir=_bin(tmp_path, '[ "${@: -1}" != paper/supplement.tex ] || exit 1\n' + FAKE),
               CALLS=(tmp_path / "calls").as_posix())
    assert out.returncode != 0
    assert not (tmp_path / "paper-pdf").exists()


@needs_shell
def test_two_roots_of_one_stem_are_refused(tmp_path, real_run):
    out = _run(real_run, tmp_path, "build_paper paper paper-pdf", "a/main.tex a/x.tex b/x.tex",
               bindir=_bin(tmp_path, FAKE), CALLS=(tmp_path / "calls").as_posix())
    assert out.returncode != 0
    assert "paper.x.pdf" in out.stdout
    assert not (tmp_path / "calls").exists()


@needs_shell
@pytest.mark.skipif(shutil.which("tectonic") is None,
                    reason="Tectonic is not installed; a caller's docs run is the check")
def test_two_cross_referencing_roots_resolve_with_tectonic(tmp_path, real_run):
    """The fixture built by the helper with the real Tectonic: the first build of main.tex
    cannot resolve its reference into the supplement, and the last build of each root resolves
    every reference. A wrapper keeps each run's log, which the helper does not."""
    shutil.copytree(FIXTURE, tmp_path / "paper")
    wrapper = (f'tex="${{@: -1}}"\n"{Path(shutil.which("tectonic")).as_posix()}" --keep-logs "$@" || exit $?\n'
               'n=$(ls "$LOGS" | wc -l)\n'
               'cp "${tex%.tex}.log" "$LOGS/$n-$(basename "${tex%.tex}").log"\n')
    logs = tmp_path / "logs"
    logs.mkdir()
    out = _run(real_run, tmp_path, "build_paper paper paper-pdf", "paper/main.tex paper/supplement.tex",
               bindir=_bin(tmp_path, wrapper), LOGS=logs.as_posix())
    assert out.returncode == 0, out.stdout + out.stderr
    runs = sorted(logs.iterdir())
    assert [p.name for p in runs] == ["0-main.log", "1-supplement.log", "2-main.log",
                                      "3-supplement.log"]
    undefined = re.compile(r"Reference `[^']+' on page \d+\s+undefined")
    assert undefined.search(runs[0].read_text(encoding="utf-8", errors="replace"))
    for log in runs[2:]:
        assert not undefined.search(log.read_text(encoding="utf-8", errors="replace")), log.name
    for name in ("paper.pdf", "paper.supplement.pdf"):
        assert (tmp_path / "paper-pdf" / name).read_bytes().startswith(b"%PDF-")


@needs_shell
def test_the_site_lists_and_validates_every_root(tmp_path, real_run):
    """Assemble dist/ and validate it, the two steps run as the workflow runs them, for a
    paper and an extra paper that each have a supplement; then lose one supplement."""
    for name in ("paper-pdf/paper.pdf", "paper-pdf/paper.supplement.pdf", "blueprint.pdf",
                 "extra-papers/iso.pdf", "extra-papers/iso.supplement.pdf"):
        (tmp_path / name).parent.mkdir(exist_ok=True)
        (tmp_path / name).write_text("%PDF-1.5\n", encoding="utf-8")
    extra = json.dumps([{"name": "iso", "tex": ["paper-iso/main.tex", "paper-iso/supplement.tex"],
                         "title": "The isotropic paper"}])
    github = {"RUNNER_TEMP": tmp_path.as_posix(), "BUILD_WEB": "false", "CHANNEL_INPUT": "",
              "GITHUB_REF": "refs/heads/main", "GITHUB_REF_NAME": "main",
              "GITHUB_SHA": "abc1234", "GITHUB_REPOSITORY": "o/r"}

    def step(name: str) -> subprocess.CompletedProcess[str]:
        return _run(real_run, tmp_path, f'"$BASH" -eo pipefail "{_step(tmp_path, name).as_posix()}"',
                    "paper/main.tex paper/supplement.tex", extra, **github)

    out = step("Assemble dist/ (PDFs + web blueprint + index.html)")
    assert out.returncode == 0, out.stdout + out.stderr
    index = (tmp_path / "dist" / "index.html").read_text(encoding="utf-8")
    for pdf in ("paper.pdf", "paper.supplement.pdf", "iso.pdf", "iso.supplement.pdf"):
        assert f'href="{pdf}"' in index
    assert "<code>paper/main.tex</code>" in index and "<code>paper-iso/main.tex</code>" in index
    out = step("Validate dist/")
    assert out.returncode == 0, out.stdout + out.stderr
    (tmp_path / "dist" / "iso.supplement.pdf").unlink()
    out = step("Validate dist/")
    assert out.returncode != 0
    assert "dist/iso.supplement.pdf is missing" in out.stdout
