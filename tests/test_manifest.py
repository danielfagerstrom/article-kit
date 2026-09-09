"""The manifest — the projection the hub consumes.

Structure and fields, never incidental values: the hub reads every satellite's manifest
with one reader, so what these tests hold still is the schema (`manifest_version`, the
per-label entry, the top-level keys) and the properties the emitter promises about it —
that a sha moves exactly when its input moves, and that `--require-render` refuses to
emit a manifest the hub would have to read as prose-only.

`git_provenance` and `pandoc` are stubbed by conftest (see its docstring), so the stamp
fields and the render decision are deterministic here.
"""

from __future__ import annotations

import json

import pytest

from conftest import run_cli
from fixtures.article import assignment, ledger_entry, statement
from linkage import artifacts
from linkage import manifest as M
from linkage.model import sha12

BODY = "The kernel is smooth."


def build(article, **kw) -> dict:
    cfg = article.cfg
    return M.build(article.parse(), cfg,
                   lean_names=artifacts.lean_declared_names(cfg),
                   ledger=artifacts.ledger_entries(cfg), **kw)


def populated(article):
    article.blueprint(
        statement(label="thm:a", body=BODY, title="Smoothness", lean="Article.smooth",
                  leanok=True, uses=("def:k",), proof="By induction.")
        + statement(env="definition", label="def:k", body="A kernel is a map.")
        + statement(label="thm:b", body="It is bounded.", status="A", ledger=("A1",),
                    note=assignment(), notready=True)
    )
    article.axioms(ledger_entry("A1"))
    article.lean("theorem smooth : True := trivial\n")
    return article


# --- the document ---------------------------------------------------------------------


def test_the_top_level_shape_is_the_hubs_contract(article):
    doc = build(populated(article))
    assert doc["manifest_version"] == M.MANIFEST_VERSION == 2
    assert doc["generated_by"] == "linkage"
    assert doc["slug"] == "test"
    assert set(doc) == {
        "generated_by", "slug", "note", "manifest_version", "generated_at",
        "source_commit", "source_dirty", "render", "labels", "lean_decls", "scripts",
    }


def test_every_labelled_node_is_projected_and_nothing_else(article):
    populated(article)
    article.blueprint(article.root.joinpath("blueprint/src/content.tex")
                      .read_text(encoding="utf-8")
                      + statement(label=None, body="An unlabelled aside."))
    assert set(build(article)["labels"]) == {"thm:a", "def:k", "thm:b"}


def test_a_label_entry_carries_exactly_the_fields_the_hub_reads(article):
    e = build(populated(article))["labels"]["thm:a"]
    assert set(e) == {
        "kind", "env", "title", "status", "ledger", "leanok", "notready", "lean", "uses",
        "statement", "statement_sha", "proof", "proof_sha", "statement_md", "proof_md",
        "rendered_sha",
    }
    assert (e["kind"], e["env"], e["title"]) == ("thm", "theorem", "Smoothness")
    assert (e["status"], e["leanok"], e["notready"]) == ("T", True, False)
    assert e["lean"] == ["Article.smooth"]
    assert e["uses"] == ["def:k"]
    assert e["statement"] == BODY
    assert e["proof"] == "By induction."


def test_the_shas_are_of_the_projected_text(article):
    e = build(populated(article))["labels"]["thm:a"]
    assert e["statement_sha"] == sha12(e["statement"])
    assert e["proof_sha"] == sha12(e["proof"])


def test_a_node_without_a_proof_projects_null_not_an_empty_string(article):
    e = build(populated(article))["labels"]["thm:b"]
    assert e["proof"] is None and e["proof_sha"] is None


def test_each_ledger_reference_carries_its_primary_citation(article):
    e = build(populated(article))["labels"]["thm:b"]
    assert e["ledger"] == [{"id": "A1", "citekey": "author2020",
                            "anchor": "Thm 3.1, p. 88"}]


def test_an_unresolvable_ledger_reference_projects_a_bare_id(article):
    """The manifest is emitted even when check 2 fails — the checker reports, not this."""
    article.blueprint(statement(label="thm:b", status="A", ledger=("A9",),
                                note=assignment("A9 carries the whole statement.")))
    assert build(article)["labels"]["thm:b"]["ledger"] == [
        {"id": "A9", "citekey": None, "anchor": None}]


def test_lean_decls_are_the_articles_declaration_names_sorted(article):
    populated(article)
    article.lean("theorem zeta : True := trivial\ntheorem alpha : True := trivial\n")
    assert build(article)["lean_decls"] == ["alpha", "zeta"]


def test_scripts_lists_the_articles_own_python_scripts(article):
    populated(article)
    assert build(article)["scripts"] == []
    article.file("scripts/figure_one.py", "# a figure generator\n")
    article.file("scripts/notes.md", "not a script\n")
    assert build(article)["scripts"] == ["scripts/figure_one.py"]


def test_the_default_filename_carries_the_slug(article):
    """Two satellites writing one fixed name would break single-writer in the hub."""
    assert M.default_filename("hcs") == "blueprint-manifest-hcs.json"


# --- rendering -----------------------------------------------------------------------


def test_without_pandoc_the_render_fields_are_null_and_a_warning_is_raised(article):
    warnings: list[str] = []
    doc = build(populated(article), warn=warnings.append)
    assert doc["render"] is None
    assert doc["labels"]["thm:a"]["statement_md"] is None
    assert doc["labels"]["thm:a"]["rendered_sha"] is None
    assert any("pandoc not found" in w for w in warnings)


def test_require_render_refuses_to_emit_without_the_pinned_pandoc(article):
    with pytest.raises(M.ManifestError, match="pandoc not found"):
        build(populated(article), require_render=True)


def test_with_the_pinned_pandoc_every_label_is_rendered(article, pandoc):
    calls = pandoc()
    doc = build(populated(article))
    assert doc["render"] == {"renderer": "pandoc", "version": "3.10",
                             "target": "commonmark+tex_math_dollars", "wrap": "none"}
    e = doc["labels"]["thm:a"]
    assert e["statement_md"] == f"md({BODY})"
    assert e["proof_md"] == "md(By induction.)"
    assert e["rendered_sha"] is not None
    assert BODY in calls[0]


def test_the_renderer_is_fed_the_render_source_not_the_statement(article, pandoc):
    r"""In-prose `\ledger{}` renders as text; deleting it leaves dangling punctuation."""
    calls = pandoc()
    article.blueprint(statement(label="thm:x", body=r"Taken as an interface \ledger{A1}."))
    article.axioms(ledger_entry("A1"))
    build(article)
    assert "Taken as an interface ledger A1." in calls[0]


def test_a_plain_title_is_not_sent_through_pandoc(article, pandoc):
    calls = pandoc()
    article.blueprint(statement(label="thm:x", title="Smoothness", body=BODY))
    doc = build(article)
    assert doc["labels"]["thm:x"]["title_md"] == "Smoothness"
    assert "Smoothness" not in calls


def test_a_title_carrying_latex_is_rendered(article, pandoc):
    calls = pandoc()
    article.blueprint(statement(label="thm:x", title=r"Smoothness --- \emph{almost}", body=BODY))
    doc = build(article)
    assert doc["labels"]["thm:x"]["title_md"].startswith("md(")
    assert any("almost" in c for c in calls)


def test_rendered_sha_covers_every_input_of_the_hubs_derived_block(article, pandoc):
    """A \\leanok flip or a title fix must move the sha — else the hub misreads a
    mechanical refresh as a hand-edit (or misses it entirely)."""
    pandoc()
    article.blueprint(statement(label="thm:x", body=BODY, title="One"))
    base = build(article)["labels"]["thm:x"]["rendered_sha"]

    article.blueprint(statement(label="thm:x", body=BODY, title="One", lean="A.x", leanok=True))
    assert build(article)["labels"]["thm:x"]["rendered_sha"] != base

    article.blueprint(statement(label="thm:x", body=BODY, title="Two"))
    assert build(article)["labels"]["thm:x"]["rendered_sha"] != base


def test_a_status_note_edit_moves_no_published_sha(article, pandoc):
    pandoc()
    article.blueprint(statement(label="thm:x", body=BODY, note="First note."))
    before = build(article)["labels"]["thm:x"]
    article.blueprint(statement(label="thm:x", body=BODY, note="A wholly rewritten note."))
    after = build(article)["labels"]["thm:x"]
    assert after["statement_sha"] == before["statement_sha"]
    assert after["rendered_sha"] == before["rendered_sha"]


def test_a_label_that_fails_to_render_is_reported_and_fatal_under_require_render(
        article, pandoc):
    pandoc(fail_on={"bounded"})
    article.blueprint(statement(label="thm:x", body=BODY)
                      + statement(label="thm:y", body="It is bounded."))
    warnings: list[str] = []
    doc = build(article, warn=warnings.append)
    assert doc["labels"]["thm:y"]["statement_md"] is None
    assert any("thm:y" in w for w in warnings)
    with pytest.raises(M.ManifestError, match="1 label"):
        build(article, require_render=True)


def test_raw_latex_surviving_into_the_markdown_is_a_render_failure(article, pandoc):
    """The clean-render gate's second half: a command pandoc dropped must not reach the hub."""
    pandoc(residue=True)
    article.blueprint(statement(label="thm:x", body=BODY))
    with pytest.raises(M.ManifestError, match="1 label"):
        build(article, require_render=True)


# --- through the CLI ------------------------------------------------------------------


def test_the_manifest_command_writes_the_default_filename(article):
    populated(article)
    rc, out, _ = run_cli("--root", str(article.root), "manifest")
    assert rc == 0
    dest = article.root / "blueprint-manifest-test.json"
    assert dest.is_file()
    doc = json.loads(dest.read_text(encoding="utf-8"))
    assert set(doc["labels"]) == {"thm:a", "def:k", "thm:b"}
    assert "3 labels, 1 proofs" in out


def test_check_can_emit_the_manifest_on_the_way_through(article, tmp_path):
    populated(article)
    dest = tmp_path / "out" / "m.json"
    rc, _, _ = run_cli("--root", str(article.root), "check", "--emit-manifest", str(dest))
    assert rc == 0
    assert json.loads(dest.read_text(encoding="utf-8"))["slug"] == "test"


def test_require_render_fails_the_command_with_exit_two(article, tmp_path):
    """Exit 2, not 1: a degraded manifest is a tooling failure, not a linkage defect."""
    populated(article)
    rc, _, err = run_cli("--root", str(article.root), "manifest", str(tmp_path / "m.json"),
                         "--require-render")
    assert rc == 2
    assert "MANIFEST EMIT FAILED" in err
    assert not (tmp_path / "m.json").exists()
