"""Only offline helper tests; mock transport, no live requests."""
from __future__ import annotations

from pathlib import Path
import sys
from urllib import error

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from run_public_readonly_smoke import base_url_ok, check_endpoint, PATHS


def test_reject_non_https_or_credentialed_staging_origin():
    assert base_url_ok('https://staging.example.org')
    assert not base_url_ok('http://staging.example.org')
    assert not base_url_ok('https://name:password@staging.example.org')
    assert not base_url_ok('https://staging.example.org/login')


def test_all_paths_are_public_gets():
    assert '/auth/login.php' in PATHS
    assert '/contact.php' in PATHS
    assert '/health' in PATHS


def test_redirect_to_different_host_blocks(monkeypatch):
    class Fake:
        status = 200
        def geturl(self): return 'https://another-host.example.org/'
        def read(self, _): return b'hello'
        def __enter__(self): return self
        def __exit__(self, *_): return False
    from run_public_readonly_smoke import request
    monkeypatch.setattr(request, 'urlopen', lambda *_a, **_k: Fake())
    assert check_endpoint('https://staging.example.org','/') == 'unsafe or unexpected redirect destination'


def test_network_failure_is_reported_not_passed(monkeypatch):
    from run_public_readonly_smoke import request
    def explode(*_a, **_k): raise error.URLError('fake offline DNS error')
    monkeypatch.setattr(request, 'urlopen', explode)
    assert check_endpoint('https://staging.example.org','/') == 'URLError'
