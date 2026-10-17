"""Regression tests for CI content gate; NOT legal compliance tests."""
from pathlib import Path

from scripts.check_release_content import analyze_content, content_blockers

ROOT = Path(__file__).resolve().parents[2]


def test_current_public_copy_contains_both_full_policies():
    assert content_blockers() == []
    page = (ROOT / "templates/main/static.html").read_text(encoding="utf-8")
    assert "{% elif kind == 'privacy' %}" in page
    assert "{% else %}" in page
    assert "Development MVP" not in page


def test_missing_terms_branch_fails_closed():
    assert "Missing terms template branch" in analyze_content("{% elif kind == 'privacy' %}<h1>Privacy Policy</h1>")


def test_empty_terms_or_privacy_fail_closed():
    sample = "{% elif kind == 'privacy' %}<h1>Privacy Policy</h1>{% else %}<h1>Terms of Use</h1>"
    blockers = analyze_content(sample)
    assert any("Privacy section missing" in item for item in blockers)
    assert any("Terms section missing" in item for item in blockers)


def test_unapproved_placeholder_is_blocked_even_with_sections():
    page = (ROOT / "templates/main/static.html").read_text(encoding="utf-8")
    assert any("Development placeholder" in error for error in analyze_content(page + "Development MVP terms template"))


def test_missing_contact_route_fails_closed():
    page = (ROOT / "templates/main/static.html").read_text(encoding="utf-8")
    page = page.replace("lc_url('contact.php')", "lc_url('')")
    assert any("contact route missing" in issue for issue in analyze_content(page))


def test_github_workflow_uses_module_entrypoints_for_both_jobs():
    workflow = (ROOT / ".github/workflows/localjoin-runtime-tests.yml").read_text(encoding="utf-8")
    assert "run: python -m scripts.run_runtime_tests" in workflow
    assert "run: python -m scripts.run_disposable_mysql_smoke" in workflow
    assert "--ignore" not in workflow
    assert "continue-on-error: true" not in workflow
