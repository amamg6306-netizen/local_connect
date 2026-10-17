"""Phase 3 checks runnable without importing uninstalled Flask dependencies."""
import ast
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _source(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_decimal_validation_rejects_non_finite_values_without_flask():
    tree = ast.parse(_source("services/marketplace_service.py"))
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "decimal_or_none")
    # Execute precisely this pure function from production source with only its
    # Decimal dependencies; this is behavior, not a substring-only assertion.
    module = ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[]))
    ctx = {"Decimal": Decimal, "InvalidOperation": InvalidOperation}
    exec(compile(module, "services/marketplace_service.py", "exec"), ctx)
    validator = ctx["decimal_or_none"]
    for raw in ("NaN", "sNaN", "Infinity", "-Infinity", "-1", "100000001", "1.001"):
        with pytest.raises(ValueError):
            validator(raw)
    assert validator("4.25") == Decimal("4.25")
    assert validator("") is None


def test_service_crud_and_ownership_guards_present():
    route = _source("routes/provider.py")
    for value in ('"add", "update", "toggle", "delete"',
                  'ProviderService.provider_user_id == user.id',
                  'row.is_active = 0 if row.is_active else 1',
                  'Category.is_active == 1',
                  'security_log("service_management_failed"'):
        assert value in route
    for page in ("templates/provider/services.html", "templates/business/services.html"):
        html = _source(page)
        for value in ('value="update"', 'value="toggle"',
                      'value="delete"', 'name="csrf_token"',
                      'name="price_from"', 'name="price_to"'):
            assert value in html, (page, value)


def test_public_readiness_uses_active_service_category_for_featured_and_claims():
    route = _source("routes/main.py")
    helper = route[route.index("def _eligible_requirement_offering"):route.index('@bp.route("/request-details.php"')]
    for key in ("ProviderService.is_active == 1", "Service.is_active == 1", "Category.is_active == 1"):
        assert key in helper
    assert "_eligible_requirement_offering(user.id, locked.service_id)" in route
    assert 'ProviderProfile.is_featured == 1' in route
    assert route.count('Category.is_active == 1).correlate(User).exists()') >= 2


def test_extended_edit_forms_preserve_legacy_post_contract():
    for path in ("templates/provider/services.html", "templates/business/services.html"):
        text = _source(path)
        assert 'name="service_id"' in text
        assert 'value="add"' in text
        assert 'data-confirm-submit="Remove this service?"' in text


def test_sqlite_bigint_autoincrement_uses_real_project_type():
    """Run an actual SQLite insert using BIGINT_UNSIGNED from the project AST."""
    from types import SimpleNamespace
    from sqlalchemy import BigInteger, Integer, Column, MetaData, String, Table, create_engine
    from sqlalchemy.dialects import mysql
    tree = ast.parse(_source("models/base.py"))
    stmt = next(n for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "BIGINT_UNSIGNED" for t in n.targets))
    globals_ = {"db": SimpleNamespace(BigInteger=BigInteger, Integer=Integer), "mysql": mysql}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[stmt], type_ignores=[])),
                 "models/base.py", "exec"), globals_)
    column_type = globals_["BIGINT_UNSIGNED"]
    assert column_type.compile(dialect=mysql.dialect()).upper() == "BIGINT UNSIGNED"
    engine = create_engine("sqlite:///:memory:")
    table = Table("phase3_probe", MetaData(), Column("id", column_type,
        primary_key=True, autoincrement=True), Column("description", String))
    table.create(engine)
    with engine.begin() as connection:
        inserted = connection.execute(table.insert().values(description="integration smoke"))
        assert inserted.inserted_primary_key == (1,)
