"""The IR — `model.Node` and friends.

Field semantics only: the model is what `checks`, `manifest` and `demand` speak, so
these are the invariants a second parser would also have to satisfy.
"""

from __future__ import annotations

from linkage.model import Blueprint, ControlChar, LedgerEntry, Node, PaperMarker, sha12


def test_sha12_is_a_stable_twelve_hex_digest():
    assert sha12("x") == sha12("x")
    assert len(sha12("x")) == 12
    assert set(sha12("x")) <= set("0123456789abcdef")
    assert sha12("x") != sha12("y")


def test_kind_comes_from_the_label_not_the_environment():
    """`thm:receptive-field` stated in a `proposition` env is still a `thm` to the hub."""
    assert Node(env="proposition", label="thm:receptive-field", title=None).kind == "thm"
    assert Node(env="theorem", label=None, title=None).kind is None


def test_shared_sha_ignores_what_statement_sha_covers():
    n = Node(env="theorem", label="thm:x", title=None,
             statement="S. A note.", shared_statement="S.")
    assert n.shared_sha == sha12("S.")
    assert n.shared_sha != sha12(n.statement)


def test_proof_of_record_is_the_stripped_proof_or_empty():
    proved = Node(env="theorem", label="thm:x", title=None, proof="  By induction. ")
    assert proved.proof_of_record() == "By induction."
    assert Node(env="theorem", label="thm:x", title=None, proof=None).proof_of_record() == ""
    assert Node(env="theorem", label="thm:x", title=None, proof="   ").proof_of_record() == ""


def test_ledger_entry_projects_id_citekey_and_anchor():
    e = LedgerEntry(id="A1", citekey="author2020", anchor="Thm 3.1, p. 88", has_cite_line=True)
    assert e.projection() == {"id": "A1", "citekey": "author2020", "anchor": "Thm 3.1, p. 88"}
    assert LedgerEntry(id="A2").projection() == {"id": "A2", "citekey": None, "anchor": None}


def test_a_markers_principal_label_is_the_first_of_its_list():
    mk = PaperMarker(file="p.tex", blueprint_labels=["thm:a", "thm:b"], statement_label="thm:a")
    assert mk.blueprint_label == "thm:a"
    assert mk.pinned == {} and mk.shared_statement is None


def test_blueprint_indexes_only_labelled_nodes():
    bp = Blueprint(
        nodes=[Node(env="theorem", label="thm:a", title=None),
               Node(env="remark", label=None, title=None)],
        ledger_refs=set(), notes_slugs=set(),
    )
    assert bp.labels == {"thm:a"}
    assert list(bp.by_label) == ["thm:a"]


def test_control_char_carries_the_code_point_and_its_context():
    cc = ControlChar(path="paper/x.tex", line=3, char=0x09, context="a\tb")
    assert f"U+{cc.char:04X}" == "U+0009"
