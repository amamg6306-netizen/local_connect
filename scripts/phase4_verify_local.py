"""Repeatable Phase 4 local checks. Does NOT imply Flask/MySQL runtime passed.

Only offline tests run here. For the real Flask gate use run_runtime_tests.py;
for disposable CI MySQL use run_disposable_mysql_smoke.py.
"""
from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
RUNS = [
    ("Python syntax", [sys.executable, "-m", "compileall", "-q", "app.py", "routes", "services", "models", "config", "utils", "scripts", "tests/python"]),
    ("Jinja template parse", [sys.executable, "-c", "from pathlib import Path; from jinja2 import Environment; env=Environment(); pages=list(Path('templates').rglob('*.html')); [env.parse(p.read_text(encoding='utf-8')) for p in pages]; print('templates parsed:',len(pages))"]),
    ("Node app syntax", ["node", "--check", "assets/js/app.js"]),
    ("Node dropdown runtime", ["node", "tests/js/dependent_dropdown.test.js"]),
    ("Offline Python tests (runtime modules excluded, zero skips)", [sys.executable, "-m", "pytest", "-q", "tests/python/test_phase2_navigation_regression.py", "tests/python/test_phase4_runtime_configuration_offline.py", "tests/python/test_final_recheck_static.py", "tests/python/test_phase3_audit_static.py", "tests/python/test_phase3_database_static.py", "tests/python/test_phase4_auth_static.py", "tests/python/test_phase5_functional_static.py", "tests/python/test_phase6_frontend_parity_static.py", "tests/python/test_phase7_production_static.py", "tests/python/test_phase8_verification_static.py", "tests/python/test_phase9_release_static.py", "tests/python/test_pre_phase8_recheck_static.py"]),
    ("PHP helper baseline", ["php", "tests/phase1/php_helper_smoke.php"]),
    ("PHP security helpers", ["php", "tests/phase2/php_security_helpers.php"]),
    ("PHP payment helpers", ["php", "tests/phase3/php_payment_helpers.php"]),
    ("PHP billing helpers", ["php", "tests/phase4/php_billing_helpers.php"]),
    ("PHP hardening helpers", ["php", "tests/phase6/php_security_helpers.php"]),
    ("Strict Flask runtime gate (must fail if unavailable/skipped)", [sys.executable, "scripts/run_runtime_tests.py"]),
]


def main() -> int:
    lines = ["Localjoin Phase 4 local execution report", "No remote production calls or writes were made."]
    failures = []
    for title, command in RUNS:
        proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=90)
        lines.extend(["", f"CHECK: {title}", "CMD: " + " ".join(command),
                      f"EXIT: {proc.returncode}", proc.stdout.rstrip(), proc.stderr.rstrip()])
        if proc.returncode != 0:
            failures.append((title, proc.returncode))
    results = "\n".join(lines) + "\n"
    output = ROOT / "LOCALJOIN_PHASE4_EXECUTION_LOG.txt"
    output.write_text(results, encoding="utf-8")
    print(results)
    print("NONZERO CHECKS:", failures)
    # Offline suite success does not override the strict runtime failure.
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
