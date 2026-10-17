"""Check public Privacy/Terms page completeness without inventing legal approval.

This CI gate validates source content only; it is NOT a legal-compliance
opinion. The release owner must separately document legal/privacy sign-off
in the fail-closed production release evidence checklist.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PLACEHOLDER_MARKERS = (
    "Development MVP policy template",
    "Development MVP terms template",
    "Before production",
    "TODO: privacy",
    "TODO: terms",
    "REPLACE WITH POLICY",
    "REPLACE WITH TERMS",
)

PRIVACY_SECTIONS = (
    "Information we collect", "How we use information",
    "Visibility and sharing", "Location information",
    "Cookies and security", "Retention and account requests",
    "Contact and updates",
)
TERMS_SECTIONS = (
    "Marketplace services", "Accounts and accurate information",
    "Requests and service arrangements", "Payments and subscriptions",
    "Reviews, content and moderation", "Service disputes and platform limitations",
    "Changes and contact",
)


def analyze_content(legal: str) -> list[str]:
    blockers = []
    for marker in PLACEHOLDER_MARKERS:
        if marker.lower() in legal.lower():
            blockers.append(f"Development placeholder still present: {marker}")
    # Distinguish branches: a heading in the About page does not satisfy legal
    # disclosure requirements. Keep independent coverage of Privacy and Terms.
    pivot = "{% elif kind == 'privacy' %}"
    terms_pivot = "{% else %}"
    if pivot not in legal:
        return blockers + ["Missing privacy template branch"]
    privacy_and_terms = legal.split(pivot, 1)[1]
    if terms_pivot not in privacy_and_terms:
        return blockers + ["Missing terms template branch"]
    privacy, terms = privacy_and_terms.split(terms_pivot, 1)
    for label, part, headings in (
        ("Privacy", privacy, PRIVACY_SECTIONS),
        ("Terms", terms, TERMS_SECTIONS),
    ):
        if f"<h1>{'Privacy Policy' if label == 'Privacy' else 'Terms of Use'}</h1>" not in part:
            blockers.append(f"{label} page heading missing")
        for title in headings:
            if f"<h2>{title}</h2>" not in part:
                blockers.append(f"{label} section missing: {title}")
        if "lc_url('contact.php')" not in part:
            blockers.append(f"{label} contact route missing")
    return blockers


def content_blockers() -> list[str]:
    path = ROOT / "templates/main/static.html"
    try:
        return analyze_content(path.read_text(encoding="utf-8"))
    except OSError:
        return ["Legal page template cannot be read"]


def main() -> int:
    failures = content_blockers()
    if failures:
        print("RELEASE CONTENT GATE: BLOCKED")
        for issue in failures:
            print(" - " + issue)
        return 1
    print("RELEASE CONTENT GATE: PASS (content completeness; NOT legal approval)")
    print("PRODUCTION STILL REQUIRES: documented owner/legal sign-off and all other release gates.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
