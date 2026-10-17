# Localjoin Phase 8 — Exact Test Status

Date: 2026-10-17. Working directory: extracted Phase 7 source plus Phase 8 changes.

| Command | Result |
|---|---|
| `python scripts/run_phase4_recheck_offline.py` | **EXIT 0:** 150 passed + 18 subtests; SQLite ORM, MySQL DDL compile, Python compile, Node syntax/behavior PASS |
| `python -m pytest -q tests/python/test_phase8_request_recovery_runtime.py` | **EXIT 2:** 1 collection error (`No module named 'flask'`); 0 tests passed |
| `python scripts/run_runtime_tests.py` | **EXIT 2:** missing Flask and other pinned packages, no tests run |
| `python scripts/check_release_content.py` | **EXIT 1:** Privacy and Terms are unapproved development templates |
| `python scripts/run_disposable_mysql_smoke.py` | **EXIT 2:** safe opt-in preflight refuses test; MySQL server absent |
| `python tools/secret_scan.py` | **EXIT 0:** no high-confidence hardcoded live secrets identified |
| `node --check assets/js/app.js` | EXIT 0 |
| `node tests/js/dependent_dropdown.test.js` | EXIT 0 |
| `find . -name '*.php' -print0 \| xargs -0 -n1 php -l` | EXIT 0: 93 PHP files |
| Jinja parse with `jinja2.Environment` | PASS: 62 templates |
| PHP helper scripts in tests/phase2, phase3, phase4, phase6 | PASS |
| `python -m pip download --no-deps --retries 0 --timeout 3 --dest ... Flask==3.1.3` | EXIT 1: wheel/index unavailable from this environment; no package installed |

The source-contract suite is not proof of Flask HTTP/runtime behavior. MySQL DDL compilation is not a running MySQL 8 service test. **Release gate: FAIL/HOLD.**
