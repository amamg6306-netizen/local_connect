"""Integration checks for admin restore policy with real Flask/SQLite.

These MUST be run on the full dependency-capable test runner. No live DB.
"""
from datetime import datetime

import pytest

from app import create_app
from config.settings import TestingConfig
from extensions import db
from models.core import User


class Phase5Config(TestingConfig):
    APP_REQUIRE_EMAIL_VERIFICATION = True
    APP_ADMIN_MFA_REQUIRED = False
    AUTO_INIT_SCHEMA = True


@pytest.fixture
def app():
    instance = create_app(Phase5Config)
    with instance.app_context():
        db.drop_all()
        db.create_all()
        admin = User(
            name="Admin", email="phase5-admin@example.com", role="admin", status="active",
            password_hash="test-hash", email_verified_at=datetime(2026, 1, 1), session_version=1,
        )
        unverified = User(
            name="Pending blocked", email="blocked-pending@example.com", role="customer", status="blocked",
            password_hash="test-hash", email_verified_at=None, session_version=1,
        )
        verified = User(
            name="Verified blocked", email="blocked-verified@example.com", role="provider", status="blocked",
            password_hash="test-hash", email_verified_at=datetime(2026, 1, 1), session_version=1,
        )
        db.session.add_all([admin, unverified, verified])
        db.session.commit()
        ids = admin.id, unverified.id, verified.id
    yield instance, ids
    with instance.app_context():
        db.session.remove()
        db.drop_all()


def _login_admin(client, admin_id):
    with client.session_transaction() as session:
        session["user_id"] = admin_id
        session["session_version"] = 1


def test_unblocking_unverified_customer_cannot_skip_email_verification(app):
    instance, (admin_id, unverified_id, _) = app
    client = instance.test_client()
    _login_admin(client, admin_id)
    response = client.post("/admin/users.php", data={"id": unverified_id, "action": "unblock"})
    assert response.status_code == 303
    with instance.app_context():
        user = db.session.get(User, unverified_id)
        assert user.status == "pending"
        assert user.session_version == 2


def test_unblocking_verified_provider_restores_active_access(app):
    instance, (admin_id, _, verified_id) = app
    client = instance.test_client()
    _login_admin(client, admin_id)
    response = client.post("/admin/users.php", data={"id": verified_id, "action": "unblock"})
    assert response.status_code == 303
    with instance.app_context():
        user = db.session.get(User, verified_id)
        assert user.status == "active"
        assert user.session_version == 2


def test_unblock_nonblocked_user_does_not_change_pending_account(app):
    instance, (admin_id, unverified_id, _) = app
    with instance.app_context():
        user = db.session.get(User, unverified_id)
        user.status = "pending"
        db.session.commit()
    client = instance.test_client()
    _login_admin(client, admin_id)
    response = client.post("/admin/users.php", data={"id": unverified_id, "action": "unblock"})
    assert response.status_code == 303
    with instance.app_context():
        user = db.session.get(User, unverified_id)
        assert user.status == "pending"
        assert user.session_version == 1
