# Localjoin.in — Phase 5 security and quality gate

**State:** local source hardening completed; **strict Flask/production integration gate BLOCKED**. Do not deploy to production based on this document.

## Fixes implemented

- Admin unblock can only act on blocked non-admin users. Unblocking a user without `email_verified_at` leaves them `pending` when verification is mandatory; it does **not** silently grant verified/active login. Session version still increments to invalidate old sessions. Verified blocked accounts can be reactivated.
- Web startup no longer creates database tables or default categories in production. Development/disposable testing can still use controlled `AUTO_INIT_SCHEMA=true`. Production `AUTO_INIT_SCHEMA=true` fails config validation. This is a schema ownership change: **apply reviewed migration(s) before deployment** and keep `check_db_schema.py` in pre-deploy.
- Production web configuration rejects disabled/log-only/unrecognized mail drivers, invalid sender email, and missing or malformed support mailbox. This prevents a production signup or contact flow with no functioning delivery setup from silently booting.
- Isolated Render reconciliation cron continues with `APP_MAIL_DRIVER=disabled` using an explicit `LOCALJOIN_WORKER_ONLY=true` role; this exception must **never** be set on the web service. Cron still requires production DB, secret and HTTPS checks.
- Updated `render.yaml` and `.env.example` with explicit schema policy and separated cron mail policy.
- 13 new executable offline regressions and 3 new Flask/SQLite integration tests were authored. Flask integration tests remain **unexecuted**, not passed, on this runner.

## Staging and release checklist

1. Back up staging MySQL and validate restore procedure. Use an authorized schema migration procedure only; never use app startup to create production tables.
2. Ensure Render web `APP_ENV=production`, `AUTO_INIT_SCHEMA=false`, `APP_MAIL_DRIVER=resend`, valid `APP_MAIL_FROM`, `APP_SUPPORT_EMAIL`, `RESEND_API_KEY`, `APP_URL` and DB connection secrets (set only in Render environment, not in code).
3. Ensure Render cron `LOCALJOIN_WORKER_ONLY=true`, `APP_MAIL_DRIVER=disabled`, `AUTO_INIT_SCHEMA=false` and payment credentials only as needed.
4. Run `python scripts/check_config.py` then `python scripts/check_db_schema.py` with approved DB access. Either failure must block release.
5. Run `python scripts/run_runtime_tests.py` with **zero failures, zero skips**, plus the disposable MySQL CI smoke (never target live records). Include tests for admin block/unblock verified and unverified accounts.
6. On staging: verify registration, verification emails reaching a controlled inbox, provider/business onboarding, contact form, requests, CSRF, dashboards, payments and signed webhook in sandbox, mobile flows. Confirm errors and audit logs contain no tokens, credentials or personal details.
7. Deploy only after review of GitHub Actions and staging logs. Verify production smoke checks using existing approved accounts and read-only/non-destructive operations.

## Rollback

- Do not run an automatic reverse migration against existing user tables. Stop rollout, revert web/cron services to previously verified app commit, and verify schema compatibility with rollback code. Restore a verified DB backup **only** with operational approval and after reconciling writes to avoid data loss.
- This phase adds no columns or DDL files. Source changes can be rolled back independently if existing schema remains compatible.

## Remaining blockers

- Full Flask application, CSRF integration, SQLite journeys and MySQL smoke **not executed** here (missing pinned runtime packages; package index could not resolve Flask).
- No real Render, Resend, DNS, authenticated browser/mobile, MySQL staging, production or billing gateway testing.
- A configured Resend API acceptance is not proof of inbox delivery. Production readiness cannot be claimed.
