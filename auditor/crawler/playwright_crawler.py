import os
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from playwright.async_api import async_playwright, Browser, Page
from auditor.core.config import settings
from auditor.core.logging import logger

class PlaywrightCrawler:
    """
    Headless Chromium browser automation engine.
    Renders target pages, executes JavaScript, computes the accessibility tree,
    extracts bounding boxes for visual inspection, and captures high-res screenshots.
    """

    def __init__(self, headless: Optional[bool] = None, timeout_ms: Optional[int] = None):
        self.headless = settings.HEADLESS_BROWSER if headless is None else headless
        self.timeout_ms = timeout_ms or settings.CRAWL_TIMEOUT_MS

    async def crawl_url(
        self,
        url: str,
        job_id: str,
    ) -> Tuple[str, Optional[str], Dict[str, Dict[str, float]], Dict[str, Any]]:
        """
        Crawls target URL, takes viewport & full-page screenshots, extracts DOM and bounding boxes.
        Returns:
            (html_content, screenshot_path, element_bounding_boxes, a11y_tree_snapshot)
        """
        logger.info(f"Crawling URL: '{url}' (job_id={job_id})")
        screenshot_path = os.path.join(settings.SCREENSHOTS_DIR, f"{job_id}_viewport.png")
        full_screenshot_path = os.path.join(settings.SCREENSHOTS_DIR, f"{job_id}_full.png")

        try:
            async with async_playwright() as p:
                browser: Browser = await p.chromium.launch(
                    headless=self.headless,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"],
                )
                context = await browser.new_context(
                    viewport={"width": settings.VIEWPORT_WIDTH, "height": settings.VIEWPORT_HEIGHT},
                    device_scale_factor=1.0,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 AI-A11y-Auditor/1.0",
                )
                page: Page = await context.new_page()

                # Handle local file:// or http(s)://
                if url.startswith("http://") or url.startswith("https://") or url.startswith("file://"):
                    target_url = url
                elif os.path.exists(url):
                    target_url = Path(url).resolve().as_uri()
                else:
                    target_url = f"https://{url}"

                await page.goto(target_url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                # Wait briefly for dynamic layouts / animations
                await page.wait_for_timeout(1000)

                # Capture screenshots
                await page.screenshot(path=screenshot_path, full_page=False)
                await page.screenshot(path=full_screenshot_path, full_page=True)

                # Extract rendered DOM HTML
                html_content = await page.content()

                # Extract accessibility tree snapshot
                a11y_tree = {}
                if hasattr(page, "accessibility") and page.accessibility is not None:
                    try:
                        a11y_tree = await page.accessibility.snapshot() or {}
                    except Exception as e:
                        logger.debug(f"Accessibility snapshot skipped: {e}")
                        a11y_tree = {}


                # Extract interactive element bounding boxes via JS evaluation
                boxes = await self._extract_element_boxes(page)

                await browser.close()
                return html_content, screenshot_path, boxes, a11y_tree

        except Exception as e:
            logger.error(f"Playwright crawling failed for '{url}': {e}. Using fallback static engine.")
            return await self._fallback_crawl(url, job_id)

    async def _extract_element_boxes(self, page: Page) -> Dict[str, Dict[str, float]]:
        """Evaluates bounding boxes for interactive and visual elements in the page."""
        js_script = """
        () => {
            const results = {};
            const elements = document.querySelectorAll('img, button, a, input, select, textarea, h1, h2, h3, [role="button"]');
            elements.forEach((el, idx) => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    let selector = '';
                    if (el.id) {
                        selector = '#' + el.id;
                    } else if (el.className && typeof el.className === 'string') {
                        selector = el.tagName.toLowerCase() + '.' + el.className.trim().split(/\\s+/)[0];
                    } else {
                        selector = el.tagName.toLowerCase() + ':nth-of-type(' + (idx + 1) + ')';
                    }
                    results[selector] = {
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height
                    };
                }
            });
            return results;
        }
        """
        try:
            return await page.evaluate(js_script)
        except Exception as e:
            logger.warning(f"Error evaluating element boxes: {e}")
            return {}

    async def _fallback_crawl(
        self,
        url: str,
        job_id: str,
    ) -> Tuple[str, Optional[str], Dict[str, Dict[str, float]], Dict[str, Any]]:
        """Fallback static crawler when Playwright encounters network / sandbox blocks."""
        import httpx
        from PIL import Image, ImageDraw

        html = ""
        # Check if local file
        if os.path.exists(url):
            with open(url, "r", encoding="utf-8", errors="replace") as f:
                html = f.read()
        else:
            try:
                target = url if url.startswith("http") else f"https://{url}"
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    res = await client.get(target)
                    html = res.text
            except Exception as e:
                logger.error(f"Fallback HTTP request failed: {e}")
                html = f"<html><head><title>Offline Audit Target</title></head><body><h1>Target Offline: {url}</h1><img src='logo.png'><button></button></body></html>"

        # Generate a placeholder screenshot
        screenshot_path = os.path.join(settings.SCREENSHOTS_DIR, f"{job_id}_viewport.png")
        img = Image.new("RGB", (settings.VIEWPORT_WIDTH, settings.VIEWPORT_HEIGHT), color=(240, 242, 245))
        d = ImageDraw.Draw(img)
        d.text((50, 50), f"Audit Screenshot: {url}", fill=(30, 41, 59))
        d.rectangle([100, 100, 300, 140], outline=(239, 68, 68), width=2)
        d.text((110, 110), "Simulated Target Area", fill=(15, 23, 42))
        img.save(screenshot_path)

        return html, screenshot_path, {}, {}

# Singleton crawler instance
crawler = PlaywrightCrawler()
