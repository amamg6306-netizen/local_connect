# How to complete the outstanding Localjoin Phase 4 tests

The local runner cannot reach package repositories and has neither Docker nor MySQL. The bundled **`.github/workflows/localjoin-runtime-tests.yml`** is ready to *attempt* both jobs on a normal GitHub Actions Ubuntu runner. **A green CI result must be observed, not assumed.**

1. Push this source to a **private GitHub repository** (do not commit `.env`, API keys, SQL backups, real user data or production secrets).
2. In that repository go to **Actions → Localjoin strict runtime tests → Run workflow**. This starts the Flask/SQLite test job and a separate disposable MySQL 8 job. The test MySQL username/password are CI-only for the throwaway service and cannot access real databases.
3. Open each job log. The Flask job calls `python scripts/run_runtime_tests.py` and fails on any missing dependency, skip, assertion or collection error. The MySQL job creates an isolated fresh database named exactly `localjoin_ci` and runs `python scripts/run_disposable_mysql_smoke.py`. It refuses nonlocal connections, existing schema, mismatched URLs and absent opt-in.
4. Fix all genuinely failing assertions and rerun both jobs. **Don't deploy to Render until both jobs have actually passed.** Keep test reports and CI run links as evidence. The current artifact has not had a completed GitHub Actions run.

If using an alternative machine with Python 3.13 and a separately provisioned disposable MySQL 8 server, install `requirements.txt` and `pytest` then use these commands (only on the safe CI DB):

```bash
python -m pip install -r requirements.txt pytest
APP_ENV=testing APP_URL=https://localjoin.in DATABASE_URL='sqlite:///:memory:' \
 APP_MAIL_DRIVER=log APP_REQUIRE_EMAIL_VERIFICATION=true \
 UPLOAD_DISK_REQUIRED=false FORCE_HTTPS=false \
 python scripts/run_runtime_tests.py
```

The MySQL job in GitHub Actions is preferable to manual MySQL credentials; it already sets the disposable URL, a test-only opt-in and `AUTO_INIT_SCHEMA=false` for the server job.

**These are not production tests**. Render/Resend/MySQL staging validation must be done separately with user authorization and reviewed accounts/data. No live registration, request, payment, or contact POST should be made without a dedicated safe staging environment.
