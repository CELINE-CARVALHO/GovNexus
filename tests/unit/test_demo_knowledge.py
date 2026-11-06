from backend.services.demo_knowledge import demo_items, demo_source


def test_demo_catalogue_has_official_provenance_and_is_local():
    items = demo_items()
    assert len(items) >= 10
    assert all(item["demo"] for item in demo_items("scholarships"))
    assert all(item["official_url"].startswith("https://") for item in items)
    assert all(demo_source(item)["checked_on"] == "2026-11-06" for item in items)


def test_demo_retrieval_prefers_the_relevant_service():
    items = demo_items("What scholarships are available for college students?")
    assert [item["title"] for item in items] == ["National Scholarship Portal"]


def test_demo_retrieval_handles_domain_aliases_without_inventing_details():
    assert [item["title"] for item in demo_items("government schemes for farmers")] == ["PM-KISAN"]
    assert demo_items("income certificate in Karnataka")[0]["title"] == "Karnataka Income Certificate"
    assert demo_items("income certificate in Karnataka")[0]["details"] == {
        "eligibility": [], "benefits": [], "documents": [], "steps": []
    }


def test_demo_evidence_is_explicitly_marked_for_local_use():
    item = demo_items("Aadhaar address update")[0]
    assert item["demo"] is True
    assert "not production" in demo_source(item)["authority_status"]
