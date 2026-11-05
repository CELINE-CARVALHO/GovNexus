from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.core.security import create_access_token, hash_password
from backend.api.v1.chat import ChatRequest, _resolve_conversation
from backend.database.base import Base
from backend.database.connection import get_db
from backend.database.models import (
    Category,
    Department,
    FactVerification,
    Language,
    Service,
    ServiceFactLink,
    ServiceTranslation,
    ServiceVersion,
    Source,
    SourceFact,
    SourceSnapshot,
    User,
)
from backend.database.models.location import Location, LocationTranslation
from backend.database.models.service_details import ServiceJurisdiction
from backend.database.models.administration import AdminUser
from backend.main import app


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with test_session() as db:
        db.add(Language(code="en", english_name="English", native_name="English", is_active=True))
        db.commit()
    with TestClient(app) as test_client:
        yield test_client, test_session
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def register(client, email="citizen@example.com"):
    response = client.post(
        "/api/v1/auth/citizen/register",
        json={
            "email": email,
            "password": "citizen-secure-password",
            "display_name": "Citizen",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def create_published_service(test_session, *, status="published"):
    with test_session() as db:
        department = Department(code=f"dept-{status}", level="national")
        category = Category(code=f"category-{status}")
        db.add_all([department, category])
        db.flush()
        service = Service(
            code=f"service-{status}",
            slug=f"service-{status}",
            department_id=department.id,
            category_id=category.id,
            status="active",
            is_active=True,
        )
        db.add(service)
        db.flush()
        version = ServiceVersion(
            service_id=service.id,
            version_number=1,
            effective_from=date.today() - timedelta(days=1),
            publication_status=status,
        )
        db.add(version)
        db.flush()
        db.add(
            ServiceTranslation(
                service_version_id=version.id,
                language_code="en",
                title=f"{status.title()} service",
                description=f"{status.title()} service description",
                application_url="https://example.gov.in/apply",
            )
        )
        db.commit()
        return service.id


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_citizen_registration_duplicate_login_and_logout(client):
    test_client, _ = client
    token = register(test_client)

    duplicate = test_client.post(
        "/api/v1/auth/citizen/register",
        json={
            "email": "CITIZEN@example.com",
            "password": "citizen-secure-password",
            "display_name": "Another",
        },
    )
    assert duplicate.status_code == 409

    login = test_client.post(
        "/api/v1/auth/citizen/login",
        json={"email": "citizen@example.com", "password": "citizen-secure-password"},
    )
    assert login.status_code == 200
    assert "password_hash" not in login.json()["citizen"]

    assert test_client.get("/api/v1/users/me", headers=bearer(token)).status_code == 200
    assert test_client.post(
        "/api/v1/auth/citizen/logout",
        headers=bearer(token),
    ).status_code == 200
    assert test_client.get("/api/v1/users/me", headers=bearer(token)).status_code == 401


def test_citizen_and_admin_http_only_cookie_sessions(client):
    test_client, test_session = client
    registration = test_client.post(
        "/api/v1/auth/citizen/register",
        json={
            "email": "cookie-citizen@example.com",
            "password": "citizen-secure-password",
            "display_name": "Cookie Citizen",
        },
    )
    assert registration.status_code == 201
    citizen_cookie = registration.headers["set-cookie"].lower()
    assert "httponly" in citizen_cookie
    assert "path=/api/v1" in citizen_cookie
    assert "samesite=lax" in citizen_cookie
    assert registration.headers["cache-control"] == "no-store"
    assert test_client.get("/api/v1/users/me").status_code == 200

    citizen_logout = test_client.post("/api/v1/auth/citizen/logout")
    assert citizen_logout.status_code == 200
    assert "max-age=0" in citizen_logout.headers["set-cookie"].lower()
    assert test_client.get("/api/v1/users/me").status_code == 401

    with test_session() as db:
        db.add(
            AdminUser(
                email="cookie-admin@example.com",
                password_hash=hash_password("admin-secure-password"),
                full_name="Cookie Admin",
                role="reviewer",
                is_active=True,
            )
        )
        db.commit()

    admin_login = test_client.post(
        "/api/v1/auth/admin/login",
        json={"email": "cookie-admin@example.com", "password": "admin-secure-password"},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    admin_cookie = admin_login.headers["set-cookie"].lower()
    assert "httponly" in admin_cookie
    assert "samesite=lax" in admin_cookie
    assert admin_login.headers["cache-control"] == "no-store"
    assert test_client.get("/api/v1/admin/services?active_only=false").status_code == 200
    assert test_client.get("/api/v1/users/me").status_code == 401

    admin_logout = test_client.post("/api/v1/auth/admin/logout")
    assert admin_logout.status_code == 200
    assert "max-age=0" in admin_logout.headers["set-cookie"].lower()
    assert test_client.get("/api/v1/admin/services?active_only=false").status_code == 401
    assert test_client.get(
        "/api/v1/admin/services?active_only=false",
        headers=bearer(admin_token),
    ).status_code == 401


def test_citizen_and_admin_tokens_are_separate(client):
    test_client, _ = client
    admin_token = create_access_token("c0d0f863-5c1f-4bb7-917e-47e7acfc7922")
    assert test_client.get("/api/v1/users/me", headers=bearer(admin_token)).status_code == 401
    assert test_client.get("/api/v1/admin/dashboard").status_code == 401


def test_password_change_invalidates_old_tokens(client):
    test_client, _ = client
    old_token = register(test_client)
    changed = test_client.post(
        "/api/v1/auth/citizen/password",
        headers=bearer(old_token),
        json={
            "current_password": "citizen-secure-password",
            "new_password": "new-citizen-secure-password",
        },
    )
    assert changed.status_code == 200
    assert test_client.get("/api/v1/users/me", headers=bearer(old_token)).status_code == 401
    assert test_client.get(
        "/api/v1/users/me",
        headers=bearer(changed.json()["access_token"]),
    ).status_code == 200


def test_accessibility_preferences_are_validated_and_persisted(client):
    test_client, _ = client
    token = register(test_client, "accessibility@example.com")
    headers = bearer(token)
    preferences = {
        "font_size": "extra_large",
        "text_scale_percent": 175,
        "high_contrast": True,
        "increased_spacing": True,
        "large_buttons": True,
        "simple_mode": True,
        "read_aloud": True,
        "reduced_motion": True,
    }

    updated = test_client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"accessibility_preferences": preferences},
    )
    assert updated.status_code == 200
    assert updated.json()["accessibility_preferences"] == preferences

    retrieved = test_client.get("/api/v1/users/me", headers=headers)
    assert retrieved.json()["accessibility_preferences"] == preferences

    invalid = test_client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={
            "accessibility_preferences": {
                **preferences,
                "text_scale_percent": 201,
            }
        },
    )
    assert invalid.status_code == 422


def test_state_filter_accepts_union_territory_and_returns_scoped_services(client):
    test_client, test_session = client
    location_id = None
    with test_session() as db:
        territory = Location(
            location_type="union_territory",
            code="IN-LA",
            is_active=True,
        )
        db.add(territory)
        db.flush()
        db.add(
            LocationTranslation(
                location_id=territory.id,
                language_code="en",
                name="Ladakh",
            )
        )
        db.commit()
        location_id = territory.id

    service_id = create_published_service(test_session)
    with test_session() as db:
        version = db.query(ServiceVersion).filter(
            ServiceVersion.service_id == service_id
        ).one()
        db.add(
            ServiceJurisdiction(
                service_version_id=version.id,
                location_id=location_id,
            )
        )
        db.commit()

    locations = test_client.get(
        "/api/v1/locations?location_type=state%2Cunion_territory&language=en"
    )
    assert locations.status_code == 200
    assert locations.json()["items"][0]["location_type"] == "union_territory"

    services = test_client.get(
        f"/api/v1/services?state_id={location_id}"
    )
    assert services.status_code == 200
    assert [item["id"] for item in services.json()["items"]] == [str(service_id)]

    profile_token = register(test_client, "territory-profile@example.com")
    updated = test_client.patch(
        "/api/v1/users/me",
        headers=bearer(profile_token),
        json={"state_id": str(location_id)},
    )
    assert updated.status_code == 200
    assert updated.json()["state_id"] == str(location_id)


def test_profile_preferences_and_conversation_ownership(client):
    test_client, _ = client
    first_token = register(test_client, "first@example.com")
    second_token = register(test_client, "second@example.com")

    profile = test_client.patch(
        "/api/v1/users/me",
        headers=bearer(first_token),
        json={
            "display_name": "Updated citizen",
            "notification_preferences": {"email": True, "sms": False},
        },
    )
    assert profile.status_code == 200
    assert profile.json()["display_name"] == "Updated citizen"
    assert profile.json()["notification_preferences"]["email"] is True

    conversation = test_client.post(
        "/api/v1/users/me/conversations",
        headers=bearer(first_token),
        json={"title": "My question"},
    )
    assert conversation.status_code == 201
    conversation_id = conversation.json()["id"]
    assert test_client.get(
        f"/api/v1/users/me/conversations/{conversation_id}",
        headers=bearer(second_token),
    ).status_code == 404


def test_citizen_conversation_can_continue_through_chat_resolver(client):
    test_client, test_session = client
    token = register(test_client)
    conversation = test_client.post(
        "/api/v1/users/me/conversations",
        headers=bearer(token),
        json={"title": "Continue me"},
    ).json()

    with test_session() as db:
        user = db.query(User).filter(User.email == "citizen@example.com").one()
        resolved, guest_token, _ = _resolve_conversation(
            db,
            ChatRequest(
                message="Continue this conversation",
                conversation_id=conversation["id"],
            ),
            user,
        )
        assert str(resolved.id) == conversation["id"]
        assert guest_token is None


def test_saved_services_and_application_records_are_private(client):
    test_client, test_session = client
    service_id = create_published_service(test_session)
    first_token = register(test_client, "first@example.com")
    second_token = register(test_client, "second@example.com")

    saved = test_client.put(
        f"/api/v1/users/me/saved-services/{service_id}",
        headers=bearer(first_token),
    )
    assert saved.status_code == 200
    assert saved.json()["translation_available"] is True
    assert test_client.get(
        "/api/v1/users/me/saved-services",
        headers=bearer(second_token),
    ).json()["total"] == 0

    application = test_client.post(
        "/api/v1/users/me/applications",
        headers=bearer(first_token),
        json={
            "service_id": str(service_id),
            "status": "submitted_externally",
            "reference_number": "citizen-entered-ref",
        },
    )
    assert application.status_code == 201
    application_data = application.json()
    assert application_data["status_source"] == "citizen_recorded"
    assert application_data["status_history"][0]["status_source"] == "citizen_recorded"
    assert test_client.get(
        f"/api/v1/users/me/applications/{application_data['id']}",
        headers=bearer(second_token),
    ).status_code == 404


def test_catalogue_exposes_only_current_published_services(client):
    test_client, test_session = client
    published_id = create_published_service(test_session)
    create_published_service(test_session, status="draft")

    response = test_client.get("/api/v1/services?search=Published")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == str(published_id)
    assert items[0]["translation_available"] is True

    assert test_client.get("/api/v1/services/suggestions?q=Published").status_code == 200
    assert test_client.get("/api/v1/services?page=0").status_code == 422


def test_service_details_only_return_approved_linked_evidence(client):
    test_client, test_session = client
    service_id = create_published_service(test_session)
    with test_session() as db:
        service = db.query(Service).filter(Service.id == service_id).one()
        version = db.query(ServiceVersion).filter(
            ServiceVersion.service_id == service_id
        ).one()
        source = Source(
            url="https://example.gov.in/scheme",
            url_hash="a" * 64,
            publisher_name="Example Department",
            source_type="government",
            authority_status="verified",
            is_active=True,
        )
        db.add(source)
        db.flush()
        snapshot = SourceSnapshot(
            source_id=source.id,
            content_hash="b" * 64,
            storage_uri="snapshots/example.txt",
            extraction_status="completed",
        )
        db.add(snapshot)
        db.flush()
        approved = SourceFact(
            source_snapshot_id=snapshot.id,
            fact_key="eligibility:verified",
            fact_type="eligibility",
            value_data={"text": "Applicants must be residents."},
            evidence_locator={"quoted_text": "Applicants must be residents."},
            extraction_status="verified",
        )
        pending = SourceFact(
            source_snapshot_id=snapshot.id,
            fact_key="eligibility:pending",
            fact_type="eligibility",
            value_data={"text": "Unsupported pending condition."},
            evidence_locator={"quoted_text": "Unsupported pending condition."},
            extraction_status="pending_review",
        )
        db.add_all([approved, pending])
        db.flush()
        db.add_all(
            [
                FactVerification(
                    source_fact_id=approved.id,
                    verification_status="approved",
                    decision="approved",
                ),
                ServiceFactLink(
                    service_version_id=version.id,
                    source_fact_id=approved.id,
                    relationship_type="eligibility",
                ),
                ServiceFactLink(
                    service_version_id=version.id,
                    source_fact_id=pending.id,
                    relationship_type="eligibility",
                ),
            ]
        )
        db.commit()

    response = test_client.get(f"/api/v1/services/{service_id}/details")
    assert response.status_code == 200
    details = response.json()
    assert len(details["evidence"]["items"]) == 1
    assert details["evidence"]["items"][0]["fact_key"] == "eligibility:verified"
    assert details["eligibility"] == []


def test_catalogue_resolves_locale_to_available_language_translation(client):
    test_client, test_session = client
    service_id = create_published_service(test_session)
    with test_session() as db:
        db.add(Language(code="hi", english_name="Hindi", native_name="हिन्दी", is_active=True))
        version = db.query(ServiceVersion).filter(
            ServiceVersion.service_id == service_id
        ).one()
        db.add(
            ServiceTranslation(
                service_version_id=version.id,
                language_code="hi",
                title="हिंदी सेवा",
                description="हिंदी विवरण",
            )
        )
        db.commit()

    response = test_client.get(f"/api/v1/services/{service_id}?language=hi-IN")
    assert response.status_code == 200
    assert response.json()["title"] == "हिंदी सेवा"
    assert response.json()["translation_available"] is True


def test_admin_dashboard_requires_and_accepts_admin_auth(client):
    test_client, test_session = client
    with test_session() as db:
        admin = AdminUser(
            email="admin@example.com",
            password_hash="not-used-in-this-test",
            full_name="Admin",
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        admin_id = str(admin.id)
    token = create_access_token(admin_id)

    response = test_client.get(
        "/api/v1/admin/dashboard",
        headers=bearer(token),
    )
    assert response.status_code == 200
    assert response.json()["citizens"]["total"] == 0


def test_admin_can_create_catalogue_entities_without_publishing_them(client):
    test_client, test_session = client
    with test_session() as db:
        admin = AdminUser(
            email="catalogue-admin@example.com",
            password_hash="not-used-in-this-test",
            full_name="Catalogue Admin",
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        token = create_access_token(str(admin.id))
    headers = bearer(token)

    department = test_client.post(
        "/api/v1/admin/departments",
        headers=headers,
        json={
            "code": "TEST-DEPT",
            "level": "national",
            "translations": [{"language_code": "en", "name": "Test department"}],
        },
    )
    assert department.status_code == 201
    category = test_client.post(
        "/api/v1/admin/categories",
        headers=headers,
        json={
            "code": "TEST-CAT",
            "translations": [{"language_code": "en", "name": "Test category"}],
        },
    )
    assert category.status_code == 201

    service = test_client.post(
        "/api/v1/services",
        headers=headers,
        json={
            "code": "test-service",
            "slug": "test-service",
            "department_id": department.json()["id"],
            "category_id": category.json()["id"],
        },
    )
    assert service.status_code == 201
    admin_list = test_client.get(
        "/api/v1/admin/services?limit=1&offset=0",
        headers=headers,
    )
    assert admin_list.status_code == 200
    assert admin_list.json()["total"] == 1
    assert admin_list.json()["limit"] == 1
    version = test_client.post(
        f"/api/v1/services/{service.json()['id']}/versions",
        headers=headers,
        json={"effective_from": date.today().isoformat(), "change_summary": "Initial version"},
    )
    assert version.status_code == 201
    translation = test_client.put(
        f"/api/v1/services/{service.json()['id']}/versions/"
        f"{version.json()['version']['id']}/translations",
        headers=headers,
        json={
            "language_code": "en",
            "title": "New service",
            "description": "Description",
            "application_url": "https://example.gov.in/apply",
        },
    )
    assert translation.status_code == 200
    assert test_client.get("/api/v1/services").json()["pagination"]["total"] == 0
