from playwright.sync_api import sync_playwright
import threading
import http.server
import socketserver
import os

PORT = 8002

def run_server():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    handler = http.server.SimpleHTTPRequestHandler
    httpd = socketserver.TCPServer(("", PORT), lambda *args, **kwargs: handler(*args, directory=repo_root, **kwargs))
    httpd.serve_forever()

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

def run_cuj(page):
    # Emulate prefers-reduced-motion: reduce
    page.emulate_media(reduced_motion="reduce")

    page.goto(f"http://localhost:{PORT}")
    page.wait_for_timeout(500)

    # Wait for the loader to appear/disappear and content to load
    page.wait_for_selector(".version-card", timeout=10000)
    page.wait_for_timeout(500)

    # Click the first version card to expand it (should not animate)
    page.locator(".version-card-header").first.click()
    page.wait_for_timeout(500)

    # Check if we can capture the expanded state
    page.screenshot(path="/home/jules/verification/screenshots/reduced_motion.png")
    page.wait_for_timeout(1000)

if __name__ == "__main__":
    os.makedirs("/home/jules/verification/screenshots", exist_ok=True)
    os.makedirs("/home/jules/verification/videos", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            record_video_dir="/home/jules/verification/videos"
        )
        page = context.new_page()
        try:
            run_cuj(page)
        finally:
            context.close()
            browser.close()
