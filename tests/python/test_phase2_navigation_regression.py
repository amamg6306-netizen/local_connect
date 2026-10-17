"""Regression tests for customer post-login redirect validation (stdlib only)."""
from utils.navigation import safe_customer_next


def test_valid_local_customer_destinations():
    assert safe_customer_next("/request-service.php?type=provider&provider=123") == "/request-service.php?type=provider&provider=123"
    assert safe_customer_next("/post-requirement.php") == "/post-requirement.php"
    assert safe_customer_next("/customer/requests.php?page=3") == "/customer/requests.php?page=3"

def test_open_redirects_and_unsafe_paths_rejected():
    for value in ("https://evil.example", "//evil.example/path", "/\\evil.example",
                  "/auth/login.php", "/admin/index.php", "/provider/dashboard.php",
                  "/customer/../admin/index.php", "/customer/%2e%2e/admin/index.php",
                  "/request-service.php%0d%0aLocation:evil",
                  "/request-service.php?x=%0d%0a", "/request-service.php#fragment",
                  " /request-service.php", ""):
        assert safe_customer_next(value) is None, value
