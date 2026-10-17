"""Execute real Localjoin SQLAlchemy models against disposable in-memory SQLite.

Useful offline *model-level* test when Flask and MySQL binaries cannot be
installed. DOES NOT substitute for Flask routes or MySQL 8 integration.
No production DB connection, network call or application import is used.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.orm import Session, declarative_base
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateTable, CreateIndex
from sqlalchemy.dialects import mysql

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Flask-SQLAlchemy is not installed on this runner. Make only its db.Model/
# type factory API available, backed by the installed real SQLAlchemy ORM.
# This shim is process-local and never installed or used by the application.
base = declarative_base()
fields = (
    "BigInteger CheckConstraint Column Date DateTime Enum ForeignKey Index "
    "Integer JSON Numeric SmallInteger String Text Time UniqueConstraint func"
).split()
db = types.SimpleNamespace(**{name: getattr(sa, name) for name in fields}, Model=base)
extensions = types.ModuleType("extensions")
extensions.db = db
sys.modules["extensions"] = extensions

from models.core import Category, User
from models.marketplace import ProviderService, Service, ServiceRequest, RequestStatusHistory
import models  # noqa: F401 - import/register complete real schema


def main() -> None:
    assert len(base.metadata.tables) == 32
    # Compile every real model for the MySQL dialect (syntax-only, not a server test).
    # Do not call sorted_tables: payments <-> subscriptions intentionally have a
    # cyclic FK relationship that MySQL DDL must resolve via deferred ALTER.
    for table in base.metadata.tables.values():
        assert "CREATE TABLE" in str(CreateTable(table).compile(dialect=mysql.dialect()))
        for index in table.indexes:
            str(CreateIndex(index).compile(dialect=mysql.dialect()))
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        conn.commit()
    base.metadata.create_all(engine)
    assert len(sa.inspect(engine).get_table_names()) == 32
    with Session(engine) as session:
        users = [User(name=f"Offline {role}", email=f"{role}@example.invalid",
                      password_hash="not-a-login-hash", role=role, status="active")
                 for role in ("customer", "provider", "business")]
        session.add_all(users)
        session.flush()
        assert all(isinstance(u.id, int) and u.id > 0 for u in users)
        category = Category(name="Offline category", slug="offline", is_active=1)
        session.add(category)
        session.flush()
        service = Service(category_id=category.id, name="Offline service", slug="offline", is_active=1)
        session.add(service)
        session.flush()
        offering = ProviderService(provider_user_id=users[1].id, service_id=service.id,
                                   title="offline offering", is_active=1)
        session.add(offering)
        row = ServiceRequest(customer_id=users[0].id, category_id=category.id,
                             service_id=service.id, request_type="requirement", title="Offline request",
                             description="Local-only testing", location_text="Offline", status="pending")
        session.add(row)
        session.flush()
        session.add(RequestStatusHistory(request_id=row.id, status="pending", changed_by=users[0].id))
        session.commit()
        assert session.scalar(sa.select(RequestStatusHistory).where(RequestStatusHistory.request_id == row.id))
        second = ServiceRequest(customer_id=users[0].id, category_id=category.id,
                                service_id=service.id, request_type="requirement", title="Rolled back",
                                description="Local-only testing", location_text="Offline", status="pending")
        session.add(second)
        session.flush()
        session.add(RequestStatusHistory(request_id=second.id, status="pending", changed_by=users[0].id))
        session.flush()
        session.rollback()
        assert session.scalar(sa.select(ServiceRequest).where(ServiceRequest.title == "Rolled back")) is None
        session.add(User(name="Duplicate", email="customer@example.invalid", password_hash="none", role="customer", status="active"))
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
        else:
            raise AssertionError("Duplicate email was not blocked")
        assert session.scalar(sa.select(ServiceRequest).where(ServiceRequest.title == "Offline request"))
    # In-memory SQLite disappears on engine disposal. Avoid DROP order problems
    # from the existing payments<->subscriptions FK cycle.
    engine.dispose()
    print("PASS: 32 real ORM tables SQLite execution + MySQL DDL compilation (NOT a MySQL server test); 3 roles; offering; request/history; rollback; UNIQUE email")


if __name__ == "__main__":
    main()
