from ranker.onnx_ranker import (
    _preserve_mozc_top_if_uncertain,
    _required_override_margin,
)


def test_weak_context_preserves_mozc_top_when_ai_margin_is_tiny():
    # Mozc: 荷物 is rank 1. AI only barely prefers another candidate, while
    # 「この」 gives little contextual evidence.
    scored = [
        (0.20, 1, "c1"),
        (0.00, 0, "c0"),
        (-1.00, 2, "c2"),
    ]
    protected = _preserve_mozc_top_if_uncertain(scored, "この", "")
    assert [item[2] for item in protected] == ["c0", "c1", "c2"]


def test_strong_context_allows_clear_ai_override():
    # Useful context lowers the safety margin, so a real model-score advantage
    # can fix a context-dependent Mozc mistake such as はかった -> 測った.
    scored = [
        (0.35, 1, "c1"),
        (0.00, 0, "c0"),
        (-1.00, 2, "c2"),
    ]
    protected = _preserve_mozc_top_if_uncertain(
        scored, "レーザーで壁までの距離を", ""
    )
    assert [item[2] for item in protected] == ["c1", "c0", "c2"]


def test_context_free_compound_repair_keeps_free_reranking():
    scored = [(0.20, 2, "c2"), (0.00, 0, "c0"), (-1.00, 1, "c1")]
    protected = _preserve_mozc_top_if_uncertain(scored, "", "")
    assert protected == scored


def test_candidate_depth_does_not_increase_required_margin():
    # The old policy charged +0.20 per original-rank step.  The new gate only
    # asks whether the AI score actually beats Mozc by enough in this context.
    assert _required_override_margin(8) == _required_override_margin(8)
    scored_rank_2 = [(0.40, 1, "c1"), (0.00, 0, "c0")]
    scored_rank_20 = [(0.40, 19, "c19"), (0.00, 0, "c0")]
    assert _preserve_mozc_top_if_uncertain(scored_rank_2, "十分な文脈です", "")[0][2] == "c1"
    assert _preserve_mozc_top_if_uncertain(scored_rank_20, "十分な文脈です", "")[0][2] == "c19"


def test_override_margin_decreases_smoothly_with_more_context():
    assert _required_override_margin(2) > _required_override_margin(8)
    assert _required_override_margin(8) > _required_override_margin(40)
    assert _required_override_margin(40) > 0.10
