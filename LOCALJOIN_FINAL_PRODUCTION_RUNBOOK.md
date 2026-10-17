# Localjoin.in — Controlled Production Release Runbook

This process **must not** be interpreted as permission to deploy without a reviewed release decision.

## 1. Repository & CI

1. Upload the exact candidate source to a controlled GitHub repository on a new branch. Review changes and compare source against the ZIP checksum. Do not commit actual `.env` secrets or customer data.
2. Trigger `.github/workflows/localjoin-runtime-tests.yml` and verify all three jobs: Flask/SQLite `integration`, isolated MySQL 8 `disposable-mysql`, `release-content`.
3. Any failed or skipped runtime test is a **NO-GO**. Investigate test failures, correct the exact source and rerun CI against the new commit.
4. Record CI run URLs and SHA for that exact source revision; do not substitute runs for unrelated commits.

## 2. Public legal content

Have the website owner and an appropriate legal reviewer approve a real Privacy Policy and Terms of Use covering marketplace roles, contact, data handling and retention, support, consent and any relevant payments/subscriptions. Update `templates/main/static.html`, keep review evidence; rerun the release-content gate. Do not remove markers solely to game CI.

## 3. Staging deployment

1. Use a **separate staging service, DB and mail/test domain**. No actual production users or payment credentials in disposable test fixtures.
2. Compare `render.yaml`, `.env.example` and `LOCALJOIN_RENDER_DEPLOYMENT_GUIDE.md`; set real credentials in Render secrets, not code. Preserve existing production `APP_KEY` if applicable to legacy MFA secrets.
3. Perform database schema preflight and migrations only according to reviewed staging change plan; never run destructive actions on live data by default.
4. Public GET smoke: `python scripts/run_public_readonly_smoke.py --base-url https://YOUR-STAGING-HOST` (HTTPS origin only).
5. Test all roles with approved staging accounts: registration, verification, verified login, password reset, provider/business service creation/editing, category dropdown, Customer request, direct request, status/history, contact submission receipt, search visibility, mobile navigation and role-specific access controls.
6. Verify **real mailbox receipt** via Resend, not just API acceptance. Verify webhook/payment isolation separately with approved sandbox settings.
7. Test on desktop and mobile browsers and record result/screenshots without sensitive user data.

## 4. Backup and rollback

1. Before any production migration, obtain a tested snapshot/backup of the **production MySQL database and persistent upload disk**, with a restore procedure and responsible operator.
2. Confirm non-destructive migration plan, preflight logs and prepared rollback. Do not use the disposable MySQL script against customer databases.
3. Review hosting costs, disk mounting, cron service, health checks, DNS/TLS, sender-domain DNS and secure environment variables.
4. Plan a maintenance window and rollback threshold. If staging fails, do **not** promote. If production smoke fails after authorized release, revert to the last verified artifact and use the approved DB restore/migration rollback plan as needed; don't assume reverting the application also reverts schema changes.

## 5. Release evidence & owner decision

- Generate exact candidate SHA-256 with `python scripts/check_release_package.py path/to/candidate.zip`.
- Copy `release/PRODUCTION_EVIDENCE_EXAMPLE.json` to a **private, untracked** evidence file; fill in `source_commit_sha` and matching run URLs, staging checks, legal sign-off, email receipt, browser checks, tested backup/rollback and Render review. Never include secrets, raw tokens, customer PII or credential-bearing URLs.
- Check consistency via:
  `python scripts/check_release_evidence.py --candidate path/to/candidate.zip --evidence path/to/private-evidence.json`
- Even a passing evidence-consistency check is **not proof** that external claims are true. The release owner must independently open and verify all external records and explicitly approve promotion.
- Only then authorize the production release. Do not label the ZIP *production ready* before live production smoke tests and real evidence are recorded.

**Current state (2026-10-17): HOLD.** No GitHub Actions evidence, staging or MySQL 8 server run, mail receipt, approved legal copy or live deployment exists in this delivery.
