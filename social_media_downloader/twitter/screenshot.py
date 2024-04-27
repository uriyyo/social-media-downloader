import math
from asyncio import gather
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from more_itertools import divide
from playwright.async_api import BrowserContext, Route, async_playwright
from twitter.constants import Operation
from twitter.scraper import Scraper

from social_media_downloader.twitter.consts import DUMMY_LAST_TWEET, DUMMY_TWEE_ID


@asynccontextmanager
async def browser_ctx(cookies: dict[str, str]) -> AsyncIterator[BrowserContext]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, channel="chrome")

        ctx = await browser.new_context(
            color_scheme="dark",
            # **p.devices["IPhone 13"],
            # **p.devices["iPhone 14 Pro"],
            **p.devices["Pixel 7"],
            # viewport={"width": 839, "height": 412},
            # device_scale_factor=3,
            # is_mobile=True,
        )

        await ctx.add_cookies(
            [
                {
                    "name": k,
                    "value": v,
                    "domain": "twitter.com",
                    "path": "/",
                    "sameSite": "Lax",
                    "secure": True,
                }
                for k, v in cookies.items()
            ]
        )

        yield ctx


async def get_thread_tweets(
    url: str,
    *,
    cookies: dict[str, str],
    scrapper: Scraper | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    tweet_id = url.removesuffix("/").split("/")[-1]

    _scrapper = scrapper or Scraper(
        pbar=False,
        save=False,
        debug=False,
        cookies=cookies,
    )

    kwargs = {}
    if limit is not None:
        kwargs["limit"] = limit

    [responses] = await _scrapper._process(Operation.TweetDetail, [{"focalTweetId": tweet_id}], **kwargs)

    entries = []
    for response in responses:
        data = response.json()

        for entry in data["data"]["threaded_conversation_with_injections_v2"]["instructions"][0]["entries"]:
            match entry:
                case {"entryId": entry_id} if entry_id.startswith("tweet-"):
                    entries.append(entry)

    return entries


def entries_to_response(entries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "data": {
            "threaded_conversation_with_injections_v2": {
                "instructions": [
                    {"entries": [*entries, DUMMY_LAST_TWEET], "type": "TimelineAddEntries"},
                    {"direction": "Top", "type": "TimelineTerminateTimeline"},
                ],
            }
        }
    }


_TWEET_PREPARE_SCRIPT = """
    const BODY_COLOR = '#16202A';

    const updateStyles = (selector, styles, root = document) => {
        let elements = [] = typeof selector === 'string' ? root.querySelectorAll(selector) : [selector];
        elements.forEach(el => Object.assign(el.style, styles))
    };

    const removeAll = (selector) => document.querySelectorAll(selector).forEach(e => e.remove());

    // updateStyles('section[role=region]', {backgroundColor: BODY_COLOR});
    // updateStyles('[data-testid="cellInnerDiv"] > div', {borderBottomColor: BODY_COLOR});

    removeAll('[data-testid="cellInnerDiv"]:nth-last-child(-n + 2)')
    removeAll('[role="group"] > div:nth-last-child(-n + 2)')
    removeAll('[data-testid="caret"]')
    removeAll('.r-12vffkv nav')

    document.querySelector('#layers + div').scrollIntoView()
"""

_TWEET_REMOVE_BAR_SCRIPT = """
    const removeAll = (selector) => document.querySelectorAll(selector).forEach(e => e.remove());

    removeAll('[data-testid="cellInnerDiv"]:nth-last-child(1) [data-testid="Tweet-User-Avatar"] + div')
"""


async def _make_screenshot(
    ctx: BrowserContext,
    entries: list[dict[str, Any]],
    *,
    is_last: bool,
) -> bytes:
    # TODO: figure out how to intercept only TweetDetail request
    async def handle(route: Route) -> None:
        if "/TweetDetail?" in route.request.url:
            await route.fulfill(json=entries_to_response(entries))
            return

        await route.continue_()

    page = await ctx.new_page()

    await page.route("*/**", handle)
    await page.goto(f"https://twitter.com/_/status/{DUMMY_TWEE_ID}", wait_until="networkidle")

    await page.evaluate(_TWEET_PREPARE_SCRIPT)

    if is_last:
        await page.evaluate(_TWEET_REMOVE_BAR_SCRIPT)

    tweets = page.locator('[data-testid="cellInnerDiv"]')

    first_box = await tweets.first.bounding_box()
    last_box = await tweets.last.bounding_box()

    assert first_box
    assert last_box

    return await page.screenshot(
        clip={**first_box, "height": last_box["y"] + last_box["height"] - first_box["y"]},
    )


async def twitter_thread_screenshot(
    url: str,
    *,
    ct0: str,
    auth_token: str,
    scrapper: Scraper | None = None,
    limit: int | None = None,
) -> list[bytes]:
    cookies = {
        "ct0": ct0,
        "auth_token": auth_token,
    }

    tweets = await get_thread_tweets(url, scrapper=scrapper, cookies=cookies, limit=limit)

    async with browser_ctx(cookies) as ctx:
        chunks = [[*chunk] for chunk in divide(math.ceil(len(tweets) / 6), tweets)]

        screenshots = await gather(*[_make_screenshot(ctx, chunk, is_last=chunk is chunks[-1]) for chunk in chunks])

    return [*screenshots]


__all__ = [
    "twitter_thread_screenshot",
]
