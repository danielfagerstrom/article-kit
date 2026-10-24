"""The three standards an article session must keep in force, rendered as plugin skills (hub
Q-0544, from the engineer office's E-0018).

Claude Code re-attaches an invoked skill's body after a compaction (its first 5,000 tokens), where a
file the session merely read is summarised away and, over 5,000 tokens, returns as a path only
(code.claude.com/docs/en/context-window, "What survives compaction"; code.claude.com/docs/en/skills).
So the rules that govern hours of drafting, a release and the drafting gate are shipped as skills:

- `write`: `docs/WRITING.md` §§ 0–4, the restraint budget (§ 2, "the rules the drafts break")
  first, since truncation keeps the start;
- `release`: `docs/RELEASE.md`'s rules and checklist; the commands, which would take the body over
  the cap, stay in the document and are read at the step;
- `gate`: `docs/DRAFTING-GATE.md` whole, run with `context: fork` so it never enters the drafting
  context and returns only the box verdicts.

**One source.** `docs/` stays the text of record, readable at its paths by the draft-reviewer and
the hub. Each skill's body is that text verbatim, rendered here; `tests/test_skills.py` fails when a
`SKILL.md` differs from what this module renders. After editing one of the documents, run
`uv run python -m linkage.skills` from a checkout of this repository.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
SKILLS = REPO / ".claude" / "skills"
TOKEN_CAP = 5000   # what Claude Code re-attaches of an invoked skill after a compaction

_H2_RE = re.compile(r"(?m)^(?=## )")

LINKS = ("Relative links below are to `${CLAUDE_PLUGIN_ROOT}/docs/` (in article-kit itself, "
         "`docs/`). Generated from the document by `linkage.skills`; edit the document, not "
         "this file.")


def sections(doc: str) -> dict[str, str]:
    """A document's `## ` sections by heading line (without the `## `), each with its text."""
    text = (DOCS / doc).read_text(encoding="utf-8")
    out = {}
    for part in _H2_RE.split(text):
        if part.startswith("## "):
            out[part.splitlines()[0][3:].strip()] = part.rstrip("\n") + "\n"
    return out


def _pick(doc: str, *prefixes: str) -> str:
    found = sections(doc)
    out = []
    for prefix in prefixes:
        match = [s for h, s in found.items() if h.startswith(prefix)]
        if len(match) != 1:
            raise KeyError(f"{doc}: expected one section starting {prefix!r}, found {len(match)}")
        out.append(match[0])
    return "\n".join(out)


def _frontmatter(**fields: str) -> str:
    lines = ["---"]
    for k, v in fields.items():
        if "\n" in v or len(v) > 80:
            lines.append(f"{k}: >")
            lines.extend("  " + ln for ln in _wrap(v))
        else:
            lines.append(f"{k}: {v}")
    return "\n".join(lines + ["---", ""])


def _wrap(text: str, width: int = 96) -> list[str]:
    out, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            out.append(line)
            line = word
        else:
            line = f"{line} {word}" if line else word
    return out + [line] if line else out


def _para(text: str) -> str:
    return "\n".join(_wrap(text, 100)) + "\n\n"


def render_write() -> str:
    head = _frontmatter(
        name="write",
        description=(
            "The article writing standard's drafting rules, WRITING.md §§ 0–4: the restraint "
            "budget (the rules the drafts break), the reader's floor, the neutral voice, the "
            "technical register and the structural mechanisms. Invoke before drafting or revising "
            "any article prose (a paper or draft section, a blueprint proof, a chapter note), and "
            "again after a compaction."))
    body = (
        "# The writing standard: the drafting rules\n\n" + _para(
        "`docs/WRITING.md` §§ 0–4, verbatim, the restraint budget first. On demand, at the step "
        "that needs them: § 5 (the process: draft, flag blind, fix at the anchor) and § 6 (the "
        "AI statement) in `${CLAUDE_PLUGIN_ROOT}/docs/WRITING.md`; the section contracts and the "
        "exposition rubric, § B and § C of `${CLAUDE_PLUGIN_ROOT}/docs/PUBLICATION-TEMPLATE.md`, "
        "for the section being written; its § D for the calibration exemplars. " + LINKS))
    return head + "\n" + body + _pick("WRITING.md", "2.", "0.", "1.", "3.", "4.")


def render_release() -> str:
    head = _frontmatter(
        name="release",
        description=(
            "The release discipline for an article module, RELEASE.md: the rules and the "
            "checklist (a DOI reserved first, the first page checked, the export, the site). "
            "Invoke before any release step and again after a compaction; the release itself "
            "is the author's."))
    body = (
        "# Releasing a module: the rules and the checklist\n\n" + _para(
        "`docs/RELEASE.md` § \"The rules\" and § \"The checklist\", verbatim. The commands, in "
        "their order, are § \"The commands\" of `${CLAUDE_PLUGIN_ROOT}/docs/RELEASE.md`: read it "
        "at the step that runs them. " + LINKS))
    return head + "\n" + body + _pick("RELEASE.md", "The rules", "The checklist")


def render_gate() -> str:
    head = _frontmatter(
        name="gate",
        description=(
            "Run the section readiness gate, DRAFTING-GATE.md, on one section of this article "
            "in a separate subagent, and return each box's verdict with its evidence. Invoke "
            "with the section, before the section is drafted."),
        context="fork",
        background="false",
        **{"argument-hint": '"<section, e.g. §5>"'})
    task = (
        "# Run the section readiness gate\n\n" + _para(
        "**Your task.** Run the gate below on section **$ARGUMENTS** of the article repository in "
        "the current working directory. For each box, give its verdict (met, not met, or a "
        "judgement for the author) and the evidence: the command and the line of its output, or "
        "the file and line. Then give the answer \"The rule\" asks for. Read and run checks only; "
        "edit no file. You do not see the conversation that invoked you: everything you need is "
        "here, in the repository and in the hub (`$WIKI_VAULT`). " + LINKS))
    text = (DOCS / "DRAFTING-GATE.md").read_text(encoding="utf-8").rstrip("\n") + "\n"
    return head + "\n" + task + "---\n\n" + text


RENDER = {"write": render_write, "release": render_release, "gate": render_gate}


def tokens(text: str) -> int:
    return len(text) // 4


def main(argv: list[str] | None = None) -> int:
    for name, render in RENDER.items():
        text = render()
        if tokens(text) > TOKEN_CAP:
            print(f"{name}: ~{tokens(text)} tokens, over the {TOKEN_CAP} re-attached after a "
                  "compaction", file=sys.stderr)
            return 1
        path = SKILLS / name / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        old = path.read_text(encoding="utf-8") if path.exists() else None
        if old != text:
            path.write_text(text, encoding="utf-8", newline="\n")
            print(f"wrote {path.relative_to(REPO).as_posix()} (~{tokens(text)} tokens)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
