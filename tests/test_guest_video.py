import re

import pytest
from playwright.sync_api import Locator, Page, TimeoutError, expect

pytestmark = pytest.mark.media


def media_state(video: Locator) -> dict:
    return video.evaluate(
        """media => ({
            currentTime: media.currentTime,
            duration: Number.isFinite(media.duration) ? media.duration : null,
            paused: media.paused,
            seeking: media.seeking,
            readyState: media.readyState,
            error: media.error?.code ?? null,
        })"""
    )


def start_guest_video(
    page: Page, url: str, title: str | None, *, wait_for_media: bool = False
) -> Locator:
    response = page.goto(url, wait_until="domcontentloaded")
    assert response and response.ok, "The guest watch page must load successfully"
    if title:
        expect(page).to_have_title(re.compile(re.escape(title)), timeout=10_000)

    play_button = page.get_by_role("button", name="Play", exact=True)
    expect(play_button).to_be_enabled(timeout=10_000)
    if wait_for_media:
        # Start the seek scenario after mobile playback initialization;
        # the first-tap test covers the cold start separately.
        page.wait_for_function(
            "document.querySelector('video')?.readyState >= 2", timeout=15_000
        )
    play_button.tap()

    video = page.locator("video").first
    expect(video).to_be_attached(timeout=15_000)
    try:
        page.wait_for_function(
            """() => {
                const media = document.querySelector('video');
                return media && (
                    media.error ||
                    (!media.paused && media.readyState >= 2 && media.currentTime >= 0.25)
                );
            }""",
            timeout=15_000,
        )
    except TimeoutError:
        raise AssertionError(f"Guest video did not start: {media_state(video)}") from None
    return video


def test_guest_can_play_public_video(
    mobile_page: Page, video_url: str, demo_video_title: str | None
) -> None:
    video = start_guest_video(mobile_page, video_url, demo_video_title)
    state = media_state(video)
    assert state["error"] is None, f"Media reported an error: {state}"
    assert not state["paused"] and state["currentTime"] >= 0.25, state


def test_guest_can_seek_and_continue_playing(
    mobile_page: Page, video_url: str, demo_video_title: str | None
) -> None:
    video = start_guest_video(mobile_page, video_url, demo_video_title, wait_for_media=True)
    started = media_state(video)
    assert started["error"] is None and not started["paused"], started
    duration = started["duration"]
    assert duration and duration > 2, "Use a test video that lasts more than two seconds"

    # Drive the media seek directly so the check is independent of the progress bar layout.
    target = min(8, duration * 2 / 3)
    video.evaluate(
        """(media, time) => {
            media.addEventListener('seeked', () => {
                media.dataset.qaSeekTime = String(media.currentTime);
            }, { once: true });
            media.currentTime = time;
        }""",
        target,
    )
    try:
        mobile_page.wait_for_function(
            """target => {
                const media = document.querySelector('video');
                return media && (
                    media.error ||
                    (media.dataset.qaSeekTime && !media.seeking &&
                     !media.paused && media.currentTime >= target + 0.25)
                );
            }""",
            arg=target,
            timeout=15_000,
        )
    except TimeoutError:
        raise AssertionError(f"Playback did not resume after seeking: {media_state(video)}") from None

    resumed = media_state(video)
    assert resumed["error"] is None and not resumed["paused"] and not resumed["seeking"], resumed
    seek_time = float(video.get_attribute("data-qa-seek-time"))
    assert abs(seek_time - target) < 0.5, f"Expected {target}s, seek ended at {seek_time}s"
