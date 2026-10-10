r"""Check 15: a shared-library statement has one home, and a later article cites it (Q-0392).

The library's record of homes (`site/library/data.json`) is read at the revision the lake
manifest pins, so most of these build a real git repository under `tmp_path`, as
`tests/test_ledger_module.py` does for a qualified `\ledger{}`; the rest hand the check a
record by path, the way a run against an unpinned library revision does.
"""

from __future__ import annotations

import json
import subprocess

import pytest
from test_ledger_module import manifest, package

from conftest import run_cli, tagged
from fixtures.article import statement
from linkage import homes
from linkage.model import sha12

CASCADE = "A cascade family is a family of kernels closed under convolution."

RECORD = {
    "source_dir": "ScaleSpaceCore",
    "modules": {
        "Family": {"home": {"kind": "home", "article": "line",
                            "labels": ["def:cascade-family"]}},
        "Bridge": {"home": {"kind": "home", "article": "line/cone",
                            "labels": ["lem:bridge"]}},
        "L1Operators": {"home": {"kind": "none", "reason": "standard analysis",
                                 "reference": None}},
        "Corners": {"home": {"kind": "owed", "article": "causal-kernels",
                             "missing": "the corner nodes tag the article's own copy"}},
    },
    "declarations": [
        {"name": "ScaleSpace.CascadeFamily", "module": "Family", "kind": "structure"},
        {"name": "ScaleSpace.bridge_exponent", "module": "Bridge", "kind": "theorem"},
        {"name": "ScaleSpace.translate", "module": "L1Operators", "kind": "def"},
        {"name": "ScaleSpace.gamma_corner", "module": "Corners", "kind": "theorem"},
    ],
}


@pytest.fixture
def unblocked(monkeypatch, real_run):
    monkeypatch.setattr(subprocess, "run", real_run)


def record_file(article, record: dict | None = None):
    article.file("record.json", json.dumps(RECORD if record is None else record))
    return article.root / "record.json"


def run(article, tex: str, *, as_article: str, record: dict | None = None):
    article.blueprint(tex)
    return article.check(library_record=record_file(article, record),
                         library_article=as_article)


def home_def(body: str = CASCADE) -> str:
    return statement(body, env="definition", label="def:cascade-family",
                     lean="ScaleSpace.CascadeFamily")


# --- the four classes --------------------------------------------------------------------


def test_the_node_the_record_names_is_the_home(article):
    f = run(article, home_def(), as_article="line")
    assert tagged(f.advisory, "home") == []
    assert f.stats["homes"]["home"] == 1 and f.stats["homes"]["uncited"] == 0


def test_a_module_of_the_same_member_is_the_same_article(article):
    """`line/cone`'s homes are nodes of the one blueprint `line`'s repository holds."""
    f = run(article, statement(label="lem:bridge", lean="ScaleSpace.bridge_exponent"),
            as_article="line")
    assert f.stats["homes"]["home"] == 1


def test_a_later_article_that_cites_the_home_is_a_citation(article):
    tex = statement(r"The marginals form a cascade family \statedin{line:def:cascade-family}.",
                    label="lem:marginal-family", lean="ScaleSpace.CascadeFamily")
    f = run(article, tex, as_article="affine")
    assert tagged(f.advisory, "home") == []
    assert f.stats["homes"]["cited"] == 1


def test_a_lemma_that_constructs_a_library_structure_uncited_is_a_use(article):
    """Paper VII's `lem:isotropic-marginal-family`: it tags the structure it builds."""
    f = run(article, statement(label="lem:marginal-family", lean="ScaleSpace.CascadeFamily"),
            as_article="affine")
    [msg] = tagged(f.advisory, "home")
    assert "uses \\lean{ScaleSpace.CascadeFamily}" in msg
    assert "\\statedin{line:def:cascade-family}" in msg and "states it again" not in msg
    assert f.stats["homes"]["uncited"] == 1 and f.ok


@pytest.mark.parametrize("tex", [
    # a definition node over a library structure, a claim node over a library theorem
    statement(CASCADE, env="definition", label="def:family", lean="ScaleSpace.CascadeFamily"),
    statement(label="lem:bridge-again", lean="ScaleSpace.bridge_exponent"),
])
def test_an_unmarked_restatement_is_reported_as_one(article, tex):
    f = run(article, tex, as_article="affine")
    [msg] = tagged(f.advisory, "home")
    assert "states it again unmarked" in msg and "\\restates{line" in msg
    assert f.ok


def test_inside_one_blueprint_a_uses_path_to_the_home_is_the_citation(article):
    tex = (home_def()
           + statement(label="lem:mid", uses=("def:cascade-family",))
           + statement(label="lem:far", lean="ScaleSpace.CascadeFamily", uses=("lem:mid",))
           + statement(label="lem:loose", lean="ScaleSpace.CascadeFamily"))
    f = run(article, tex, as_article="line")
    [msg] = tagged(f.advisory, "home")
    assert msg.startswith("[home]   lem:loose") and "\\uses{def:cascade-family}" in msg
    assert (f.stats["homes"]["home"], f.stats["homes"]["cited"]) == (1, 1)


def test_standard_material_and_an_owed_home(article):
    tex = (statement(label="lem:shift", lean="ScaleSpace.translate")
           + statement(label="prop:gamma", lean="ScaleSpace.gamma_corner"))
    f = run(article, tex, as_article="causal-kernels")
    [msg] = tagged(f.advisory, "home")
    assert "a home is owed by causal-kernels" in msg and "prop:gamma" in msg
    assert "the corner nodes tag" in msg
    assert (f.stats["homes"]["standard"], f.stats["homes"]["owed"]) == (1, 1)


def test_a_citation_the_record_does_not_know_does_not_resolve(article):
    tex = statement(r"A family \statedin{line:def:no-such-node} \statedin{nonsense}.",
                    label="lem:marginal-family")
    f = run(article, tex, as_article="affine")
    msgs = tagged(f.advisory, "home")
    assert len(msgs) == 2 and f.stats["homes"]["unresolved"] == 2
    assert "names no home line:def:no-such-node" in msgs[0]
    assert "is not `[<article>:]<label>`" in msgs[1]


def test_the_article_is_linkage_tomls_library_article_then_its_slug(article):
    toml = (article.root / "linkage.toml").read_text(encoding="utf-8")
    article.file("linkage.toml", 'library_article = "line"\n' + toml)
    article.blueprint(home_def())
    f = article.check(library_record=record_file(article))
    assert f.stats["homes"]["home"] == 1
    article.file("linkage.toml", toml)       # slug `test`: the home is another article's
    f = article.check(library_record=record_file(article))
    assert f.stats["homes"]["uncited"] == 1


def test_the_citations_are_not_statement_text(article):
    """Citing a home must not move the sha the hub and the paper markers hold."""
    article.blueprint(statement("A family.", label="lem:a")
                      + statement(r"A family\statedin{line:def:cascade-family}"
                                  r"\restates{line:def:cascade-family@0123456789ab}.",
                                  label="lem:b"))
    a, b = article.parse().nodes
    assert a.statement == b.statement and a.shared_sha == b.shared_sha
    assert b.stated_in == ["line:def:cascade-family"]
    assert b.restates == ["line:def:cascade-family@0123456789ab"]


# --- a marked restatement is compared with the home ----------------------------------------


def restated(body: str, ref: str = "line:def:cascade-family") -> str:
    return statement(f"{body}\\restates{{{ref}}}", env="definition", label="def:family",
                     lean="ScaleSpace.CascadeFamily")


@pytest.fixture
def paper_v(article, unblocked):
    """Paper V's export as a required package: it ships the home's blueprint."""
    sha = package(article, "SpatialHemigroup", {
        "blueprint/src/content.tex": "\\input{parts/05-cascade}\n",
        "blueprint/src/parts/05-cascade.tex": home_def(),
    })
    manifest(article, ("SpatialHemigroup", "v0.1", sha))


def test_a_marked_restatement_equal_to_the_home_is_verbatim(article, paper_v):
    f = run(article, restated(CASCADE), as_article="affine")
    assert tagged(f.advisory, "home") == []
    h = f.stats["homes"]
    assert (h["cited"], h["restated"], h["verbatim"]) == (1, 1, 1)


def test_a_marked_restatement_that_differs_says_where(article, paper_v):
    f = run(article, restated(CASCADE.replace("closed", "stable")), as_article="affine")
    [msg] = tagged(f.advisory, "home")
    assert "SpatialHemigroup @ v0.1" in msg and "differs from the home after" in msg
    assert f.stats["homes"]["differing"] == 1 and f.ok


def test_an_editorial_restatement_is_tracked_by_the_homes_sha(article, paper_v):
    pin = sha12(CASCADE)
    f = run(article, restated("Our families.", f"line:def:cascade-family@{pin}"),
            as_article="affine")
    assert tagged(f.advisory, "home") == [] and f.stats["homes"]["tracked"] == 1
    f = run(article, restated("Our families.", "line:def:cascade-family@0123456789ab"),
            as_article="affine")
    [msg] = tagged(f.advisory, "home")
    assert "changed since this restatement was pinned" in msg and pin in msg


def test_a_restatement_of_an_unreachable_home_is_uncompared_not_failed(article):
    """The home is in an article this one does not require."""
    f = run(article, restated(CASCADE), as_article="affine")
    [msg] = tagged(f.advisory, "home")
    assert "uncompared" in msg
    assert f.stats["homes"]["uncompared"] == 1 and f.ok


# --- the record is read at the pin ----------------------------------------------------------


def library(article, files: dict[str, str], *, listed: bool = True) -> None:
    sha = package(article, "ScaleSpaceCore", files)
    manifest(article, ("ScaleSpaceCore", "v0.5.0", sha))
    if listed:
        toml = (article.root / "linkage.toml").read_text(encoding="utf-8")
        article.file("linkage.toml", toml + 'lean_packages = ["ScaleSpaceCore"]\n')


def test_the_record_is_read_at_the_pinned_commit_not_the_working_tree(article, unblocked):
    library(article, {homes.RECORD_PATH: json.dumps(RECORD)})
    (article.root / "Formalization/.lake/packages/ScaleSpaceCore" / homes.RECORD_PATH
     ).write_text("{}", encoding="utf-8")
    article.blueprint(statement(label="lem:marginal-family", lean="ScaleSpace.CascadeFamily"))
    f = article.check(library_article="affine")
    assert len(tagged(f.advisory, "home")) == 1
    assert len(f.stats["homes"]["records"]) == 1
    assert f.stats["homes"]["records"][0].startswith("ScaleSpaceCore @ v0.5.0 (")


def test_a_library_with_no_data_json_is_not_checked(article, unblocked):
    library(article, {"ScaleSpaceCore.lean": "structure CascadeFamily where\n"})
    article.blueprint(statement(label="lem:marginal-family", lean="ScaleSpace.CascadeFamily"))
    f = article.check(library_article="affine")
    assert tagged(f.advisory, "home") == [] and f.stats["homes"]["records"] == []
    [note] = f.stats["homes_notes"]
    assert "no shared package carries site/library/data.json" in note
    assert "ScaleSpaceCore @ v0.5.0" in note


def test_a_package_the_article_does_not_name_as_shared_is_silent(article, unblocked):
    library(article, {"README.md": "a dependency\n"}, listed=False)
    article.blueprint(statement(label="lem:x"))
    f = article.check()
    assert f.stats["homes_notes"] == [] and tagged(f.advisory, "home") == []


def test_a_pinned_record_without_home_predates_it_and_is_not_an_error(article, unblocked):
    old = {"modules": {"Family": {"title": "families"}},
           "declarations": RECORD["declarations"]}
    library(article, {homes.RECORD_PATH: json.dumps(old)})
    article.blueprint(statement(label="lem:marginal-family", lean="ScaleSpace.CascadeFamily"))
    f = article.check(library_article="affine")
    assert tagged(f.advisory, "home") == [] and f.ok
    [note] = f.stats["homes_notes"]
    assert "predates the record of homes" in note


def test_a_record_given_by_path_stands_in_for_the_pinned_one(article, unblocked):
    library(article, {"README.md": "no record at this tag\n"})
    article.blueprint(statement(label="lem:marginal-family", lean="ScaleSpace.CascadeFamily"))
    f = article.check(library_record=record_file(article), library_article="affine")
    assert len(tagged(f.advisory, "home")) == 1 and f.stats["homes_notes"] == []
    assert "not read at the pin" in f.stats["homes"]["records"][0]


# --- the CLI --------------------------------------------------------------------------------


def test_linkage_check_prints_the_counts_and_stays_green(article, monkeypatch):
    article.blueprint(home_def() + statement(label="lem:loose", lean="ScaleSpace.CascadeFamily"))
    rc, out, _ = run_cli("--root", str(article.root), "check",
                         "--library-record", str(record_file(article)),
                         "--library-article", "line")
    assert rc == 0
    assert "1 home(s), 0 citation(s), 1 uncited use(s)" in out
    assert "advisory [home]   lem:loose" in out
    monkeypatch.setenv(homes.ENV_RECORD, str(record_file(article)))
    monkeypatch.setenv(homes.ENV_ARTICLE, "line")
    rc, out, _ = run_cli("--root", str(article.root), "check")
    assert rc == 0 and "1 home(s), 0 citation(s), 1 uncited use(s)" in out


def test_an_article_with_no_shared_library_prints_nothing_about_homes(article):
    article.blueprint(statement(label="lem:x"))
    rc, out, _ = run_cli("--root", str(article.root), "check")
    assert rc == 0 and "Library homes" not in out
