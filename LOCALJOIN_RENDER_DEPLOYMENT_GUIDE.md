# LOCALJOIN.IN — Render Staging, Deployment, Smoke Tests & Rollback

**Prepared 17 October 2026. Current decision: HOLD — full Flask/MySQL runtime verification and staging evidence are missing.**

This guide applies to the cumulative Localjoin **Flask/Python** source in this package. The `.php` URLs on the public site are Flask-compatible routes. Do not deploy the legacy PHP files as a separate production app. No deployment, MySQL writes, production signup or test emails were performed while preparing this document.

## 1. Release gates (all mandatory)

1. In a connected GitHub repository, run **both** jobs in `.github/workflows/localjoin-runtime-tests.yml` on an approved commit. Job `integration` must install pinned dependencies, execute **all** Flask pytest integration tests with **0 failures, 0 skips, and 0 collection errors**, and pass the Node/static checks. Job `disposable-mysql` must pass against the disposable, initially empty `mysql:8.0` service. Archive GitHub run URLs, runner logs, run date and commit SHA.
2. Prepare an isolated **staging** Render Web Service and **staging** MySQL instance with only fabricated user data. Do not point staging to the production `DATABASE_URL`. Use a dedicated verified testing mailbox/domain for Resend; check **actual receipt**, spam/bounce events and verification token expiry/resend, not just HTTP acceptance from the API. Record pass/fail for customer, provider and business independently.
3. Use the app's migration preflights on staging, then verify staging schema, requests/history transactionality, uploads, CSRF, role isolation and rate limits. Test payment **sandbox** paths, webhooks and reconciliation cron without live charges. Record any failures and fixes before further promotion.
4. Obtain an approved maintenance window, database snapshot **and tested restore**, upload-disk backup, reviewed migration checksums/preflights, Rollback Owner signoff and go/no-go decision. Leave payments in sandbox/off mode unless separately approved.
5. Only after gates 1–4 pass, deploy to production and execute the smoke test below. Record production commit SHA, Render deploy ID, observed response codes and evidence. Deploy success is *not* inferred from these instructions.

## 2. Render Blueprint review

`render.yaml` uses `runtime: python`, `plan: 0.5c-512mb` (a **paid** tier, not Render Free), `buildCommand: pip install -r requirements.txt`, pre-deploy `python scripts/check_config.py && python scripts/check_db_schema.py`, start `gunicorn app:app --bind 0.0.0.0:$PORT`, `/health`, a 1 GB mounted disk at `/var/data/localconnect/uploads`, and a paid reconciliation cron scheduled every 5 minutes. Compare the proposed Blueprint diff with the *existing* Render services before syncing; avoid accidentally replacing a live service or changing disk ownership. The service name `localconnect` is inherited from source. Confirm any plan/cost changes with the account owner.

Render disk constraints: only one instance can attach the disk; it is **not present during build or pre-deploy**; attaching it prevents zero-downtime redeployment. Upload migration must occur from an authorized running instance or via an approved external backup workflow. Avoid scaling this web service horizontally until uploads move to shared storage.

Render reference: https://render.com/docs/blueprint-spec and https://render.com/docs/disks.

## 3. Configure nonsecret and secret environment variables

Use `.env.example` as a *nonsecret* checklist only. Set real values in Render Environment for the **web** service, do not commit `.env` or share screenshots containing credentials.

| Required web name | Required setting / security purpose |
| --- | --- |
| `APP_ENV`, `APP_DEBUG`, `APP_URL` | `production`, `false`, `https://localjoin.in` (or approved HTTPS staging hostname) |
| `SECRET_KEY` | existing long stable application secret, rotated only via an approved session/MFA plan |
| `APP_KEY` | preserve existing value if legacy admin MFA encryption uses it |
| `DATABASE_URL` | dedicated production MySQL user/host/database; staging has **different** credentials/database |
| `APP_MAIL_DRIVER` | `resend` (Blueprint default) |
| `RESEND_API_KEY` | valid secret, never checked into Git |
| `APP_MAIL_FROM` | plain verified sender email; DNS verified with Resend |
| `APP_SUPPORT_EMAIL` | monitored support email destination |
| `AUTO_INIT_SCHEMA` | `false` on **web and cron** |
| `APP_REQUIRE_EMAIL_VERIFICATION`, `APP_ADMIN_MFA_REQUIRED` | `true` |
| `FORCE_HTTPS`, `SESSION_COOKIE_SECURE` | `true`; test trusted proxy and canonical hosts |
| `TRUST_PROXY`, `TRUSTED_PROXY_IPS`, `TRUSTED_PROXY_HOPS`, `TRUSTED_HOSTS` | configure only known trusted network path; verify forwarding headers on staging; avoid exposing direct proxy spoofing |
| `UPLOAD_STORAGE_BACKEND`, `UPLOAD_STORAGE_ROOT`, `UPLOAD_DISK_REQUIRED` | `filesystem`, `/var/data/localconnect/uploads`, `true` on web |
| `UPLOAD_REQUIRE_REENCODE`, `SECURITY_CSP_MODE` | `true`, `enforce` |
| `PAYMENT_ALLOW_LIVE` | `false` until sandbox and approval gate passed |
| `PAYMENT_RAZORPAY_KEY_ID`, `PAYMENT_RAZORPAY_KEY_SECRET`, `PAYMENT_RAZORPAY_WEBHOOK_SECRET` | set only appropriate credentials; never publish, separate sandbox from live |

Other existing rate limit / max upload / pool settings should be reviewed using `config/settings.py`. Validate sender/domain/DNS with Resend, and **confirm real inbox delivery and support form receipt** in staging. For Render cron, `LOCALJOIN_WORKER_ONLY=true` and `APP_MAIL_DRIVER=disabled` are intentionally worker-only; never put `LOCALJOIN_WORKER_ONLY=true` on the public web service. The cron's payment secrets are linked from the web service via `fromService` and should be handled separately if the service names change.

## 4. Database workflow — backup before altering anything

**Empty isolated staging DB only**: set staging database credentials, run `python scripts/init_db.py` (detect empty DB) and only after confirming the environment, `python scripts/init_db.py --yes`.

**Existing DB**: use a dedicated DBA/migration account with `MIGRATION_DATABASE_URL` (distinct from the runtime user when possible). First save and verify a physical/logical backup and test restore to an *isolated* destination. Then run:

```bash
python scripts/check_config.py
python scripts/migrate_db.py                        # status only; 2=pending, 0=current
python scripts/migrate_db.py --preflight            # read-only query output for human review
# ONLY after review, approval and verified backup:
python scripts/migrate_db.py --preflight --apply --acknowledge-reviewed-backup
python scripts/check_db_schema.py                   # schema/connection check
```

`migrate_db.py` refuses missing migration tracking, checksum mismatches and missing/non-read-only preflight files. It does **not** automatically baseline unknown legacy databases. Do not blindly apply old migrations if the tracking table is absent: compare actual schema, migrations and records with a DBA. MySQL DDL can auto-commit and partial deploys are possible; don't assume ordinary database transaction rollback reverses a migration.

**Render pre-deploy** runs only config/schema validation, not migrations. Deploy will fail safely if schema is not already compatible. Review the migration SQL, affected tables, runtime compatibility and rollback files (`database/production/`) before any production action.

## 5. Staging smoke matrix — capture evidence

| Feature / route | Expected staging result |
| --- | --- |
| `/health`, homepage, `/search.php`, `/categories.php` | 200 / correct redirects and assets; DB connectivity; no stack traces |
| Customer registration → email verify → login/logout/reset | Valid CSRF, hashed password, no duplicate email, real verification email, dashboard |
| Provider and Business registration | Correct role/profile linkage, email verification, profile/service add/edit/pause/resume |
| Empty/inactive categories/services | Cannot submit invalid pair, no ready-to-request CTA for empty profile |
| Customer requirement POST | Request and initial status history created atomically, appears in dashboard |
| Direct request from provider/business | Only eligible target offerings allowed; shown in correct target dashboard |
| Guest login with original `next` URL | Returns to valid same-origin GET destination; rejects external or POST redirects |
| Contact submission | CSRF/validation/rate limits; real accepted mail and verified receiving mailbox |
| Upload to persistent disk | Reencoded file stays accessible after safe restart; storage monitored |
| Admin/MFA/security | Role permissions, verified email requirement, no CSRF bypass or exposed secrets |
| Razorpay **sandbox** & cron | Signed webhook and sandbox reconciliation verified; production charges disabled |
| Browser mobile + desktop | Dropdowns, navbar, forms, Bootstrap, CSP console, navigation functional |

## 6. Production rollout and rollback

- Obtain approval and archive passing test runs and staging logs with secrets redacted. Confirm Render service region/plan, domain/DNS, expected database, disk mount, attached cron, and correct environment variables.
- Snapshot database and persistent uploads. Validate that backup **restores on a separate host**. Record current running commit SHA, schema version and availability baseline.
- Run the migration read-only review and explicitly approved apply (if needed) from a securely authorized environment. Never use live credentials in Github CI or on this inspection machine.
- Deploy the reviewed Git commit via Render, observe build/pre-deploy/start logs, `/health`, route smoke tests, email deliverability and dashboard flows. Monitor errors and queue/reconciliation status; confirm `PAYMENT_ALLOW_LIVE=false` unless independent approval exists.
- For a **code-only regression**, redeploy the previous known-good commit if schema is backward compatible; if schema was altered, coordinate the matching rollback or restore from verified backups. Do not run rollback SQL blindly. Persistent disk uploads have a **separate backup/restore procedure**, and must not be overwritten inadvertently.
- If verification fails, stop rollout, return traffic to last safe service version per Render features, restore data only with DBA authorization, and re-run the smoke matrix. Record incident and resolution.

## 7. Unverified gates — as of 17 October 2026

- Full Flask runtime suite with pinned requirements: **NOT RUN SUCCESSFULLY** in this environment (package DNS/install blocked).
- Disposable MySQL 8 **server** smoke: **NOT EXECUTED** (no server or Docker here).
- Render staging configuration, production credentials, backup/restore and deployment: **NOT VERIFIED**.
- Resend actual inbox delivery, end-to-end three-role onboarding, mobile browser and Razorpay sandbox: **NOT VERIFIED**.

**Current decision: HOLD; not production-ready.** These instructions and offline checks are not proof that the live service has been updated.

## Phase 8 addendum — business requirements and regression gate

The existing `/provider/available-requirements.php` route remains available; the Business Dashboard now uses `/business/available-requirements.php` with its own `business` role authorization. Before staging or production rollout, run the strict GitHub Actions workflow and include `tests/python/test_phase8_request_recovery_runtime.py` in the Flask integration evidence. Injected notification failures must leave claimed requests unassigned or status transitions unchanged after rollback. Review sanitized server references for unexpected failures without logging request details, identities, or credentials. An offline-only green result is not a rollout approval. Privacy/Terms require independent owner signoff, and changes must not run against production users in CI.
