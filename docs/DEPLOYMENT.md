# LocalConnect — Native Python Render deployment

This repository deploys as a Render **Native Python Web Service**. Docker, Apache, PHP runtime, Nginx configuration and `.htaccess` are not production dependencies.

## Render Blueprint

`render.yaml` configures:

- runtime: `python`
- Python: `3.13.15`
- plan: `0.5c-512mb` (paid; required for the attached persistent disk)
- build: `pip install -r requirements.txt`
- pre-deploy: `python scripts/check_config.py && python scripts/check_db_schema.py`
- start: `gunicorn app:app --bind 0.0.0.0:$PORT`
- health check: `/health`
- disk: `/var/data/localconnect/uploads`, 1 GB
- cron: `localconnect-payment-reconciliation`, every 5 minutes, running `python scripts/payment_reconciliation_worker.py --limit=20`

The cron service reuses the web service database/payment secrets through Blueprint `fromService` references. It intentionally uses temporary upload storage because reconciliation does not read or write user uploads.

The health endpoint executes a bounded `SELECT 1` probe. It returns 503 without exposing diagnostics if the primary DB is unavailable.

## Required account-level configuration

Before the first production deploy, set the Blueprint's `sync: false` values in Render:

- `SECRET_KEY`
- `APP_KEY` only if legacy encrypted admin-MFA records still exist
- `APP_URL`
- `DATABASE_URL`
- `APP_MAIL_FROM`: plain sender email on verified sending domain
- `RESEND_API_KEY` when `APP_MAIL_DRIVER=resend` (current `render.yaml` default)
- `APP_SUPPORT_EMAIL`: working support mailbox for contact submissions
- `SMTP_HOST` / `SMTP_USERNAME` / `SMTP_PASSWORD` only if you explicitly select an SMTP mail driver instead of Resend
- `PAYMENT_RAZORPAY_KEY_ID` if Razorpay is enabled
- `PAYMENT_RAZORPAY_KEY_SECRET` if Razorpay is enabled
- `PAYMENT_RAZORPAY_WEBHOOK_SECRET` if Razorpay is enabled
- `PAYMENT_RAZORPAY_WEBHOOK_IP_ALLOWLIST` only if an approved fixed allowlist is available

`PAYMENT_ALLOW_LIVE=false` remains the deployment default. Use sandbox credentials until the complete payment release gate has passed.

## Phase 5 production startup and email hardening

- Set `AUTO_INIT_SCHEMA=false` on **both** Render web and payment cron services. Production application startup no longer calls `db.create_all()` or inserts seed categories. Follow the reviewed schema/pre-deploy steps below and keep a verified database backup. An attempted `AUTO_INIT_SCHEMA=true` production override now causes configuration preflight to fail.
- Web service email must be configured (`APP_MAIL_DRIVER=resend` or an available SMTP mode); `log`, `disabled` or unknown drivers are prohibited in production web. Configure plain mailbox addresses for `APP_MAIL_FROM` and `APP_SUPPORT_EMAIL`, plus valid provider settings, before deploy. Confirm real email delivery from staging separately.
- The payment-reconciliation **cron only** has `LOCALJOIN_WORKER_ONLY=true` and deliberately disables outgoing email. **Do not put `LOCALJOIN_WORKER_ONLY=true` on the web service**; that flag bypasses only web-specific mail/support config requirements for this private worker.
- Admin user unblocking preserves email verification requirements: an unverified blocked user becomes pending, and must complete email verification before login. It is not an account-verification shortcut.

## Database preparation

MySQL/MariaDB is external; do not deploy it through this Render service.

For an empty database, initialize it from the canonical schema using an authorized environment:

```bash
python scripts/init_db.py
python scripts/init_db.py --yes
```

For an existing production database:

1. Take and verify a database backup.
2. Check status using `python scripts/migrate_db.py` (read-only; exit code 2 means pending migration(s), not a successful release).
3. Run `python scripts/migrate_db.py --preflight` separately. This executes **read-only** preflight queries; review their outputs and check every pending migration and its rollback SQL.
4. Confirm an external, restorable backup (including proof of restoration on a separate database) and a maintenance/rollback plan.
5. Only an approved operator should run `python scripts/migrate_db.py --preflight --apply --acknowledge-reviewed-backup` with dedicated migration credentials.
6. Verify with `python scripts/check_db_schema.py` and application staging tests. Note that MySQL DDL often implicitly commits, so rollback requires a tested backup/restore plan, not just a SQL transaction.

**Safety:** `migrate_db.py` never creates `schema_migrations` in status mode. If the tracking table is missing, it refuses to apply migrations; determine the legacy baseline manually instead of blindly reapplying migrations. Do not run the fresh initializer on an existing database. Do not insert production credentials into CI.

The Render pre-deploy command intentionally blocks a release if configuration is invalid or the effective schema is incomplete. It does **not** apply migrations. Render persistent disks are not available during build/pre-deploy; upload checks and data migration belong to post-start staging verification.

**Phase 6 release gate:** run both GitHub Actions jobs defined in `.github/workflows/localjoin-runtime-tests.yml` with a clean disposable MySQL 8 instance. Zero failed/skipped Flask tests and a successful MySQL server smoke are mandatory. In staging, verify actual Resend delivery (not just API acceptance), uploads to the mounted disk, domain/DNS, proxy/HTTPS, all three registration roles, admin authorization, and controlled Razorpay sandbox workflows. Keep `PAYMENT_ALLOW_LIVE=false` until payment approval and sandbox evidence exist. See `LOCALJOIN_RENDER_DEPLOYMENT_GUIDE.md` for the staged rollout and recovery procedure.

## Persistent uploads

Render's ordinary filesystem is ephemeral. The Blueprint mounts a persistent disk at `/var/data/localconnect/uploads` and configures the application to store profile, business-logo and portfolio images there.

If migrating existing uploads, run from the deployed service environment after the disk is attached:

```bash
python scripts/sync_uploads_to_storage.py --source <legacy-upload-root>
```

The synchronizer does not overwrite differing existing files and reports conflicts.

A Render persistent disk is attached to only one service instance. Do not scale this service to multiple instances while local persistent-disk uploads are in use; move uploads to shared object storage first.

## First deploy verification

After the deploy becomes live, verify at minimum:

1. `/health` returns HTTP 200.
2. Public home/search/profile pages render and static assets load.
3. Register/login/logout/email verification/password reset.
4. Customer/provider/business/admin role boundaries.
5. Customer request creation and request status lifecycle.
6. Provider/business service/profile workflows and uploads.
7. Favorites, notifications, reviews and reports.
8. Admin CRUD/moderation/MFA/re-auth operations.
9. Razorpay **sandbox** checkout, callback, signed webhook and reconciliation if Razorpay is enabled.
10. Manual payment review flow if enabled.
11. The payment-reconciliation cron appears in Render, runs successfully, and does not accumulate retryable jobs unexpectedly.
12. Render logs contain no stack traces/secrets and show no unexpected 4xx/5xx failures.

Do not mark deployment complete until the live URL and critical routes have been checked.
