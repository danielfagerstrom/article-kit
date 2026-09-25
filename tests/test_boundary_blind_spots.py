r"""What the boundary harness does NOT catch, written as the tests it would pass if it did.

Same contract as `test_blind_spots.py`: every test is `xfail(strict=True)`, so it fails the
day the gap is closed. The harness is a source-text lint, and these three are where that
shows. None of them is a crash; each is a way a tree passes the harness while the guarantee
it publishes — "every headline result is pinned, probed and still means something" — is
weaker than it reads.

Two of the three are arguably not the lint's to close at all: whether a probe says anything
and whether an adversarial goal is really false are judgments, and the fidelity review makes
them (`.claude/skills/fidelity-review/`). They are recorded here anyway, because the harness's
own failure message claims more than it checks, and a reader of that message deserves to find
the limit written down somewhere.
"""

from __future__ import annotations

import pytest
from test_boundary import LIB, TABLE, built

from linkage import boundary

pytestmark = pytest.mark.xfail(strict=True, reason="documented blind spot — see the docstring")


def findings(article, **kw) -> str:
    rep = boundary.run(article.cfg, **kw)
    return "\n".join(rep.fatal + rep.advisory)


def test_a_reflexive_probe_is_reported(article):
    """`Art.main = Art.main` mentions the headline, is not a `sorry`, and is not stated as
    `True` — so it satisfies every check 2 makes, and holds whatever became of the theorem.
    `is_vacuous` catches the one syntactic form of nothing-said; this is the other one, and
    the general question (does this statement constrain anything?) is not a source-text
    question at all."""
    built(article, probes="import Art\n\ntheorem probe_main : Art.main = Art.main := rfl\n")
    assert "probe" in findings(article)


def test_an_adversarial_goal_that_is_actually_true_is_reported(article):
    """The file's contract is "every statement here is FALSE", and the lint checks only that
    each is still a `sorry`. A goal mis-stated into something true sits there forever, passing,
    testing nothing — and the day someone proves it, the failure will read as an unsoundness
    alarm when it is a mis-statement. Nothing short of elaborating the file can tell the two
    apart; what could be done cheaply is to require each goal to name the counterexample its
    docstring claims."""
    built(article, adversarial="import Art\n\n/-- FALSE: -/\ntheorem adv : 0 = 0 := sorry\n")
    assert "adversarial" in findings(article)


def test_a_headline_result_missing_from_the_manifest_is_reported(article):
    r"""`[boundary] headline` is the article's own say-so about which results matter, and
    nothing cross-checks it against the blueprint. Dropping a name from the list silently
    exempts that theorem from both the pin and the probe — the same hand-kept step the guard
    file's own header warns about ("adding a node to the blueprint without adding its
    declaration here silently exempts it from the guard"). The blueprint already knows: a
    `\leanok` node with a `\lean{}` tag and a `\statusT` is a proved headline claim, so the
    harness could ask the parser instead of the author."""
    from fixtures.article import statement

    built(article, table=TABLE.replace('headline = ["Art.main"]', "headline = []"),
          lib=LIB)
    article.blueprint(statement(label="thm:main", lean="Art.main", leanok=True,
                                proof="Immediate.", proof_leanok=True))
    assert "Art.main" in findings(article)
