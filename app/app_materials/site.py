from playwright.async_api import async_playwright

from ..config import LIGHTPANDA_CDP_URL


async def fetch_rendered_html(url: str, timeout_ms: int = 15000) -> tuple[str, str]:
    """Load a page through Lightpanda (over CDP) and return (final_url, html)
    after client-side JS has had a chance to hydrate the page — catches media
    that only appears in the DOM after the framework's JS runs, not in the
    server-rendered markup a plain HTTP request would see."""
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(LIGHTPANDA_CDP_URL)
        # Don't call browser.close(): this is a shared, long-running Lightpanda
        # instance, not a browser we launched ourselves — closing our context
        # is enough cleanup and leaves it running for the next scan.
        context = await browser.new_context()
        try:
            page = await context.new_page()
            await page.goto(url, wait_until="load", timeout=timeout_ms)
            await page.wait_for_timeout(1500)
            html = await page.content()
            return page.url, html
        finally:
            await context.close()
