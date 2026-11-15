"""The `[article]` table: declared parts, the phase, anonymity, and what they oblige (ADR-0002)."""

from __future__ import annotations

import json
import shutil

import pytest

from conftest import run_cli
from fixtures.article import statement
from linkage import article, config

PAPER = r"""\documentclass{article}
\newtheorem{theorem}{Theorem}
\begin{document}
\begin{theorem}\label{thm:main}A statement.\end{theorem}
\end{document}
"""


def _repo(tmp_path, toml: str, dirs=("paper",), paper: str = PAPER):
    root = tmp_path / "repo"
    root.mkdir()
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)
    if "paper" in dirs:
        (root / "paper" / "main.tex").write_text(paper, encoding="utf-8", newline="\n")
    if "draft" in dirs:
        (root / "draft" / "x.md").write_text("# Draft\n", encoding="utf-8")
    (root / "linkage.toml").write_text(toml, encoding="utf-8")
    return root


PAPER_ONLY = """slug = "ppr"

[article]
parts = ["paper"]
phase = "passes"
anonymous = true
cites = ["hcs@v1.0.0"]

[paths]
paper = "paper"
"""


def _check(root):
    return run_cli("--root", str(root), "check")


# --- the table -------------------------------------------------------------------------


def test_a_paper_only_declaration_reads_and_projects(tmp_path):
    cfg = config.load(_repo(tmp_path, PAPER_ONLY))
    assert cfg.article.declared and cfg.article.parts == {"paper"}
    assert cfg.absent == {"draft", "blueprint", "lean"}
    doc = article.projection(cfg)
    assert doc["phase"] == "passes" and doc["anonymous"] and doc["cites"] == ["hcs@v1.0.0"]
    assert doc["parts"] == ["paper"] and doc["present"] == ["paper"]
    assert doc["jobs"] == {"docs": True, "deploy": False, "blueprint_manifest": False,
                           "lean": False}


def test_parts_json_is_the_projection(tmp_path):
    root = _repo(tmp_path, PAPER_ONLY)
    rc, out, _ = run_cli("--root", str(root), "parts", "--json")
    assert rc == 0
    assert json.loads(out) == article.projection(config.load(root))


@pytest.mark.parametrize("toml, match", [
    ('slug = "x"\n[article]\nparts = ["paper"]\nphase = "article"\n'
     '[paths]\nlean = "Formalization"\n', "does not list lean"),
    ('slug = "x"\n[article]\nparts = ["paper"]\nphase = "writing"\n', "`phase` is one of"),
    ('slug = "x"\n[article]\nparts = ["paper", "slides"]\nphase = "article"\n',
     "non-empty list"),
    ('slug = "x"\n[article]\nparts = ["paper"]\nphase = "article"\nanonymous = true\n'
     'site = "s"\n', "anonymous and names a site"),
    ('slug = "x"\n[article]\nparts = ["paper"]\nphase = "article"\ncites = ["hcs"]\n',
     "<slug>@<tag>"),
    ('slug = "x"\n[article]\nparts = ["paper"]\nphase = "article"\ncolour = 1\n',
     "no key"),
    ('slug = "x"\n[article]\nparts = ["paper"]\nphase = "article"\n'
     '[[modules]]\nname = "m"\nphase = "passes"\n', "given both in"),
])
def test_a_malformed_declaration_is_a_config_error(tmp_path, toml, match):
    with pytest.raises(config.ConfigError, match=match):
        config.load(_repo(tmp_path, toml))


def test_a_listed_part_not_yet_written_is_not_missing(article):
    """The blueprint phase, Lean listed: no Formalization/ yet, and `paths.lean` written."""
    shutil.rmtree(article.root / "Formalization")
    article.file("linkage.toml", article.root.joinpath("linkage.toml").read_text()
                 + '\n[article]\nparts = ["blueprint", "lean", "paper"]\n'
                   'phase = "blueprint"\n')
    cfg = config.load(article.root)
    assert not cfg.has("lean") and cfg.listed("lean")
    assert article_problems(cfg) == []


def article_problems(cfg):
    return article.problems(cfg).fatal


def test_modules_carry_the_phase_and_the_most_advanced_one_decides(tmp_path):
    toml = ('slug = "x"\n[article]\nparts = ["blueprint", "lean", "paper"]\n\n'
            '[[modules]]\nname = "a"\nphase = "released"\ntag = "v0.1"\nsite = "s-a"\n\n'
            '[[modules]]\nname = "b"\nphase = "proving"\n')
    cfg = config.load(_repo(tmp_path, toml), validate=False)
    assert cfg.phase() == "released"
    assert cfg.required() == {"blueprint", "lean", "paper"}
    assert article.projection(cfg)["sites"] == ["s-a"]


# --- what `linkage check` obliges ------------------------------------------------------


def test_check_passes_a_declared_paper_only_repository(tmp_path):
    rc, out, err = _check(_repo(tmp_path, PAPER_ONLY))
    assert rc == 0, out + err
    assert "Article: phase passes; parts paper; never draft, blueprint, lean; anonymous." in out
    assert "[article]" not in out


def test_a_part_the_phase_requires_is_fatal_when_missing(tmp_path):
    toml = 'slug = "x"\n[article]\nparts = ["draft", "paper"]\nphase = "article"\n'
    rc, out, _ = _check(_repo(tmp_path, toml, dirs=("draft",)))
    assert rc == 1
    assert "[phase]  phase `article` (PROCESS.md § 7) requires the paper part" in out


def test_a_directory_of_an_unlisted_part_is_fatal(tmp_path):
    root = _repo(tmp_path, PAPER_ONLY.replace("anonymous = true\n", ""),
                 dirs=("paper", "blueprint"))
    rc, out, _ = _check(root)
    assert rc == 1
    assert "[parts]  blueprint/ exists, but `[article] parts` does not list blueprint" in out


def test_released_needs_a_tagged_module(tmp_path):
    toml = 'slug = "x"\n[article]\nparts = ["paper"]\nphase = "released"\n'
    rc, out, _ = _check(_repo(tmp_path, toml))
    assert rc == 1 and "no `[[modules]]` table carries a release `tag`" in out


def test_an_undeclared_repository_is_advised_to_declare(article):
    article.blueprint(statement(label="thm:x"))
    rc, out, _ = _check(article.root)
    assert rc == 0
    assert "advisory [article]" in out


# --- anonymity --------------------------------------------------------------------------

ANON = PAPER_ONLY + '\n[release]\ncreators = [{ name = "Ångström, Anders" }]\n'


@pytest.mark.parametrize("line, flagged", [
    ("As shown by Angstrom, the kernel is causal.", True),       # accent-folded name
    ("As shown by Ångström, the kernel is causal.", True),
    (r"As shown in \cite{angstrom2005axioms}, it holds.", False),  # a citekey never renders
    ("See github.com/someone/repo.", True),
    ("Write to a@b.org.", True),
    (r"\author{Anders \AA ngstr\"om} % anonymity-ok", False),     # the exempt marker
    ("In our previous paper we used this.", True),
    ("A projsite.example.net link.", True),                        # `identity`
])
def test_the_anonymity_scan(tmp_path, line, flagged):
    toml = ANON.replace('cites = ["hcs@v1.0.0"]', 'identity = ["projsite"]')
    root = _repo(tmp_path, toml, paper=PAPER.replace("A statement.", line))
    rc, out, _ = _check(root)
    assert ("[anonymity]" in out) is flagged, out
    assert rc == (1 if flagged else 0)


def test_the_bibliography_may_name_the_author(tmp_path):
    root = _repo(tmp_path, ANON)
    (root / "paper" / "refs.bib").write_text(
        "@article{x, author = {Ångström, Anders}}\n", encoding="utf-8")
    rc, out, _ = _check(root)
    assert rc == 0 and "[anonymity]" not in out


def test_a_repository_that_is_not_anonymous_is_not_scanned(tmp_path):
    root = _repo(tmp_path, ANON.replace("anonymous = true", "anonymous = false"),
                 paper=PAPER.replace("A statement.", "By Angstrom."))
    rc, out, _ = _check(root)
    assert rc == 0 and "[anonymity]" not in out


# --- `linkage phase` --------------------------------------------------------------------


def _declared(article, phase, parts='["draft", "blueprint", "lean", "paper"]'):
    article.file("draft/a.md", "# Draft\n")
    article.blueprint(statement(label="thm:x"))
    article.file("linkage.toml", article.root.joinpath("linkage.toml").read_text()
                 + f'\n[article]\n# where it stands\nparts = {parts}\nphase = "{phase}"  '
                   '# kept\n')
    return article.root


def test_phase_says_what_the_next_one_lacks(article):
    root = _declared(article, "skeleton")
    rc, out, _ = run_cli("--root", str(root), "phase")
    assert rc == 0
    assert "Next:  proving (PROCESS.md § 5)." in out
    assert "lacks the author's approval of the reviewed skeleton" in out


def test_advance_refuses_while_something_is_lacking(article):
    root = _declared(article, "skeleton")
    rc, out, _ = run_cli("--root", str(root), "phase", "--advance")
    assert rc == 1 and "PHASE NOT ADVANCED" in out
    assert config.load(root).phase() == "skeleton"


def test_advance_moves_the_phase_and_keeps_the_comments(article):
    root = _declared(article, "skeleton")
    article.file("records/approval.md", "Approved.\n")
    rc, out, err = run_cli("--root", str(root), "phase", "--advance",
                           "--record", "records/approval.md")
    assert rc == 0, out + err
    text = (root / "linkage.toml").read_text(encoding="utf-8")
    assert 'phase = "proving"  # kept' in text and "# where it stands" in text
    assert config.load(root).phase() == "proving"


def test_advance_to_the_article_needs_the_fidelity_review(article):
    root = _declared(article, "fidelity")
    rc, out, _ = run_cli("--root", str(root), "phase")
    assert "lacks the fidelity review's blueprint/REVIEW-fidelity.md" in out


def test_set_phase_inserts_a_missing_phase_line():
    text = '[article]\nparts = ["paper"]\n\n[paths]\nphase = "not this one"\n'
    out = article.set_phase(text, "article")
    assert out.startswith('[article]\nphase = "article"\nparts')
    assert 'phase = "not this one"' in out
