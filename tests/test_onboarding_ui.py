import json

import onboarding_ui


def test_onboarding_is_required_when_state_is_missing(tmp_path):
    assert onboarding_ui.should_show_onboarding(tmp_path / "missing.json") is True


def test_mark_seen_suppresses_current_version_guide(tmp_path):
    state_path = tmp_path / "nested" / "onboarding.json"
    onboarding_ui.mark_onboarding_seen(state_path)

    assert onboarding_ui.should_show_onboarding(state_path) is False
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["completed_for_version"] == onboarding_ui.PRODUCT_VERSION
    assert state["guide"] == "tray-ai-toggle-v1"


def test_old_version_shows_guide_again(tmp_path):
    state_path = tmp_path / "onboarding.json"
    state_path.write_text(
        json.dumps({"completed_for_version": "0.9.0"}), encoding="utf-8"
    )

    assert onboarding_ui.should_show_onboarding(state_path) is True
