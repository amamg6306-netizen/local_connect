"""One-time, explicit admin account bootstrap for the Flask application.

Required environment variables:
  ADMIN_BOOTSTRAP_EMAIL
  ADMIN_BOOTSTRAP_PASSWORD
  ADMIN_BOOTSTRAP_CONFIRM=CREATE_ADMIN

Optional:
  ADMIN_BOOTSTRAP_NAME (defaults to "Site Administrator")

This script only CREATES a new account. It intentionally refuses to modify an
existing account. Run it once in a trusted environment connected to the intended
database; do not add it to every web-service startup.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    email = (os.getenv("ADMIN_BOOTSTRAP_EMAIL") or "").strip().lower()
    password = os.getenv("ADMIN_BOOTSTRAP_PASSWORD") or ""
    name = (os.getenv("ADMIN_BOOTSTRAP_NAME") or "Site Administrator").strip()

    if os.getenv("ADMIN_BOOTSTRAP_CONFIRM") != "CREATE_ADMIN":
        print(
            "Refusing to run: set ADMIN_BOOTSTRAP_CONFIRM=CREATE_ADMIN "
            "for a one-time execution.",
            file=sys.stderr,
        )
        return 2

    if (
        not email
        or len(email) > 190
        or "@" not in email
        or "." not in email.rsplit("@", 1)[-1]
    ):
        print(
            "Refusing to run: ADMIN_BOOTSTRAP_EMAIL must be a valid email address.",
            file=sys.stderr,
        )
        return 2

    if not name or len(name) > 120:
        print(
            "Refusing to run: ADMIN_BOOTSTRAP_NAME must be 1-120 characters.",
            file=sys.stderr,
        )
        return 2

    if not password:
        print(
            "Refusing to run: ADMIN_BOOTSTRAP_PASSWORD is required.",
            file=sys.stderr,
        )
        return 2

    # Import after validating the explicit execution gate and inputs.
    try:
        from sqlalchemy import select
        from app import create_app
        from extensions import db
        from models.core import User
        from services.auth_service import password_hash, validate_new_password
    except Exception as exc:
        print(
            f"Cannot load application modules ({type(exc).__name__}). "
            "Check the project's Python environment.",
            file=sys.stderr,
        )
        return 1

    try:
        validate_new_password(password)
    except ValueError as exc:
        print(f"Refusing to run: {exc}", file=sys.stderr)
        return 2

    try:
        app = create_app()
    except Exception as exc:
        print(
            f"Cannot initialize Flask application ({type(exc).__name__}).",
            file=sys.stderr,
        )
        return 1

    with app.app_context():
        try:
            existing = db.session.scalar(
                select(User.id).where(User.email == email).limit(1)
            )
            if existing is not None:
                print(
                    "No account created: this email already exists. "
                    "No existing account was changed.",
                    file=sys.stderr,
                )
                return 3

            user = User(
                name=name,
                email=email,
                password_hash=password_hash(password),
                role="admin",
                status="active",
                email_verified_at=datetime.now(),
            )
            db.session.add(user)
            db.session.commit()
            print(
                "Admin account created successfully. "
                "Password was stored as a hash."
            )
            print(
                "Next: sign in through the normal login page and complete "
                "the required admin MFA setup."
            )
            return 0
        except Exception as exc:
            db.session.rollback()
            # Do not print connection strings, SQL parameters, or secrets.
            print(
                f"Admin account creation failed ({type(exc).__name__}). "
                "Check database connectivity and schema.",
                file=sys.stderr,
            )
            return 1
        finally:
            db.session.remove()


if __name__ == "__main__":
    raise SystemExit(main())
