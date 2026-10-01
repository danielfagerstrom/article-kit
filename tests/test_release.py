"""The release commands: the gate a build must pass, and the export it then writes.

The gate tests mirror `spatial-hemigroup-scale-space`'s `scripts/tests/test_export_release.py`,
which this port replaces: rule 6 of `docs/RELEASE.md` — a release after a module's first names
that first release in the date line and closes with a version-history entry for the version
being exported; a first release is exempt from both.

The export tests are about the *parameterization*: every constant that was a module-specific
literal in that repository's script (chapters, paper directory, tag, roots, headline, records,
title, repository URL, the Lake libraries) must now come from `linkage.toml`'s `[[modules]]`.
They run the CLI end to end over a synthetic article, since that is where a mis-read parameter
would show.

The suite blocks `subprocess.run` (conftest), and both the gate and the export shell out to git;
the tests that need it restore the real one through the `real_run` fixture, over a tmp tree that
is either a real repository or no repository at all.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from conftest import run_cli
from linkage import config, release, zenodo
from linkage.prose import register


@pytest.fixture
def unblocked(monkeypatch, real_run):
    """The real `subprocess.run`, for the git the release gate reads tags with."""
    monkeypatch.setattr(subprocess, "run", real_run)
    return real_run


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def commit(root: Path, message: str, date_iso: str) -> None:
    """A commit dated `date_iso`, so a tag on it has a deterministic `git log` date."""
    stamp = f"{date_iso}T12:00:00"
    env = {**os.environ, "GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp}
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", message], cwd=root, check=True,
                   capture_output=True, text=True, env=env)


@pytest.fixture
def repo(tmp_path: Path, unblocked) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Test")
    (root / "CHANGELOG.md").write_text("# Changelog\n\n", encoding="utf-8")
    commit(root, "init", "2026-01-01")
    return root


def write_paper(root: Path, date_line: str, version_history: str | None = None,
                name: str = "paper") -> Path:
    paper = root / name
    paper.mkdir(exist_ok=True)
    vh = f"\n\\section*{{Version history}}\n{version_history}\n" if version_history else ""
    (paper / "main.tex").write_text(
        "\\documentclass{article}\n"
        f"\\date{{{date_line}}}\n"
        "\\begin{document}\n"
        "Body.\n"
        f"{vh}"
        "\\end{document}\n",
        encoding="utf-8")
    return paper


def faults_about(faults: list[str], *needles: str) -> list[str]:
    return [f for f in faults if any(n in f for n in needles)]


# ---- earlier_release_tag, first_release_line -------------------------------------------------

def test_earlier_release_tag_none_for_first_release(repo: Path) -> None:
    assert release.earlier_release_tag("v0.1", repo) is None


def test_earlier_release_tag_finds_lower_version_of_same_module(repo: Path) -> None:
    commit(repo, "cone-v0.1", "2026-09-20")
    git(repo, "tag", "cone-v0.1")
    commit(repo, "unrelated v9.9 of another module", "2026-09-21")
    git(repo, "tag", "v9.9")  # a *different* module's tag (no "cone-" prefix): must not match
    assert release.earlier_release_tag("cone-v0.2", repo) == "cone-v0.1"


def test_earlier_release_tag_reads_three_part_tags(repo: Path) -> None:
    """Paper I tags `v1.0.0`: a later `v1.1.0` must find it, or the rule 6 gate is skipped."""
    commit(repo, "v1.0.0", "2026-09-02")
    git(repo, "tag", "v1.0.0")
    assert release.earlier_release_tag("v1.1.0", repo) == "v1.0.0"
    assert release.earlier_release_tag("v1.1", repo) == "v1.0.0"
    assert release.earlier_release_tag("v1.0.0", repo) is None


def test_a_primed_declaration_is_found_and_not_confused_with_its_unprimed_twin() -> None:
    mods = {"Lib.A": "theorem foo' : True := trivial\n",
            "Lib.B": "theorem foo : True := trivial\n"}
    assert release.find_modules("Lib.foo'", mods) == ["Lib.A"]
    assert release.find_modules("Lib.foo", mods) == ["Lib.B"]


def test_first_release_line_reads_changelog_entry(repo: Path) -> None:
    (repo / "CHANGELOG.md").write_text(
        "# Changelog\n\n## cone-v0.1 — 2026-09-20 — first release of module B\n\ntext\n",
        encoding="utf-8")
    commit(repo, "cone-v0.1", "2026-09-20")
    git(repo, "tag", "cone-v0.1")
    assert release.first_release_line("cone-v0.1", repo) == ("v0.1", "September 20, 2026")


def test_first_release_line_falls_back_to_tag_date(repo: Path) -> None:
    # No changelog entry names cone-v0.1: the date must come from the tag's own commit date.
    commit(repo, "cone-v0.1", "2026-09-20")
    git(repo, "tag", "cone-v0.1")
    assert release.first_release_line("cone-v0.1", repo) == ("v0.1", "September 20, 2026")


# ---- the rule 6 gate: a first release is exempt ------------------------------------------------

def test_first_release_passes_without_first_release_naming_or_version_history(repo: Path) -> None:
    paper = write_paper(repo, "September 20, 2026 (v0.1)")
    faults = release.release_gate(paper, "v0.1", repo)
    assert not faults_about(faults, "first release", "Version history")


# ---- the rule 6 gate: a later release ----------------------------------------------------------

@pytest.fixture
def cone_first_release(repo: Path) -> Path:
    """cone-v0.1 exists as a changelog entry and a git tag; cone-v0.2 is being gated."""
    (repo / "CHANGELOG.md").write_text(
        "# Changelog\n\n## cone-v0.1 — 2026-09-20 — first release of module B\n\ntext\n",
        encoding="utf-8")
    commit(repo, "cone-v0.1", "2026-09-20")
    git(repo, "tag", "cone-v0.1")
    return repo


def test_later_version_fails_without_first_release_naming(cone_first_release: Path) -> None:
    root = cone_first_release
    paper = write_paper(root, "September 25, 2026 (v0.2)",
                        version_history="\\paragraph{v0.2 (2026-09-25).} Changes.")
    faults = release.release_gate(paper, "cone-v0.2", root)
    assert faults_about(faults, "first release's version")
    assert faults_about(faults, "first release's date")
    assert not faults_about(faults, "Version history")


def test_later_version_fails_without_version_history(cone_first_release: Path) -> None:
    root = cone_first_release
    paper = write_paper(
        root, "September 25, 2026 (v0.2), first released as v0.1, September 20, 2026")
    faults = release.release_gate(paper, "cone-v0.2", root)
    assert not faults_about(faults, "first release's version", "first release's date")
    assert faults_about(faults, "Version history")


def test_later_version_fails_when_version_history_has_no_entry_for_this_version(
        cone_first_release: Path) -> None:
    root = cone_first_release
    paper = write_paper(
        root, "September 25, 2026 (v0.2), first released as v0.1, September 20, 2026",
        version_history="\\paragraph{v0.1 (2026-09-20).} The first release.")
    assert faults_about(release.release_gate(paper, "cone-v0.2", root), "Version history")


def test_later_version_passes_with_both(cone_first_release: Path) -> None:
    root = cone_first_release
    paper = write_paper(
        root, "September 25, 2026 (v0.2), first released as v0.1, September 20, 2026",
        version_history="\\paragraph{v0.2 (2026-09-25).} Changes since v0.1.")
    faults = release.release_gate(paper, "cone-v0.2", root)
    assert not faults_about(faults, "first release", "Version history")


def test_commented_version_history_example_does_not_count(cone_first_release: Path) -> None:
    """The template's worked example is commented out; a real entry must be live text."""
    root = cone_first_release
    paper = write_paper(
        root, "September 25, 2026 (v0.2), first released as v0.1, September 20, 2026",
        version_history="% \\paragraph{v0.2 (2026-09-25).} Delete before filling in.")
    assert faults_about(release.release_gate(paper, "cone-v0.2", root), "Version history")


def test_draft_marked_date_skips_the_later_release_checks(cone_first_release: Path) -> None:
    """A still-draft date line is faulted on its own terms; the later-release checks would be
    noise on top of a date that has not been frozen at all yet."""
    root = cone_first_release
    paper = write_paper(root, "Working draft --- not yet released")
    faults = release.release_gate(paper, "cone-v0.2", root)
    assert faults_about(faults, "still reads")
    assert not faults_about(faults, "first release", "Version history")


def test_the_doi_must_be_printed_by_the_paper(cone_first_release: Path) -> None:
    root = cone_first_release
    paper = write_paper(root, "September 20, 2026 (v0.1)")
    assert faults_about(release.release_gate(paper, "v0.1", root, "10.5281/zenodo.1"),
                        "is not printed by")


# ---- the deposit sentence gate -----------------------------------------------------------------

DEPOSIT_SENTENCES = {"draft": "will be deposited as a verification export",
                     "release": "deposited with this version of the paper under the doi"}


def write_paper_with_body(root: Path, date_line: str, body: str, name: str = "paper") -> Path:
    paper = root / name
    paper.mkdir(exist_ok=True)
    (paper / "main.tex").write_text(
        "\\documentclass{article}\n"
        f"\\date{{{date_line}}}\n"
        "\\begin{document}\n"
        f"{body}\n"
        "\\end{document}\n",
        encoding="utf-8")
    return paper


def test_deposit_sentence_draft_phrase_faults_when_the_release_form_is_due(repo: Path) -> None:
    paper = write_paper_with_body(
        repo, "September 20, 2026 (v0.1)",
        "The export " + DEPOSIT_SENTENCES["draft"] + ", named on the first page.")
    faults = release.release_gate(paper, "v0.1", repo, deposit_sentences=DEPOSIT_SENTENCES)
    assert faults_about(faults, "draft deposit sentence")


def test_deposit_sentence_release_phrase_with_the_doi_is_clean(repo: Path) -> None:
    paper = write_paper_with_body(
        repo, "September 20, 2026 (v0.1)",
        "The verification export is " + DEPOSIT_SENTENCES["release"]
        + " 10.5281/zenodo.1 printed on the first page.")
    faults = release.release_gate(paper, "v0.1", repo, deposit_sentences=DEPOSIT_SENTENCES)
    assert not faults_about(faults, "deposit sentence")


def test_deposit_sentence_faults_when_neither_phrase_is_present(repo: Path) -> None:
    paper = write_paper_with_body(repo, "September 20, 2026 (v0.1)", "Nothing about a deposit.")
    faults = release.release_gate(paper, "v0.1", repo, deposit_sentences=DEPOSIT_SENTENCES)
    assert faults_about(faults, "release deposit sentence")


def test_a_module_without_deposit_sentences_is_unaffected(repo: Path) -> None:
    paper = write_paper_with_body(repo, "September 20, 2026 (v0.1)", "Nothing about a deposit.")
    assert not faults_about(release.release_gate(paper, "v0.1", repo), "deposit sentence")


# ---- the module table -------------------------------------------------------------------------

TOML = """\
slug = "test"

[paths]
blueprint = "blueprint/src/content.tex"
axioms    = "blueprint/AXIOMS.md"
macros    = "blueprint/src/macros.tex"
allowlist = "blueprint/render-allowlist.txt"
lean      = "Formalization"
paper     = ["paper", "paper-b"]
lean_packages = ["Shared"]

[release]
creators = [{ name = "Author, An", orcid = "0000-0000-0000-0000" }]
copyright = "2026 An Author"
keywords = []

[[modules]]
name     = "line"
chapters = ["02"]
paper    = "paper"
tag      = "v0.1"
roots    = ["Lib.Interfaces"]
headline = "Lib.main_theorem"
stem     = "an-article"
title    = "An article"
repo_url = "https://example.invalid/an-article"
records  = "records/line"
keywords = ["scale space"]
related  = ["10.5281/zenodo.1:continues"]

[[modules]]
name     = "cone"
chapters = ["03"]
paper    = "paper-b"
tag      = "cone-v0.1"
roots    = ["Lib.Interfaces"]
title    = "An article: module B"
repo_url = "https://example.invalid/an-article-cone"
records  = "records/cone"
"""


def build_article(root: Path) -> Path:
    """The smallest tree the export reads: two blueprint chapters, a Lean library with a
    tagged declaration and one it imports, two papers, a guard, a ledger, records."""
    (root / "blueprint" / "src" / "parts").mkdir(parents=True)
    (root / "linkage.toml").write_text(TOML, encoding="utf-8")
    (root / "blueprint" / "src" / "content.tex").write_text(
        "\\input{parts/02-first.tex}\n", encoding="utf-8")
    (root / "blueprint" / "src" / "macros.tex").write_text("", encoding="utf-8")
    (root / "blueprint" / "src" / "web.tex").write_text(
        "\\home{https://dev.invalid}\n\\github{https://dev.invalid/repo}\n"
        "\\dochome{https://dev.invalid/docs}\n", encoding="utf-8")
    (root / "blueprint" / "src" / "print.tex").write_text("", encoding="utf-8")
    (root / "blueprint" / "AXIOMS.md").write_text("# Ledger\n", encoding="utf-8")
    (root / "blueprint" / "render-allowlist.txt").write_text("emph\n", encoding="utf-8")
    (root / "blueprint" / "trust-boundary.txt").write_text("# names\nLib.iface\n",
                                                           encoding="utf-8")
    (root / "blueprint" / "src" / "parts" / "02-first.tex").write_text(
        "\\begin{theorem}\n  \\label{thm:main}\n  \\lean{Lib.main_theorem}\n  It holds.\n"
        "\\end{theorem}\n", encoding="utf-8")
    (root / "blueprint" / "src" / "parts" / "03-second.tex").write_text(
        "\\begin{theorem}\n  \\label{thm:later}\n  \\lean{Lib.later_theorem, Shared.elsewhere}\n"
        "  It also holds.\n\\end{theorem}\n", encoding="utf-8")
    form = root / "Formalization"
    (form / "Lib").mkdir(parents=True)
    (form / "Lib" / "Main.lean").write_text(
        "import Lib.Interfaces\ntheorem main_theorem : True := trivial\n", encoding="utf-8")
    (form / "Lib" / "Interfaces.lean").write_text("axiom iface : True\n", encoding="utf-8")
    (form / "Lib" / "Later.lean").write_text("theorem later_theorem : True := trivial\n",
                                             encoding="utf-8")
    (form / "Lib.lean").write_text(
        "import Lib.Main\nimport Lib.Interfaces\nimport Lib.Later\n", encoding="utf-8")
    (form / "lakefile.toml").write_text("name = \"lib\"\n", encoding="utf-8")
    (form / "lean-toolchain").write_text("leanprover/lean4:v4.21.0\n", encoding="utf-8")
    (form / "CIAxiomGuard.lean").write_text(
        "import Lib\n#print axioms Lib.main_theorem\n#print axioms Lib.later_theorem\n",
        encoding="utf-8")
    for name, title in (("paper", "An article"), ("paper-b", "Module B")):
        p = root / name
        p.mkdir()
        (p / "main.tex").write_text(
            "\\documentclass{article}\n\\date{Working draft --- not yet released}\n"
            "\\begin{document}\n\\begin{abstract}\nThe \\Matern{} kernel, in $L^2$.\n"
            "\\end{abstract}\n" + f"{title}.\n" + "\\end{document}\n", encoding="utf-8")
    (root / "records" / "line").mkdir(parents=True)
    (root / "records" / "line" / "PROCESS.md").write_text("# Process\n", encoding="utf-8")
    (root / "CHANGELOG.md").write_text(
        "# Changelog\n\n## v0.1 — 2026-09-20 — the first release\n\nwhat changed\n",
        encoding="utf-8")
    return root


@pytest.fixture
def article_repo(tmp_path: Path) -> Path:
    return build_article(tmp_path / "art")


def test_a_module_is_read_from_the_config(article_repo: Path) -> None:
    cfg = config.load(article_repo)
    mod = cfg.module("cone")
    assert (mod.chapters, mod.paper, mod.tag) == (("03",), "paper-b", "cone-v0.1")
    assert mod.process_file() == "records/cone/PROCESS.md"
    assert mod.reviews_dir() == "records/cone/reviews"


def test_naming_no_module_where_there_are_several_is_an_error(article_repo: Path) -> None:
    cfg = config.load(article_repo)
    with pytest.raises(config.ConfigError) as e:
        cfg.module()
    assert "--module" in str(e.value)


def test_a_cited_tag_resolves_to_the_module_that_carries_its_prefix(article_repo: Path) -> None:
    cfg = config.load(article_repo)
    assert cfg.module_of_tag("cone-v0.2").name == "cone"
    assert cfg.module_of_tag("v0.3").name == "line"


def test_a_releases_table_holds_a_tags_own_parameters(tmp_path: Path) -> None:
    root = build_article(tmp_path / "art")
    root.joinpath("linkage.toml").write_text(
        TOML + "\n[modules.releases.\"cone-v0.1\"]\nchapters = [\"02\"]\n", encoding="utf-8")
    mod = config.load(root).module("cone")
    assert mod.parameters_at("cone-v0.1") == (("02",), "paper-b", ("Lib.Interfaces",))
    assert mod.parameters_at("cone-v0.2") == (("03",), "paper-b", ("Lib.Interfaces",))


def test_deposit_sentences_is_read_from_the_module_table(tmp_path: Path) -> None:
    root = build_article(tmp_path / "art")
    root.joinpath("linkage.toml").write_text(
        TOML + "\n[modules.deposit_sentences]\ndraft = \"will be\"\nrelease = \"was\"\n",
        encoding="utf-8")
    cfg = config.load(root)
    assert cfg.module("cone").deposit_sentences == {"draft": "will be", "release": "was"}
    assert cfg.module("line").deposit_sentences == {}


def test_deposit_sentences_must_set_both_phrases(tmp_path: Path) -> None:
    root = build_article(tmp_path / "art")
    root.joinpath("linkage.toml").write_text(
        TOML + "\n[modules.deposit_sentences]\ndraft = \"will be\"\n", encoding="utf-8")
    with pytest.raises(config.ConfigError) as e:
        config.load(root)
    assert "deposit_sentences" in str(e.value)


# ---- the export ---------------------------------------------------------------------------------

def test_dry_run_reports_the_closure_and_writes_the_index(article_repo: Path, unblocked) -> None:
    rc, out, _ = run_cli("--root", str(article_repo), "release", "export",
                         "--module", "line", "--dry-run")
    assert rc == 0
    assert "chapters 02, paper paper:" in out
    # `Lib.Main` holds the tagged declaration; `Lib.Interfaces` is a root and an import.
    assert "closure 2 of 3 modules" in out
    index = (article_repo / "Formalization" / "INDEX.md").read_text(encoding="utf-8")
    assert "| `thm:main` | `Lib.main_theorem` | `Lib.Main` |" in index
    # A declaration of a shared package is not in this tree, and is not reported as lost.
    assert "Shared.elsewhere" in index


def test_a_build_that_is_not_a_release_is_refused_without_draft(article_repo: Path,
                                                                unblocked, tmp_path) -> None:
    rc, out, _ = run_cli("--root", str(article_repo), "release", "export",
                         "--module", "line", "--out", str(tmp_path / "export"))
    assert rc == 1
    assert "still reads" in out
    assert "nothing exported" in out
    assert not (tmp_path / "export").exists()


def test_the_export_is_written_from_the_module_table(article_repo: Path, unblocked,
                                                     tmp_path) -> None:
    out_dir = tmp_path / "export"
    rc, out, _ = run_cli("--root", str(article_repo), "release", "export",
                         "--module", "line", "--draft", "--out", str(out_dir))
    assert rc == 0
    assert (out_dir / "DRAFT").exists()                      # --draft, and the date is a draft
    # The module's chapters, and only those.
    assert (out_dir / "blueprint" / "src" / "parts" / "02-first.tex").exists()
    assert not (out_dir / "blueprint" / "src" / "parts" / "03-second.tex").exists()
    content = (out_dir / "blueprint" / "src" / "content.tex").read_text(encoding="utf-8")
    assert "\\setcounter{chapter}{1}" in content and "\\input{parts/02-first.tex}" in content
    # The module's repository URL, not the development's, in the generated web.tex.
    web = (out_dir / "blueprint" / "src" / "web.tex").read_text(encoding="utf-8")
    assert "https://example.invalid/an-article" in web and "dev.invalid" not in web
    # The closure, the library root restricted to it, and the guard.
    assert (out_dir / "Formalization" / "Lib" / "Main.lean").exists()
    assert not (out_dir / "Formalization" / "Lib" / "Later.lean").exists()
    root_lean = (out_dir / "Formalization" / "Lib.lean").read_text(encoding="utf-8")
    assert "import Lib.Main" in root_lean and "import Lib.Later" not in root_lean
    guard = (out_dir / "Formalization" / "CIAxiomGuard.lean").read_text(encoding="utf-8")
    assert "#print axioms Lib.main_theorem" in guard
    assert "#print axioms Lib.later_theorem" not in guard   # its module is not exported
    assert "2026 An Author" in guard
    # The records the module names, and the changelog entry for its tag.
    assert (out_dir / "notes" / "PROCESS.md").exists()
    assert "## v0.1" in (out_dir / "CHANGELOG.md").read_text(encoding="utf-8")
    assert (out_dir / "README.md").read_text(encoding="utf-8").startswith(
        "# An article — release v0.1")
    # `reserve` writes the state file at the export's root and `upload` a zip there; neither
    # belongs in the tagged tree or the public zip it makes (#31: both went in by hand once).
    gitignore = (out_dir / ".gitignore").read_text(encoding="utf-8")
    assert ".zenodo-deposition.json" in gitignore.splitlines()
    assert "*.zip" in gitignore.splitlines()


def test_the_deposit_metadata_comes_from_the_config(article_repo: Path, unblocked,
                                                    tmp_path) -> None:
    out_dir = tmp_path / "export"
    run_cli("--root", str(article_repo), "release", "export", "--module", "line", "--draft",
            "--out", str(out_dir))
    zen = json.loads((out_dir / ".zenodo.json").read_text(encoding="utf-8"))
    assert zen["title"] == "An article"
    assert zen["version"] == "0.1"
    assert zen["creators"] == [{"name": "Author, An", "orcid": "0000-0000-0000-0000"}]
    assert zen["keywords"] == ["scale space"]
    assert {"identifier": "10.5281/zenodo.1", "relation": "continues",
            "scheme": "doi"} in zen["related_identifiers"]
    assert {"identifier": "https://example.invalid/an-article", "relation": "isSupplementedBy",
            "scheme": "url"} in zen["related_identifiers"]
    cff = (out_dir / "CITATION.cff").read_text(encoding="utf-8")
    assert "family-names: Author" in cff and "given-names: An" in cff
    assert "repository-code: \"https://example.invalid/an-article\"" in cff


def test_a_module_specific_macro_is_expanded_in_the_abstract(article_repo: Path) -> None:
    cfg = config.load(article_repo)
    plain = release.plain_abstract(article_repo / "paper", {"Matern": "Matérn"})
    assert plain == "The Matérn kernel, in L^2."
    assert cfg.module("line").abstract_macros == {}     # not configured here: the macro drops
    assert release.plain_abstract(article_repo / "paper") == "The kernel, in L^2."


def test_the_export_needs_a_module_table(tmp_path: Path, unblocked) -> None:
    root = build_article(tmp_path / "art")
    root.joinpath("linkage.toml").write_text(
        root.joinpath("linkage.toml").read_text(encoding="utf-8").split("[[modules]]")[0],
        encoding="utf-8")
    rc, _, err = run_cli("--root", str(root), "release", "export", "--dry-run")
    assert rc == 2
    assert "no `[[modules]]` table" in err


# ---- the register counts -------------------------------------------------------------------

REGISTER_TEX = """\
Some prose --- with an em-dash; and a semicolon.

% shared with blueprint thm:main
\\begin{theorem}
  A shared statement --- not ours to edit; really.
\\end{theorem}

\\begin{proof}
  A proof --- of record; here.
\\end{proof}

More prose $a; b$ and \\cite{key; other}.
"""


def test_the_zones_are_counted_apart(tmp_path: Path) -> None:
    f = tmp_path / "01-intro.tex"
    f.write_text(REGISTER_TEX, encoding="utf-8")
    counts, _ = register.analyse(f)
    assert counts["prose"][:2] == (1, 1)         # math and cite keys are stripped first
    assert counts["statement"][:2] == (1, 1)
    assert counts["proof"][:2] == (1, 1)


def test_register_counts_the_modules_paper_by_default(article_repo: Path) -> None:
    (article_repo / "paper" / "01-intro.tex").write_text(REGISTER_TEX, encoding="utf-8")
    rc, out, _ = run_cli("--root", str(article_repo), "prose", "register", "--module", "line")
    assert rc == 0
    assert "01-intro.tex" in out and "main.tex" not in out    # main.tex is preamble, not prose
    assert "TOTAL" in out


def test_a_shared_namespace_is_not_looked_for_in_this_tree(article_repo: Path) -> None:
    """`ScaleSpaceCore` declares `ScaleSpace.*`: the package's name and its namespace need not
    agree, so a tag naming a shared declaration must not be resolved to a local module that
    happens to define the same short name."""
    mods = {"Lib.Later": "theorem elsewhere : True := trivial\n"}
    assert release.find_modules("Shared.elsewhere", mods, ("Lib",), ("Shared",)) == []
    assert release.find_modules("Lib.elsewhere", mods, ("Lib",), ("Shared",)) == ["Lib.Later"]
    # The default is the package list, and `paths.shared_namespaces` overrides it.
    assert config.load(article_repo).shared_namespaces == ("Shared",)


# ---- the Zenodo steps (no network: the state file and the gate) ---------------------------------

def test_a_step_without_a_reserved_draft_says_to_reserve_first(tmp_path: Path) -> None:
    rc, _, err = run_cli("release", "zenodo", "status", "--export", str(tmp_path))
    assert rc == 2
    assert "reserve" in err


def test_the_deposit_gate_refuses_a_draft_export(tmp_path: Path) -> None:
    (tmp_path / "DRAFT").write_text("not a release\n", encoding="utf-8")
    faults = zenodo.deposit_gate(tmp_path, {"doi": "10.5281/zenodo.1", "sandbox": False}, [])
    assert faults and "DRAFT file" in faults[0]


def test_the_deposit_gate_passes_an_export_with_no_pdf_to_read(tmp_path: Path) -> None:
    assert zenodo.deposit_gate(tmp_path, {"doi": "10.5281/zenodo.1", "sandbox": False}, []) == []


# ---- zenodo: the draft page and the default preview -------------------------------------------

def test_the_draft_page_is_the_uploads_page() -> None:
    assert zenodo.draft_page({"sandbox": True, "id": 7}) == "https://sandbox.zenodo.org/uploads/7"
    assert zenodo.draft_page({"sandbox": False, "id": 7}) == "https://zenodo.org/uploads/7"


def test_the_default_preview_writes_the_draft_back_whole(monkeypatch) -> None:
    """Only `files` changes: `pids` (the reserved DOI) and the metadata go back as read."""
    draft = {"id": "7", "links": {}, "access": {"record": "public"}, "metadata": {"title": "T"},
             "pids": {"doi": {"identifier": "10.5281/zenodo.7"}},
             "files": {"enabled": True, "entries": {}}}
    draft["metadata"] = {"title": "T", "creators": [{"person_or_org": {"name": "F, D"}}],
                         "resource_type": {"id": "publication-preprint"}}
    calls = []

    def fake(method, url, tok, data=None, **kw):
        calls.append((method, url, data, kw))
        return draft if method == "GET" else {}

    monkeypatch.setattr(zenodo, "call", fake)
    zenodo.set_default_preview({"sandbox": True, "id": 7}, "tok", "paper-v1.1.0.pdf")
    (m1, u1, _, k1), (m2, u2, body, k2) = calls
    assert (m1, m2) == ("GET", "PUT")
    # Plain JSON gets the legacy serialization, whose fields RDM drops on the way back in.
    assert k1["accept"] == zenodo.RDM
    # ...but the write is labelled plain JSON: the endpoint answers 415 to its own media type.
    assert k2.get("ctype", "application/json") == "application/json"
    assert u1 == u2 == "https://sandbox.zenodo.org/api/records/7/draft"
    assert body["files"] == {"enabled": True, "default_preview": "paper-v1.1.0.pdf"}
    assert body["pids"] == draft["pids"] and body["metadata"] == draft["metadata"]
    assert "links" not in body and "id" not in body


# ---- the export's lakefile and the source zip's name -------------------------------------------

def test_default_targets_keep_only_the_exported_libraries() -> None:
    """Paper I's export carries no skeleton module; a `Skeleton` default target failed its build."""
    lf = '# c\ndefaultTargets = ["Hemigroup", "Skeleton"]\n\n[[lean_lib]]\nname = "Skeleton"\n'
    out = release.trim_default_targets(lf, {"Hemigroup"})
    assert 'defaultTargets = ["Hemigroup"]' in out
    assert '[[lean_lib]]\nname = "Skeleton"' in out           # the table stays
    both = release.trim_default_targets(lf, {"Hemigroup", "Skeleton"})
    assert 'defaultTargets = ["Hemigroup", "Skeleton"]' in both


def test_the_source_zip_is_named_after_the_pdf(tmp_path: Path) -> None:
    export = tmp_path / "paper-export"
    pdf = export / "hemigroup-kernels-v1.1.0.pdf"
    assert zenodo.zip_stem(pdf, "v1.1.0", export) == "hemigroup-kernels-v1.1.0"
    assert zenodo.zip_stem(export / "main.pdf", "v1.1.0", export) == "paper-export-v1.1.0"


def test_a_draft_read_without_creators_is_not_written_back(monkeypatch) -> None:
    """Paper I's v1.1.0 draft lost its DOI, type, creators and keywords to a write-back of a
    legacy-format read; a draft that reads without them must be refused, not written."""
    legacy = {"metadata": {"title": "T", "creators": [{"name": "F, D"}],
                           "upload_type": "publication"}, "doi": "10.5281/zenodo.7"}
    puts = []

    def fake(method, url, tok, data=None, **kw):
        if method == "PUT":
            puts.append(data)
        return legacy

    monkeypatch.setattr(zenodo, "call", fake)
    with pytest.raises(zenodo.ZenodoError, match="not writing it back"):
        zenodo.set_default_preview({"sandbox": False, "id": 7}, "tok", "p.pdf")
    assert puts == []


def test_metadata_restores_a_pids_doi_the_legacy_put_left_empty(monkeypatch) -> None:
    """#28's `metadata` step set `prereserve_doi` (legacy) but not `pids.doi` (records API), so
    `preview`'s guard still refused a draft the legacy write hadn't reached."""
    calls = []

    def fake(method, url, tok, data=None, **kw):
        calls.append((method, url, kw))
        if method == "GET":
            return {"pids": {}}
        return {"pids": {"doi": {"identifier": "10.5281/zenodo.7"}}}

    monkeypatch.setattr(zenodo, "call", fake)
    zenodo.restore_doi(Path("."), {"sandbox": True, "id": 7, "doi": "10.5281/zenodo.7"}, "tok")
    (m1, u1, k1), (m2, u2, k2) = calls
    assert (m1, u1) == ("GET", "https://sandbox.zenodo.org/api/records/7/draft")
    assert k1["accept"] == zenodo.RDM
    assert (m2, u2) == ("POST", "https://sandbox.zenodo.org/api/records/7/draft/pids/doi")


def test_metadata_leaves_a_present_pids_doi_alone(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(zenodo, "call", lambda method, *a, **kw: calls.append(method) or
                        {"pids": {"doi": {"identifier": "10.5281/zenodo.7"}}})
    zenodo.restore_doi(Path("."), {"sandbox": True, "id": 7, "doi": "10.5281/zenodo.7"}, "tok")
    assert calls == ["GET"]


def test_metadata_refuses_a_restored_doi_that_differs_from_the_state(monkeypatch) -> None:
    """The PDF already prints the reserved DOI; a different one from the API is not written."""
    def fake(method, url, tok, data=None, **kw):
        if method == "GET":
            return {"pids": {}}
        return {"pids": {"doi": {"identifier": "10.5281/zenodo.99"}}}

    monkeypatch.setattr(zenodo, "call", fake)
    with pytest.raises(zenodo.ZenodoError, match="not writing further"):
        zenodo.restore_doi(Path("."), {"sandbox": True, "id": 7, "doi": "10.5281/zenodo.7"}, "tok")


def test_metadata_refuses_a_present_doi_that_differs_from_the_state(monkeypatch) -> None:
    monkeypatch.setattr(zenodo, "call", lambda method, *a, **kw:
                        {"pids": {"doi": {"identifier": "10.5281/zenodo.99"}}})
    with pytest.raises(zenodo.ZenodoError, match="not writing further"):
        zenodo.restore_doi(Path("."), {"sandbox": True, "id": 7, "doi": "10.5281/zenodo.7"}, "tok")


def test_publish_refuses_a_draft_missing_what_a_deposit_carries() -> None:
    ok = {"metadata": {"title": "T", "creators": [{"name": "F, D"}], "upload_type": "publication",
                       "prereserve_doi": {"doi": "10.5281/zenodo.7"}}}
    assert zenodo.metadata_missing(ok, "10.5281/zenodo.7") == []
    emptied = {"metadata": {"title": "T"}}
    assert zenodo.metadata_missing(emptied, "10.5281/zenodo.7") == [
        "creators", "resource type", "reserved DOI 10.5281/zenodo.7"]
