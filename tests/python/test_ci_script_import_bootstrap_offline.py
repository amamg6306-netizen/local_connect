"""Regression: script entrypoints must resolve local packages from CI and other cwd."""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def test_script_runner_repo_root_import_path(tmp_path):
    for name in ("run_runtime_tests.py", "run_disposable_mysql_smoke.py"):
        script = ROOT / "scripts" / name
        probe = (
            "import sys, runpy, importlib.util; "
            "root = sys.argv[2]; "
            "runpy.run_path(sys.argv[1], run_name='ci_import_probe'); "
            "assert root in sys.path, 'repo root missing from sys.path'; "
            "assert importlib.util.find_spec('app'), 'app not found'; "
            "assert importlib.util.find_spec('utils'), 'utils not found'; "
            "assert importlib.util.find_spec('database'), 'database not found'; "
            "assert importlib.util.find_spec('scripts'), 'scripts not found'"
        )
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        run = subprocess.run(
            [sys.executable, "-c", probe, str(script), str(ROOT)],
            cwd=str(tmp_path), env=env, capture_output=True, text=True,
            timeout=15,
        )
        assert run.returncode == 0, (name, run.stdout, run.stderr)
