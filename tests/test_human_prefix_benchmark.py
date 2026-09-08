from scripts.human_prefix_benchmark_cases import CASES


def test_human_prefix_benchmark_is_paired_and_prefix_only():
    assert len(CASES) == 210
    assert sum(case.form == "対象語のみ" for case in CASES) == 105
    assert sum(case.form == "助詞・活用込み" for case in CASES) == 105
    assert all(case.prefix for case in CASES)
    assert all(not case.suffix for case in CASES)


def test_expected_is_always_an_acceptable_answer():
    assert all(case.expected in case.acceptable for case in CASES)


def test_semantic_homophones_are_not_accepted_as_spelling_variants():
    cases = {case.label: case for case in CASES}
    assert "花" not in cases["顔の鼻・単語"].acceptable
    assert "決済" not in cases["稟議決裁・単語"].acceptable
    assert "保証" not in cases["損害補償・単語"].acceptable
