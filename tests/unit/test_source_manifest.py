import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.database.base import Base
from backend.database.models.language import Language
from backend.database.models.source import Source
from backend.scripts.import_official_source_manifest import (
    _official_hostname,
    register_manifest_sources,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = Session(engine)
    session.add(
        Language(
            code="en",
            english_name="English",
            native_name="English",
            is_active=True,
        )
    )
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_official_domain_check_rejects_non_government_hosts():
    assert _official_hostname("https://scholarships.gov.in/") == "scholarships.gov.in"
    assert _official_hostname("https://services.nic.in/") == "services.nic.in"
    with pytest.raises(ValueError, match="Only .gov.in and .nic.in"):
        _official_hostname("https://example.com/")
    with pytest.raises(ValueError, match="non-standard HTTPS ports"):
        _official_hostname("https://myscheme.gov.in:8443/")


def test_manifest_registers_only_inactive_unverified_sources_and_is_idempotent(db):
    row = {
        "url": "https://myscheme.gov.in/",
        "publisher_name": "myScheme",
    }

    first = register_manifest_sources(db, [row], url_validator=lambda url: url)
    db.commit()
    second = register_manifest_sources(db, [row], url_validator=lambda url: url)

    source = db.scalar(select(Source))
    assert first["created_unverified_inactive"] == 1
    assert second["created_unverified_inactive"] == 0
    assert second["already_registered"] == 1
    assert source is not None
    assert source.authority_status == "unverified"
    assert source.is_active is False
    assert source.url == row["url"]


def test_manifest_rejects_unknown_language_and_external_hosts(db):
    with pytest.raises(ValueError, match="Language"):
        register_manifest_sources(
            db,
            [{
                "url": "https://scholarships.gov.in/",
                "publisher_name": "National Scholarship Portal",
                "language_code": "xx",
            }],
            url_validator=lambda url: url,
        )

    with pytest.raises(ValueError, match="Only .gov.in and .nic.in"):
        register_manifest_sources(
            db,
            [{"url": "https://example.com/", "publisher_name": "Example"}],
            url_validator=lambda url: url,
        )
