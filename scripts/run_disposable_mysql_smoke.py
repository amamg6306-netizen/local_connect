"""Destructive schema integration test, ONLY for fresh local MySQL 8 `localjoin_ci`.

This script refuses non-local URLs, unmatched app DB URLs, pre-existing tables,
and missing opt-in. It is never part of web startup or production deploy.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

# Make in-repository imports work when executed as a script from any cwd.
# This changes only the module search path; all database-write safety
# checks below remain mandatory and unchanged.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_OPT_IN = "YES_I_UNDERSTAND_DISPOSABLE"
_DB_NAME = "localjoin_ci"


def preflight_error(env: dict[str, str]) -> str | None:
    url = env.get("LOCALJOIN_DISPOSABLE_DB_URL", "")
    if env.get("LOCALJOIN_ALLOW_DISPOSABLE_DB_WRITES") != _OPT_IN:
        return "explicit opt-in missing"
    if env.get("APP_ENV") != "testing":
        return "APP_ENV must be testing"
    if not url or env.get("DATABASE_URL") != url:
        return "DATABASE_URL must match LOCALJOIN_DISPOSABLE_DB_URL exactly"
    try:
        parsed = urlsplit(url)
        if parsed.scheme != "mysql+pymysql" or parsed.hostname not in {"127.0.0.1", "localhost"}:
            return "only local mysql+pymysql connections are supported"
        if parsed.path != "/" + _DB_NAME or parsed.fragment or not parsed.username:
            return "database must be exactly localjoin_ci with an explicit user"
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            return "invalid port"
    except (ValueError, TypeError):
        return "malformed database URL"
    return None


def main() -> int:
    issue = preflight_error(os.environ)
    if issue:
        print("BLOCKED: disposable MySQL test safety preflight: " + issue, file=sys.stderr)
        return 2

    # Prevent import-time app initialization from writing before we confirm that
    # the connected database is empty and disposable.
    os.environ["AUTO_INIT_SCHEMA"] = "false"
    from sqlalchemy import inspect, select, text
    from sqlalchemy.exc import IntegrityError
    from app import create_app
    from config.settings import TestingConfig
    from extensions import db
    from models.core import Category, User
    from models.marketplace import Service, ServiceRequest, RequestStatusHistory

    class CiConfig(TestingConfig):
        AUTO_INIT_SCHEMA = False
        SQLALCHEMY_DATABASE_URI = os.environ["LOCALJOIN_DISPOSABLE_DB_URL"]
        SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    app = create_app(CiConfig)
    schema_created_by_us = False
    with app.app_context():
        actual_name = db.session.execute(text("SELECT DATABASE()")) .scalar_one()
        if actual_name != _DB_NAME:
            raise RuntimeError("Connected database does not match localjoin_ci")
        version = db.session.execute(text("SELECT VERSION()")) .scalar_one()
        if not version.startswith("8.") or "mariadb" in version.lower():
            raise RuntimeError("MySQL 8 required for disposable integration test")
        existing_tables = inspect(db.engine).get_table_names()
        existing_views = inspect(db.engine).get_view_names()
        if existing_tables or existing_views:
            raise RuntimeError("Disposable test DB is not empty: refusing to modify existing objects")
        try:
            # On an empty, verified local CI DB only.
            schema_created_by_us = True
            db.create_all()
            tables = inspect(db.engine).get_table_names()
            assert len(tables) == 32, f"Expected 32 tables, found {len(tables)}"
            users = []
            for role in ("customer", "provider", "business"):
                user = User(name=f"CI {role}", email=f"ci-{role}@example.invalid",
                            password_hash="unused-ci-only", role=role, status="active")
                db.session.add(user)
                users.append(user)
            db.session.flush()
            assert all(user.id is not None and int(user.id) > 0 for user in users)
            customer = users[0]
            category = Category(name="CI Repairs", slug="ci-repairs", is_active=1)
            db.session.add(category)
            db.session.flush()
            service = Service(category_id=category.id, name="CI Wiring", slug="ci-wiring", is_active=1)
            db.session.add(service)
            db.session.flush()
            request = ServiceRequest(customer_id=customer.id, category_id=category.id,
                                     service_id=service.id, request_type="requirement", title="CI request",
                                     description="Disposable test only", location_text="CI location", status="pending")
            db.session.add(request)
            db.session.flush()
            db.session.add(RequestStatusHistory(request_id=request.id, status="pending",
                                                changed_by=customer.id, note="CI initial transaction"))
            db.session.commit()
            assert db.session.scalar(select(RequestStatusHistory).where(RequestStatusHistory.request_id == request.id))
            assert db.session.scalar(select(ServiceRequest).where(ServiceRequest.title == "CI request"))

            # Confirm atomic rollback after request and its history have both been flushed.
            rolled_back = ServiceRequest(customer_id=customer.id, category_id=category.id,
                                         service_id=service.id, request_type="requirement", title="CI rollback",
                                         description="Rollback verification", location_text="CI", status="pending")
            db.session.add(rolled_back)
            db.session.flush()
            db.session.add(RequestStatusHistory(request_id=rolled_back.id, status="pending", changed_by=customer.id))
            db.session.flush()
            db.session.rollback()
            assert db.session.scalar(select(ServiceRequest).where(ServiceRequest.title == "CI rollback")) is None

            # A database uniqueness violation must be raised and safely recoverable.
            db.session.add(User(name="CI Duplicate", email=customer.email,
                                password_hash="unused-ci-only", role="customer", status="active"))
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
            else:
                raise AssertionError("MySQL UNIQUE email constraint did not reject duplicate")
            assert db.session.scalar(select(ServiceRequest).where(ServiceRequest.title == "CI request"))
            print("PASS: disposable MySQL 8; 32 tables; 3 role IDs; request/history commit; rollback; UNIQUE email")
        finally:
            db.session.remove()
            if schema_created_by_us:
                db.drop_all()  # only in the initially empty, specifically allowed local CI database
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
