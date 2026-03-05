import os
import asyncio
import logging
from playwright.async_api import async_playwright

from core.event_bus import event_bus, NovaEvent
from core.biometric import biometric_auth

logger = logging.getLogger(__name__)

class BrowserController:
    """N.O.V.A Browser Automation Module using Playwright."""
    
    def __init__(self):
        self.playwright = None
        self.context = None
        self.page = None
        
    async def start(self, headless: bool = True):
        """Launch Chromium and attach to the existing user profile."""
        self.playwright = await async_playwright().start()
        
        # Point to existing Chrome profile so user is pre-logged into Gmail, WhatsApp Web, etc.
        profile_path = os.path.expanduser("~/Library/Application Support/Google/Chrome/Default")
        
        try:
            # We use channel="chrome" to ensure we use the local Chrome browser binaries that support the existing active profile properly
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=profile_path,
                headless=headless,
                channel="chrome",
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            # Use the default initial page if one spawned, else create one
            if self.context.pages:
                self.page = self.context.pages[0]
            else:
                self.page = await self.context.new_page()
                
            logger.info("Browser automation started successfully.")
        except Exception as e:
            logger.error(f"Failed to start browser automation: {e}")
            raise

    async def _publish_success(self, action: str, target: str):
        """Internal helper to publish successful actions."""
        await event_bus.publish(NovaEvent(
            source="browser",
            type="browser_action",
            payload={"action": action, "target": target},
            priority=3
        ))
        
    async def _publish_error(self, action: str, error: str):
        """Internal helper to publish failed actions."""
        await event_bus.publish(NovaEvent(
            source="browser",
            type="browser_error",
            payload={"action": action, "error": error},
            priority=6
        ))

    async def open_page(self, url: str) -> str:
        """Navigate to a URL and return the page title."""
        authorized = await biometric_auth.require_auth("open_page", "MEDIUM")
        if not authorized:
            await self._publish_error("open_page", "Authorization denied")
            return "Authorization Denied"
            
        try:
            await self.page.goto(url)
            title = await self.page.title()
            await self._publish_success("open_page", url)
            return title
        except Exception as e:
            await self._publish_error("open_page", str(e))
            return f"Error: {e}"

    async def read_page_text(self, url: str) -> str:
        """Open a page in headless mode and return all visible text."""
        # Risk: LOW -- no auth needed
        try:
            # Create a separate temporary page for background reading without disrupting primary page
            tmp_page = await self.context.new_page()
            await tmp_page.goto(url)
            text = await tmp_page.evaluate("document.body.innerText")
            await tmp_page.close()
            
            await self._publish_success("read_page_text", url)
            return text
        except Exception as e:
            await self._publish_error("read_page_text", str(e))
            return f"Error: {e}"

    async def click_element(self, selector: str) -> bool:
        """Click a CSS selector on the current page."""
        authorized = await biometric_auth.require_auth("click_element", "HIGH")
        if not authorized:
            await self._publish_error("click_element", "Authorization denied")
            return False
            
        try:
            await self.page.click(selector)
            await self._publish_success("click_element", selector)
            return True
        except Exception as e:
            await self._publish_error("click_element", str(e))
            return False

    async def type_text(self, selector: str, text: str) -> bool:
        """Type into a CSS selector."""
        authorized = await biometric_auth.require_auth("type_text", "HIGH")
        if not authorized:
            await self._publish_error("type_text", "Authorization denied")
            return False
            
        try:
            await self.page.fill(selector, text)
            await self._publish_success("type_text", selector)
            return True
        except Exception as e:
            await self._publish_error("type_text", str(e))
            return False

    async def submit_form(self, selector: str) -> bool:
        """Click a submit button."""
        authorized = await biometric_auth.require_auth("submit_form", "HIGH")
        if not authorized:
            await self._publish_error("submit_form", "Authorization denied")
            return False
            
        try:
            await self.page.click(selector)
            await self._publish_success("submit_form", selector)
            return True
        except Exception as e:
            await self._publish_error("submit_form", str(e))
            return False

    async def stop(self):
        """Close browser gracefully and publish closed event."""
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
            
        await event_bus.publish(NovaEvent(
            source="browser",
            type="browser_closed",
            payload={},
            priority=1
        ))

# Export singleton
browser = BrowserController()
