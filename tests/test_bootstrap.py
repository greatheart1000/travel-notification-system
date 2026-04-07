from app.main import bootstrap_demo


def test_bootstrap_demo_outputs_expected_flags() -> None:
    result = bootstrap_demo()
    assert result["dispatch"]["ok"] is True
    assert result["complaint_escalated"] is True
    assert result["survey_follow_up"] is True
