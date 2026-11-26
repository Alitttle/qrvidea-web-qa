"""Anonymous browser checks for QRVidea's public website."""

import re

import pytest
from playwright.sync_api import Page, expect


def open_public_page(page: Page, base_url: str, path: str) -> None:
    response = page.goto(f"{base_url}{path}", wait_until="domcontentloaded")
    assert response is not None and response.ok, f"Could not open {path}: {response}"


@pytest.mark.smoke
def test_homepage_explains_how_to_create_a_qr(page: Page, base_url: str) -> None:
    open_public_page(page, base_url, "/")
    expect(page.locator("html")).to_have_attribute("lang", "es-MX")
    expect(page.get_by_role("heading", level=1)).to_contain_text("en un código QR")

    # "Cómo funciona" 同时出现在 hero CTA 和页脚导航里，必须限定作用域，
    # 否则会依赖 i18n 填充文案的时序（本地能过、CI 上 strict mode 冲突）。
    page.locator(".marketing-copy .marketing-buttons").get_by_role(
        "link", name="Cómo funciona", exact=True
    ).click()

    expect(page).to_have_url(re.compile(r"#como-funciona$"))
    expect(page.locator("#como-funciona").get_by_role("heading", level=2)).to_be_in_viewport()


@pytest.mark.parametrize(
    ("locale", "heading"),
    [("en", "Turn videos, images and more"), ("zh-CN", "把视频、图片等内容")],
    ids=["english", "simplified-chinese"],
)
@pytest.mark.smoke
def test_language_switch_survives_reload(
    page: Page, base_url: str, locale: str, heading: str
) -> None:
    open_public_page(page, base_url, "/")
    page.get_by_role("combobox", name="Idioma").select_option(locale)
    expect(page.get_by_role("heading", level=1)).to_contain_text(heading)

    page.reload(wait_until="domcontentloaded")

    expect(page.locator("html")).to_have_attribute("lang", locale)
    expect(page.get_by_role("heading", level=1)).to_contain_text(heading)


@pytest.mark.smoke
def test_mobile_menu_opens_help_without_horizontal_scroll(
    mobile_page: Page, base_url: str
) -> None:
    open_public_page(mobile_page, base_url, "/")
    menu = mobile_page.locator("details.mobile-menu")
    toggle = menu.locator("summary")
    faq = menu.get_by_role("link", name="Preguntas frecuentes", exact=True)
    expect(faq).not_to_be_visible()

    toggle.click()
    expect(faq).to_be_visible()
    toggle.click()
    expect(faq).not_to_be_visible()
    toggle.click()
    faq.click()

    expect(mobile_page).to_have_url(re.compile(r"/faq(?:[?#].*)?$"))
    expect(
        mobile_page.get_by_role("heading", name="¿En qué podemos ayudarte?")
    ).to_be_visible()
    mobile_page.wait_for_function(
        "document.documentElement.scrollWidth <= window.innerWidth + 1"
    )


@pytest.mark.smoke
def test_faq_can_show_and_hide_an_answer(page: Page, base_url: str) -> None:
    open_public_page(page, base_url, "/faq")
    question = page.get_by_role(
        "button", name="¿Cómo recupero el acceso a mi cuenta?", exact=True
    )
    answer = page.get_by_role(
        "region", name="¿Cómo recupero el acceso a mi cuenta?", exact=True
    )
    expect(question).to_have_attribute("aria-expanded", "false")

    question.click()
    expect(question).to_have_attribute("aria-expanded", "true")
    expect(answer).to_be_visible()

    question.click()
    expect(question).to_have_attribute("aria-expanded", "false")
    expect(answer).not_to_be_visible()


@pytest.mark.smoke
def test_faq_search_shows_results_and_empty_state(page: Page, base_url: str) -> None:
    open_public_page(page, base_url, "/faq")
    search = page.get_by_role("searchbox")
    results = page.locator(".faq-results").get_by_role("status")

    search.fill("contraseña")
    expect(results).to_have_text(re.compile(r"^[1-9]\d* preguntas?$"))
    expect(
        page.get_by_role("button", name=re.compile("contraseña", re.IGNORECASE)).first
    ).to_be_visible()

    search.fill("qrvidea-qa-zz031")
    expect(results).to_have_text("0 preguntas")
    expect(page.get_by_text("No encontramos respuestas con esos filtros.")).to_be_visible()


@pytest.mark.parametrize(
    "path", ["/plans", "/trial", "/cases"], ids=["plans", "trial", "industry-cases"]
)
@pytest.mark.solutions
def test_solution_page_renders_its_main_content(
    page: Page, base_url: str, path: str
) -> None:
    frame_errors = []

    def collect_frame_error(message):
        if message.type == "error" and "frame-src" in message.text:
            frame_errors.append(message.text)

    page.on("console", collect_frame_error)
    open_public_page(page, base_url, path)
    content = page.frame_locator("#solution-page-frame").get_by_role("main")
    heading = content.get_by_role("heading", level=1)

    # The outer page can return 200 while the browser blocks the content iframe.
    try:
        expect(heading).to_be_visible(timeout=10_000)
    except AssertionError:
        if frame_errors:
            pytest.fail("Main content did not render. Browser console: " + frame_errors[-1])
        raise
    expect(heading).to_have_text(re.compile(r"\S"))
