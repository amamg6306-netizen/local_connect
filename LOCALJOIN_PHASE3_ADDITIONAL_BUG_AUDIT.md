# Localjoin.in — Phase 3 additional bug audit and repair report

**Date:** 2026-10-17  
**Status:** PHASE 3 INTERIM SOURCE FIXES. NOT PRODUCTION-READY.  
**Input:** Phase 2 runtime-test-gate ZIP (not the original pre-fix ZIP). Separate source workspace; no live DB records changed.  
**Scope:** Additional defects found in marketplace service management, offer eligibility, featured discovery, data validation, and offline integration-test infrastructure, plus read-only route/security review.

## Confirmed source-level defects and implemented repairs

| ID | Verified source behavior / root cause | Files changed / implemented fix | Verification | Remaining gate |
|---|---|---|---|---|
| P3-01 | Provider and Business service pages exposed add and delete, but no update or pause/resume actions; stale listings remained bookable until removed. | `routes/provider.py`, `templates/provider/services.html`, `templates/business/services.html`: owner-checked update/toggle, active category/service preflight on add/reactivation, price validation, sanitized failure handling and UI forms. | Python syntax, Jinja parse, 2 offline structural tests pass; four new Flask runtime cases authored, not run. | Flask and staging DB action tests, mobile UI test. |
| P3-02 | Claim eligibility checked the provider_services row but not whether its catalogue Service and Category were still active, including after the locked row was re-read. | `routes/main.py`: `_eligible_requirement_offering()` uses joined active service+category criteria; claims revalidate in the transactional lock. `routes/provider.py`: offered requirement feed also rejects inactive catalogue records. | AST/static assertions pass; claim-denial Flask test authored but unexecuted. | Staging MySQL concurrency and status-history checks. |
| P3-03 | Featured homepage providers/businesses could appear without an active category, service, and offering; dashboard service counts also included inactive entries. | `routes/main.py`, `routes/provider.py`, `routes/business.py`: readiness existence filters, catalogue-aware active service counts. | Source review and static test; no live homepage verification. | Flask query compilation and actual MySQL query checks. |
| P3-04 | `decimal_or_none()` did not reject non-finite Decimal values before comparisons; `Decimal("NaN")` triggers `InvalidOperation` instead of the intended input validation. | `services/marketplace_service.py`: explicit `is_finite()` check. | Real Python production-function AST extraction test passes for NaN, sNaN, +/-Infinity and valid values; Flask request test authored, not executed. | Real Flask budget validation check. |
| P3-05 | SQLAlchemy BIGINT_PRIMARY_KEY on SQLite does **not** autoincrement unless compiled as `INTEGER PRIMARY KEY`, causing offline integration tests to fail to insert users/profiles without IDs. | `models/base.py`: **SQLite-only** `Integer()` variant for `BIGINT_UNSIGNED`; MySQL remains `BIGINT UNSIGNED`. | Actual `sqlite:///:memory:` insert using extracted production SQLAlchemy type passes, MySQL dialect compiles as `BIGINT UNSIGNED`; before-fix reproducer raised IntegrityError. | Complete Flask/SQLite runtime suite still blocked by dependency availability. |

No destructive migrations, credential changes, payment flows or existing public route names changed. No live database writes attempted.

## Additional review: confirmed vs suspected

- **Examined routes:** Authentication, customer requests, provider/business dashboards, service management, admin actions, billing, signed payment webhook, reviews, favorites, health and contact. Route guard inventory is in `LOCALJOIN_PHASE3_ROUTE_SECURITY_INVENTORY.csv`. Route guard presence is a source-level inspection, **not** proof of end-to-end authorization safety.
- **No payment/subscription logic changed.** Payment gateway signature verification, webhook processing, entitlement and admin MFA flows remain integration-test / sandbox-regression candidates; no new payment defect is confirmed by this audit.
- **Unresolved pre-existing Phase 2 items:** mail delivery, account creation across all roles, password resets, POST request atomicity in MySQL, no-available-service empty categories, contact Resend acceptance/delivery, mobile bootstrap behavior and production logs. These are NOT recorded as passed.
- **Production startup review note:** `app.py` invokes `db.create_all()` and default category creation in the application factory. This can create schema objects during web startup; review operational migration policy and staging privileges before deployment. This was *not changed* in this pass, because production deployment behavior was not available to validate a compatible alteration.
- **Live site:** GET checks through the available external tool did not return usable pages during this pass; current `localjoin.in` deployment version could not be independently confirmed. No claim of live deployment or live fix.

## Change boundaries

Changed files are listed in `LOCALJOIN_PHASE3_CHANGED_FILES.csv`; no original source deletions. Old Phase 1 and Phase 2 releases remain untouched. Existing route names and payment implementations are retained. Updated service forms reuse original CSRF tokens.

## Test / release status

- Offline/test infrastructure: **91 passed, 20 skipped, 0 failed**, plus 18 successful unittest subtests. These 20 skips remain outstanding legacy Flask runtime tests.
- **Strict runtime gate fails (exit 2):** Flask, Flask-SQLAlchemy, Flask-WTF, WTForms, PyMySQL, bcrypt, PyNaCl and Gunicorn not installed; package installation previously blocked by package DNS failure.
- **New Phase 3 Flask runtime tests: 4 written, 0 executed**, in addition to Phase 2's 7 previously authored/unexecuted integration cases.
- Python syntax, 62 Jinja templates, Node syntax, JS dropdown runtime, legacy PHP helper smoke tests: pass. See `LOCALJOIN_PHASE3_TEST_RESULTS.txt`.
- **Ready for staging?** No complete verification yet. **Production-ready?** No. No Render deploy or MySQL/Resend end-to-end run.

## Next necessary execution (do not skip)

On a network-capable CI runner with isolated SQLite and mocked mail:

```bash
python -m pip install -r requirements.txt pytest
APP_ENV=testing APP_URL=https://localjoin.in APP_MAIL_DRIVER=log \
  FORCE_HTTPS=false UPLOAD_DISK_REQUIRED=false \
  python scripts/run_runtime_tests.py
```

Treat ANY skip as a failure (already enforced by `scripts/run_runtime_tests.py`). Then run safe tests against **staging MySQL**, configured Resend test inbox, and Playwright / mobile viewport smoke checks. Use a migration-reviewed staging release and backout plan; never run automated test writes against production.
