"""Screenshot the React board for each ticket with Playwright.

Needs the backend (port 8000) and dashboard (port 5173) running.
Run from the hw5 folder:
    .venv\\Scripts\\python tools\\capture_board.py
Saves output/screenshots/ticket_<id>.png.
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

BOARD = "http://localhost:5173"
OUT = Path(__file__).resolve().parent.parent / "output" / "screenshots"
TICKETS = (101, 102, 103)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        page.goto(BOARD)
        page.wait_for_selector(".status-light.up")
        page.wait_for_selector(".ticket-card")
        for tid in TICKETS:
            page.locator(".ticket-card", has_text=f"#{tid}").click()
            page.wait_for_selector(".event")              # this ticket's run has loaded
            page.wait_for_timeout(2500)                     # let polling, stamp and map settle
            page.eval_on_selector(".feed", "el => el.scrollTop = el.scrollHeight")
            page.wait_for_timeout(400)
            status = page.locator(".ticket-card.selected .status-pill").inner_text()
            path = OUT / f"ticket_{tid}.png"
            page.screenshot(path=str(path), full_page=True)
            print(f"ticket {tid}: board status '{status}' -> {path.name}")
        browser.close()


if __name__ == "__main__":
    main()
