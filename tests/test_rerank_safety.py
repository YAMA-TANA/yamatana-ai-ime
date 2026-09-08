from ranker.onnx_ranker import (
    _preserve_mozc_top_if_uncertain,
    _rank_prior_penalty,
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
    evidence = {"c6": 2.00, "c0": 0.00, "c1": -0.2}
    protected = _preserve_mozc_top_if_uncertain(
        scored, "レーザーで壁までの距離を", "", evidence
    )
    assert [item[2] for item in protected] == ["c6", "c0", "c1"]


def test_context_free_long_phrase_uses_shared_candidate_context():
    # A collapsed segment contains its own evidence around the single differing
    # span. It must not be mistaken for an isolated context-free word.
    scored = [(1.58, 1, "c1"), (0.0, 0, "c0")]
    evidence = {"c1": 1.58, "c0": 0.0}
    texts = {"c1": "彼の顔の鼻は大きい", "c0": "彼の顔の花は大きい"}
    protected = _preserve_mozc_top_if_uncertain(
        scored, "", "", evidence, texts
    )
    assert protected == scored


def test_short_shared_suffix_does_not_make_sparse_context_safe():
    # 「貨物を」 may be truncated to a two-character signal. A confident but
    # implausible 輸送して -> 油送して change has only three shared characters.
    scored = [(2.33, 1, "c1"), (0.0, 0, "c0")]
    evidence = {"c1": 2.33, "c0": 0.0}
    texts = {"c1": "油送して", "c0": "輸送して"}
    protected = _preserve_mozc_top_if_uncertain(
        scored, "物を", "", evidence, texts
    )
    assert [item[2] for item in protected] == ["c0", "c1"]


def test_both_sides_allow_mid_confidence_clear_lead():
    # Eight choices dilute softmax confidence for はな, but strong context on
    # both sides plus a clear Mozc lead should still allow 花 -> 鼻.
    scored = [
        (2.83, 1, "c1"),
        (1.47, 2, "c2"),
        (1.20, 3, "c3"),
        (0.80, 4, "c4"),
        (0.30, 5, "c5"),
        (0.00, 0, "c0"),
        (-0.50, 6, "c6"),
        (-1.00, 7, "c7"),
    ]
    evidence = {item[2]: item[0] for item in scored}
    protected = _preserve_mozc_top_if_uncertain(
        scored, "彼の顔の", "は大きい", evidence
    )
    assert protected == scored


def test_one_sided_mid_confidence_preserves_when_ai_margin_is_small():
    scored = [(2.0, 1, "c1"), (0.0, 0, "c0"), (1.9, 2, "c2")]
    evidence = {item[2]: item[0] for item in scored}
    protected = _preserve_mozc_top_if_uncertain(
        scored, "神社の", "", evidence
    )
    assert [item[2] for item in protected] == ["c0", "c1", "c2"]


def test_numeric_surface_tie_allows_normalized_ai_candidate():
    # 15日 and 十五日 express the same numeric family.  A near tie between
    # those spellings should not send a strong normalized candidate back to
    # an unrelated Mozc top result.
    scored = [(1.0, 2, "c1"), (0.0, 0, "c0"), (0.98, 1, "c2")]
    evidence = {"c1": 1.0, "c0": 0.55, "c2": 0.98}
    texts = {"c1": "15日", "c0": "中五日", "c2": "十五日"}
    protected = _preserve_mozc_top_if_uncertain(
        scored, "提出", "までに出す", evidence, texts, "じゅうごにち"
    )
    assert protected == scored


def test_rank_prior_is_real_but_sublinear():
    # Rank still matters, but rank 20 is no longer hit by a 1.9-point linear
    # penalty when prior_w=0.1. This lets a clear neural score difference win.
    rank2 = _rank_prior_penalty(1, 0.1)
    rank10 = _rank_prior_penalty(9, 0.1)
    rank20 = _rank_prior_penalty(19, 0.1)
    assert 0.0 < rank2 < rank10 < rank20 < 0.35
