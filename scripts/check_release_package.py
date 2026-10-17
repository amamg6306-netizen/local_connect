"""Offline safety/integrity checks for a distributable Localjoin source ZIP.

This does not verify production deployment, third-party service configuration or
secret values embedded in arbitrary Python source: perform separate review.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path, PurePosixPath
import stat
import sys
import zipfile

REQUIRED = {
    'app.py', 'requirements.txt', 'render.yaml', '.env.example',
    'scripts/run_runtime_tests.py', 'scripts/check_release_content.py',
    '.github/workflows/localjoin-runtime-tests.yml',
    'templates/base.html',
}


def inspect_archive(path: Path) -> list[str]:
    problems = []
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            names = [item.filename for item in entries]
            if len(names) != len(set(names)):
                problems.append('ZIP contains duplicate paths')
            for item in entries:
                name = item.filename
                parts = PurePosixPath(name).parts
                if (not parts or name.startswith('/') or '\\' in name or
                        any(part in ('', '.', '..') for part in parts)):
                    problems.append('Unsafe ZIP member path detected')
                    continue
                if stat.S_ISLNK(item.external_attr >> 16):
                    problems.append('ZIP symlink found (not allowed)')
                lowered = [part.lower() for part in parts]
                if ('__pycache__' in lowered or '.git' in lowered or '.pytest_cache' in lowered or
                        any(part.endswith(('.pyc', '.pyo', '.sqlite', '.sqlite3', '.db')) for part in lowered)):
                    problems.append('Cache, Git metadata, or DB file bundled in archive')
                if any(part == '.env' or (part.startswith('.env.') and part != '.env.example') for part in lowered):
                    problems.append('Non-example environment file bundled in archive')
                if any(part in ('id_rsa', 'id_ed25519') or part.endswith(('.pem', '.key', '.p12', '.pfx')) for part in lowered):
                    problems.append('Private key or certificate-like file bundled in archive')
                if 'uploads' in lowered and not name.endswith('/') and not name.endswith('/.htaccess'):
                    problems.append('Non-placeholder uploaded data bundled in archive')
            missing = REQUIRED - set(names)
            if missing:
                problems.append('Required release files absent: ' + ', '.join(sorted(missing)))
            failed = archive.testzip()
            if failed:
                problems.append('ZIP CRC verification failed')
    except (OSError, zipfile.BadZipFile) as exc:
        problems.append('Archive cannot be inspected: ' + type(exc).__name__)
    return sorted(set(problems))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('candidate', type=Path)
    args = parser.parse_args()
    problems = inspect_archive(args.candidate)
    if problems:
        print('PACKAGE GATE: FAIL')
        for problem in problems:
            print(' - ' + problem)
        return 1
    print('PACKAGE GATE: PASS (ZIP structural checks only)')
    print('SHA256:', sha256(args.candidate))
    print('This is NOT a runtime, staging, secrets, or production-readiness attestation.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
