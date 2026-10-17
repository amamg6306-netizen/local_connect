"""Execute actual application config under test SQLite and MySQL settings.

Unlike the Flask test-client matrix, these can run on an offline local runner.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run_with_database(uri):
    env = os.environ.copy()
    env.update({"APP_ENV": "testing", "DATABASE_URL": uri})
    probe = ("from config.settings import BaseConfig, TestingConfig; "
             "print(repr(BaseConfig.SQLALCHEMY_ENGINE_OPTIONS)); "
             "print(repr(TestingConfig.TRUSTED_HOSTS))")
    result = subprocess.run([sys.executable, "-c", probe], cwd=ROOT, env=env,
                            check=True, capture_output=True, text=True, timeout=15)
    return result.stdout


def test_sqlite_test_url_does_not_receive_mysql_connect_options():
    stdout = _run_with_database("sqlite:///:memory:")
    assert stdout.splitlines()[0] == "{}"
    assert "'localhost'" in stdout.splitlines()[1]


def test_mysql_keeps_production_pool_settings():
    stdout = _run_with_database("mysql+pymysql://example:sample@127.0.0.1:3306/localjoin_ci")
    assert "'pool_pre_ping': True" in stdout
    assert "'connect_timeout':" in stdout


def test_mysql_disposable_guard_rejects_no_explicit_optin():
    env = os.environ.copy()
    env.pop("LOCALJOIN_ALLOW_DISPOSABLE_DB_WRITES", None)
    env["LOCALJOIN_DISPOSABLE_DB_URL"] = "mysql+pymysql://ci:ci@localhost:3306/localjoin_ci"
    result = subprocess.run([sys.executable, "scripts/run_disposable_mysql_smoke.py"],
                            cwd=ROOT, env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode == 2
    assert "BLOCKED" in result.stderr


def test_mysql_disposable_guard_rejects_production_db_even_with_optin():
    env = os.environ.copy()
    env["LOCALJOIN_ALLOW_DISPOSABLE_DB_WRITES"] = "YES_I_UNDERSTAND_DISPOSABLE"
    env["LOCALJOIN_DISPOSABLE_DB_URL"] = "mysql+pymysql://ci:ci@localhost:3306/localjoin_production"
    result = subprocess.run([sys.executable, "scripts/run_disposable_mysql_smoke.py"],
                            cwd=ROOT, env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode == 2
    assert "BLOCKED" in result.stderr
