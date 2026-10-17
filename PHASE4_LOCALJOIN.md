# Phase 4 deliverables — Localjoin

* `LOCALJOIN_PHASE4_TEST_REPORT.md`: actual pass/fail/blocked results and release decision.
* `LOCALJOIN_PHASE4_EXECUTION_LOG.txt`: output of the repeatable local verification script.
* `scripts/phase4_verify_local.py`: syntax, template, JS, PHP, offline test, strict-runtime command sequence; **exit code 1** while Flask prerequisites are blocked.
* `tests/python/test_phase4_journey_matrix_runtime.py`: **9 Flask client cases authored, not yet executed**.
* `tests/python/test_phase4_runtime_configuration_offline.py`: **4 executed offline cases passed**.
* `scripts/run_disposable_mysql_smoke.py`: isolated MySQL test (writes/deletes schema; guarded).
* `.github/workflows/localjoin-runtime-tests.yml`: two independent jobs for full SQLite tests and disposable MySQL smoke. Both must pass once CI is run.

This is an interim test release, **not a production-ready Localjoin ZIP**.
