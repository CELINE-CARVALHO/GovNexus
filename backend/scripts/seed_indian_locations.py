from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.connection import SessionLocal
from backend.database.models.language import Language
from backend.database.models.location import Location, LocationTranslation
from backend.master_data import EIGHTH_SCHEDULE_LANGUAGES, INDIAN_SUBDIVISIONS


def seed_indian_locations(db: Session) -> dict[str, int]:
    languages_added = 0
    locations_added = 0
    translations_added = 0

    for code, english_name, native_name in EIGHTH_SCHEDULE_LANGUAGES:
        language = db.get(Language, code)
        if language is None:
            language = Language(
                code=code,
                english_name=english_name,
                native_name=native_name,
                is_active=True,
            )
            db.add(language)
            languages_added += 1
        else:
            language.english_name = english_name
            language.native_name = native_name
            language.is_active = True

    english = db.get(Language, "en")
    if english is None:
        db.add(
            Language(
                code="en",
                english_name="English",
                native_name="English",
                is_active=True,
            )
        )
        languages_added += 1
        db.flush()

    for code, location_type, name in INDIAN_SUBDIVISIONS:
        location = db.scalar(
            select(Location).where(
                Location.parent_id.is_(None),
                Location.code == code,
            )
        )
        if location is None:
            location = Location(
                location_type=location_type,
                code=code,
                is_active=True,
            )
            db.add(location)
            db.flush()
            locations_added += 1
        else:
            location.location_type = location_type
            location.is_active = True

        translation = db.scalar(
            select(LocationTranslation).where(
                LocationTranslation.location_id == location.id,
                LocationTranslation.language_code == "en",
            )
        )
        if translation is None:
            db.add(
                LocationTranslation(
                    location_id=location.id,
                    language_code="en",
                    name=name,
                )
            )
            translations_added += 1
        elif translation.name != name:
            translation.name = name

    db.flush()
    return {
        "languages_added": languages_added,
        "locations_added": locations_added,
        "translations_added": translations_added,
        "languages_enabled": len(EIGHTH_SCHEDULE_LANGUAGES),
        "states": sum(item[1] == "state" for item in INDIAN_SUBDIVISIONS),
        "union_territories": sum(
            item[1] == "union_territory" for item in INDIAN_SUBDIVISIONS
        ),
    }


def main() -> None:
    db = SessionLocal()
    try:
        result = seed_indian_locations(db)
        db.commit()
        print("Indian language and location master data seeded.")
        for key, value in result.items():
            print(f"{key}: {value}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
