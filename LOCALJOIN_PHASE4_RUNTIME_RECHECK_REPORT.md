# Localjoin.in — Phase 4 runtime recheck (after Phase 5 security updates)

**Date:** 17 October 2026  
**Input:** `Localjoin_Phase5_Security_Hardening_RUNTIME_PENDING.zip` (retains Phase 4 tests)  
**Decision:** **FULL PHASE 4 NOT VERIFIED; production release blocked.**

## What actually ran (no production access)

| Check | Actual result |
|---|---|
| Offline pytest subset (static/config/navigation/safety) | **116 passed; 18 unittest subtests passed; 0 failed, 0 skipped** *in this subset only* |
| Actual SQLAlchemy ORM models + disposable in-memory SQLite | **PASS:** 32 tables, Customer/Provider/Business rows, ProviderService, request/history commit, rollback, duplicate-email unique constraint |
| MySQL dialect DDL compilation from 32 actual models | **PASS:** compilation only, **not** MySQL server execution |
| Node dropdown runtime behavior + JavaScript syntax | **PASS** |
| Jinja template syntax | **62 PASS** |
| PHP syntax | **93 PASS** |
| Python syntax compilation | **PASS** |
| GitHub Actions YAML parse | **PASS:** two jobs, one configured for `mysql:8.0` |
| Strict **Flask** runtime suite | **BLOCKED, exit 2:** no Flask / Flask-SQLAlchemy / Flask-WTF / WTForms / PyMySQL / bcrypt / PyNaCl / Gunicorn |
| Disposable **MySQL 8 server** smoke | **NOT EXECUTED:** no local MySQL server, client, Docker, or MySQL test service. Its deliberately no-opt-in invocation returned exit 2. |
| PyPI dependency installation | **FAILED, exit 1:** package repository unreachable (DNS/network); not evidence that package version is nonexistent |
| Production `localjoin.in`, Render, Resend integration | **NOT TESTED**; no live POSTs, test accounts, writes, or email sends |

**Do not interpret 116 passing offline tests as full suite success or the MySQL DDL compile as a MySQL 8 server pass.**

## Code changes in this recheck

1. `scripts/run_disposable_mysql_smoke.py`: added explicit preflight requiring `APP_ENV=testing`, opt-in, exact `localjoin_ci` database name, localhost/127.0.0.1, and matching `DATABASE_URL`. Prevents accidental import-time `AUTO_INIT_SCHEMA` writes. Checks MySQL server version, connected database, and **empty database** before any DDL. Explicitly creates Customer, Provider, Business, category/service, request/history; checks transaction commit/rollback and duplicate-email protection. Cleans up only the initially empty, verified CI schema it created.
2. `.github/workflows/localjoin-runtime-tests.yml`: retained zero-skip Flask gate, isolated `mysql:8.0` service; disabled import-time automatic schema creation in MySQL job; added actual ORM model smoke.
3. `tests/python/test_phase4_mysql_guard_extended_offline.py`: **8 new executed guard tests**, covering local eligibility, wrong host/name, mismatched app URL, non-testing env, malformed port, no opt-in, and wrong database driver.
4. `scripts/run_offline_model_integration.py`: process-isolated SQLAlchemy schema test against **actual Localjoin ORM models**, plus MySQL DDL compilation. Not a Flask or MySQL server test.
5. `scripts/run_phase4_recheck_offline.py`: reproducible offline subset, explicitly labeled not equivalent to full runtime.

No production application routes, business logic, or credentials were changed in this recheck.

## Commands executed and source of truth

* `python scripts/run_phase4_recheck_offline.py` — PASS; see `LOCALJOIN_PHASE4_RECHECK_OFFLINE_LOG.txt`.
* `python scripts/run_runtime_tests.py` — FAIL, exit 2; see `LOCALJOIN_PHASE4_RECHECK_STRICT_FLASK_LOG.txt`.
* `APP_ENV=testing DATABASE_URL='mysql+pymysql://localjoin_ci:ci_only_password@127.0.0.1:3306/localjoin_ci' LOCALJOIN_DISPOSABLE_DB_URL='mysql+pymysql://localjoin_ci:ci_only_password@127.0.0.1:3306/localjoin_ci' python scripts/run_disposable_mysql_smoke.py` — correctly BLOCKED, exit 2, **no opt-in**. This is only a safety test, not a DB smoke pass; see `LOCALJOIN_PHASE4_RECHECK_MYSQL_GUARD_LOG.txt`.
* `python -m pip install --disable-pip-version-check --retries 0 --timeout 4 --index-url https://pypi.org/simple -r requirements.txt` — FAIL; see `LOCALJOIN_PHASE4_RECHECK_DEPENDENCY_LOG.txt`.
* Jinja parse/PHP lint/YAML parse — PASS; see `LOCALJOIN_PHASE4_RECHECK_TEMPLATES_PHP_LOG.txt`.

## Mandatory unfinished acceptance tests

**Flask:** run the **actual** `scripts/run_runtime_tests.py` with dependencies installed; all existing Phase 2–5 regression and role-flow cases must execute with **zero skips, failures, and collection errors**.

**MySQL 8:** run the **actual** disposable MySQL CI job, verify 32 tables, three role IDs, category/service, request + status history, successful rollback and unique-email database constraint with cleanup. Never use a real/staging/production database or put production credentials into CI.

**External deployment:** separately verify Render startup, staging MySQL schema, Resend delivery to a controlled inbox, and browser routes after both CI jobs are green.

**How to run:** see `LOCALJOIN_PHASE4_CI_RUNBOOK.md`. Workflow is authored, **not reported as executed**. No GitHub repo/session was provided here for triggering it.
