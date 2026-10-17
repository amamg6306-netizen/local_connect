"""Validated post-login GET destinations; no Flask dependency."""

from urllib.parse import unquote, urlsplit


def safe_customer_next(value: str | None) -> str | None:
    """Preserve only relative customer GET destinations, never open redirects."""
    if not value or len(value) > 1500 or not value.startswith("/") or value.startswith("//"):
        return None
    if "\\" in value or any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    if parsed.scheme or parsed.netloc or parsed.fragment:
        return None
    decoded = unquote(value)
    if "\\" in decoded or any(ord(ch) < 32 or ord(ch) == 127 for ch in decoded):
        return None
    if any(segment in {".", ".."} for segment in unquote(parsed.path).split("/")):
        return None
    if parsed.path not in {"/request-service.php", "/post-requirement.php"} and not parsed.path.startswith("/customer/"):
        return None
    return value
