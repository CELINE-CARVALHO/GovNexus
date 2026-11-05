from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.database.base import Base
from backend.database.models.language import Language
from backend.database.models.location import Location, LocationTranslation
from backend.master_data import EIGHTH_SCHEDULE_LANGUAGES, INDIAN_SUBDIVISIONS
from backend.scripts.seed_indian_locations import seed_indian_locations


def test_indian_master_data_contains_22_languages_and_36_subdivisions():
    assert len(EIGHTH_SCHEDULE_LANGUAGES) == 22
    assert len({code for code, _, _ in EIGHTH_SCHEDULE_LANGUAGES}) == 22
    assert sum(kind == "state" for _, kind, _ in INDIAN_SUBDIVISIONS) == 28
    assert sum(kind == "union_territory" for _, kind, _ in INDIAN_SUBDIVISIONS) == 8
    assert len({code for code, _, _ in INDIAN_SUBDIVISIONS}) == 36


def test_master_data_seeding_is_idempotent_and_enables_scheduled_languages():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as db:
            db.add(
                Language(
                    code="en",
                    english_name="English",
                    native_name="English",
                    is_active=True,
                )
            )
            db.commit()

            first = seed_indian_locations(db)
            db.commit()
            second = seed_indian_locations(db)
            db.commit()

            enabled = db.scalars(
                select(Language).where(Language.code != "en")
            ).all()
            locations = db.scalars(select(Location)).all()
            translations = db.scalars(select(LocationTranslation)).all()

            assert first["languages_added"] == 22
            assert first["locations_added"] == 36
            assert first["translations_added"] == 36
            assert second["languages_added"] == 0
            assert second["locations_added"] == 0
            assert second["translations_added"] == 0
            assert len(enabled) == 22
            assert all(language.is_active for language in enabled)
            assert len(locations) == 36
            assert len(translations) == 36
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
