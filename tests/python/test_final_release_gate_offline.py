"""Only unit tests of the gate's behavior; never production attestation."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import stat
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_release_package import inspect_archive, sha256  # noqa: E402
from check_release_evidence import evaluate, REQUIRED_EVIDENCE  # noqa: E402


def make_archive(tmp_path: Path, extra: dict[str, str] | None = None) -> Path:
    from check_release_package import REQUIRED
    path = tmp_path / 'candidate.zip'
    with zipfile.ZipFile(path, 'w') as archive:
        for name in REQUIRED:
            archive.writestr(name, 'placeholder, tests only')
        for name, contents in (extra or {}).items():
            archive.writestr(name, contents)
    return path


def test_candidate_no_secrets_or_cache(tmp_path):
    assert inspect_archive(make_archive(tmp_path)) == []


def test_block_dotenv_secret(tmp_path):
    zipfile_path = make_archive(tmp_path, {'.env': 'SECRET_KEY=not_a_real_secret'})
    assert any('environment' in x for x in inspect_archive(zipfile_path))


def test_block_cache_database_and_uploaded_file(tmp_path):
    archive_path = make_archive(tmp_path, {'uploads/profiles/customer.jpg':'fake', 'tests/__pycache__/foo.pyc':'fake', 'backup.db': 'fake'})
    errors = inspect_archive(archive_path)
    assert any('uploaded' in x for x in errors)
    assert any('Cache' in x for x in errors)


def test_block_path_traversal(tmp_path):
    archive_path = make_archive(tmp_path, {'../outside.txt': 'fake'})
    assert any('Unsafe ZIP member' in x for x in inspect_archive(archive_path))


def test_evidence_absent_fails_closed(tmp_path):
    archive_path = make_archive(tmp_path)
    assert any('SHA-256' in x for x in evaluate({}, archive_path, ROOT))
    assert any('checks object missing' in x for x in evaluate({}, archive_path, ROOT))


def test_legal_signoff_is_required_even_after_public_placeholders_are_replaced(tmp_path):
    archive_path = make_archive(tmp_path)
    evidence = {
        'source_commit_sha': 'a' * 40, 'artifact_sha256': sha256(archive_path),
        'checks': {name: {'status': 'passed', 'commit_sha': 'a' * 40,
                          'evidence_url': 'https://github.com/example/repo/actions/runs/123' if name.endswith('github_actions') else 'https://internal.example.org/evidence'}
                   for name in REQUIRED_EVIDENCE if name != 'privacy_terms_approval'},
    }
    # The release evidence gate is independent of the public-copy placeholder
    # test. Legal sign-off must not be silently inferred from complete copy.
    assert any('privacy_terms_approval' in x for x in evaluate(evidence, archive_path, ROOT))


def test_claimed_pass_without_https_evidence_fails(tmp_path):
    archive_path = make_archive(tmp_path)
    evidence = {'source_commit_sha': 'a' * 40, 'artifact_sha256':sha256(archive_path), 'checks': {
        name: {'status':'passed','evidence_url':'http://example.org/not-secure'} for name in REQUIRED_EVIDENCE}}
    assert any('HTTPS' in x for x in evaluate(evidence, archive_path, ROOT))


def test_github_job_needs_actual_actions_run_link(tmp_path):
    archive_path = make_archive(tmp_path)
    evidence = {'source_commit_sha': 'a' * 40, 'artifact_sha256':sha256(archive_path), 'checks': {
        name: {'status':'passed','evidence_url':'https://example.org/pretend'} for name in REQUIRED_EVIDENCE}}
    assert any('GitHub Actions run URL' in x for x in evaluate(evidence, archive_path, ROOT))
