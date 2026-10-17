# Localjoin — GitHub CI import and legal-content fixes

**Status: code patches complete locally; GitHub rerun and production verification pending.**

## Errors supplied by the site owner

1. `disposable-mysql` failed with `ModuleNotFoundError: No module named 'app'` at `scripts/run_disposable_mysql_smoke.py`. GitHub run shown in screenshots: `39005293763`. This is an import-path/old-revision issue. The latest patched script bootstraps the repository root before importing `app`. In addition, `.github/workflows/localjoin-runtime-tests.yml` now invokes both runners with `python -m scripts.run_disposable_mysql_smoke` and `python -m scripts.run_runtime_tests`, which uses repository-root package resolution in GitHub Actions. The MySQL job still performs strict local-only disposable-database checks and requires an empty `localjoin_ci` database. **Not yet confirmed against GitHub MySQL 8**.

2. `release-content` failed because `templates/main/static.html` contained the `Development MVP policy template`, `Development MVP terms template`, and `Before production` placeholders. These were replaced with complete, platform-grounded **draft** Privacy Policy and Terms of Use sections. `scripts/check_release_content.py` now checks that both branches contain expected sections and a contact route; its gate returns success for content completeness **only**. Human approval is independently required by `scripts/check_release_evidence.py` via the `privacy_terms_approval` evidence item. The draft is NOT legal advice, does NOT assert legal compliance, and is **not yet approved**.

## Files updated for these two GitHub jobs

- `.github/workflows/localjoin-runtime-tests.yml`: module-based CI entrypoints.
- `scripts/run_runtime_tests.py`: carries forward previous project-root import-path fix.
- `scripts/run_disposable_mysql_smoke.py`: carries forward import-path fix; keeps strict safety checks.
- `templates/main/static.html`: substantive review-draft legal pages.
- `scripts/check_release_content.py`: privacy/terms branch and completeness checks.
- `tests/python/test_phase7_seo_discovery_offline.py`: changes obsolete placeholder-specific expectation.
- `tests/python/test_final_release_gate_offline.py`: release approval evidence still required independently.
- `tests/python/test_ci_release_content_gate_offline.py`: new content and workflow regression tests.
- `docs/LEGAL_OWNER_REVIEW_REQUIRED.md`: review checklist and deployment safeguards.

## Local execution — completed

- `python -m pytest -q tests/python --ignore=tests/python/test_localjoin_runtime_regressions.py --ignore=tests/python/test_phase4_journey_matrix_runtime.py --ignore=tests/python/test_phase5_security_hardening_runtime.py --ignore=tests/python/test_phase8_request_recovery_runtime.py` — **169 passed, 20 skipped, 18 subtests passed**, exit 0. This is an offline subset ONLY, not the strict full suite. Skipped cases require dependencies.
- `python -m pytest -q tests/python/test_ci_release_content_gate_offline.py tests/python/test_ci_script_import_bootstrap_offline.py tests/python/test_phase7_seo_discovery_offline.py` — **18 passed**, exit 0.
- `python -m scripts.check_release_content` — **PASS** (content completeness, not legal approval).
- Jinja parse — **62 templates passed**.
- Python syntax compile — passed.
- Node dependent dropdown check — passed.
- PHP syntax checks — **93 files passed**.
- `APP_ENV=testing python -m scripts.run_disposable_mysql_smoke` with no opt-in — **exit 2, fail-closed preflight as expected**; this is NOT a MySQL server integration pass.
- `python -m scripts.run_runtime_tests` — **exit 2**, missing Flask and other runtime packages in this environment. Full Flask suite is NOT passed.

## Required GitHub steps

1. Commit the changed files to `main` of your private `local_connect` repository (or upload the full ZIP after checking differences). The GitHub runner executes the repository commit; downloading a ZIP alone does not update CI.
2. GitHub Actions → `Localjoin strict runtime tests` → Run workflow (`main`), preferably a NEW run. Verify new commit SHA is shown in the run.
3. Inspect `integration`, `disposable-mysql`, and `release-content` separately. A green content job does **not** constitute legal approval. Send the log for any red step, not just the overall red mark.
4. Do not deploy until full Flask/MySQL tests, staging checks, verified Resend delivery and owner/legal sign-off have independent passing evidence.

No live production data, Render service, Resend configuration, or DNS record was changed during this patch.
