from backend.database.connection import SessionLocal
from backend.database.models.language import Language
from backend.database.models.category import Category, CategoryTranslation


LANGUAGES = [
    ("en", "English", "English", True),
    ("as", "Assamese", "অসমীয়া", False),
    ("bn", "Bengali", "বাংলা", False),
    ("brx", "Bodo", "बड़ो", False),
    ("doi", "Dogri", "डोगरी", False),
    ("gu", "Gujarati", "ગુજરાતી", False),
    ("hi", "Hindi", "हिन्दी", False),
    ("kn", "Kannada", "ಕನ್ನಡ", False),
    ("ks", "Kashmiri", "कॉशुर", False),
    ("kok", "Konkani", "कोंकणी", False),
    ("mai", "Maithili", "मैथिली", False),
    ("ml", "Malayalam", "മലയാളം", False),
    ("mni", "Manipuri", "মৈতৈলোন্", False),
    ("mr", "Marathi", "मराठी", False),
    ("ne", "Nepali", "नेपाली", False),
    ("or", "Odia", "ଓଡ଼ିଆ", False),
    ("pa", "Punjabi", "ਪੰਜਾਬੀ", False),
    ("sa", "Sanskrit", "संस्कृतम्", False),
    ("sat", "Santali", "ᱥᱟᱱᱛᱟᱲᱤ", False),
    ("sd", "Sindhi", "سنڌي", False),
    ("ta", "Tamil", "தமிழ்", False),
    ("te", "Telugu", "తెలుగు", False),
    ("ur", "Urdu", "اردو", False),
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
