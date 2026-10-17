"""Conservative, side-effect-free SEO policy for the active Flask application.

Only known public GET pages are crawlable, and the canonical host is taken from
operator-controlled APP_URL rather than untrusted Host/X-Forwarded-Host headers.
Authentication, tokens, dashboards, search filters and staging are noindex.
"""
from __future__ import annotations

from urllib.parse import urlsplit
import re

STATIC_PUBLIC_PATHS = frozenset({
    "/", "/index.php", "/categories.php", "/about.php", "/contact.php",
})
PUBLIC_PROFILE_PATHS = frozenset({"/provider.php", "/business.php"})
SITEMAP_PATHS = ("/", "/categories.php", "/about.php", "/contact.php")


def canonical_site_root(app_url: str) -> str | None:
    """Reject unsafe/malformed canonical bases; never consult request Host."""
    try:
        parsed = urlsplit(app_url.strip())
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or
                parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}):
            return None
        if parsed.port not in {None, 443}:
            return None
        hostname = parsed.hostname.lower()
        labels = hostname.split(".")
        if len(labels) < 2 or not all(
            len(label) <= 63 and re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label)
            for label in labels
        ):
            return None
        return f"https://{hostname}"
    except (ValueError, AttributeError):
        return None


def seo_policy(path: str, args: dict[str, str], app_url: str, app_env: str) -> dict[str, str | None]:
    """Return a canonical and robots directive for a route, fail closed."""
    result: dict[str, str | None] = {"robots": "noindex,nofollow", "canonical": None}
    if app_env != "production":
        return result
    root = canonical_site_root(app_url)
    if not root:
        return result
    if path in STATIC_PUBLIC_PATHS:
        normalized = "/" if path == "/index.php" else path
        result.update(robots="index,follow", canonical=root + normalized)
        return result
    # Legal pages are still development templates and deliberately remain
    # noindex until reviewed content replaces them and this allowlist is updated.
    if path in PUBLIC_PROFILE_PATHS:
        # Strip every query parameter except a validated numeric profile ID.
        raw = args.get("id", "")
        if isinstance(raw, str) and raw.isascii() and raw.isdecimal():
            profile_id = int(raw)
            if 0 < profile_id <= 2**63 - 1:
                result.update(robots="index,follow", canonical=f"{root}{path}?id={profile_id}")
    elif path == "/search.php":
        # Arbitrary search terms/filter combinations must not be indexed.
        result["robots"] = "noindex,follow"
    return result


def robots_txt(app_url: str, app_env: str) -> str:
    root = canonical_site_root(app_url)
    if app_env != "production" or root is None:
        return "User-agent: *\nDisallow: /\n"
    return (
        "User-agent: *\n"
        "Disallow: /auth/\nDisallow: /admin/\nDisallow: /customer/\n"
        "Disallow: /business/\nDisallow: /provider/\nDisallow: /billing/\n"
        "Disallow: /search.php\nDisallow: /post-requirement.php\n"
        "Disallow: /request-service.php\nDisallow: /notifications.php\n"
        "Sitemap: " + root + "/sitemap.xml\n"
    )


def sitemap_xml(app_url: str, app_env: str) -> str | None:
    root = canonical_site_root(app_url)
    if app_env != "production" or root is None:
        return None
    # APP_URL has already passed URL parsing and host validation. No private,
    # token-bearing or unbounded search/filter URLs are published.
    urls = "".join(f"<url><loc>{root}{path}</loc></url>" for path in SITEMAP_PATHS)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + \
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + urls + '</urlset>\n'
