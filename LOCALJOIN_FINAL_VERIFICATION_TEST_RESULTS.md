# Final Verification — Recorded Commands & Outcomes

Executed locally on 17 October 2026, starting from the unmodified Phase 8 archive extracted into an isolated copy; new release-gate scripts/tests were added to that copy.

| Command / check | Recorded outcome |
|---|---|
| `python scripts/run_phase4_recheck_offline.py` | **Exit 0**. `162 passed, 18 subtests passed`; actual in-memory SQLite ORM/DDL checks; compileall; Node JS dropdown behavior. |
| Jinja2 parse of `templates/**/*.html` | **PASS: 62 templates** |
| `php -l` for each `.php` source | **PASS: 93 files, 0 lint failures** |
| `python scripts/run_runtime_tests.py` | **Exit 2, BLOCKED** (missing dependencies); no Flask tests claimed passed. |
| `python scripts/run_disposable_mysql_smoke.py` | **Exit 2, BLOCKED** (safety guard refuses unconfigured disposable DB); not a MySQL server test. |
| `python scripts/check_release_content.py` | **Exit 1, FAILED**, Privacy/Terms development templates. |
| `python scripts/run_public_readonly_smoke.py --base-url https://localjoin.in --timeout 2` | **Exit 1, UNVERIFIED**. 8/8 endpoints returned `URLError` due to this execution environment; no live outage conclusion. |
| `python -m pip install --isolated --no-cache-dir --retries 0 --timeout 5 --target /tmp/localjoin_runtime_deps 'Flask==3.1.3'` | **Exit 1**. No package available through this runtime. Not proof that version is absent from external package indexes. |
| `python scripts/check_release_package.py <candidate-zip>` | ZIP CRC and sensitive-file path structure checked after packaging; SHA-256 emitted. |
| `python scripts/check_release_evidence.py --candidate <zip> --evidence release/PRODUCTION_EVIDENCE_EXAMPLE.json` | **HOLD** expected: no real approvals/runs; example is deliberately pending. |

**Scope:** The offline subset recorded zero skipped tests. The real Flask tests remain **unexecuted**, not counted as successful or hidden as skipped. Real MySQL 8, Resend inbox, payment isolation, mobile browsers and Render staging/production are not verified.

**Original logs (outside archive):** `FINAL_RELEASE_OFFLINE_CHECKS_UPDATED.log`, `FINAL_RELEASE_FLASK_GATE.log`, `FINAL_RELEASE_CONTENT_GATE.log`, `FINAL_RELEASE_PHP_LINT.log`, `FINAL_RELEASE_PUBLIC_GET_ATTEMPT.log`, `FINAL_RELEASE_MYSQL_GUARD.log`.
