"""Real Flask/SQLite regressions. Runs in strict CI when dependencies exist.

No test here uses live database accounts, mail or payments.
"""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from app import create_app
from config.settings import TestingConfig
from extensions import db
from models.core import Category, User
from models.marketplace import BusinessProfile, ProviderService, RequestStatusHistory, Service, ServiceRequest


class Phase8RequestConfig(TestingConfig):
    APP_REQUIRE_EMAIL_VERIFICATION = False
    APP_ADMIN_MFA_REQUIRED = False
    APP_MAIL_DRIVER = 'log'
    APP_URL = 'https://localjoin.in'


@pytest.fixture
def application():
    app = create_app(Phase8RequestConfig)
    with app.app_context():
        db.create_all()
        category = Category(name='Local repairs', slug='phase8-local-repairs', is_active=1)
        db.session.add(category)
        db.session.flush()
        service = Service(name='Fixture repairs', slug='phase8-fixture-repairs', category_id=category.id, is_active=1)
        db.session.add(service)
        db.session.flush()
        customer = User(name='Customer', email='phase8-customer@example.com', password_hash='unused', role='customer', status='active', session_version=1)
        business = User(name='Business', email='phase8-business@example.com', password_hash='unused', role='business', status='active', session_version=1)
        db.session.add_all([customer, business])
        db.session.flush()
        db.session.add(BusinessProfile(user_id=business.id, business_name='Local Repairs', verification_status='verified'))
        db.session.add(ProviderService(provider_user_id=business.id, service_id=service.id, title='Fix a fixture', is_active=1))
        request_row = ServiceRequest(customer_id=customer.id, category_id=category.id, service_id=service.id,
                                     request_type='requirement', title='Repair a fixture', description='Help with fixture',
                                     location_text='City centre', status='pending')
        db.session.add(request_row)
        db.session.commit()
        app.phase8_ids = {'business':business.id, 'customer':customer.id, 'request':request_row.id}
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


def login_as(client, user_id):
    now = int(time.time())
    with client.session_transaction() as session:
        session.clear()
        session.update(user_id=user_id, session_version=1, _created_at=now, _last_activity=now,
                       _rotated_at=now, _nonce='phase8-recovery')


def test_business_has_own_available_requirements_route_and_customer_is_denied(application):
    client = application.test_client()
    login_as(client, application.phase8_ids['business'])
    response = client.get('/business/available-requirements.php')
    assert response.status_code == 200
    assert b'Repair a fixture' in response.data
    login_as(client, application.phase8_ids['customer'])
    assert client.get('/business/available-requirements.php').status_code == 403


def test_claim_failure_rolls_back_and_returns_to_business_marketplace(application):
    client = application.test_client()
    login_as(client, application.phase8_ids['business'])
    request_id = application.phase8_ids['request']
    with patch('routes.main.create_notification', side_effect=RuntimeError('injected transient failure')):
        response = client.post('/request-details.php', data={'id':request_id, 'action':'claim'})
    assert response.status_code == 303
    assert response.headers['Location'].endswith('/business/available-requirements.php')
    with application.app_context():
        row = db.session.get(ServiceRequest, request_id)
        assert row.business_id is None
        assert db.session.query(RequestStatusHistory).filter_by(request_id=request_id).count() == 0


def test_status_failure_is_not_partially_committed(application):
    request_id = application.phase8_ids['request']
    business_id = application.phase8_ids['business']
    with application.app_context():
        row = db.session.get(ServiceRequest, request_id)
        row.business_id = business_id
        db.session.commit()
    client = application.test_client()
    login_as(client, business_id)
    with patch('routes.main.create_notification', side_effect=RuntimeError('injected transient failure')):
        response = client.post('/request-details.php', data={'id': request_id, 'action':'status', 'status':'accepted'})
    assert response.status_code == 303
    assert response.headers['Location'].endswith(f'/request-details.php?id={request_id}')
    with application.app_context():
        assert db.session.get(ServiceRequest, request_id).status == 'pending'
        assert db.session.query(RequestStatusHistory).filter_by(request_id=request_id).count() == 0
