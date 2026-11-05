from backend.database.connection import SessionLocal
from backend.database.models.language import Language
from backend.database.models.category import Category, CategoryTranslation
from backend.master_data import EIGHTH_SCHEDULE_LANGUAGES


LANGUAGES = [("en", "English", "English", True)] + [
    (*language, True) for language in EIGHTH_SCHEDULE_LANGUAGES
]

CATEGORIES = [
    (
        "identity",
        "Identity & certificates",
        "Government identity documents, certificates, and related correction services.",
    ),
    (
        "education",
        "Education & scholarships",
        "Education-related services, scholarships, and student support.",
    ),
    (
        "welfare",
        "Women & child welfare",
        "Women, children, family welfare, and related public services.",
    ),
    (
        "finance",
        "Pensions & financial aid",
        "Pensions, financial assistance, and eligible welfare support.",
    ),
    (
        "business",
        "Business & employment",
        "Business-related services, employment support, and registrations.",
    ),
    (
        "health",
        "Health & insurance",
        "Public health services, health coverage, and insurance-related support.",
    ),
    (
        "agriculture",
        "Agriculture",
        "Agriculture and farmer support services.",
    ),
    (
        "employment",
        "Employment",
        "Employment and livelihood services.",
    ),
    (
        "skills",
        "Skill development",
        "Skill development and vocational training services.",
    ),
    (
        "housing",
        "Housing",
        "Housing and shelter support services.",
    ),
    (
        "senior-citizens",
        "Senior citizens",
        "Services and support for senior citizens.",
    ),
    (
        "disability",
        "Disability assistance",
        "Accessibility, disability assistance, and related services.",
    ),
]


def seed_languages(db):
    created = 0
    updated = 0

    for code, english_name, native_name, is_active in LANGUAGES:
        language = db.get(Language, code)

        if language is None:
            language = Language(
                code=code,
                english_name=english_name,
                native_name=native_name,
                is_active=is_active,
            )
            db.add(language)
            created += 1
        else:
            language.english_name = english_name
            language.native_name = native_name
            language.is_active = is_active
            updated += 1

    db.flush()
    print(f"Languages: {created} created, {updated} updated.")


def seed_categories(db):
    created = 0
    updated = 0

    for code, name, description in CATEGORIES:
        category = (
            db.query(Category)
            .filter(Category.code == code)
            .first()
        )

        if category is None:
            category = Category(code=code, is_active=True)
            db.add(category)
            db.flush()
            created += 1
        else:
            category.is_active = True
            updated += 1

        translation = (
            db.query(CategoryTranslation)
            .filter(
                CategoryTranslation.category_id == category.id,
                CategoryTranslation.language_code == "en",
            )
            .first()
        )

        if translation is None:
            translation = CategoryTranslation(
                category_id=category.id,
                language_code="en",
                name=name,
                description=description,
            )
            db.add(translation)
        else:
            translation.name = name
            translation.description = description

    db.flush()
    print(f"Categories: {created} created, {updated} updated.")


def main():
    db = SessionLocal()

    try:
        seed_languages(db)
        seed_categories(db)
        db.commit()
        print("Reference data seeded successfully.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
