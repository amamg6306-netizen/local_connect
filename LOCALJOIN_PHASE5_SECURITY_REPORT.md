# Localjoin.in — Phase 5 Security and Quality Audit

**Audit date:** 17 October 2026  
**Input:** `Localjoin_Phase4_Tests_Added_RUNTIME_BLOCKED.zip` / identical Phase 4 working directory  
**Output:** Phase 5 updated full source ZIP (interim only)  
**Release verdict:** **NOT production ready — full Flask, isolated MySQL, Resend, browser and Render deployment verification outstanding.**

## Source-level issues confirmed and repaired

| ID | Severity / actual root cause | Source patch | Evidence / limitations |
|---|---|---|---|
| P5-01 | **High:** `routes/admin.py` `unblock` directly assigned `active` to every nonadmin account, including blocked users who had never verified their email. It could also modify an already-pending account. | Added `utils/account_status.py` and updated admin action: only `blocked` accounts may be unblocked. When verification is required and `email_verified_at` absent, status becomes `pending`; verified users become `active`. Session version invalidation remains in place. | 3 actual pure-policy regression tests and source guard pass. 3 new real Flask test-client cases were authored, **not run** due to missing Flask. |
| P5-02 | **High operational risk:** `app.py` ran `db.create_all()` and inserted default categories every time a production web worker started, outside a reviewed migration workflow; exceptions were swallowed. | Added `AUTO_INIT_SCHEMA` (false by default in production, true by default in dev/test). Production startup bypasses this block. Production validation refuses `AUTO_INIT_SCHEMA=true`; Render web/cron set false. Schema validation remains in existing Render predeploy command. | Production config and source path checks executed locally; no staging DB migration tested. |
| P5-03 | **High:** Production preflight allowed `APP_MAIL_DRIVER=log`, `disabled`, arbitrary values, or missing support mailbox. Such a deployment could run with non-delivering signup/contact email. | `production_config_errors()` now rejects non-delivering web mail drivers and invalid `APP_MAIL_FROM` / `APP_SUPPORT_EMAIL`. Existing API path and email-verification requirement remain intact. | Executed subprocess validation of real production config functions for valid/invalid modes. **Actual Resend API acceptance and inbox delivery are unverified.** |
| P5-04 | **Deployment integration:** Stronger mail checks would otherwise break the existing Render payment-reconciliation cron, which deliberately sets mail disabled. | Render cron explicitly sets `LOCALJOIN_WORKER_ONLY=true`; production validation permits disabled mail and no support mailbox **only** for that isolated private worker role; other production safety checks stay active. Web service must not use this flag. | Real production-settings subprocess checks confirm worker/web distinction. Cron execution and Razorpay reconciliation are not run; payment code remains unchanged. |

## Preserved boundaries

- No modifications to existing payment amounts, gateway signatures, webhook status reconciliation or subscription grants.
- No changes to route URLs, UI design or session/CSRF initialization. The Razorpay webhook keeps its signature-authenticated, CSRF-exempt server-to-server design.
- No hardcoded live secrets, credential rotation, live email sends or production writes.
- No schema changes or automatic destructive migrations; the production startup automatic schema **creation** path was disabled, which requires preparing the schema ahead of rollout.
- Updated `.env.example`, `render.yaml`, and `docs/DEPLOYMENT.md` with new preflight requirements.

## Tests — execution truth

- Offline/static Python suite: **108 passed, 18 unittest subtests passed, 0 failed, 0 skipped** in its explicitly selected subset.
- Python compileall: PASS.
- Jinja syntax: **62 templates parsed**.
- JavaScript `node --check` and dependent dropdown behavior: PASS.
- PHP `php -l`: **93 PHP files passed**.
- Render YAML parse: **2 services**, PASS.
- Entire `tests/python`: **FAIL, exit 2**, 3 collection errors, `ModuleNotFoundError: No module named 'flask'`. Test cases after collection did **not** execute.
- Strict `scripts/run_runtime_tests.py`: **FAIL, exit 2**, required modules missing: Flask, Flask-SQLAlchemy, Flask-WTF, WTForms, PyMySQL, bcrypt, PyNaCl, gunicorn.
- Pinned package install: **FAIL, exit 1** (configured package index could not provide Flask==3.1.3). No claims of partial Flask runtime coverage.
- Disposable MySQL, staging email delivery, real browser/mobile, Razorpay sandbox and live site deployment: **NOT EXECUTED**.

**Important:** 0 skipped in the offline subset does not mean runtime tests passed or were skipped safely. The full-suite collection errors and strict gate remain blockers.

## Quality/security residual risks and release gates

1. Install pinned requirements in network-capable CI; execute `python scripts/run_runtime_tests.py` with zero skipped/failed/collection errors. Review failures, patch and rerun.
2. Run disposable MySQL 8 smoke in CI (suffix `_ci`, explicit opt-in); run approved staging DB schema preflight against a backed-up dataset. **Never point disposable tests at production.**
3. Verify test-client journeys with CSRF enabled, three user roles, email resend/reset, request/history atomicity, search readiness, contact, and admin unblock verified/unverified users.
4. Confirm Render web-specific production environment fields and dedicated cron role; verify predeploy `python scripts/check_config.py && python scripts/check_db_schema.py` returns zero after a reviewed migration.
5. Verify Resend sender DNS, API acceptance and inbox delivery using controlled mailboxes; verify Razorpay signature/webhook and payment cron only in sandbox.
6. Review trusted-proxy wildcard handling and public/browser/mobile checks using actual Render ingress and browser observations before live rollout. Existing `TRUSTED_PROXY_IPS=*` configuration is still a trust-boundary risk if an application origin can be reached by an untrusted client; no unsupported network topology change was made locally.
7. Verify manual rollback to previous checked code version and read-only schema compatibility; do not silently reverse DB migrations.

**Production deployment:** Not performed. **Ready for staging:** Local code available for controlled staging preparation; execution gate not green. **Production readiness verified:** NO.
