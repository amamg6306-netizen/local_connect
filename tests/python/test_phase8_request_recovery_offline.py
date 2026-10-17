"""Source-contract checks for the Phase 8 fallback/rollback handling.

These do NOT stand in for the Flask test-client scenarios in the runtime module.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_business_available_requirements_route_has_role_guard():
    source = (ROOT / 'routes/business.py').read_text()
    tree = ast.parse(source)
    view = next(fn for fn in tree.body if isinstance(fn, ast.FunctionDef) and fn.name == 'available_requirements')
    decorators = [ast.unparse(dec) for dec in view.decorator_list]
    assert "bp.get('/business/available-requirements.php')" in decorators
    assert "require_roles('business')" in decorators
    assert '_available_requirements_page()' in ast.unparse(view)
    dashboard = (ROOT / 'templates/business/dashboard.html').read_text()
    assert "lc_url('business/available-requirements.php')" in dashboard


def test_claim_exception_paths_roll_back_and_redirect_to_correct_role():
    source = (ROOT / 'routes/main.py').read_text()
    tree = ast.parse(source)
    view = next(fn for fn in tree.body if isinstance(fn, ast.FunctionDef) and fn.name == 'request_details')
    tries = [node for node in ast.walk(view) if isinstance(node, ast.Try)]
    claim = next(node for node in tries if 'Requirement claimed; awaiting provider acceptance' in ast.unparse(node))
    assert len(claim.handlers) == 2
    for handler in claim.handlers:
        assert 'db.session.rollback()' in ast.unparse(handler)
    recovery = ast.unparse(view)
    assert "'/business/available-requirements.php' if user.role == 'business'" in recovery
    assert 'requirement_claim_failed reference=%s error_type=%s' in recovery
    assert 'secrets.token_hex(4)' in recovery


def test_status_database_errors_roll_back_with_reference_but_no_stack_trace_to_user():
    source = (ROOT / 'routes/main.py').read_text()
    tree = ast.parse(source)
    view = next(fn for fn in tree.body if isinstance(fn, ast.FunctionDef) and fn.name == 'request_details')
    tries = [node for node in ast.walk(view) if isinstance(node, ast.Try)]
    status = next(node for node in tries if 'request_status_change_failed' in ast.unparse(node))
    assert len(status.handlers) == 2
    for handler in status.handlers:
        assert 'db.session.rollback()' in ast.unparse(handler)
    text = ast.unparse(status)
    assert 'raise ValueError(\'This request is no longer available.\')' in text
    assert 'type(exc).__name__' in text
    assert 'Could not update request status. Reference:' in text
