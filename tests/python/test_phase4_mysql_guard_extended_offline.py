"""Ensure the destructive smoke script cannot touch nonlocal or non-empty databases."""
from __future__ import annotations

from scripts.run_disposable_mysql_smoke import preflight_error


def env(**updates):
    defaults = {
        "APP_ENV": "testing",
        "LOCALJOIN_ALLOW_DISPOSABLE_DB_WRITES": "YES_I_UNDERSTAND_DISPOSABLE",
        "LOCALJOIN_DISPOSABLE_DB_URL": "mysql+pymysql://ci:password@127.0.0.1:3306/localjoin_ci",
        "DATABASE_URL": "mysql+pymysql://ci:password@127.0.0.1:3306/localjoin_ci",
    }
    return {**defaults, **updates}


def test_exact_local_ci_url_eligible_for_secondary_database_safety_checks():
    assert preflight_error(env()) is None


def test_rejects_hostname_pointing_outside_local_runner():
    assert preflight_error(env(LOCALJOIN_DISPOSABLE_DB_URL="mysql+pymysql://ci:p@db.example.com/localjoin_ci"))


def test_rejects_prodish_name_even_with_ci_suffix():
    url = "mysql+pymysql://ci:p@127.0.0.1:3306/localjoin_production_ci"
    assert preflight_error(env(LOCALJOIN_DISPOSABLE_DB_URL=url, DATABASE_URL=url))


def test_rejects_disagreement_between_module_app_database_and_test_database():
    assert preflight_error(env(DATABASE_URL="mysql+pymysql://ci:p@127.0.0.1/localjoin_production"))


def test_rejects_non_testing_environment():
    assert preflight_error(env(APP_ENV="production"))


def test_rejects_malformed_port():
    url = "mysql+pymysql://ci:p@127.0.0.1:99999/localjoin_ci"
    assert preflight_error(env(LOCALJOIN_DISPOSABLE_DB_URL=url, DATABASE_URL=url))


def test_rejects_missing_optin():
    assert preflight_error(env(LOCALJOIN_ALLOW_DISPOSABLE_DB_WRITES=""))


def test_rejects_sqlite_url_even_if_local():
    assert preflight_error(env(DATABASE_URL="sqlite:///:memory:", LOCALJOIN_DISPOSABLE_DB_URL="sqlite:///:memory:"))
