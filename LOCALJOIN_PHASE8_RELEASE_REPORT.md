# Localjoin.in — Phase 8 Release Verification & Repairs

**Date:** 17 October 2026  
**Starting artifact:** `Localjoin_Phase7_Finalization_RELEASE_GATES_PENDING.zip`  
**Decision:** **HOLD — NOT PRODUCTION-READY, NOT DEPLOYED**

## What actually changed

1. **Business requirement discovery URL:** added `/business/available-requirements.php`, using the same existing, permission-checked query/filtering logic as the provider listing; switched the Business Dashboard link to this business-specific URL. Original `/provider/available-requirements.php` remains supported.
2. **Claim failure recovery:** a stale/invalid claim now rolls back and displays a meaningful error; an unexpected database/notification failure rolls back, logs only an exception *type* and random reference, and returns to the correct role's requirements listing. No account details, request text or tokens are logged.
3. **Status transition failure recovery:** unexpected failures after changing a request status/history/notification roll back and produce a safe reference-bearing error instead of an uncaught 500. The pre-existing row lock and authorization/status-transition revalidation are preserved.
4. **Regression coverage:** 3 new executed offline/source-contract checks and 3 new *unexecuted* real Flask/SQLite test-client scenarios covering business-only route authorization, claim rollback, and status rollback. Registered offline checks with local runner and CI. Full Flask CI job collects the new runtime test module automatically.

### Scope and preservation

No production MySQL, Render service, Resend account, real payment, or live customer record was modified. Existing legacy Flask/PHP-compatible paths, pricing, roles and payment code remain in the package. No schema migration was introduced in Phase 8.

## Execution evidence

| Gate | Status | Evidence |
|---|---|---|
| Offline Python suite (includes new 3 cases) | **150 PASS**, 18 subtests PASS, 0 skipped in explicitly selected suite | `LOCALJOIN_PHASE8_OFFLINE_FINAL.log` |
| SQLAlchemy model exercise | PASS — 32 tables created in SQLite, duplicate-email constraint and request/history rollback; MySQL DDL **compile only** | same log |
| Python compilation, JavaScript syntax and dropdown | PASS | same log |
| Jinja templates | 62 parsed PASS | independent Jinja parse |
| PHP lint and helper regression | 93 files syntax PASS; Phase 2/3/4/6 helpers PASS | PHP lint log |
| Embedded secret scan | PASS (scanner heuristics only) | `LOCALJOIN_PHASE8_SECRET_SCAN.log` |
| New Flask request-recovery module | **BLOCKED**: `ModuleNotFoundError: flask`, 1 collection error | `LOCALJOIN_PHASE8_NEW_FLASK_ATTEMPT.log` |
| Full strict Flask suite | **BLOCKED**, exit code 2: Flask, Flask-SQLAlchemy, Flask-WTF, WTForms, PyMySQL, bcrypt, PyNaCl, gunicorn unavailable | `LOCALJOIN_PHASE8_STRICT_GATE.log` |
| Disposable MySQL 8 | **NOT EXECUTED**: no local server/Docker; safe smoke preflight refused missing opt-in (exit 2) | `LOCALJOIN_PHASE8_MYSQL_GUARD.log` |
| Privacy/Terms content gate | **BLOCKED**, exit code 1: two development policy placeholders | `LOCALJOIN_PHASE8_LEGAL_GATE.log` |
| GitHub Actions | NOT RUN: repository integration and external CI results unavailable | pending |
| Resend and Render staging, mobile browser, production | NOT TESTED / NOT DEPLOYED | pending |

A `pip download` probe could not retrieve pinned Flask from the configured environment; this does **not** demonstrate that the pinned version is nonexistent on PyPI. See `LOCALJOIN_PHASE8_PIP_PROBE.log`. Public GET through available web tool could not reach `localjoin.in` during this phase, so no new production status is asserted.

**No skipped or unexecuted runtime tests are treated as passed.** This release is not allowed into production merely because local static and SQLite ORM checks succeeded.

## Next release gates (in order)

1. Connect a real repository and run `.github/workflows/localjoin-runtime-tests.yml` (`integration`, `disposable-mysql`, `release-content`). Preserve raw logs and rerun after addressing any failures. The runtime job disallows skips.
2. Have the site owner approve final Privacy and Terms content; replace legal templates, and independently sign off on the content, retention, support, consent and payment disclosures. Do not remove placeholder markers just to game CI.
3. Run staging MySQL 8 preflight and clean disposable smoke **only on fresh `localjoin_ci`**, never customer data, then execute reviewed migrations on a separate backed-up staging database.
4. Validate Customer/Provider/Business signup, verified email delivery, login, request creation, claim/status history and rollback, role authorization, contact inbox receipt, browser dropdown/mobile nav and payment isolation in staging.
5. Use the Render rollback procedure documented in `LOCALJOIN_RENDER_DEPLOYMENT_GUIDE.md`. Promote to live only with recorded passing evidence for each gate.

**Release owner decision:** HOLD.
