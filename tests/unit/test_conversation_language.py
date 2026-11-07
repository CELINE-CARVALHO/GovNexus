from backend.api.v1.chat import validate_generated_answer
from backend.services.application_guidance import question_for_retrieval
from backend.services.conversation_language import (
    resolve_conversation_language,
    response_language_instruction,
)
from backend.services.document_guidance import AADHAAR_NOTE, build_document_guidance


def test_hindi_and_kannada_messages_keep_their_language_when_the_interface_is_english():
    assert resolve_conversation_language("पीएम किसान के लिए कौन से दस्तावेज चाहिए?", "en") == "hi"
    assert resolve_conversation_language("ಪಿಎಂ ಕಿಸಾನ್ ಬಗ್ಗೆ ಹೇಳಿ", "en-IN") == "kn"
    assert resolve_conversation_language("What documents do I need?", "hi-IN") == "en"


def test_explicit_language_request_overrides_the_message_script():
    assert resolve_conversation_language("Explain that in Kannada", "en") == "kn"
    assert resolve_conversation_language("हिंदी में जवाब दो", "en") == "hi"


def test_detected_speech_language_distinguishes_marathi_from_hindi():
    assert resolve_conversation_language("मला काय कागदपत्रे लागतील?", "en", "mr-IN") == "mr"
    assert resolve_conversation_language("मुझे क्या दस्तावेज़ चाहिए?", "en", "hi-IN") == "hi"


def test_language_instruction_is_explicit_for_both_providers():
    instruction = response_language_instruction("kn")
    assert "Kannada" in instruction
    assert "Do not switch to English" in instruction


def test_indic_follow_up_keeps_scheme_context_and_a_new_topic_does_not():
    history = ["Tell me about PM-KISAN."]
    follow = question_for_retrieval("दस्तावेज क्या चाहिए?", history, pinned_title="PM-KISAN")
    assert "PM-KISAN" in follow
    switched = question_for_retrieval("छात्रवृत्ति चाहिए", history, pinned_title="PM-KISAN")
    assert "scholarship" in switched
    assert not switched.startswith("PM-KISAN")


def test_hindi_sentence_with_danda_can_pass_citation_validation():
    answer = "पीएम-किसान भूमिधारक किसान परिवारों के लिए है। [S1]"
    assert validate_generated_answer(answer, {"S1"}, set())


def test_confirmed_aadhaar_stays_mandatory_only_when_the_source_says_so():
    confirmed = build_document_guidance(
        [{
            "name": "Aadhaar",
            "why": "The scheme guideline lists Aadhaar.",
            "is_mandatory": True,
            "source_url": "https://example.gov.in/scheme",
            "alternatives": ["Other accepted identity proof"],
        }],
        category="Agriculture",
        title="PM-KISAN",
    )
    assert confirmed["status"] == "confirmed"
    assert confirmed["confirmed"][0]["requirement"] == "mandatory"
    assert confirmed["confirmed"][0]["alternatives"] == ["Other accepted identity proof"]
    assert confirmed["commonly_useful"] == []


def test_missing_document_list_offers_suggestions_without_calling_them_mandatory():
    guidance = build_document_guidance([], category="Agriculture", title="PM-KISAN")
    assert guidance["status"] == "incomplete"
    assert "could not confirm" in guidance["message"]
    assert guidance["section_title"].startswith("Commonly useful documents")
    assert all(item["requirement"] == "confirm" for item in guidance["commonly_useful"])
    assert guidance["aadhaar_note"] == AADHAAR_NOTE
    assert any("Land or agricultural" in item["name"] for item in guidance["commonly_useful"])
