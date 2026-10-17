"""Offline checks only. Will never label unexecuted Flask/MySQL tests as passed."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(*cmd: str) -> None:
    print(f"$ {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, cwd=ROOT, check=False)
    print(f"exit={result.returncode}", flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)


def main() -> None:
    tests = sorted(str(path.relative_to(ROOT)) for path in (ROOT / "tests/python").glob("test_*static.py"))
    tests += [
        "tests/python/test_phase2_navigation_regression.py",
        "tests/python/test_phase4_runtime_configuration_offline.py",
        "tests/python/test_phase4_mysql_guard_extended_offline.py",
        "tests/python/test_phase5_security_hardening_offline.py",
        "tests/python/test_phase6_migration_safety_offline.py",
        "tests/python/test_phase7_seo_discovery_offline.py",
        "tests/python/test_phase8_request_recovery_offline.py",
        "tests/python/test_final_release_gate_offline.py",
        "tests/python/test_final_public_smoke_offline.py",
    ]
    run(sys.executable, "-m", "pytest", "-q", *tests)
    run(sys.executable, "scripts/run_offline_model_integration.py")
    run(sys.executable, "-m", "compileall", "-q", "app.py", "routes", "services", "models", "config", "utils", "scripts", "tests/python")
    run("node", "--check", "assets/js/app.js")
    run("node", "tests/js/dependent_dropdown.test.js")
    print("PASS: OFFLINE CHECKS ONLY. Flask and MySQL test gates are separate and mandatory.")


if __name__ == "__main__":
    main()
