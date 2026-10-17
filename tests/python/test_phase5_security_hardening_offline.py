"""Phase 5 regressions executable without Flask or external services."""
from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys

from utils.account_status import status_after_unblock

ROOT = Path(__file__).resolve().parents[2]


def _production_errors(**overrides):
    env = os.environ.copy()
    for key in (
        "APP_ENV", "APP_DEBUG", "APP_URL", "SECRET_KEY", "APP_KEY",
        "DATABASE_URL", "APP_MAIL_DRIVER", "APP_MAIL_FROM", "RESEND_API_KEY",
        "APP_SUPPORT_EMAIL", "AUTO_INIT_SCHEMA", "LOCALJOIN_WORKER_ONLY",
        "UPLOAD_DISK_REQUIRED", "TRUST_PROXY", "FORCE_HTTPS",
        "SESSION_COOKIE_SECURE", "APP_ADMIN_MFA_REQUIRED",
        "APP_REQUIRE_EMAIL_VERIFICATION", "SECURITY_CSP_MODE",
    ):
        env.pop(key, None)
    env.update({
        "APP_ENV": "production",
        "APP_DEBUG": "false",
        "APP_URL": "https://localjoin.in",
        "SECRET_KEY": "example_only_local_test_secret_32_bytes_not_real",
        "DATABASE_URL": "mysql+pymysql://ci:ci@127.0.0.1:3306/localjoin_ci",
        "APP_MAIL_DRIVER": "resend",
        "APP_MAIL_FROM": "no-reply@localjoin.in",
        "RESEND_API_KEY": "local_fake_key_never_sends",
        "APP_SUPPORT_EMAIL": "support@localjoin.in",
        "UPLOAD_DISK_REQUIRED": "false",
        "TRUST_PROXY": "false",
        "FORCE_HTTPS": "true",
        "SESSION_COOKIE_SECURE": "true",
        "APP_ADMIN_MFA_REQUIRED": "true",
        "APP_REQUIRE_EMAIL_VERIFICATION": "true",
        "SECURITY_CSP_MODE": "enforce",
    })
    env.update(overrides)
    proc = subprocess.run(
        [sys.executable, "-c", "from config.settings import production_config_errors; print(repr(production_config_errors()))"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=20,
    )
    assert proc.returncode == 0, proc.stderr
    import ast
    return ast.literal_eval(proc.stdout.strip())


def test_unblocking_unverified_keeps_pending_when_verification_required():
    assert status_after_unblock(None, True) == "pending"


def test_unblocking_verified_allows_active_account():
    assert status_after_unblock(datetime(2026, 1, 1), True) == "active"


def test_unblocking_legacy_when_verification_disabled():
    assert status_after_unblock(None, False) == "active"


def test_valid_production_web_config_stays_accepted():
    assert _production_errors() == []


def test_production_web_rejects_log_or_disabled_mail():
    for driver in ("log", "disabled", "none"):
        assert any("APP_MAIL_DRIVER" in e for e in _production_errors(APP_MAIL_DRIVER=driver))


def test_production_web_rejects_contact_without_support_mailbox():
    assert any("APP_SUPPORT_EMAIL" in e for e in _production_errors(APP_SUPPORT_EMAIL=""))


def test_sender_and_support_must_be_plain_email_addresses():
    assert any("APP_MAIL_FROM" in e for e in _production_errors(APP_MAIL_FROM="Localjoin <user@example.com>"))
    assert any("APP_SUPPORT_EMAIL" in e for e in _production_errors(APP_SUPPORT_EMAIL="bad-example"))


def test_production_auto_schema_optin_is_rejected():
    assert any("AUTO_INIT_SCHEMA" in e for e in _production_errors(AUTO_INIT_SCHEMA="true"))


def test_production_cron_without_mail_is_accepted_with_isolated_worker_role():
    assert _production_errors(LOCALJOIN_WORKER_ONLY="true", APP_MAIL_DRIVER="disabled", APP_SUPPORT_EMAIL="") == []


def test_production_defaults_disable_auto_schema():
    env = os.environ.copy()
    env.update({"APP_ENV": "production", "DATABASE_URL": "mysql+pymysql://ci:ci@localhost/localjoin_ci"})
    env.pop("AUTO_INIT_SCHEMA", None)
    proc = subprocess.run(
        [sys.executable, "-c", "from config.settings import BaseConfig; print(BaseConfig.AUTO_INIT_SCHEMA)"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=20,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "False"


def test_production_app_only_runs_auto_schema_in_nonproduction():
    source = (ROOT / "app.py").read_text()
    assert 'app.config.get("AUTO_INIT_SCHEMA", False) and app.config.get("APP_ENV") != "production"' in source
    assert "db.create_all()" in source  # dev & disposable testing still supported


def test_render_config_declares_no_auto_migration_for_web_and_cron():
    source = (ROOT / "render.yaml").read_text()
    assert source.count("key: AUTO_INIT_SCHEMA") == 2
    assert "key: LOCALJOIN_WORKER_ONLY" in source


def test_admin_unblock_does_not_override_pending_or_inactive_status_without_block():
    source = (ROOT / "routes/admin.py").read_text()
    assert 'action == "unblock" and target.status != "blocked"' in source
    assert "status_after_unblock(" in source
