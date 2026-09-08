from ranker.candidate_supplements import (
    merge_supplemental_surfaces,
    numeric_supplement_surfaces,
    prepare_supplemented_segments,
    supplemental_surfaces,
)


def test_numeric_supplements_cover_dates_ordinals_and_counters():
    assert "15日" in numeric_supplement_surfaces("じゅうごにち")
    assert "2026年度" in numeric_supplement_surfaces("にせんにじゅうろくねんど")
    assert "第5位" in numeric_supplement_surfaces("だいごい")
    assert "10個" in numeric_supplement_surfaces("じゅっこ")


def test_abbreviation_and_dictionary_supplements():
    assert "API連携" in supplemental_surfaces("えーぴーあいれんけい")
    assert "API" in supplemental_surfaces("えーぴーあい")
    assert "健診" in supplemental_surfaces("けんしん")


def test_supplements_are_appended_without_reordering_mozc():
    assert merge_supplemental_surfaces("けんしん", ["検診"]) == ["検診", "健診"]


def test_numeric_span_repair_keeps_following_grammar_segment():
    segments = [
        {"key": "じゅう", "candidates": ["中"]},
        {"key": "ご", "candidates": ["五"]},
        {"key": "にちまでに", "candidates": ["日までに"]},
        {"key": "だす", "candidates": ["出す"]},
    ]
    repaired = prepare_supplemented_segments("じゅうごにちまでにだす", segments)
    assert repaired[0]["candidates"][1] == "15日までに"
    assert repaired[-1]["key"] == "だす"
