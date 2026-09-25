"""The reviewer output contract: pooling, breadth ranking, and the rules it enforces.

The fixture is the shape the contract is for — two blind reviews of one section that
found the same defect and described it differently, plus a third review of another
section that the same label runs through. What the suite pins is that this arrives as
*one* entry with a count of two, because the count is the product; the ~120 flags of the
trial batch were all well-formed and none of it was actionable until it was pooled.
"""

from __future__ import annotations

import json
from pathlib import Path

from conftest import REPO, run_cli
from linkage import review

FIXTURES = REPO / "tests" / "fixtures" / "reviews"
A, B, C = (FIXTURES / f"review-{x}.jsonl" for x in "abc")
BAD = FIXTURES / "malformed.jsonl"


def agg(*paths: Path, top: int = 10):
    return review.aggregate(list(paths), FIXTURES, top=top)


def test_two_reviews_of_one_section_pool_a_shared_defect_with_count_two():
    doc, lines, rc = agg(A, B)
    assert rc == 0, doc["malformed"]
    scope = [d for d in doc["defects"] if d["tag"] == "SCOPE"]
    assert len(scope) == 1
    assert scope[0]["count"] == 2
    assert scope[0]["reviews"] == ["review-a", "review-b"]
    assert scope[0]["flags"] == 2
    assert "x2 sev<=3  SCOPE" in "\n".join(lines)


def test_the_ranking_is_breadth_not_severity():
    """A severity-3 defect one reviewer found ranks below a defect two found."""
    doc, _, _ = agg(A, B)
    order = [(d["tag"], d["count"], d["severity"])
             for d in doc["defects"] if d["layer"] == "structure"]
    assert order[0] == ("SCOPE", 2, 3)
    assert ("COUNT", 1, 2) in order
    assert order.index(("COUNT", 1, 2)) > 0


def test_severity_is_recorded_as_the_maximum_and_never_pools_away():
    doc, _, _ = agg(A, B)
    scope = next(d for d in doc["defects"] if d["tag"] == "SCOPE")
    assert scope["severity"] == 3          # review-a said 3, review-b said 1


def test_flags_citing_no_label_pool_on_overlapping_anchors():
    """Voice flags carry no `refs`, so the quoted prose is what identifies them —
    including across the line break LaTeX put in the middle of review-b's quote."""
    doc, _, _ = agg(A, B)
    voice = [d for d in doc["defects"] if d["layer"] == "voice"]
    assert len(voice) == 1
    assert voice[0]["tag"] == "MOTIVATION" and voice[0]["count"] == 2


def test_the_defect_key_is_the_smallest_label_the_pool_cites():
    doc, _, _ = agg(A, B)
    scope = next(d for d in doc["defects"] if d["tag"] == "SCOPE")
    assert scope["key"] == "paper/09-signaling.tex::SCOPE::def:standing-hypothesis"
    voice = next(d for d in doc["defects"] if d["layer"] == "voice")
    assert voice["key"].startswith("paper/09-signaling.tex::MOTIVATION::anchor:")


def test_the_key_does_not_move_when_the_reviews_are_given_in_another_order():
    first, _, _ = agg(A, B)
    second, _, _ = agg(B, A)
    assert [d["key"] for d in first["defects"]] == [d["key"] for d in second["defects"]]


def test_a_shared_label_across_sections_is_proposed_as_a_thread():
    doc, lines, rc = agg(A, B, C)
    assert rc == 0, doc["malformed"]
    assert len(doc["threads"]) == 1
    t = doc["threads"][0]
    assert t["files"] == ["paper/07-characterization.tex", "paper/09-signaling.tex"]
    assert "def:standing-hypothesis" in t["refs"]
    assert len(t["defects"]) == 2
    text = "\n".join(lines)
    assert text.index("THREADS") < text.index("STRUCTURE")   # never the raw list first


def test_a_single_section_review_proposes_no_thread():
    doc, _, _ = agg(A)
    assert doc["threads"] == []


def test_the_report_opens_with_the_strengths_and_the_boundary():
    _, lines, _ = agg(A, B)
    head = "\n".join(lines[:6])
    assert "2 review(s) of paper/09-signaling.tex [contract B.5]" in head
    assert "motivates before it formalizes" in head
    assert "correctness is Lean's" in head


def test_an_anchor_that_is_not_unique_is_rejected_and_the_flag_dropped():
    doc, _, rc = agg(BAD)
    assert rc == 1
    assert any("anchor occurs 3 times" in m for m in doc["malformed"])
    assert not any(d["tag"] == "SCOPE" for d in doc["defects"])


def test_a_tag_outside_the_vocabulary_and_a_wrong_layer_are_rejected():
    doc, _, rc = agg(BAD)
    assert rc == 1
    joined = "\n".join(doc["malformed"])
    assert "tag 'VIBE' is not in the vocabulary" in joined
    assert "severity 9 is not 1, 2 or 3" in joined
    assert "MOTIVATION is a voice tag, but layer says 'structure'" in joined


def test_a_malformed_contract_declaration_invalidates_the_review(tmp_path):
    p = tmp_path / "r.jsonl"
    p.write_text(json.dumps({"kind": "review", "target": "paper/09-signaling.tex",
                             "contract": "5", "contract_why": "main results",
                             "strengths": "clear"}) + "\n", encoding="utf-8")
    doc, _, rc = review.aggregate([p], FIXTURES)
    assert rc == 1
    assert doc["reviews"] == []
    assert any("is not a declaration of the form B.<1-10>" in m for m in doc["malformed"])


def test_several_contracts_in_one_declaration_are_accepted(tmp_path):
    p = tmp_path / "r.jsonl"
    p.write_text(json.dumps({"kind": "review", "target": "paper/09-signaling.tex",
                             "contract": "B.2+B.3", "contract_why": "the intro absorbs "
                             "the related-work contract", "strengths": "clear"}) + "\n",
                 encoding="utf-8")
    doc, _, rc = review.aggregate([p], FIXTURES)
    assert rc == 0 and doc["reviews"][0]["contract"] == "B.2+B.3"


def test_two_reviews_disagreeing_about_the_contract_are_reported(tmp_path):
    """A wrong mapping invalidates every structural flag under it, so the disagreement
    is a finding in its own right rather than something to average over."""
    p = tmp_path / "other.jsonl"
    rec = json.loads(B.read_text(encoding="utf-8").splitlines()[0])
    rec["contract"] = "B.7"
    p.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    doc, _, rc = review.aggregate([A, p], FIXTURES)
    assert rc == 1
    assert any("contract conflict on paper/09-signaling.tex" in m
               for m in doc["malformed"])


def test_a_refs_label_that_resolves_nowhere_is_reported_but_keeps_the_flag(tmp_path):
    p = tmp_path / "r.jsonl"
    lines = A.read_text(encoding="utf-8").splitlines()
    flag = json.loads(lines[1])
    flag["refs"] = ["def:standing-hypothesis", "thm:not-a-label"]
    p.write_text(lines[0] + "\n" + json.dumps(flag) + "\n", encoding="utf-8")
    doc, _, rc = review.aggregate([p], FIXTURES)
    assert rc == 1
    assert any("thm:not-a-label" in m for m in doc["malformed"])
    assert len(doc["defects"]) == 1


def test_a_flag_with_no_review_record_before_it_is_rejected(tmp_path):
    p = tmp_path / "r.jsonl"
    p.write_text(A.read_text(encoding="utf-8").splitlines()[1] + "\n", encoding="utf-8")
    doc, _, rc = review.aggregate([p], FIXTURES)
    assert rc == 1
    assert doc["defects"] == []
    assert any("flag before any well-formed review record" in m
               for m in doc["malformed"])


def test_the_cli_prints_the_aggregate_and_exits_zero():
    rc, out, _ = run_cli("review", "--base", str(FIXTURES), str(A), str(B))
    assert rc == 0
    assert "x2 sev<=3  SCOPE" in out
    assert "MALFORMED (0)" in out


def test_the_cli_exits_one_on_a_malformed_record_and_says_what_survived():
    rc, _, err = run_cli("review", "--base", str(FIXTURES), str(BAD))
    assert rc == 1
    assert "REVIEW AGGREGATE" in err and "malformed record(s)" in err


def test_the_cli_json_is_the_whole_aggregate():
    rc, out, _ = run_cli("review", "--base", str(FIXTURES), "--json", str(A), str(B),
                         str(C))
    assert rc == 0
    doc = json.loads(out)
    assert {"reviews", "threads", "defects", "malformed"} == set(doc)
    assert len(doc["reviews"]) == 3
