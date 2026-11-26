import os
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import BrowserContext, Page


@pytest.fixture(scope="session")
def base_url(base_url: str) -> str:
    # Normalize the pytest-base-url fixture for path concatenation.
    return base_url.rstrip("/")


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    return {
        **browser_context_args,
        "locale": "es-MX",
    }


@pytest.fixture
def mobile_page(new_context) -> Page:
    context: BrowserContext = new_context(
        viewport={"width": 390, "height": 844},
        is_mobile=True,
        has_touch=True,
    )
    return context.new_page()


@pytest.fixture(scope="session")
def video_url(base_url: str) -> str:
    url = os.environ.get("QRVIDEA_QA_VIDEO_URL", "").strip()
    if not url:
        pytest.skip("Set QRVIDEA_QA_VIDEO_URL to an authorized public test video")

    target, site = urlsplit(url), urlsplit(base_url)
    if (
        target.scheme != site.scheme
        or target.netloc != site.netloc
        or not target.path.startswith("/watch/videos/")
        or target.query
        or target.fragment
    ):
        pytest.fail("Use a public watch page on the site under test, without query parameters")
    return url


@pytest.fixture(scope="session")
def demo_video_title() -> str | None:
    return os.environ.get("QRVIDEA_QA_VIDEO_TITLE") or None
