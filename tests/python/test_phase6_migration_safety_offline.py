"""Phase 6 unit checks: these are mocked/offline controls, NOT real MySQL tests."""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load_module():
    dummy_db = types.ModuleType("database.connection")
    dummy_db.connect = lambda **kwargs: None
    dummy_db.connection_settings = lambda **kwargs: types.SimpleNamespace(database="localjoin_ci")
    location = ROOT / "scripts/migrate_db.py"
    spec = importlib.util.spec_from_file_location("localjoin_phase6_migrate_offline", location)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"database.connection": dummy_db}):
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)
    return module


@pytest.fixture
def migration():
    return load_module()


@pytest.mark.parametrize("expected", [
    "20260924_001_security_foundation",
    "20260924_002_payment_methods",
    "20260924_003_checkout_webhooks",
    "20260924_004_performance_reliability",
    "20260924_005_production_hardening",
])
def test_forward_migration_has_valid_read_only_preflight(migration, expected):
    paths = {version: path for version, path in migration.forward_migrations()}
    assert expected in paths
    preflight = migration.matching_preflight(paths[expected])
    assert migration.verify_preflight_read_only(preflight) >= 1


@pytest.mark.parametrize("sql", [
    "DELETE FROM users;",
    "UPDATE users SET status='active';",
    "DROP TABLE users;",
    "SELECT id FROM users FOR UPDATE;",
    "SELECT id INTO OUTFILE '/tmp/private' FROM users;",
    "-- misleading comment\nINSERT INTO users VALUES (1);",
    "-- only a comment\n",
])
def test_unsafe_preflights_refused(migration, tmp_path, sql):
    path = tmp_path / "bad_preflight.sql"
    path.write_text(sql)
    with pytest.raises(RuntimeError):
        migration.verify_preflight_read_only(path)


def test_absent_preflight_refused(migration, tmp_path):
    path = tmp_path / "20990101_999_missing.sql"
    path.write_text("SELECT 1;")
    with pytest.raises(RuntimeError, match="Missing read-only preflight"):
        migration.matching_preflight(path)


@pytest.mark.parametrize("args", [
    ["--apply"],
    ["--apply", "--preflight"],
    ["--apply", "--acknowledge-reviewed-backup"],
    ["--acknowledge-reviewed-backup"],
])
def test_apply_without_all_approvals_blocked_before_connection(migration, args):
    with patch.object(migration, "connection_settings", side_effect=AssertionError("must not connect")):
        with pytest.raises(SystemExit) as err:
            migration.main(args)
    assert err.value.code == 2


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.description = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        self.connection.queries.append(sql.strip())

    def fetchone(self):
        return {"cnt": int(self.connection.has_tracking)}

    def fetchall(self):
        return []


class FakeConnection:
    def __init__(self, has_tracking=True):
        self.has_tracking = has_tracking
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def cursor(self):
        return FakeCursor(self)


def test_status_is_read_only_and_does_not_create_tracking_table(migration):
    conn = FakeConnection()
    with patch.object(migration, "connect", return_value=conn):
        code = migration.main([])
    assert code == 2  # Pending migrations need operator review
    assert len(conn.queries) == 2
    assert conn.queries[0].startswith("SELECT COUNT(*)")
    assert conn.queries[1].startswith("SELECT version")
    assert not any("CREATE " in query or "INSERT " in query for query in conn.queries)


def test_missing_tracking_table_fails_closed_without_creating_it(migration):
    conn = FakeConnection(has_tracking=False)
    with patch.object(migration, "connect", return_value=conn):
        with pytest.raises(RuntimeError, match="schema_migrations is missing"):
            migration.main([])
    assert len(conn.queries) == 1
    assert "CREATE TABLE" not in " ".join(conn.queries)


def test_read_only_preflight_mode_runs_without_ddl_or_dml(migration):
    conn = FakeConnection()
    with patch.object(migration, "connect", return_value=conn):
        code = migration.main(["--preflight"])
    assert code == 0
    assert all(not q.upper().startswith(("CREATE", "ALTER", "INSERT", "UPDATE", "DELETE", "DROP")) for q in conn.queries)
