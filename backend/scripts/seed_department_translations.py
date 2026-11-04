
from backend.database.connection import SessionLocal
from backend.database.models.department import (
    Department,
    DepartmentTranslation,
)

DEPARTMENTS = {
    "uidai": {
        "name": "Unique Identification Authority of India",
        "description": "Authority responsible for Aadhaar services.",
    },
    "income-tax": {
        "name": "Income Tax Department",
        "description": "Government department responsible for income tax and PAN-related services.",
    },
    "national-scholarship-portal": {
        "name": "National Scholarship Portal",
        "description": "Government portal for scholarship information and applications.",
    },
}


def seed():
    db = SessionLocal()

    try:
        created = 0
        updated = 0

        for code, data in DEPARTMENTS.items():
            department = (
                db.query(Department)
                .filter(Department.code == code)
                .first()
            )

            if not department:
                print(f"Department not found: {code}")
                continue

            translation = (
                db.query(DepartmentTranslation)
                .filter(
                    DepartmentTranslation.department_id == department.id,
                    DepartmentTranslation.language_code == "en",
                )
                .first()
            )

            if translation:
                translation.name = data["name"]
                translation.description = data["description"]
                updated += 1
            else:
                translation = DepartmentTranslation(
                    department_id=department.id,
                    language_code="en",
                    name=data["name"],
                    description=data["description"],
                )
                db.add(translation)
                created += 1

        db.commit()

        print("Department translations completed.")
        print(f"Created: {created}")
        print(f"Updated: {updated}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed()

