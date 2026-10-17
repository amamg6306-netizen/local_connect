"""Strict local/CI test gate: unavailable dependencies and skipped tests are failures.

Usage: python scripts/run_runtime_tests.py
       python scripts/run_runtime_tests.py -q tests/python/test_localjoin_runtime_regressions.py

No production credentials are required: Flask integration tests use temporary SQLite
and mocked email. Passing this gate does NOT validate production MySQL/Resend.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys

# When invoked as `python scripts/run_runtime_tests.py`, Python puts
# `scripts/` rather than the repository root on sys.path.  Pytest imports
# application packages such as `app`, `utils`, and `database` from that root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED_MODULES = {
    "flask": "Flask",
    "flask_sqlalchemy": "Flask-SQLAlchemy",
    "flask_wtf": "Flask-WTF",
    "wtforms": "WTForms",
    "pymysql": "PyMySQL",
    "bcrypt": "bcrypt",
    "nacl": "PyNaCl",
    "PIL": "Pillow",
    "gunicorn": "gunicorn",
    "dotenv": "python-dotenv",
}


def main() -> int:
    os.chdir(PROJECT_ROOT)
    missing = [label for module, label in REQUIRED_MODULES.items() if importlib.util.find_spec(module) is None]
    if missing:
        print("BLOCKED: Flask integration tests have NOT run; missing required modules: " + ", ".join(missing), file=sys.stderr)
        print("Install project requirements with: python -m pip install -r requirements.txt", file=sys.stderr)
        print("No tests were marked as PASS. This strict gate returns failure (exit 2).", file=sys.stderr)
        return 2

    import pytest

    class NoSkippedTests:
        def __init__(self) -> None:
            self.skipped = 0
            self.failed = 0

        def pytest_runtest_logreport(self, report):
            if report.skipped:
                self.skipped += 1
            if report.failed:
                self.failed += 1

        def pytest_sessionfinish(self, session, exitstatus):
            if self.skipped:
                print(f"STRICT GATE FAILED: {self.skipped} skipped test reports; resolve or explicitly test these scenarios.", file=sys.stderr)
                session.exitstatus = pytest.ExitCode.TESTS_FAILED
            if session.testscollected == 0:
                print("STRICT GATE FAILED: zero tests collected.", file=sys.stderr)
                session.exitstatus = pytest.ExitCode.NO_TESTS_COLLECTED

    args = sys.argv[1:] or ["-q", "-ra", "tests/python"]
    return int(pytest.main(args, plugins=[NoSkippedTests()]))


if __name__ == "__main__":
    raise SystemExit(main())
