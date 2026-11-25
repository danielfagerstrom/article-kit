r"""Check 1 compares full, namespace-qualified Lean names (Q-0876).

`theorem SymLevyData.hasTriplet` is declared as `SymLevyData.hasTriplet`, not `SymLevyData`; a
`\lean{}` tag naming a different namespace's `knot_data` is not the declaration it names.
"""

from __future__ import annotations

from fixtures.article import statement
from linkage import artifacts


def lean_fatal(article, tag):
    article.blueprint(statement(label="thm:x", lean=tag, leanok=True))
    return [m for m in article.check().fatal if m.startswith("[lean]")]


def test_a_dotted_declaration_is_recorded_whole(article):
    article.lean("theorem SymLevyData.hasTriplet : True := trivial\n")
    assert artifacts.lean_declared_names(article.cfg) == {"SymLevyData.hasTriplet"}


def test_namespaces_and_sections_prefix_the_name(article):
    article.lean("""
namespace Pyramids
section Aux
theorem a : True := trivial
end Aux
namespace Inner.Deep
def b := 1
end Inner.Deep
noncomputable section
def c := 2
end
theorem _root_.top : True := trivial
end Pyramids
theorem after : True := trivial
""")
    assert artifacts.lean_declared_names(article.cfg) == {
        "Pyramids.a", "Pyramids.Inner.Deep.b", "Pyramids.c", "top", "after"}


def test_a_dotted_tag_is_found(article):
    article.lean("theorem SymLevyData.hasTriplet : True := trivial\n")
    assert lean_fatal(article, "Pyramids.SymLevyData.hasTriplet") == []
    assert lean_fatal(article, "SymLevyData.hasTriplet") == []


def test_a_tag_naming_the_wrong_declaration_is_rejected(article):
    article.lean("theorem CarriesLatticeLadder.other : True := trivial\n"
                 "namespace LineAppendix\ntheorem knot_data : True := trivial\nend LineAppendix\n")
    (msg,) = lean_fatal(article, "Pyramids.CarriesLatticeLadder.knot_data")
    assert "not declared" in msg


def test_a_library_prefix_falls_back_to_a_unique_last_segment(article):
    article.lean("namespace Inner\ntheorem only_one : True := trivial\nend Inner\n")
    assert lean_fatal(article, "Lib.only_one") == []


def test_an_ambiguous_last_segment_is_not_a_fallback(article):
    article.lean("namespace A\ntheorem dup : True := trivial\nend A\n"
                 "namespace B\ntheorem dup : True := trivial\nend B\n")
    assert lean_fatal(article, "Lib.dup") != []
    assert lean_fatal(article, "B.dup") == []
