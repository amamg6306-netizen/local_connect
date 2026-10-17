# Localjoin.in — Phase 5 Exact Test Results

**Date:** 17 October 2026; runner Python 3.13; no production credentials used.

| Actual command or operation | Result |
|---|---|
| `python -m pytest -q tests/python/test_*static.py tests/python/test_phase2_navigation_regression.py tests/python/test_phase4_runtime_configuration_offline.py tests/python/test_phase5_security_hardening_offline.py` | **PASS:** 108 tests and 18 subtests, 0 skips and 0 failures in offline subset |
| `python -m compileall -q app.py routes services models config utils scripts tests/python` | PASS |
| Parse Jinja templates with installed `jinja2.Environment().parse` | PASS, 62 templates |
| `node --check assets/js/app.js` | PASS |
| `node tests/js/dependent_dropdown.test.js` | PASS |
| `php -l` on every `.php` source file | PASS, 93/93 |
| `yaml.safe_load(render.yaml)` | PASS, 2 Render service declarations |
| `python -m pytest -q tests/python` | **FAIL (exit 2):** 3 collection errors (missing Flask); full tests never executed |
| `python scripts/run_runtime_tests.py` | **FAIL (exit 2):** missing Flask, Flask-SQLAlchemy, Flask-WTF, WTForms, PyMySQL, bcrypt, PyNaCl, gunicorn |
| `python -m pip install --disable-pip-version-check --retries 0 --timeout 3 -r requirements.txt` | **FAIL (exit 1):** configured package repository has no installable Flask==3.1.3 in this environment |
| MySQL 8 staging/disposable smoke | NOT EXECUTED |
| Real Resend inbox and Render deploy | NOT EXECUTED |

Full command output is in `LOCALJOIN_PHASE5_OFFLINE_TESTS.log`, `LOCALJOIN_PHASE5_FULL_SUITE_ATTEMPT.log`, `LOCALJOIN_PHASE5_STRICT_RUNTIME_GATE.log`, and `LOCALJOIN_PHASE5_PIP_INSTALL.log` (separate files outside the ZIP). Flask integration regression source files are bundled but **are not counted as passes**.

**Release gate remains RED.** Do not infer a production-ready result from the offline successes.
