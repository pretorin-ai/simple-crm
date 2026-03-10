"""CLI script to create the first admin user in production.

Usage:
    python -m app.create_admin

Prompts for email, name, and password interactively.
"""

import getpass
import sys

from sqlalchemy.exc import IntegrityError

from app.auth import get_password_hash
from app.database import Base, SessionLocal, engine
from app.models.models import User
from app.utils import generate_id


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        email = input("Email: ").strip()
        if not email:
            print("Error: email is required.")
            sys.exit(1)

        name = input("Full name: ").strip()
        if not name:
            print("Error: name is required.")
            sys.exit(1)

        password = getpass.getpass("Password: ")
        if len(password) < 8:
            print("Error: password must be at least 8 characters.")
            sys.exit(1)

        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Error: passwords do not match.")
            sys.exit(1)

        user = User(
            id=generate_id(),
            email=email,
            name=name,
            hashed_password=get_password_hash(password),
            role="admin",
            is_active=True,
        )

        db.add(user)
        db.commit()
        print(f"Admin user '{email}' created successfully.")

    except IntegrityError:
        db.rollback()
        print(f"Error: a user with email '{email}' already exists.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
