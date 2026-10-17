# Localjoin GitHub Actions Import-Path Fix

**Observed GitHub Actions error:** nine pytest collection errors with `ModuleNotFoundError` for `app`, `utils`, `database`, `scripts` in the integration job. 

**Root cause:** `python scripts/run_runtime_tests.py` starts with `scripts/` on `sys.path`; the project root is missing when `pytest.main` collects the tests. Similarly, `python scripts/run_disposable_mysql_smoke.py` may fail local application imports in the MySQL job. Both scripts now explicitly add the repository root to `sys.path` before importing project modules.

**Files changed:** `scripts/run_runtime_tests.py`, `scripts/run_disposable_mysql_smoke.py`. **Test added:** `tests/python/test_ci_script_import_bootstrap_offline.py`.

## GitHub steps

1. Back up your repository branch or open a pull request.
2. Apply only the two changed runner scripts (and optional regression test) to your current GitHub repository. Do not replace newer unrelated code from your repository with this ZIP.
3. Commit and rerun the `Localjoin strict runtime tests` workflow on `main`.
4. Inspect all three jobs: `integration`, `disposable-mysql`, `release-content`. Do not assume that import fixes imply full runtime correctness.
5. `release-content` should remain red until the actual Privacy/Terms text is reviewed and approved. Never hide this red job by disabling it.

## Important verification limits

This patch has been tested for Python package import resolution and offline syntax/regression checks. Complete Flask/MySQL 8 CI execution and the failed job logs from the MySQL and release-content jobs are not yet available to this audit. The production website was not modified.
