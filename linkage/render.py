"""The transclusion renderer — normalized blueprint source to Obsidian-dialect markdown.

The manifest carries, per label, a markdown rendering of the normalized statement/proof
source, produced by a version-PINNED pandoc so the output is deterministic (`wiki lint`
byte-compares transcluded blocks against it; a version drift would move every rendered_sha
at once). Macro expansion is pandoc's own `latex_macros` extension, fed the article's
macros file as a preamble — macros expand inside math too, so the output contains no
unexpanded custom commands. `\\ref{X}` is pre-passed to \\texttt{X} (a code span — the way
wiki notes write labels). Rendering degrades gracefully: no pandoc, or a version other than
the pin, emits the manifest without rendered fields and warns; `--require-render` (CI) turns
that, or any per-label render failure, into a hard error.
"""
from __future__ import annotations

import re
import subprocess


class RenderUnavailable(RuntimeError):
    """pandoc is absent, or present at a version other than the pin."""


def pandoc_version() -> str | None:
    try:
        r = subprocess.run(["pandoc", "--version"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=30)
        m = re.match(r"pandoc(?:\.exe)?\s+(\S+)", r.stdout) if r.returncode == 0 else None
        return m.group(1) if m else None
    except (OSError, subprocess.SubprocessError):
        return None


def unknown_commands(src: str, known: set[str]) -> list[str]:
    """Commands in normalized statement/proof source the pipeline cannot render (gate 4)."""
    return sorted(set(re.findall(r"\\([A-Za-z]+)", src)) - known)


# math ($$…$$ then $…$) and code spans — regions where backslash commands are legitimate
_MATH_OR_CODE = re.compile(r"\$\$.*?\$\$|\$[^$\n]*?\$|`[^`\n]*`", re.S)


def render_residue(md: str) -> list[str]:
    """Raw LaTeX commands surviving outside math/code spans — the clean-render gate (T2).

    The preamble expands every custom macro and pandoc converts every standard construct,
    so a `\\command` in rendered prose means a node uses something the pipeline does not
    handle — it must fail CI (via --require-render) rather than reach the hub, where the
    transcluded block would show literal LaTeX to a reader."""
    return sorted(set(re.findall(r"\\[A-Za-z]+", _MATH_OR_CODE.sub(" ", md))))


def render_markdown(src: str, preamble: str, target: str) -> str:
    """Normalized statement/proof LaTeX -> markdown with $/$$ math (Obsidian dialect)."""
    src = re.sub(r"\\ref\{([^}]+)\}", r"\\texttt{\1}", src)
    r = subprocess.run(
        ["pandoc", "-f", "latex", "-t", target, "--wrap=none"],
        input=preamble + "\n" + src + "\n",
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or f"pandoc exit {r.returncode}")
    return r.stdout.replace("\r\n", "\n").strip()


def check_pin(pin: str) -> str | None:
    """None when the pinned pandoc is available; otherwise why it is not."""
    ver = pandoc_version()
    if ver == pin:
        return None
    return f"pandoc {ver} found but pin is {pin}" if ver else "pandoc not found on PATH"
