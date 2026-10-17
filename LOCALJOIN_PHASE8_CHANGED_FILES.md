# Phase 8 — Code changes relative to Phase 7 ZIP

**Modified (6):**
- `routes/main.py` — requirement claim and status update rollback/error recovery; sanitized reference logs
- `routes/provider.py` — factored shared eligible-requirements rendering without changing provider URL
- `routes/business.py` — adds business-specific eligible-requirements endpoint with business role guard
- `templates/business/dashboard.html` — business-specific discovery link
- `scripts/run_phase4_recheck_offline.py` — Phase 7 SEO and Phase 8 request recovery checks included
- `.github/workflows/localjoin-runtime-tests.yml` — Phase 8 offline check step; runtime suite still enforces zero skips

**Added tests (2):**
- `tests/python/test_phase8_request_recovery_offline.py` — 3 passed source-contract tests
- `tests/python/test_phase8_request_recovery_runtime.py` — 3 authored Flask/SQLite integration tests, **not run successfully**

**Documentation added/updated:** `PHASE8.md`, `LOCALJOIN_PHASE8_RELEASE_REPORT.md`, `LOCALJOIN_PHASE8_TEST_RESULTS.md`, this file, plus cumulative summaries/guides. No existing application files were removed, and no schema changes were made.
