from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.connection import connect, connection_settings
from database.sql_runner import (
    _sql_without_leading_comments,
    execute_sql_file,
    file_checksum,
    iter_mysql_statements,
    strip_database_switches,
)


MIGRATION_DIR = ROOT / "database" / "production"
FORWARD_RE = re.compile(r"^(\d{8}_\d{3}_[a-z0-9_]+)\.sql$")
READ_ONLY_START = re.compile(r"^(?:SELECT|SHOW|EXPLAIN|DESCRIBE)\b", flags=re.I)


def forward_migrations() -> list[tuple[str, Path]]:
    result: list[tuple[str, Path]] = []
    for path in sorted(MIGRATION_DIR.glob("*.sql")):
        if path.stem.endswith(("_preflight", "_rollback")):
            continue
        match = FORWARD_RE.match(path.name)
        if match:
            result.append((match.group(1), path))
    return result


def migration_tracking_exists(connection, schema_name: str) -> bool:
    """Inspect tracking without creating tables or mutating the application DB."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM information_schema.tables "
            "WHERE table_schema=%s AND table_name='schema_migrations' AND table_type='BASE TABLE'",
            (schema_name,),
        )
        return int(cursor.fetchone()["cnt"]) == 1


def applied_migrations(connection) -> dict[str, str | None]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT version, checksum_sha256 FROM schema_migrations")
        return {row["version"]: row["checksum_sha256"] for row in cursor.fetchall()}


def record_checksum(connection, version: str, checksum: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO schema_migrations(version, checksum_sha256)
            VALUES(%s, %s)
            ON DUPLICATE KEY UPDATE checksum_sha256=VALUES(checksum_sha256)
            """,
            (version, checksum),
        )


def matching_preflight(path: Path) -> Path:
    candidates = (
        path.with_name(path.stem + "_preflight.sql"),
        path.with_name("_".join(path.stem.split("_")[:2]) + "_preflight.sql"),
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError(f"Missing read-only preflight for {path.name}; refusing migration.")


def verify_preflight_read_only(path: Path) -> int:
    """Do not run arbitrary DML/DDL disguised as preflight SQL."""
    statements = list(strip_database_switches(iter_mysql_statements(path.read_text(encoding="utf-8"))))
    checked = 0
    for statement in statements:
        stripped = _sql_without_leading_comments(statement).strip()
        if not stripped:
            continue
        if not READ_ONLY_START.match(stripped):
            raise RuntimeError(f"Unsafe preflight SQL in {path.name}: only read-only queries are allowed.")
        # Query-level serialization/writes are not legitimate deployment preflights.
        if re.search(r"\bINTO\s+(?:OUTFILE|DUMPFILE)\b|\bFOR\s+UPDATE\b|\bLOCK\s+IN\s+SHARE\s+MODE\b", stripped, re.I):
            raise RuntimeError(f"Unsafe preflight SQL in {path.name}: query has side effects.")
        checked += 1
    if checked == 0:
        raise RuntimeError(f"Empty preflight {path.name}; refusing migration.")
    return checked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review and apply Localjoin forward-only production database migrations.")
    parser.add_argument("--apply", action="store_true", help="Apply pending forward migrations (explicit approval required).")
    parser.add_argument("--preflight", action="store_true", help="Run read-only preflight SQL for pending migrations.")
    parser.add_argument(
        "--acknowledge-reviewed-backup", action="store_true",
        help="Confirm a verified backup exists and the separate preflight output was reviewed. Does not create a backup.",
    )
    args = parser.parse_args(argv)
    if args.apply and not (args.preflight and args.acknowledge_reviewed_backup):
        parser.error("--apply requires both --preflight and --acknowledge-reviewed-backup after backup review")
    if args.acknowledge_reviewed_backup and not args.apply:
        parser.error("--acknowledge-reviewed-backup is valid only with --apply")

    settings = connection_settings(migration=True)
    with connect(migration=True) as connection:
        if not migration_tracking_exists(connection, settings.database):
            raise RuntimeError(
                "schema_migrations is missing. Refusing changes: verify whether this is an empty DB "
                "(use scripts/init_db.py) or a legacy DB needing a DBA-approved baseline."
            )
        applied = applied_migrations(connection)
        pending: list[tuple[str, Path, str]] = []

        for version, path in forward_migrations():
            checksum = file_checksum(path)
            if version in applied:
                recorded = applied[version]
                if recorded and recorded != checksum:
                    raise RuntimeError(
                        f"Checksum mismatch for already-applied migration {version}; refusing to continue."
                    )
                print(f"APPLIED {version}")
            else:
                pending.append((version, path, checksum))
                print(f"PENDING {version}")

        if not pending:
            print("Database migration status: current. No changes made.")
            return 0

        if args.preflight:
            for version, path, _ in pending:
                preflight = matching_preflight(path)
                count = verify_preflight_read_only(preflight)
                print(f"READ-ONLY PREFLIGHT {version}: {preflight.name} ({count} queries)")
                execute_sql_file(connection, preflight, skip_use=True, echo_results=True)
            print("Preflight executed. Review its results and check a verified backup before applying migrations.")

        if not args.apply:
            print(f"{len(pending)} migration(s) pending in {settings.database!r}. No changes made.")
            return 0 if args.preflight else 2

        # MySQL DDL may implicitly commit. Execute only after explicit permission;
        # a database snapshot is essential for recovery from a partial migration.
        for version, path, checksum in pending:
            print(f"APPLY {path.name}")
            execute_sql_file(connection, path, skip_use=True)
            record_checksum(connection, version, checksum)

        print(f"Applied {len(pending)} migration(s) to {settings.database!r}; verify full schema before deploy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
