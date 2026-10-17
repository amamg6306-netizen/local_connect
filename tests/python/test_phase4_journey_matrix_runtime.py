"""Phase 4 Flask integration matrix (isolated SQLite; no live writes or emails).

These are REAL Flask test-client cases, not source-string assertions. They are
expected to run in CI with the pinned application dependencies installed.
Keep imports explicit: missing runtime packages must cause a failed test gate.
"""
from __future__ import annotations

from datetime import datetime
import re
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app import create_app
from config.settings import TestingConfig
from extensions import db
from models.core import Category, User
from models.marketplace import BusinessProfile, ProviderProfile, ProviderService, RequestStatusHistory, Service, ServiceRequest
from services.auth_service import password_hash


class JourneysConfig(TestingConfig):
    APP_REQUIRE_EMAIL_VERIFICATION = False
    APP_ADMIN_MFA_REQUIRED = False
    APP_MAIL_DRIVER = "log"
    APP_URL = "https://localjoin.in"


@pytest.fixture
def app():
    application = create_app(JourneysConfig)
    with application.app_context():
        db.drop_all()
        db.create_all()
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def register(client, role):
    payload = {
        "role": role,
        "name": f"Phase 4 {role}",
        "email": f"phase4-{role}@example.com",
        "phone": "9876543210",
        "city": "Varanasi",
        "state": "Uttar Pradesh",
        "password": "phase four safe password",
        "confirm_password": "phase four safe password",
    }
    response = client.post("/auth/register.php", data=payload)
    assert response.status_code == 303, response.get_data(as_text=True)[:250]
    return payload


@pytest.mark.parametrize("role,profile_type,dashboard", [
    ("customer", None, "/customer/dashboard.php"),
    ("provider", ProviderProfile, "/provider/dashboard.php"),
    ("business", BusinessProfile, "/business/dashboard.php"),
])
def test_registration_and_role_dashboard(app, client, role, profile_type, dashboard):
    data = register(client, role)
    with app.app_context():
        account = db.session.scalar(select(User).where(User.email == data["email"]))
        assert account is not None
        assert account.role == role
        assert account.status == "active"
        if profile_type is not None:
            assert db.session.scalar(select(profile_type).where(profile_type.user_id == account.id)) is not None
    assert client.get(dashboard).status_code == 200
    for other_role in ("customer", "provider", "business"):
        if other_role != role:
            assert client.get(f"/{other_role}/dashboard.php").status_code == 403
    assert client.post("/auth/logout.php").status_code == 303
    assert client.get(dashboard).status_code == 303
    assert client.post("/auth/login.php", data={"email": data["email"], "password": data["password"]}).status_code == 303
    assert client.get(dashboard).status_code == 200


def make_user(role, name):
    user = User(name=name, email=f"{role}-{name.replace(' ', '-')}-phase4@example.com",
                role=role, status="active", email_verified_at=datetime.now(),
                password_hash=password_hash("phase four safe password"), session_version=1)
    db.session.add(user)
    db.session.flush()
    if role == "provider":
        db.session.add(ProviderProfile(user_id=user.id, headline=name))
    if role == "business":
        db.session.add(BusinessProfile(user_id=user.id, business_name=name))
    db.session.flush()
    return user


def make_catalogue():
    category = Category(name="Repairs phase 4", slug="repairs-phase4", is_active=1)
    db.session.add(category)
    db.session.flush()
    service = Service(category_id=category.id, name="Wiring phase 4", slug="wiring-phase4", is_active=1)
    db.session.add(service)
    db.session.flush()
    return category, service


def login(client, user):
    response = client.post("/auth/login.php", data={"email": user.email, "password": "phase four safe password"})
    assert response.status_code == 303


@pytest.mark.parametrize("role", ["provider", "business"])
def test_service_crud_and_ownership_isolation(app, client, role):
    with app.app_context():
        owner = make_user(role, "Owner")
        other = make_user(role, "Other")
        category, service = make_catalogue()
        db.session.commit()
        email = owner.email
        other_email = other.email
        service_id = service.id
    assert client.post("/auth/login.php", data={"email": email, "password": "phase four safe password"}).status_code == 303
    url = f"/{role}/services.php"
    assert client.post(url, data={"action": "add", "service_id": service_id, "title": "Electrical repair", "price_from": "199"}).status_code == 303
    with app.app_context():
        offering = db.session.scalar(select(ProviderService).where(ProviderService.service_id == service_id))
        assert offering is not None
        offering_id = offering.id
    assert client.post(url, data={"action": "update", "id": offering_id, "title": "Updated repair"}).status_code == 303
    assert client.post(url, data={"action": "toggle", "id": offering_id}).status_code == 303
    with app.app_context():
        assert db.session.get(ProviderService, offering_id).is_active == 0
    client.post("/auth/logout.php")
    assert client.post("/auth/login.php", data={"email": other_email, "password": "phase four safe password"}).status_code == 303
    denied = client.post(url, data={"action": "delete", "id": offering_id})
    assert denied.status_code == 200
    with app.app_context():
        assert db.session.get(ProviderService, offering_id) is not None
    client.post("/auth/logout.php")
    assert client.post("/auth/login.php", data={"email": email, "password": "phase four safe password"}).status_code == 303
    assert client.post(url, data={"action": "toggle", "id": offering_id}).status_code == 303
    assert client.post(url, data={"action": "delete", "id": offering_id}).status_code == 303
    with app.app_context():
        assert db.session.get(ProviderService, offering_id) is None


def test_direct_request_business_target_persists_with_history(app, client):
    with app.app_context():
        customer = make_user("customer", "Customer")
        business = make_user("business", "Business")
        category, service = make_catalogue()
        db.session.add(ProviderService(provider_user_id=business.id, service_id=service.id, title="Wiring", is_active=1))
        db.session.commit()
        customer_email, business_id, category_id, service_id = customer.email, business.id, category.id, service.id
    assert client.post("/auth/login.php", data={"email": customer_email, "password": "phase four safe password"}).status_code == 303
    response = client.post("/request-service.php", data={"target_type": "business", "target_id": business_id,
        "category_id": category_id, "service_id": service_id, "title": "Electrical repair",
        "description": "Wire repair requested", "location_text": "Varanasi"})
    assert response.status_code == 303
    with app.app_context():
        request = db.session.scalar(select(ServiceRequest))
        assert request is not None and request.business_id == business_id and request.provider_id is None
        assert db.session.scalar(select(RequestStatusHistory).where(RequestStatusHistory.request_id == request.id)) is not None


def test_requirement_transaction_rolls_back_on_commit_failure(app, client):
    from sqlalchemy.exc import OperationalError
    with app.app_context():
        customer = make_user("customer", "Customer")
        category, service = make_catalogue()
        db.session.commit()
        customer_email, category_id, service_id = customer.email, category.id, service.id
    assert client.post("/auth/login.php", data={"email": customer_email, "password": "phase four safe password"}).status_code == 303
    with patch.object(db.session, "commit", side_effect=OperationalError("commit", {}, Exception("simulated"))):
        response = client.post("/post-requirement.php", data={
            "category_id": category_id, "service_id": service_id, "title": "Wire repair",
            "description": "Need wire replacement", "location_text": "Varanasi"})
    assert response.status_code == 200
    assert b"Could not post your requirement" in response.data
    with app.app_context():
        assert db.session.scalar(select(ServiceRequest)) is None
        assert db.session.scalar(select(RequestStatusHistory)) is None


class CsrfConfig(JourneysConfig):
    WTF_CSRF_ENABLED = True


def test_csrf_rejection_and_valid_post_for_registration():
    """Exercise actual Flask-WTF, unlike the other test configs which disable it."""
    application = create_app(CsrfConfig)
    with application.app_context():
        db.drop_all()
        db.create_all()
    try:
        client = application.test_client()
        url = "/auth/register.php"
        payload = {"role": "customer", "name": "CSRF Tester", "email": "csrf-phase4@example.com",
                   "password": "phase four safe password", "confirm_password": "phase four safe password"}
        assert client.post(url, data=payload).status_code == 400
        html = client.get(url).get_data(as_text=True)
        found = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
        assert found, "Registration form does not expose CSRF token"
        assert client.post(url, data={**payload, "csrf_token": "invalid"}).status_code == 400
        response = client.post(url, data={**payload, "csrf_token": found.group(1)})
        assert response.status_code == 303
        with application.app_context():
            assert db.session.scalar(select(User).where(User.email == payload["email"])) is not None
    finally:
        with application.app_context():
            db.session.remove()
            db.drop_all()


def test_testing_host_whitelist_allows_flask_client_without_weakening_production(app, client):
    assert client.get("/health").status_code == 200
    # Host validation is still active for arbitrary host headers in testing.
    assert client.get("/health", headers={"Host": "untrusted.example"}).status_code == 400
