import pytest

from backend.api.v1.demo import get_demo_service
from backend.services.application_guidance import (
    assess_eligibility,
    build_guidance_packet,
    question_for_retrieval,
    reject_sensitive_answers,
)


def test_follow_up_keeps_the_active_scheme_and_a_new_topic_does_not():
    history = ["Tell me about PM-KISAN."]
    follow_up = question_for_retrieval("Am I eligible?", history)
    assert "PM-KISAN" in follow_up or "Kisan" in follow_up
    new_topic = question_for_retrieval(
        "What scholarships are available for college students?",
        history,
    )
    assert not new_topic.startswith("PM-KISAN")
    assert "scholarship" in new_topic.lower()
    for follow in (
        "What documents do I need?",
        "Where do I get that?",
        "What if I don't have it?",
        "Explain the second condition.",
        "Can you explain that in Kannada?",
    ):
        resolved = question_for_retrieval(follow, history, pinned_title="PM-KISAN")
        assert "PM-KISAN" in resolved or "Kisan" in resolved


def test_eligibility_assessment_keeps_three_distinct_statuses():
    conditions = [
        {"prompt": "Landholding family?", "expected": "yes"},
        {"prompt": "Institutional holder?", "expected": "no"},
        {"prompt": "Excluded category?", "expected": "no"},
    ]
    result = assess_eligibility(conditions, {"0": "yes", "1": "yes", "2": "unknown"})
    assert [item["status"] for item in result] == [
        "appears_satisfied",
        "not_satisfied",
        "cannot_determine",
    ]


def test_pm_kisan_guidance_uses_only_stored_source_material():
    packet = build_guidance_packet(get_demo_service("demo-pm-kisan"))
    assert packet["title"] == "PM-KISAN"
    assert packet["official_application_url"] == "https://pmkisan.gov.in/"
    assert packet["submitted_by_govnexus"] is False
    assert packet["approval_guaranteed"] is False
    assert len(packet["eligibility"]) == 3
    assert packet["documents"] == []
    assert packet["document_guidance"]["status"] == "incomplete"
    assert packet["document_guidance"]["commonly_useful"]
    assert "mandatory" not in {
        item["requirement"] for item in packet["document_guidance"]["commonly_useful"]
    }
    assert "Aadhaar may be requested" in packet["document_guidance"]["aadhaar_note"]
    assert packet["benefits"]
    assert "landholding" in packet["description"].lower()
    assert packet["jurisdiction"] == "Central Government"
    assert packet["form_fields"] == []
    assert any(stage["id"] == "documents" and stage["available"] is True for stage in packet["stages"])
    assert len(packet["stages"]) == 8
    assert "pending human verification" in packet["verification_label"]


def test_sensitive_answers_are_rejected_and_sensitive_fields_stay_on_the_portal():
    with pytest.raises(ValueError):
        reject_sensitive_answers({"note": "my aadhaar is 1234"})
    packet = build_guidance_packet({
        "demo": True,
        "service": {"id": "demo-pm-kisan", "title": "PM-KISAN", "application_url": "https://pmkisan.gov.in/"},
        "form_fields": [
            {"field_key": "state", "official_label": "State", "required_status": "unknown", "plain_language_explanation": "The state named on the form."},
            {"field_key": "aadhaar", "official_label": "Aadhaar number", "sensitive": True},
        ],
    })
    assert [field["field_key"] for field in packet["form_fields"]] == ["state"]
    assert packet["portal_only_fields"][0]["instruction"].startswith("Complete securely")
    assert packet["official_application_url"] == "https://pmkisan.gov.in/"
