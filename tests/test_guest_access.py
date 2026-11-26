import re
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.security


def test_guest_merchant_navigation_goes_to_demo_or_login(page: Page, base_url: str):
    page.goto(f"{base_url}/app/#/secure/video", wait_until="domcontentloaded")

    # The website currently sends anonymous visitors to a demo. A direct
    # sign-in route also preserves access control for the merchant area.
    expect(page).to_have_url(
        re.compile(
            rf"^{re.escape(base_url)}(?:/login(?:[?#].*)?"
            r"|/app/#/(?:solutions/demo(?:/[^?]*)?|login)(?:\?.*)?)$"
        ),
        timeout=20_000,
    )


def test_guest_reviewer_navigation_requires_sign_in(page: Page, base_url: str):
    page.goto(f"{base_url}/app/#/platform-admin/video-review", wait_until="domcontentloaded")

    expect(page.locator('input[type="password"]')).to_be_visible(timeout=20_000)
    assert urlsplit(page.url).fragment.split("?", 1)[0] == "/platform-admin/login"
    expect(page.locator(".platform-review-row")).to_have_count(0)


@pytest.mark.parametrize(
    "path",
    [
        "/backend-api/auth/login/login-status",
        "/backend-api/super-manager/video-review/list",
    ],
    ids=["merchant-session", "review-queue"],
)
def test_protected_api_requires_authentication(page: Page, base_url: str, path: str):
    response = page.request.get(base_url + path, max_redirects=0, timeout=15_000)
    assert response.status in (401, 403), f"Expected denial, received HTTP {response.status}"
