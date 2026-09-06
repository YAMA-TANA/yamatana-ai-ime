from ranker.onnx_ranker import (
    _preserve_mozc_top_if_uncertain,
    _required_override_margin,
)


def test_weak_context_preserves_mozc_top_when_ai_margin_is_modest():
    # Mozc: 荷物 is rank 1.  AI slightly prefers に持つ, but 「この」 alone is
    # weak evidence and must not be enough to create a bizarre regression.
    scored = [
        (2.0, 1, "c1"),  # AI top: Mozc rank 2
        (0.0, 0, "c0"),  # Mozc top
        (-1.0, 2, "c2"),
    ]
    protected = _preserve_mozc_top_if_uncertain(scored, "この", "")
    assert [item[2] for item in protected] == ["c0", "c1", "c2"]


def test_strong_context_allows_clear_ai_override():
    # With a useful sentence fragment and a large score lead, AI still gets to
    # fix a context-dependent Mozc mistake such as はかった -> 測った.
    scored = [
        (3.0, 1, "c1"),
        (0.0, 0, "c0"),
        (-1.0, 2, "c2"),
    ]
    protected = _preserve_mozc_top_if_uncertain(
        scored, "レーザーで壁までの距離を", ""
    )
    assert [item[2] for item in protected] == ["c1", "c0", "c2"]


def test_context_free_compound_repair_keeps_free_reranking():
    # Context-free model calls are used by explicit compound-boundary repair
    # (e.g. 主戦 + 率 -> 主旋律), so the preservation gate must not block them.
    scored = [(2.0, 2, "c2"), (0.0, 0, "c0"), (-1.0, 1, "c1")]
    protected = _preserve_mozc_top_if_uncertain(scored, "", "")
    assert protected == scored


def test_lower_mozc_candidates_need_more_evidence():
    assert _required_override_margin(8, 5) > _required_override_margin(8, 1)
