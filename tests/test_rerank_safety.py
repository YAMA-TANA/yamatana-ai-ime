from ranker.onnx_ranker import (
    _preserve_mozc_top_if_uncertain,
    _rank_prior_penalty,
    _required_override_margin,
)


def test_weak_context_preserves_mozc_top_when_ai_margin_is_tiny():
    scored = [
        (0.20, 1, "c1"),
        (0.00, 0, "c0"),
        (-1.00, 2, "c2"),
    ]
    protected = _preserve_mozc_top_if_uncertain(scored, "この", "")
    assert [item[2] for item in protected] == ["c0", "c1", "c2"]


def test_strong_context_allows_clear_ai_override():
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


def test_rank_prior_is_real_but_bounded():
    p2 = _rank_prior_penalty(1, 0.10)
    p5 = _rank_prior_penalty(4, 0.10)
    p10 = _rank_prior_penalty(9, 0.10)
    p20 = _rank_prior_penalty(19, 0.10)
    p100 = _rank_prior_penalty(99, 0.10)
    assert 0.0 < p2 < p5 < p10 < p20
    assert p20 == p100 == 0.10


def test_clear_ai_lead_can_overcome_even_deep_rank_prior():
    raw_ai_lead = 0.50
    adjusted_rank_2 = raw_ai_lead - _rank_prior_penalty(1, 0.10)
    adjusted_rank_20 = raw_ai_lead - _rank_prior_penalty(19, 0.10)
    assert adjusted_rank_2 > _required_override_margin(8)
    assert adjusted_rank_20 > _required_override_margin(8)


def test_override_margin_decreases_smoothly_with_more_context():
    assert _required_override_margin(2) > _required_override_margin(8)
    assert _required_override_margin(8) > _required_override_margin(40)
    assert _required_override_margin(40) > 0.05
