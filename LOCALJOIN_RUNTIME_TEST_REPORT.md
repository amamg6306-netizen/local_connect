# Localjoin.in — Runtime test recheck (2026-10-17)

**Status: STRICT FLASK RUNTIME GATE FAILED/BLOCKED (exit code 2). NOT production-ready.**

## What was actually run

| Command | Result | Meaning |
|---|---|---|
| `python -m pip install --disable-pip-version-check --no-input -r requirements.txt` | **FAILED** | Network DNS failure accessing package index; Flask packages could not be installed. See external install log. |
| `python scripts/run_runtime_tests.py` | **BLOCKED, exit 2** | Deliberate fail-closed check: Flask, Flask-SQLAlchemy, Flask-WTF, WTForms, PyMySQL, bcrypt, PyNaCl, gunicorn missing. No Flask test has been falsely labeled passed. |
| `python -m pytest -q tests/python --ignore=tests/python/test_localjoin_runtime_regressions.py` | **86 passed / 20 skipped / 0 failed** | Historical static/offline suite. The 20 skips are **unresolved runtime tests**, not success. The new tests were excluded because Flask is unavailable. |
| `python -m compileall -q app.py routes services models config utils scripts tests/python/test_localjoin_runtime_regressions.py` | **PASSED** | Python syntax only; does not run Flask routes. |
| Jinja parsing of `templates/**/*.html` | **62 passed, 0 parse errors** | Template syntax only. |
| `node --check assets/js/app.js` | **PASSED** | JS syntax. |
| `node tests/js/dependent_dropdown.test.js` | **PASSED** | JavaScript dropdown runtime behavior in mocked DOM. |
| `python -m pytest -q tests/python/test_phase2_navigation_regression.py` | **2 passed** | Real Python validation of allowed/blocked login redirects. |
| `php tests/phase{1,2,3,4,6}/*helpers*.php` | **PASSED** | Legacy PHP helper runtime checks only; NOT Flask/MySQL integration tests. See separate log for exact scripts and results. |

## Newly authored integration tests (added, NOT YET EXECUTED)

`tests/python/test_localjoin_runtime_regressions.py` contains 7 tests for:

1. Customer, provider, and business registrations with verification requirements and duplicate email handling.
2. Pending customer recovery via mocked resend mail, email verification, and login.
3. Excluding a service-less provider from service search and request CTA.
4. Rejecting invalid category-service request combinations; persisting valid requirement plus initial status-history.
5. Rejecting direct requests to unoffered services, and accepting eligible requests with status-history.
6. Preserving an intended customer login destination without allowing external URL redirects.
7. Contact form: failure when mail API declines, success only when mocked provider accepts.

These tests use **in-memory SQLite**, **mocked email**, and **no live production writes**. Even when they pass, staging MySQL / Resend acceptance & delivery / actual browser checks will remain separate deployment gates.

## Changes to prevent silent skips

- `scripts/run_runtime_tests.py`: validates dependencies, runs pytest, and fails if any tests are skipped, or none collected. When dependencies are unavailable it exits **2** rather than claiming green tests.
- `.github/workflows/localjoin-runtime-tests.yml`: installs pinned dependencies on a network-capable CI runner, exercises Node and entire strict Python suite, and fails the build on missing dependencies, test failures or skipped tests.
- The new integration tests above test essential repaired flows without production credentials; email API calls are mocked.

## Real website public GET check

Read-only inspection of https://localjoin.in shows the public homepage/login and provider/business registration pages reachable, while contact form still reports it only validates input, and search still lists known service-less profiles. This strongly indicates that the patched source has not been deployed. Some URLs did not load through the inspection tool, so no HTTP status can be asserted for those URLs. No account creation, live POST, email, payment or database write attempted.

## To run the mandatory runtime gate with package access

```bash
python -m pip install -r requirements.txt pytest
APP_ENV=testing APP_URL=https://localjoin.in DATABASE_URL=sqlite:///:memory: \
  APP_MAIL_DRIVER=log UPLOAD_DISK_REQUIRED=false FORCE_HTTPS=false \
  python scripts/run_runtime_tests.py
```

Use `.github/workflows/localjoin-runtime-tests.yml` in GitHub Actions to execute this automatically after committing/uploading the complete repository. A green GitHub Actions run would confirm local Flask+SQLite runtime tests only. For the actual website, separately configure a **staging** database with MySQL-compatible schema and a safe email test inbox before end-to-end confirmation. Do not send automated test submissions or emails to live users.

**Pass condition:** zero skips, zero failures, successful Flask integration tests, staging MySQL test run, verified Resend acceptance/delivery and safe browser smoke checks. **Not yet met.**
