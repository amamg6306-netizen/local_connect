"""Read-only GET checks for an explicitly selected staging/public deployment.

Never sends registration data, credentials or POST requests. This cannot
verify login, mail delivery, payments, interactive JS, or DB write flows.
"""
from __future__ import annotations

import argparse
import sys
from urllib import error, request
from urllib.parse import urljoin, urlsplit

PATHS = (
    '/', '/auth/login.php', '/auth/register.php', '/search.php',
    '/contact.php', '/robots.txt', '/sitemap.xml', '/health',
)


def base_url_ok(base: str) -> bool:
    parts = urlsplit(base)
    return (parts.scheme == 'https' and bool(parts.hostname) and
            parts.username is None and parts.password is None and
            not parts.query and not parts.fragment and parts.path in ('', '/'))


def check_endpoint(base: str, path: str, timeout: float = 8) -> str | None:
    url = urljoin(base.rstrip('/') + '/', path.lstrip('/'))
    req = request.Request(url, headers={'User-Agent': 'Localjoin-Release-Readonly-Smoke/1.0'})
    try:
        with request.urlopen(req, timeout=timeout) as response:
            final = urlsplit(response.geturl())
            original = urlsplit(base)
            if final.scheme != 'https' or final.hostname != original.hostname:
                return 'unsafe or unexpected redirect destination'
            if response.status != 200:
                return f'HTTP {response.status}'
            # Read only small public response body; do not log or store its content.
            response.read(64)
    except (error.HTTPError, error.URLError, TimeoutError, OSError) as exc:
        return type(exc).__name__
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--timeout', type=float, default=8.0)
    args = parser.parse_args()
    if not base_url_ok(args.base_url) or args.timeout <= 0:
        print('SMOKE GATE: HOLD — supply an HTTPS origin URL without credentials or path')
        return 2
    errors = []
    for path in PATHS:
        failed = check_endpoint(args.base_url, path, args.timeout)
        if failed:
            errors.append((path, failed))
            print(f'FAIL {path}: {failed}')
        else:
            print(f'PASS {path}: public GET HTTP 200')
    if errors:
        print(f'SMOKE GATE: FAIL ({len(errors)}/{len(PATHS)} GET checks failed)')
        return 1
    print('SMOKE GATE: PASS (read-only public endpoints only; not an E2E acceptance test)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
