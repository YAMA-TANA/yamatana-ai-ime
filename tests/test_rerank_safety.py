from ranker.onnx_ranker import (
    _preserve_mozc_top_if_uncertain,
    _rank_prior_penalty,
    _required_override_margin,
)


def test_weak_context_preserves_mozc_top_when_ai_margin_is_modest():
    # Mozc: 荷物 is rank 1. AI only slightly prefers a challenger, and 「この」
    # alone is too weak to justify changing the committed top candidate.
    scored = [
        (0.45, 1, "c1"),  # AI/combined top: Mozc rank 2
        (0.00, 0, "c0"),  # Mozc top
        (-1.0, 2, "c2"),
    ]
    evidence = {"c1": 0.50, "c0": 0.00, "c2": -1.0}
    protected = _preserve_mozc_top_if_uncertain(scored, "この", "", evidence)
    assert [item[2] for item in protected] == ["c0", "c1", "c2"]


def test_strong_context_allows_clear_ai_override():
    # With a useful sentence fragment and a clear model-score gap, AI should
    # fix a context-dependent Mozc mistake such as はかった -> 測った.
    scored = [
        (0.72, 6, "c6"),  # a deep Mozc candidate may still win
        (0.00, 0, "c0"),
        (-0.2, 1, "c1"),
    ]
    evidence = {"c6": 1.00, "c0": 0.00, "c1": -0.2}
    protected = _preserve_mozc_top_if_uncertain(
        scored, "レーザーで壁までの距離を", "", evidence
    )
    assert [item[2] for item in protected] == ["c6", "c0", "c1"]


def test_context_free_compound_repair_keeps_free_reranking():
    # Context-free model calls are used by explicit compound-boundary repair
    # (e.g. 主戦 + 率 -> 主旋律), so the preservation gate must not block them.
    scored = [(2.0, 2, "c2"), (0.0, 0, "c0"), (-1.0, 1, "c1")]
    protected = _preserve_mozc_top_if_uncertain(scored, "", "")
    assert protected == scored


def test_rank_prior_is_real_but_sublinear():
    # Rank still matters, but rank 20 is no longer hit by a 1.9-point linear
    # penalty when prior_w=0.1. This lets a clear neural score difference win.
    rank2 = _rank_prior_penalty(1, 0.1)
    rank10 = _rank_prior_penalty(9, 0.1)
    rank20 = _rank_prior_penalty(19, 0.1)
    assert 0.0 < rank2 < rank10 < rank20 < 0.35


def test_override_threshold_depends_on_context_not_candidate_rank():
    assert _required_override_margin(2) > _required_override_margin(8)
    assert _required_override_margin(8) > _required_override_margin(20)
