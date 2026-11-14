"""The reusable Lean workflow: its `workflow_call` interface, and the build-log filter that
shows a consuming package's own warnings and hides its dependencies' (`own_warnings_only`).

The filter is a Python script the workflow writes from a heredoc, so these tests take it out of
`lean.yml` itself: what is tested is what runs. The log below is an excerpt of a real one,
spatial-hemigroup-pyramids' run 43583992727 (645 warnings, 250 of them from the pinned
`AffineHemigroup` and `ScaleSpaceCore`), with a failing tail added."""

from __future__ import annotations

import io
import os
import re
import sys
import textwrap
from pathlib import Path

import pytest

from fixtures.shell import find_bash

LEAN = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "lean.yml"
BASH = find_bash()
needs_bash = pytest.mark.skipif(BASH is None, reason="needs bash, as the runner has")

INPUTS = {
    "lean_dir", "build_args", "sorry_guard_dir", "axiom_guard_file", "own_warnings_only",
    "boundary_strict_shadows", "build_jobs", "free_disk", "linkage_ref", "private_dep_owner",
}

HEAD = """\
info: some setup line Lake prints before any job
⚠ [3183/3227] Replayed ScaleSpaceCore.LaplaceLaw
warning: ScaleSpaceCore/LaplaceLaw.lean:133:2: The `show` tactic should only be used to indicate intermediate goal states for readability.
However, this tactic invocation changed the goal. Please use `change` instead for these purposes.

Note: This linter can be disabled with `set_option linter.style.show false`
⚠ [3198/3227] Replayed AffineHemigroup.Polar
warning: AffineHemigroup/Polar.lean:16:100: This line exceeds the 100 character limit, please shorten it!

Note: This linter can be disabled with `set_option linter.style.longLine false`
warning: AffineHemigroup/Polar.lean:59:100: This line exceeds the 100 character limit, please shorten it!

Note: This linter can be disabled with `set_option linter.style.longLine false`
⚠ [3199/3227] Replayed ScaleSpaceCore.Cin
warning: ScaleSpaceCore/Cin.lean:419:4: `simp` is a flexible tactic modifying `⊢`.

Note: This linter can be disabled with `set_option linter.flexible false`
info: ScaleSpaceCore/Cin.lean:419:4: Try this:
  [apply] simp only [mul_zero, Real.cos_zero, sub_self, div_zero]
⚠ [3201/3227] Replayed Mathlib.Foo
warning: ././.lake/packages/mathlib/Mathlib/Foo.lean:1:0: a warning Lake names by its checkout path
⚠ [3210/3227] Replayed Pyramids.RecursionHelmholtz
warning: Pyramids/RecursionHelmholtz.lean:520:100: This line exceeds the 100 character limit, please shorten it!

Note: This linter can be disabled with `set_option linter.style.longLine false`
⚠ [3220/3227] Built PyramidsSkeleton.Ch07Jet (2.1s)
warning: PyramidsSkeleton/Ch07Jet.lean:103:8: declaration uses `sorry`
warning: PyramidsSkeleton/Ch07Jet.lean:110:8: declaration uses `sorry`
✔ [3226/3227] Built PyramidsSkeleton (1.9s)
"""
OK_TAIL = "Build completed successfully (3227 jobs).\n"
FAIL = """\
✖ [3222/3227] Building AffineHemigroup.Broken (0.4s)
error: AffineHemigroup/Broken.lean:7:2: unknown identifier 'x'
error: Lean exited with code 1
✖ [3223/3227] Building Pyramids.Broken (0.4s)
warning: Pyramids/Broken.lean:3:0: an own warning in a failing module
error: Pyramids/Broken.lean:9:4: type mismatch
Some required targets logged failures:
- AffineHemigroup.Broken
- Pyramids.Broken
error: build failed
"""
OWN_FILES = ["Pyramids/RecursionHelmholtz.lean", "PyramidsSkeleton/Ch07Jet.lean",
             "Pyramids/Broken.lean"]


def _filter_source() -> str:
    m = re.search(r"""cat > "\$RUNNER_TEMP/lake_log.py" <<'LAKE_LOG_PY'\n(.*?)\n\s*LAKE_LOG_PY\n""",
                  LEAN.read_text(encoding="utf-8"), re.S)
    assert m, "lean.yml no longer writes $RUNNER_TEMP/lake_log.py"
    return textwrap.dedent(m.group(1)) + "\n"


def _module() -> dict:
    ns = {"__name__": "lake_log"}
    exec(compile(_filter_source(), "lake_log.py", "exec"), ns)
    return ns


def _package(tmp_path: Path) -> Path:
    """The consuming package: its own files, and a dependency checkout under `.lake/`."""
    root = tmp_path / "Formalization"
    for rel in OWN_FILES:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("-- own\n", encoding="utf-8")
    dep = root / ".lake" / "packages" / "affine" / "AffineHemigroup"
    dep.mkdir(parents=True)
    (dep / "Polar.lean").write_text("-- a dependency\n", encoding="utf-8")
    return root


def _filter(tmp_path: Path, log: str, annotate: str | None = "Formalization", limit: int = 10):
    ns = _module()
    out = io.StringIO()
    f = ns["Filter"](str(_package(tmp_path)), annotate, out)
    for line in log.splitlines():
        f.feed(line)
    f.finish()
    f.report("lake-build-log")
    f.annotations_out(limit)
    summary = tmp_path / "summary.md"
    f.summary(str(summary), "lake-build-log")
    return out.getvalue(), summary.read_text(encoding="utf-8")


# --- the interface -----------------------------------------------------------------------

def _keys_under(header: str, indent: int) -> list[str]:
    keys, inside = [], False
    for line in LEAN.read_text(encoding="utf-8").splitlines():
        if not inside:
            inside = line.rstrip() == header
            continue
        if line.strip() and not line.startswith(" " * indent) and not line.lstrip().startswith("#"):
            break
        m = re.fullmatch(" " * indent + r"([A-Za-z0-9_]+):\s*", line)
        if m:
            keys.append(m.group(1))
    return keys


def test_the_interface_adds_own_warnings_only_and_keeps_the_rest():
    assert set(_keys_under("    inputs:", 6)) == INPUTS
    text = LEAN.read_text(encoding="utf-8")
    block = text[text.index("      own_warnings_only:"):text.index("      boundary_strict_shadows:")]
    assert "default: true" in block and "type: boolean" in block


def test_lean_action_builds_only_when_the_filter_is_off():
    text = LEAN.read_text(encoding="utf-8")
    assert "build: ${{ inputs.own_warnings_only && 'false' || 'default' }}" in text
    for step in ("Write the Lake log filter", "Build the Lean library (this package's warnings only)"):
        assert re.search(rf"- name: {re.escape(step)}\n\s+if: inputs.own_warnings_only\n", text)
    assert re.search(r"- name: Keep the unfiltered build log\n\s+if: always\(\) && inputs.own_warnings_only\n", text)


# --- the filter ----------------------------------------------------------------------------

def test_a_dependency_s_warnings_are_hidden_and_counted(tmp_path):
    out, summary = _filter(tmp_path, HEAD + OK_TAIL)
    assert "AffineHemigroup/Polar.lean" not in out
    assert "ScaleSpaceCore/" not in out
    assert "Mathlib/Foo.lean" not in out
    assert "Try this" not in out  # a dependency's infos go with its block
    assert ("5 dependency warnings hidden (ScaleSpaceCore 2, AffineHemigroup 2, mathlib 1), "
            "and 1 dependency infos; the full log is the job artifact `lake-build-log`.") in out
    assert "| `AffineHemigroup` | 2 |" in summary


def test_the_package_s_own_warnings_pass_through_unchanged_and_in_order(tmp_path):
    out, _ = _filter(tmp_path, HEAD + OK_TAIL)
    lines = out.splitlines()
    assert lines[0] == "info: some setup line Lake prints before any job"
    own = HEAD[HEAD.index("⚠ [3210/3227]"):]
    assert out.startswith(lines[0] + "\n" + own + OK_TAIL)
    assert "3 warnings in this package's own files." in out


def test_the_summary_counts_the_own_warnings_by_kind(tmp_path):
    _, summary = _filter(tmp_path, HEAD + OK_TAIL)
    assert "**3** in this package's own files (2 files); **5** from dependencies hidden" in summary
    assert "| `sorry` | 2 |" in summary
    assert "| `linter.style.longLine` | 1 |" in summary
    assert "The unfiltered build log is the job artifact `lake-build-log`." in summary


def test_annotations_are_capped_and_a_sorry_comes_last(tmp_path):
    out, summary = _filter(tmp_path, HEAD + OK_TAIL, limit=2)
    notes = [ln for ln in out.splitlines() if ln.startswith("::")]
    assert notes == [
        "::warning file=Formalization/Pyramids/RecursionHelmholtz.lean,line=520,col=101,"
        "title=Lean linter.style.longLine::This line exceeds the 100 character limit, please shorten it!",
        "::warning file=Formalization/PyramidsSkeleton/Ch07Jet.lean,line=103,col=9,"
        "title=Lean sorry::declaration uses `sorry`",
    ]
    assert "Annotated on the pull request: 2 of the 3" in summary


def test_no_annotations_without_a_prefix(tmp_path):
    out, _ = _filter(tmp_path, HEAD + OK_TAIL, annotate=None)
    assert "::warning" not in out


def test_every_error_is_shown_in_full_a_dependency_s_too(tmp_path):
    out, summary = _filter(tmp_path, HEAD + FAIL)
    assert FAIL in out  # both failing blocks and Lake's tail, verbatim
    assert "::error file=Formalization/Pyramids/Broken.lean,line=9,col=5,title=Lean error::type mismatch" in out
    assert "**1** errors in this package's own files" in summary
    assert "4 warnings in this package's own files." in out  # the failing module's warning counts


def test_a_block_naming_no_file_is_shown(tmp_path):
    log = "⚠ [1/2] Ran something\nwarning: a message with no file\n" + OK_TAIL
    out, _ = _filter(tmp_path, log)
    assert out.startswith(log)


def test_a_file_under_lake_is_never_the_package_s_own(tmp_path):
    ns = _module()
    root = _package(tmp_path)
    assert ns["is_own"]("Pyramids/Broken.lean", str(root))
    assert not ns["is_own"](".lake/packages/affine/AffineHemigroup/Polar.lean", str(root))
    assert not ns["is_own"]("AffineHemigroup/Polar.lean", str(root))
    assert ns["is_own"](str(root / "Pyramids" / "Broken.lean"), str(root))


# --- the two steps, as the runner runs them ------------------------------------------------

def _step(name: str) -> str:
    """The `run:` script of the step `name`, its `${{ }}` expressions blanked."""
    m = re.search(rf"\n      - name: {re.escape(name)}\n(?:        .*\n)*?        run: \|\n"
                  r"((?:          .*\n|\s*\n)+)", LEAN.read_text(encoding="utf-8"))
    assert m, f"lean.yml has no step {name!r}"
    return re.sub(r"\$\{\{.*?\}\}", "X", textwrap.dedent(m.group(1)))


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8", newline="\n")
    path.chmod(0o755)
    return path


def _build(tmp_path: Path, real_run, log: str, status: int):
    """Run the two steps with a fake `lake` that prints `log` and exits `status`."""
    root = _package(tmp_path)
    temp = tmp_path / "runner-temp"
    temp.mkdir()
    bindir = tmp_path / "bin"
    bindir.mkdir()
    _write(tmp_path / "lake.log", log)
    _write(bindir / "lake", f'#!/usr/bin/env bash\ncat "{(tmp_path / "lake.log").as_posix()}"\n'
                            f"exit {status}\n")
    # the runner's `python3`; on Windows the name may be the Store's stub, so point it here
    _write(bindir / "python3", f'#!/usr/bin/env bash\nexec "{Path(sys.executable).as_posix()}" "$@"\n')
    summary = tmp_path / "summary.md"
    env = {**os.environ, "RUNNER_TEMP": temp.as_posix(), "GITHUB_STEP_SUMMARY": summary.as_posix(),
           "LEAN_DIR": "Formalization", "BUILD_ARGS": "",
           "PATH": os.pathsep.join([str(bindir), os.environ["PATH"]])}
    for name in ("Write the Lake log filter", "Build the Lean library (this package's warnings only)"):
        script = _write(tmp_path / "step.sh", _step(name))
        # the runner's `bash -e {0}`
        out = real_run([BASH, "--noprofile", "--norc", "-eo", "pipefail", script.as_posix()],
                       cwd=root, env=env, capture_output=True, encoding="utf-8", check=False)
        if out.returncode:
            break
    return out, (temp / "lake-build.log").read_text(encoding="utf-8"), summary


@needs_bash
def test_a_green_build_stays_green_and_keeps_the_whole_log(tmp_path, real_run):
    out, full, summary = _build(tmp_path, real_run, HEAD + OK_TAIL, 0)
    assert out.returncode == 0, out.stderr
    assert "AffineHemigroup/Polar.lean" not in out.stdout
    assert "Pyramids/RecursionHelmholtz.lean:520:100" in out.stdout
    assert full == HEAD + OK_TAIL
    assert "### Lean build: warnings" in summary.read_text(encoding="utf-8")


@needs_bash
def test_a_failed_build_fails_the_step_with_lake_s_status(tmp_path, real_run):
    out, full, _ = _build(tmp_path, real_run, HEAD + FAIL, 3)
    assert out.returncode == 3
    assert "::error::lake build failed (exit 3)" in out.stdout
    assert "error: AffineHemigroup/Broken.lean:7:2" in out.stdout
    assert full == HEAD + FAIL
