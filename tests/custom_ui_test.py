import unittest
from playwright.sync_api import sync_playwright

class TestCustomUI(unittest.TestCase):
    def test_expand_collapse_latest_section(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Route intercept to block external fonts for speed/stability
            def route_intercept(route):
                if route.request.resource_type in ["font", "image"]:
                    route.abort()
                elif "fonts.googleapis.com" in route.request.url or "fonts.gstatic.com" in route.request.url:
                    route.abort()
                else:
                    route.continue_()

            page.route("**/*", route_intercept)

            page.goto('http://127.0.0.1:8000')

            # Wait for `#latest-version` text to change from '-' indicating load completion
            page.wait_for_function('document.getElementById("latest-version").textContent !== "-"', timeout=10000)

            # Wait for the first version card
            first_card = page.locator('.version-card-header').first
            first_card.wait_for(state="visible", timeout=10000)

            # Verify latest section is initially visible
            latest_section = page.locator('#latest-section')
            self.assertTrue(latest_section.is_visible())

            # Click to expand
            first_card.click()

            # Verify latest section is hidden
            self.assertFalse(latest_section.is_visible())

            # Click to collapse
            first_card.click()

            # Verify latest section is visible again
            self.assertTrue(latest_section.is_visible())

            browser.close()

if __name__ == '__main__':
    unittest.main()
