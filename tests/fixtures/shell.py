"""The bash a test that runs a shell script spawns."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def find_bash() -> str | None:
    """A bash that reads `C:/…` paths. On Windows the `bash` on PATH may be WSL's launcher
    (`System32\\bash.exe`), which fails without a distribution, so look for Git's: under
    Program Files, or beside the `git` on PATH (`<Git>/cmd/git.exe` → `<Git>/bin/bash.exe`)."""
    if os.name != "nt":
        return shutil.which("bash")
    candidates = [Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "Git" / "bin" / "bash.exe"]
    git = shutil.which("git")
    if git:
        candidates += [Path(git).resolve().parent.parent / "bin" / "bash.exe"]
    for bash in candidates:
        if bash.is_file():
            return str(bash)
    return None
