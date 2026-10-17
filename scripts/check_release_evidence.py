"""Fail-closed pre-promotion checklist for external release evidence.

This checks evidence *completeness and consistency*, not authenticity of a
human assertion or a third-party service. The release owner must verify links,
records and approvals independently before production promotion.

Do NOT commit real evidence carrying customer details, tokens or credentials.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

from check_release_package import inspect_archive, sha256

REQUIRED_EVIDENCE = (
    'flask_github_actions', 'mysql8_github_actions', 'render_staging_flows',
    'resend_inbox_receipt', 'mobile_desktop_browser',
    'privacy_terms_approval', 'verified_database_backup', 'rollback_plan',
    'render_environment_review',
)


def evaluate(evidence: object, candidate: Path, project_root: Path) -> list[str]:
    blockers: list[str] = []
    if not isinstance(evidence, dict):
        return ['Evidence must be a JSON object']
    if not candidate.is_file():
        return ['Candidate ZIP is missing']
    blockers.extend(inspect_archive(candidate))
    if evidence.get('artifact_sha256') != sha256(candidate):
        blockers.append('Evidence SHA-256 does not match exact ZIP candidate')

    commit = evidence.get('source_commit_sha')
    if not isinstance(commit, str) or not re.fullmatch(r'[0-9a-f]{40}', commit):
        blockers.append('Exact source_commit_sha (40 lowercase hex) missing')
    checks = evidence.get('checks')
    if not isinstance(checks, dict):
        blockers.append('checks object missing')
        checks = {}
    for name in REQUIRED_EVIDENCE:
        item = checks.get(name)
        if not isinstance(item, dict) or item.get('status') != 'passed':
            blockers.append(f'{name}: no verified passed evidence recorded')
            continue
        url = item.get('evidence_url')
        if not isinstance(url, str):
            blockers.append(f'{name}: HTTPS evidence URL missing')
            continue
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
            blockers.append(f'{name}: evidence link must be HTTPS without embedded credentials')
        if parsed.hostname in ('example.com', 'example.org', 'example.net') or '/example/' in parsed.path:
            blockers.append(f'{name}: placeholder evidence URL is not valid release evidence')
        if name.endswith('github_actions'):
            if not isinstance(commit, str) or item.get('commit_sha') != commit:
                blockers.append(f'{name}: CI commit must match the exact release source commit')
            if not re.fullmatch(r'github\.com', parsed.hostname or '') or not re.search(r'/actions/runs/\d+(?:/|$)', parsed.path):
                blockers.append(f'{name}: GitHub Actions run URL missing')

    legal_template = project_root / 'templates/main/static.html'
    if not legal_template.is_file():
        blockers.append('Legal page template missing')
    else:
        page = legal_template.read_text(encoding='utf-8')
        if any(marker in page for marker in (
            'Development MVP policy template',
            'Development MVP terms template',
            'Before production',
        )):
            blockers.append('Privacy/Terms still contain development placeholder text')

    return sorted(set(blockers))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--evidence', required=True, type=Path)
    args = parser.parse_args()
    if not args.evidence.is_file():
        print('RELEASE EVIDENCE GATE: HOLD — external evidence file absent')
        return 2
    try:
        data = json.loads(args.evidence.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        print('RELEASE EVIDENCE GATE: HOLD — unreadable evidence (' + type(exc).__name__ + ')')
        return 2
    blockers = evaluate(data, args.candidate, Path(__file__).resolve().parent.parent)
    if blockers:
        print('RELEASE EVIDENCE GATE: HOLD')
        for problem in blockers:
            print(' - ' + problem)
        return 1
    print('RELEASE EVIDENCE GATE: COMPLETE — recorded fields are consistent.')
    print('Not an independent verification of URLs, signatures or production functionality.')
    print('Human release owner must validate original evidence before deployment.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
