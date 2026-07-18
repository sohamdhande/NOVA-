from playwright.async_api import (
    async_playwright, Browser, Page
)
import asyncio, os, json
from datetime import datetime

class BrowserAutomation:
    
    def __init__(self):
        self._browser = None
        self._page = None
        self._playwright = None
    
    async def start(self):
        """Launch browser."""
        self._playwright = await \
            async_playwright().start()
        self._browser = await \
            self._playwright.chromium.launch(
                headless=False,
                args=['--start-maximized']
            )
        context = await \
            self._browser.new_context(
                viewport={'width': 1280, 
                          'height': 800}
            )
        self._page = await context.new_page()
        return self._page
    
    async def navigate(self, url: str) -> str:
        if not self._page:
            await self.start()
        if not url.startswith('http'):
            url = 'https://' + url
        await self._page.goto(
            url, wait_until='networkidle',
            timeout=30000
        )
        title = await self._page.title()
        return f"Navigated to: {title}"
    
    async def click(self, selector: str) -> str:
        """Click element by text or selector."""
        try:
            # Try text first
            await self._page.click(
                f'text={selector}', timeout=5000
            )
            return f"Clicked: {selector}"
        except:
            try:
                await self._page.click(
                    selector, timeout=5000
                )
                return f"Clicked: {selector}"
            except Exception as e:
                return f"Click failed: {e}"
    
    async def type_text(self, selector: str,
                         text: str) -> str:
        """Type into input field."""
        try:
            await self._page.fill(selector, text)
            return f"Typed: {text[:30]}"
        except Exception as e:
            return f"Type failed: {e}"
    
    async def get_text(self) -> str:
        """Get all visible text from page."""
        try:
            text = await self._page.inner_text(
                'body'
            )
            return text[:3000]
        except Exception as e:
            return f"Get text failed: {e}"
    
    async def screenshot(self, 
                          path: str = None) -> str:
        """Take browser screenshot."""
        if not path:
            ts = datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
            path = os.path.expanduser(
                f"~/Desktop/browser_{ts}.png"
            )
        await self._page.screenshot(path=path)
        return f"Screenshot: {path}"
    
    async def scrape(self, url: str,
                      selector: str = None) -> str:
        """Scrape content from URL."""
        await self.navigate(url)
        await asyncio.sleep(2)
        if selector:
            try:
                elements = await \
                    self._page.query_selector_all(
                        selector
                    )
                texts = []
                for el in elements[:20]:
                    t = await el.inner_text()
                    if t.strip():
                        texts.append(t.strip())
                return "\n".join(texts)
            except:
                pass
        return await self.get_text()
    
    async def fill_form(self, 
                         fields: dict) -> str:
        """Fill form fields. 
        fields: {selector: value}"""
        results = []
        for selector, value in fields.items():
            try:
                await self._page.fill(
                    selector, str(value)
                )
                results.append(
                    f"✓ {selector}: {value}"
                )
            except Exception as e:
                results.append(
                    f"✗ {selector}: {e}"
                )
        return "\n".join(results)
    
    async def search_google(self, 
                             query: str) -> str:
        """Search Google and return results."""
        await self.navigate(
            f"https://www.google.com"
            f"/search?q={query}"
        )
        await asyncio.sleep(2)
        
        # Extract search results
        try:
            results = await \
                self._page.query_selector_all(
                    'h3'
                )
            texts = []
            for r in results[:5]:
                t = await r.inner_text()
                if t.strip():
                    texts.append(t.strip())
            return "Search results:\n" + \
                   "\n".join(
                       f"• {t}" for t in texts
                   )
        except:
            return await self.get_text()
    
    async def close(self):
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._page = None

browser_automation = BrowserAutomation()
