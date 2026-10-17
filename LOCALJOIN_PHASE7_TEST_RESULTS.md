# Phase 7 — Actual Test Execution Results

Date: 17 October 2026. Execution was local against the copied Phase 6 source; **no production write, no actual MySQL 8 connection, no Resend send, no real Flask route tests**.

## Completed

| Executed test/check | Result |
|---|---|
| `python -m pytest -q tests/python/test_phase7_seo_discovery_offline.py` | **11 passed**, 0 failed, 0 skipped |
| `python -m pytest -q tests/python --ignore=tests/python/test_localjoin_runtime_regressions.py --ignore=tests/python/test_phase3_database_runtime.py --ignore=tests/python/test_phase4_auth_runtime.py --ignore=tests/python/test_phase4_journey_matrix_runtime.py --ignore=tests/python/test_phase5_functional_runtime.py --ignore=tests/python/test_phase5_security_hardening_runtime.py --ignore=tests/python/test_phase8_release_runtime.py -rs` | **147 passed, 5 skipped, 18 subtests passed**; no test failures in this subset. The five were skipped inside a test module because Flask was missing. |
| `python scripts/run_offline_model_integration.py` | PASS: 32 real SQLAlchemy model tables on disposable SQLite, MySQL DDL syntax compilation, three roles, offering, request/history, rollback, duplicate email UNIQUE enforcement. **Not a MySQL 8 server test.** |
| `python -m compileall -q app.py routes services models config utils scripts tests/python` | PASS |
| Jinja2 parsing all `templates/**/*.html` | **62 parsed**, no parse errors |
| `node --check assets/js/app.js` and `node tests/js/dependent_dropdown.test.js` | PASS |
| `php -l` over all repository PHP files | **93 passed** |
| PyYAML parsing `.github/workflows/localjoin-runtime-tests.yml` | PASS, 3 jobs |

## Failed / blocked (not counted as successful tests)

| Gate | Result and exact blocker |
|---|---|
| `python scripts/run_runtime_tests.py` | **exit 2**. Missing Flask, Flask-SQLAlchemy, Flask-WTF, WTForms, PyMySQL, bcrypt, PyNaCl, gunicorn. No Flask tests actually ran. |
| `python -m pip install --disable-pip-version-check --no-cache-dir --retries 0 --timeout 4 'Flask==3.1.3' 'Werkzeug==3.1.9'` | **exit 1**; configured package index returned no matching packages; cannot conclude pins are inherently unavailable online. |
| `python scripts/check_release_content.py` | **exit 1**; privacy/terms placeholders require review. This is an intentional production-release failure, not a test reported as passed. |
| Disposable MySQL 8 CI smoke | **NOT EXECUTED**, neither `mysqld`, `mysql`, `docker` nor `podman` available locally. The GitHub Actions service job remains unverified. |
| Live web/Resend/Render staging browser smoke | **NOT EXECUTED**; no staging authorization/credentials or connected service test environment. |

## Evidence files

- `LOCALJOIN_PHASE7_OFFLINE_TESTS.log`
- `LOCALJOIN_PHASE7_STRICT_RUNTIME_GATE.log`
- `LOCALJOIN_PHASE7_DEPENDENCY_INSTALL.log`
- `LOCALJOIN_PHASE7_ORM_SQLITE.log`
- `LOCALJOIN_PHASE7_SYNTAX.log`
- `LOCALJOIN_PHASE7_CONTENT_GATE.log`

**Release gate:** BLOCKED. A broad offline subset passing with skipped tests does **not** satisfy the strict 0-skips full Flask/MySQL requirement.
