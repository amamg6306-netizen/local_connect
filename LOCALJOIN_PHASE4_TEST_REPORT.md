# Localjoin.in — Phase 4 testing and regression report

**Date:** 17 October 2026  
**Input:** `Localjoin_Phase3_Additional_Fixes_RUNTIME_PENDING.zip` / Phase 3 project state  
**Phase 4 status:** **PARTIAL; STRICT RUNTIME GATE FAILS. NOT READY FOR PRODUCTION.**

## Changes actually implemented in this phase

1. Fixed `config/settings.py` test-environment engine handling: when `DATABASE_URL` is SQLite, Flask-SQLAlchemy no longer receives MySQL-specific connection timeouts/pool arguments. MySQL production engine options remain unchanged.
2. Fixed `TestingConfig.TRUSTED_HOSTS` to include the real Flask test-client default `localhost` (and test loopback) while retaining host validation. **Production BaseConfig host restrictions remain unchanged.**
3. Added `tests/python/test_phase4_journey_matrix_runtime.py` with **9 parametrized Flask test-client cases** for three account roles, role access, service CRUD with owner isolation for Provider and Business, direct Business requests/history, requirement transaction rollback, actual CSRF validation enabled, and test-client trusted-host enforcement. **Authored, syntax-checked; NOT executed successfully in this machine.**
4. Added `scripts/run_disposable_mysql_smoke.py`: smoke test for real MySQL 8 schema, primary keys, requirement/history persistence and duplicate-email constraints, protected by explicit opt-in **and database-name suffix `_ci`**. Its no-write safety guard was executed and passed; the MySQL smoke itself is not executed locally.
5. Updated `.github/workflows/localjoin-runtime-tests.yml` with isolated disposable MySQL 8 service and strict full Flask/SQLite test job; pipeline syntax parsed. **No GitHub Actions job was run from this workspace.**
6. Added 4 locally executed offline config/guard regression tests and a repeatable `scripts/phase4_verify_local.py` runner that correctly returns **failure** when the strict runtime check is blocked.

## Exact local execution results

| Verification | Actual result |
|---|---|
| `python -m pytest -q tests/python/test_*static.py tests/python/test_phase2_navigation_regression.py` (plus new offline config test in repeatable runner) | **95 passed, 18 unittest subtests passed, 0 failed, 0 skipped** in explicit offline-only selection |
| `python -m compileall -q app.py routes services models config utils scripts tests/python` | PASS |
| Jinja2 parse all templates | **62 parsed, 0 errors** |
| `node --check assets/js/app.js` | PASS |
| `node tests/js/dependent_dropdown.test.js` | PASS |
| PHP helper smoke scripts (phase 1/2/3/4/6) | PASS |
| `php -l` all 93 legacy PHP files | **93 passed, 0 errors** |
| Parse CI YAML workflow, verify both job definitions | PASS |
| `python scripts/run_disposable_mysql_smoke.py` (without opt-in) | Guard **correctly rejected** write (exit 2), not a MySQL schema test |
| `python -m pytest -q tests/python` (entire suite) | **FAIL, exit 2** — 2 test collection errors: missing `flask` |
| `python scripts/run_runtime_tests.py` (strict 0-skips release gate) | **FAIL, exit 2** — Flask, Flask-SQLAlchemy, Flask-WTF, WTForms, PyMySQL, bcrypt, PyNaCl, Gunicorn not installed |
| `python -m pip install --disable-pip-version-check --retries 0 --timeout 4 -r requirements.txt` | **FAILED** — package index DNS unavailable; no package installation achieved |
| Disposable MySQL 8 CI integration run | **NOT EXECUTED** (no MySQL/container/credentials in this workspace) |
| Resend real inbox delivery / Render app / real browser/mobile | **NOT EXECUTED** (unavailable external systems or runtime) |

The offline suite deliberately **excludes Flask-only test modules**, so its *zero skipped* result must **not** be interpreted as the full application test suite passing. In the previous Phase 3 constrained-environment run, 20 Flask-dependent tests were skipped. This Phase 4 release gate keeps dependency failures visible and red, rather than treating those tests as green.

## Command to run full Flask test gate on network-capable CI/dev runner

```bash
python -m pip install -r requirements.txt pytest
APP_ENV=testing APP_URL=https://localjoin.in \
  DATABASE_URL='sqlite:///:memory:' \
  APP_MAIL_DRIVER=log APP_REQUIRE_EMAIL_VERIFICATION=true \
  UPLOAD_DISK_REQUIRED=false FORCE_HTTPS=false \
  python scripts/run_runtime_tests.py
```

This requires all pinned packages and does **not** send emails or use live database credentials. Any missing dependency, skip, collection error, or assertion failure must block release.

## Separate disposable MySQL 8 smoke

The new workflow provisions a fresh `localjoin_ci` schema in an isolated MySQL service and runs the smoke with an explicit allow-disposable flag. The MySQL script **creates and drops schema objects** and must **NEVER** be pointed at staging with real users or production. The mandatory suffix/opt-in guard is defense in depth and not permission to use production data.

Staging MySQL testing against a non-disposable, real dataset still needs separately reviewed safe read-only checks, staging log access, and test accounts. Email delivery requires controlled inbox and the real Resend sending-domain configuration. Browser/mobile tests require an appropriate browser runner.

## No production actions

No deployment to `localjoin.in`, no production database changes, no API-key access, no real email sends, and no live login or customer request writes were performed in this phase.

**Release decision:** **BLOCKED**. Source tests and added test coverage are useful, but **actual Flask runtime, MySQL, Resend, and staging/browser integration still need successful execution before production readiness can be claimed.**
