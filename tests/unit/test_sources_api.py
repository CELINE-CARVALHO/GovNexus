from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.v1 import sources as sources_api
from backend.database.base import Base
from backend.database.connection import get_db
from backend.database.models.language import Language
from backend.database.models.source import Source
from backend.main import app


SOURCE_ADMIN_KEY = "test-source-admin-key"


@pytest.fixture
def source_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    previous_key = sources_api.settings.SOURCE_ADMIN_API_KEY

    def override_get_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    sources_api.settings.SOURCE_ADMIN_API_KEY = SOURCE_ADMIN_KEY
    source_id = uuid4()
    with test_session() as db:
        db.add(Language(code="en", english_name="English", native_name="English", is_active=True))
        db.add(
            Source(
                id=source_id,
                url="https://example.gov.in/source",
                url_hash="a" * 64,
                publisher_name="Example Government Publisher",
                source_type="government_portal",
                authority_status="unverified",
                language_code="en",
                is_active=False,
            )
        )
        db.commit()

    try:
        with TestClient(app) as client:
            yield client, test_session, source_id
    finally:
        sources_api.settings.SOURCE_ADMIN_API_KEY = previous_key
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def admin_headers(key=SOURCE_ADMIN_KEY):
    return {"X-Source-Admin-Key": key}


def test_update_source_accepts_valid_uuid(source_client):
    client, session_factory, source_id = source_client

    response = client.patch(
        f"/api/v1/sources/{source_id}",
        headers=admin_headers(),
        json={"authority_status": "official"},
    )

    assert response.status_code == 200
    with session_factory() as db:
        source = db.get(Source, source_id)
        assert source.authority_status == "official"
        assert source.is_active is False


def test_source_activation_accepts_valid_uuid(source_client):
    client, session_factory, source_id = source_client

    activated = client.patch(
        f"/api/v1/sources/{source_id}/activation?is_active=true",
        headers=admin_headers(),
    )
    deactivated = client.patch(
        f"/api/v1/sources/{source_id}/activation?is_active=false",
        headers=admin_headers(),
    )

    assert activated.status_code == 200
    assert activated.json()["source"]["is_active"] is True
    assert deactivated.status_code == 200
    assert deactivated.json()["source"]["is_active"] is False
    with session_factory() as db:
        assert db.get(Source, source_id).is_active is False


@pytest.mark.parametrize("path", [
    "/api/v1/sources/not-a-uuid",
    "/api/v1/sources/not-a-uuid/activation?is_active=true",
])
def test_invalid_source_uuid_returns_422(source_client, path):
    client, _, _ = source_client

    response = client.patch(path, headers=admin_headers(), json={})

    assert response.status_code == 422


def test_source_admin_key_is_required_and_exact(source_client):
    client, _, source_id = source_client
    path = f"/api/v1/sources/{source_id}"

    assert client.patch(path, json={}).status_code == 403
    assert client.patch(path, headers=admin_headers("wrong-key"), json={}).status_code == 403
    assert client.patch(path, headers=admin_headers(), json={}).status_code == 200
