from getpass import getpass

from sqlalchemy import select

from backend.database.connection import get_db
from backend.database.models.administration import AdminUser
from backend.core.security import hash_password


def main():
    email = input("Admin email: ").strip().lower()
    full_name = input("Admin full name: ").strip()
    role = input("Admin role [admin]: ").strip() or "admin"

    password = getpass("Password (minimum 12 characters): ")
    confirm = getpass("Confirm password: ")

    if password != confirm:
        print("Passwords do not match.")
        return

    try:
        password_hash = hash_password(password)
    except ValueError as exc:
        print(exc)
        return

    db_generator = get_db()
    db = next(db_generator)

    try:
        existing = db.scalar(
            select(AdminUser).where(AdminUser.email == email)
        )

        if existing:
            print("An admin account with this email already exists.")
            return

        admin = AdminUser(
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            role=role,
            is_active=True,
        )

        db.add(admin)
        db.commit()

        print(f"Admin account created successfully: {email}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        db_generator.close()


if __name__ == "__main__":
    main()
