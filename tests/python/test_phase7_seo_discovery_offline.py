"""Phase 7 guards: no Flask or live external services required."""
from pathlib import Path

from utils.seo import canonical_site_root, robots_txt, seo_policy, sitemap_xml
from utils.search_filters import parse_max_price

ROOT = Path(__file__).resolve().parents[2]


def test_indexable_public_pages_use_configured_canonical_not_host():
    for path in ("/", "/index.php", "/categories.php", "/about.php", "/contact.php"):
        meta = seo_policy(path, {"utm_source": "evil.example"}, "https://localjoin.in/", "production")
        assert meta["robots"] == "index,follow"
        assert meta["canonical"] == "https://localjoin.in" + ("/" if path == "/index.php" else path)


def test_private_token_and_search_pages_never_indexed():
    for path in ("/admin/index.php", "/auth/login.php", "/auth/verify-email.php", "/auth/reset-password.php",
                 "/customer/dashboard.php", "/provider/services.php", "/business/dashboard.php", "/notifications.php",
                 "/request-details.php", "/uploads/profiles/test.jpg", "/privacy.php", "/terms.php"):
        meta = seo_policy(path, {"token": "private-secret"}, "https://localjoin.in", "production")
        assert meta["robots"].startswith("noindex"), path
        assert meta["canonical"] is None
    search = seo_policy("/search.php", {"q": "secret query", "page": "5"}, "https://localjoin.in", "production")
    assert search == {"robots": "noindex,follow", "canonical": None}


def test_staging_and_invalid_public_host_fail_closed():
    for env in ("development", "testing", "staging"):
        assert seo_policy("/", {}, "https://localjoin.in", env)["canonical"] is None
        assert seo_policy("/", {}, "https://localjoin.in", env)["robots"] == "noindex,nofollow"
        assert "Disallow: /" in robots_txt("https://localjoin.in", env)
        assert sitemap_xml("https://localjoin.in", env) is None
    for url in ("", "http://localjoin.in", "https://evil.example@localjoin.in", "https://localjoin.in/?a=b",
                "https://localjoin.in/unsafe", "https://localjoin.in:444", "https://<svg>.com", "https://localjoin..in"):
        assert canonical_site_root(url) is None, url


def test_profile_canonical_only_accepts_positive_decimal_id():
    valid = seo_policy("/provider.php", {"id": "00030004", "next": "//evil.example"}, "https://localjoin.in", "production")
    assert valid == {"robots": "index,follow", "canonical": "https://localjoin.in/provider.php?id=30004"}
    business = seo_policy("/business.php", {"id": "30005"}, "https://localjoin.in", "production")
    assert business["canonical"] == "https://localjoin.in/business.php?id=30005"
    for bad in ("", "0", "-1", "+1", "1.5", "1%26token=bad", "evil", "9" * 30, "٣", "1&next=bad"):
        assert seo_policy("/provider.php", {"id": bad}, "https://localjoin.in", "production")["canonical"] is None


def test_robots_and_sitemap_exclude_account_and_dynamic_queries():
    robots = robots_txt("https://localjoin.in", "production")
    assert "Disallow: /auth/" in robots and "Disallow: /search.php" in robots
    assert "Sitemap: https://localjoin.in/sitemap.xml" in robots
    xml = sitemap_xml("https://localjoin.in", "production")
    assert xml is not None
    assert "<loc>https://localjoin.in/</loc>" in xml
    for secret in ("auth/", "admin/", "provider.php?", "?q=", "customer/", "privacy.php", "terms.php"):
        assert secret not in xml


def test_price_filter_rejects_infinite_nan_overflow():
    for bad in (None, "", "NaN", "nan", "Infinity", "-Infinity", "-3", "1e9999", "abc", "100000001"):
        assert parse_max_price(bad) == 0.0
    assert parse_max_price("0") == 0.0
    assert parse_max_price("350.50") == 350.5


def test_routes_disallow_inactive_catalogue_matches_and_false_availability_claims():
    source = (ROOT / "routes/main.py").read_text(encoding="utf-8")
    page = (ROOT / "templates/main/search.html").read_text(encoding="utf-8")
    assert 'Category.id == Service.category_id) & (Category.is_active == 1)' in source
    assert 'stmt.where(eligible_offering, Category.id.is_not(None))' in source
    assert 'ProviderProfile.availability_status == "available"' in source
    assert 'User.role == "business", ProviderProfile.availability_status' not in source
    assert 'Workers accepting requests' in page
    assert 'Available now</option>' not in page


def test_secure_robot_headers_and_template_metadata_hooks():
    security = (ROOT / "utils/security.py").read_text(encoding="utf-8")
    base = (ROOT / "templates/base.html").read_text(encoding="utf-8")
    assert 'response.headers["X-Robots-Tag"]' in security
    for value in ('seo.canonical', 'seo.robots', 'rel="canonical"', 'og:title', 'og:url'):
        assert value in base


def test_release_content_gate_checks_real_policy_and_terms_copy():
    from scripts.check_release_content import content_blockers
    assert content_blockers() == [], "Public policy/terms copy should have no placeholders and all required sections"


def test_phase7_navigation_search_controls_have_accessible_names():
    nav = (ROOT / "templates/partials/navbar.html").read_text(encoding="utf-8")
    search = (ROOT / "templates/main/search.html").read_text(encoding="utf-8")
    assert 'aria-controls="mainNav"' in nav
    assert 'aria-label="Toggle navigation"' in nav
    for label in ("Service or keyword", "City or service area", "Service category", "Provider type",
                  "Availability", "Maximum service price", "Sort search results"):
        assert f'aria-label="{label}"' in search


def test_phase7_static_navigation_links_resolve_to_legacy_flask_paths():
    """Catch accidentally broken static site links without a Flask server."""
    import re
    routes = set()
    for module in (ROOT / "routes").glob("*.py"):
        routes.update(re.findall(r'@bp\.(?:get|post|route)\("([^"<]+)', module.read_text(encoding="utf-8")))
    checked = set()
    for template in (ROOT / "templates").rglob("*.html"):
        for link in re.findall(r"lc_url\('([^']+)[')]", template.read_text(encoding="utf-8")):
            if '.php' in link:
                checked.add("/" + link.split("?")[0])
    assert len(checked) >= 40
    assert checked <= routes, sorted(checked - routes)
