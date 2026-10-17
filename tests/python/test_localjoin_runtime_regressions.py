"""Offline Flask integration tests for the repaired Localjoin user journeys.

Executed in CI by scripts/run_runtime_tests.py with an in-memory SQLite
schema and mocked mail. No requests to the live localjoin.in site are made.
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import patch
from urllib.parse import urlsplit
import re

from sqlalchemy import select

from app import create_app
from config.settings import TestingConfig
from extensions import db
from models.core import Category, User
from models.marketplace import (
    BusinessProfile, ProviderProfile, ProviderService, RequestStatusHistory,
    Service, ServiceRequest,
)
from services.auth_service import password_hash


class IntegrationConfig(TestingConfig):
    APP_URL = "https://localjoin.in"
    APP_REQUIRE_EMAIL_VERIFICATION = True
    APP_ADMIN_MFA_REQUIRED = False
    APP_SUPPORT_EMAIL = "support@example.com"
    APP_MAIL_DRIVER = "log"  # all test calls to mail sender are mocked


def _test_app():
    app = create_app(IntegrationConfig)
    with app.app_context():
        db.drop_all()
        db.create_all()
    return app


def _create_user(email, role, *, name="Integration Test"):
    user = User(
        name=name, email=email, role=role, status="active",
        email_verified_at=datetime.now(), session_version=1,
        password_hash=password_hash("this is a long testing password"),
    )
    db.session.add(user)
    db.session.flush()
    return user


def _create_service(category_name, service_name):
    category = Category(name=category_name, slug=category_name.lower().replace(" ", "-"), is_active=1)
    db.session.add(category)
    db.session.flush()
    service = Service(category_id=category.id, name=service_name, slug=service_name.lower().replace(" ", "-"), is_active=1)
    db.session.add(service)
    db.session.flush()
    return category, service


def _login(client, email):
    response = client.post("/auth/login.php", data={"email": email, "password": "this is a long testing password"})
    assert response.status_code == 303, response.get_data(as_text=True)[:200]
    return response


def test_all_three_roles_register_as_pending_with_mocked_email_failure():
    for role, profile_class in (("customer", None), ("provider", ProviderProfile), ("business", BusinessProfile)):
        app = _test_app()
        client = app.test_client()
        payload = {
            "role": role, "name": f"Test {role}", "email": f"{role}@example.com",
            "phone": "9876543210", "city": "Varanasi", "state": "Uttar Pradesh",
            "password": "this is a long testing password",
            "confirm_password": "this is a long testing password",
        }
        with patch("routes.auth.send_app_email", return_value=False):
            response = client.post("/auth/register.php", data=payload)
        assert response.status_code == 303
        with app.app_context():
            user = db.session.scalar(select(User).where(User.email == payload["email"]))
            assert user is not None and user.role == role and user.status == "pending"
            if profile_class is not None:
                assert db.session.scalar(select(profile_class).where(profile_class.user_id == user.id)) is not None
        denied = client.post("/auth/login.php", data={"email": payload["email"], "password": payload["password"]})
        assert b"verify your email" in denied.data.lower()
        repeat = client.post("/auth/register.php", data=payload)
        assert b"already exists" in repeat.data.lower()


def test_pending_customer_can_resend_verify_and_login_without_live_mail():
    app = _test_app()
    client = app.test_client()
    messages = []
    payload = {
        "role": "customer", "name": "Test Customer", "email": "pending@example.com",
        "password": "this is a long testing password", "confirm_password": "this is a long testing password",
    }
    with patch("routes.auth.send_app_email", side_effect=lambda to, subject, body: messages.append(body) or True):
        assert client.post("/auth/register.php", data=payload).status_code == 303
        assert client.post("/auth/resend-verification.php", data={"email": payload["email"]}).status_code == 200
    assert len(messages) == 2
    verification_url = re.search(r"https://[^\s]+", messages[-1])
    assert verification_url is not None
    path = urlsplit(verification_url.group()).path + "?" + urlsplit(verification_url.group()).query
    assert client.get(path).status_code == 303
    with app.app_context():
        user = db.session.scalar(select(User).where(User.email == payload["email"]))
        assert user.status == "active" and user.email_verified_at is not None
    _login(client, payload["email"])


def test_service_less_provider_not_bookable_or_searchable():
    app = _test_app()
    with app.app_context():
        provider = _create_user("unready@example.com", "provider", name="Unready Provider")
        db.session.add(ProviderProfile(user_id=provider.id, headline="Unready Provider"))
        provider_id = provider.id
        db.session.commit()
    client = app.test_client()
    detail = client.get(f"/provider.php?id={provider_id}")
    assert detail.status_code == 200
    assert b"No services listed yet" in detail.data
    assert b'href="/request-service.php?' not in detail.data
    search = client.get("/search.php?q=Unready")
    assert search.status_code == 200
    assert b"Unready Provider" not in search.data


def test_post_requirement_invalid_pair_rejected_and_valid_pair_atomic():
    app = _test_app()
    with app.app_context():
        customer = _create_user("customer@requests.example", "customer")
        category, service = _create_service("Electrical", "Wiring")
        empty = Category(name="Empty Category", slug="empty-category", is_active=1)
        db.session.add(empty)
        db.session.commit()
        customer_email = customer.email
        category_id, service_id, empty_id = category.id, service.id, empty.id
    client = app.test_client()
    _login(client, customer_email)
    form = client.get("/post-requirement.php")
    assert form.status_code == 200
    assert b"Empty Category" not in form.data
    data = {
        "category_id": empty_id, "service_id": service_id,
        "title": "Fix switchboard", "description": "Need a switchboard repair",
        "location_text": "Varanasi", "budget_min": "100", "budget_max": "700",
    }
    invalid = client.post("/post-requirement.php", data=data)
    assert invalid.status_code == 200 and b"valid service" in invalid.data
    with app.app_context():
        assert db.session.query(ServiceRequest).count() == 0
    data["category_id"] = category_id
    valid = client.post("/post-requirement.php", data=data)
    assert valid.status_code == 303
    with app.app_context():
        assert db.session.query(ServiceRequest).count() == 1
        assert db.session.query(RequestStatusHistory).count() == 1
    assert b"Fix switchboard" in client.get("/customer/requests.php").data


def test_direct_service_request_must_be_offered_to_selected_provider():
    app = _test_app()
    with app.app_context():
        customer = _create_user("direct@requests.example", "customer")
        provider = _create_user("provider@requests.example", "provider")
        db.session.add(ProviderProfile(user_id=provider.id, headline="Local repair"))
        category, offered_service = _create_service("Plumbing", "Pipe repair")
        _, other_service = _create_service("Painting", "Wall painting")
        db.session.add(ProviderService(provider_user_id=provider.id, service_id=offered_service.id, title="Pipe repairs", is_active=1))
        db.session.commit()
        customer_email, provider_id = customer.email, provider.id
        cat_id, valid_id, invalid_id = category.id, offered_service.id, other_service.id
    client = app.test_client()
    _login(client, customer_email)
    data = {
        "target_id": provider_id, "target_type": "provider", "category_id": cat_id,
        "service_id": invalid_id, "title": "Pipe repair", "description": "Please fix pipe",
        "location_text": "Varanasi",
    }
    response = client.post("/request-service.php", data=data)
    assert response.status_code == 200 and b"not offered" in response.data
    with app.app_context():
        assert db.session.query(ServiceRequest).count() == 0
    data["service_id"] = valid_id
    response = client.post("/request-service.php", data=data)
    assert response.status_code == 303
    with app.app_context():
        row = db.session.query(ServiceRequest).one()
        assert row.provider_id == provider_id and row.status == "pending"
        assert db.session.query(RequestStatusHistory).filter_by(request_id=row.id).count() == 1


def test_post_login_intended_destination_and_open_redirect_rejection():
    app = _test_app()
    with app.app_context():
        user = _create_user("redirect@example.com", "customer")
        email = user.email
        db.session.commit()
    client = app.test_client()
    target = "/post-requirement.php"
    unauthorized = client.get(target)
    assert unauthorized.status_code == 303 and "next=" in unauthorized.headers["Location"]
    login = client.post("/auth/login.php", data={"email": email, "password": "this is a long testing password", "next": target})
    assert login.status_code == 303 and login.headers["Location"] == target
    client.post("/auth/logout.php")
    external = client.post("/auth/login.php", data={"email": email, "password": "this is a long testing password", "next": "https://evil.example/phish"})
    assert external.status_code == 303 and external.headers["Location"] == "/customer/dashboard.php"


def test_contact_form_only_acknowledges_mocked_mail_acceptance():
    app = _test_app()
    client = app.test_client()
    form = {"name": "A tester", "email": "contact1@example.com", "message": "A detailed support question"}
    with patch("routes.main.send_app_email", return_value=False) as sender:
        response = client.post("/contact.php", data=form)
        assert response.status_code == 200 and b"could not be accepted" in response.data
        assert b"accepted for sending to support" not in response.data
        assert sender.call_count == 1
    form["email"] = "contact2@example.com"
    with patch("routes.main.send_app_email", return_value=True) as sender:
        response = client.post("/contact.php", data=form)
        assert response.status_code == 200 and b"accepted for sending to support" in response.data
        assert sender.call_count == 1


def test_provider_service_update_pause_and_restore_with_owner_checks():
    app = _test_app()
    with app.app_context():
        provider = _create_user("services-owner@example.com", "provider", name="Service Owner")
        competitor = _create_user("other-owner@example.com", "provider", name="Competitor")
        db.session.add_all([ProviderProfile(user_id=provider.id, headline="Repair specialist"),
                            ProviderProfile(user_id=competitor.id, headline="Competitor")])
        category, service = _create_service("Electrical phase3", "Fan Repair")
        owner_email, other_email = provider.email, competitor.email
        service_id = service.id
        db.session.commit()
    client = app.test_client()
    _login(client, owner_email)
    response = client.post("/provider/services.php", data={"action": "add", "service_id": service_id,
        "title": "Fan installation", "price_from": "199.00"})
    assert response.status_code == 303
    with app.app_context():
        item = db.session.scalar(select(ProviderService).where(ProviderService.service_id == service_id))
        item_id = item.id
        assert item.is_active == 1
    assert client.post("/provider/services.php", data={"action": "update", "id": item_id,
        "title": "Fan and wiring", "description": "Electrical jobs", "price_from": "299", "price_to": "500"}).status_code == 303
    with app.app_context():
        item = db.session.get(ProviderService, item_id)
        assert item.title == "Fan and wiring" and str(item.price_from) == "299.00"
    assert client.post("/provider/services.php", data={"action": "toggle", "id": item_id}).status_code == 303
    with app.app_context():
        assert db.session.get(ProviderService, item_id).is_active == 0
    _login(client, other_email)
    unauthorized = client.post("/provider/services.php", data={"action": "toggle", "id": item_id})
    assert unauthorized.status_code == 200 and b"not on your profile" in unauthorized.data
    with app.app_context():
        assert db.session.get(ProviderService, item_id).is_active == 0
    _login(client, owner_email)
    assert client.post("/provider/services.php", data={"action": "toggle", "id": item_id}).status_code == 303
    with app.app_context():
        assert db.session.get(ProviderService, item_id).is_active == 1


def test_disabled_catalogue_service_cannot_be_added_or_restored():
    app = _test_app()
    with app.app_context():
        user = _create_user("disabled-service@example.com", "provider")
        db.session.add(ProviderProfile(user_id=user.id))
        category, service = _create_service("Unusable", "Offered service")
        db.session.add(ProviderService(provider_user_id=user.id, service_id=service.id, is_active=0))
        db.session.commit()
        email, item_id, service_id = user.email, db.session.scalar(select(ProviderService.id)), service.id
        category.is_active = 0
        db.session.commit()
    client = app.test_client()
    _login(client, email)
    assert b"unavailable" in client.post("/provider/services.php", data={"action": "toggle", "id": item_id}).data
    assert b"active service and category" in client.post("/provider/services.php", data={"action": "add", "service_id": service_id}).data
    with app.app_context():
        assert db.session.get(ProviderService, item_id).is_active == 0


def test_inactive_catalogue_blocks_open_requirement_claim():
    app = _test_app()
    with app.app_context():
        customer = _create_user("claim-customer@example.com", "customer")
        provider = _create_user("claim-provider@example.com", "provider")
        category, service = _create_service("Inactive for claim", "Claim service")
        db.session.add(ProviderService(provider_user_id=provider.id, service_id=service.id, is_active=1))
        db.session.flush()
        row = ServiceRequest(customer_id=customer.id, category_id=category.id, service_id=service.id,
            request_type="requirement", title="Original request", description="Need help",
            location_text="Varanasi", status="pending")
        db.session.add(row)
        db.session.commit()
        request_id, email = row.id, provider.email
        category.is_active = 0
        db.session.commit()
    client = app.test_client()
    _login(client, email)
    assert client.get(f"/request-details.php?id={request_id}").status_code == 403
    assert client.post("/request-details.php", data={"id": request_id, "action": "claim"}).status_code == 403
    with app.app_context():
        row = db.session.get(ServiceRequest, request_id)
        assert row.provider_id is None and row.business_id is None


def test_non_finite_request_budget_rejected_without_database_insert():
    app = _test_app()
    with app.app_context():
        customer = _create_user("nan-budget@example.com", "customer")
        category, service = _create_service("Valid category", "Valid service")
        email, category_id, service_id = customer.email, category.id, service.id
        db.session.commit()
    client = app.test_client()
    _login(client, email)
    for bad in ("NaN", "Infinity", "-Infinity"):
        response = client.post("/post-requirement.php", data={
            "category_id": category_id, "service_id": service_id,
            "title": "Budget test", "description": "Fix a local issue",
            "location_text": "Varanasi", "budget_min": bad,
        })
        assert response.status_code == 200
        assert b"Minimum budget is invalid" in response.data
    with app.app_context():
        assert db.session.query(ServiceRequest).count() == 0
