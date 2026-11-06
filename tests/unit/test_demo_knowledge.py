from backend.services.demo_knowledge import demo_items, demo_source


def test_demo_catalogue_has_official_provenance_and_is_local():
    items = demo_items()
    assert len(items) >= 10
    assert all(item["demo"] for item in demo_items("scholarships"))
    assert all(item["official_url"].startswith("https://") for item in items)
    assert all(demo_source(item)["checked_on"] == item["checked_on"] for item in items)
    assert all("not yet human-verified" in item["verification_label"] for item in items)


def test_state_selection_keeps_central_schemes_and_can_exclude_them():
    karnataka = demo_items(jurisdiction="IN-KA")
    codes = {item["jurisdiction_code"] for item in karnataka}
    assert "IN" in codes
    assert "IN-KA" in codes
    assert "IN-MH" not in codes
    state_only = demo_items(jurisdiction="IN-GA", level="state")
    assert state_only == []
    central = {item["title"] for item in demo_items(level="central")}
    assert "PM-KISAN" in central
    assert "Karnataka Seva Sindhu" not in central


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
