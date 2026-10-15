"""Optional headed-browser assistant, using the public upload UI only."""

import re
import uuid
from datetime import datetime, timezone

from .core import asset_path, load, now, save

LENS_URL = "https://www.google.com/?hl=en"


def run_lens(case, asset=None):
    """Caller must explicitly opt into sending the selected image to Google."""
    try:
        from playwright.sync_api import TimeoutError as BrowserTimeout
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ValueError('Install browser support: pip install -e ".[browser]"; playwright install chromium') from exc

    data = load(case)
    relative = asset or data["source"]["asset"]
    if relative not in [data["source"]["asset"]] + [c["native"] for c in data["crops"]]:
        raise ValueError("Select the prepared source or a native crop from case.json.")
    photo = asset_path(case, relative)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    screenshot = f"assets/lens-{stamp}.png"
    record = {"provider": "Google Lens", "asset": relative, "reviewed_at": now(),
              "status": "unreviewed", "url": LENS_URL, "links": [], "screenshot": screenshot}

    with sync_playwright() as pw:
        # A disposable context avoids using or publishing the user's normal profile.
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(locale="en-US", viewport={"width": 1280, "height": 900})
        page = context.new_page()
        try:
            page.goto(LENS_URL, wait_until="domcontentloaded")
            try:
                page.get_by_role("button", name="Search by image", exact=True).click(timeout=15000)
                with page.expect_file_chooser(timeout=10000) as chooser:
                    page.get_by_role("button", name=re.compile("upload a file", re.I)).click()
                chooser.value.set_files(str(photo))
                page.wait_for_url(re.compile(r"https://(www\.)?google\.com/search.*|https://lens\.google\.com/.*"), timeout=45000)
            except BrowserTimeout:
                print("Google's UI did not reach results. Complete consent/login/upload in the visible browser if needed.")
            print("Inspect visual matches. If blocked by a CAPTCHA, solve it yourself or stop. No bypass is attempted.")
            input("Press Enter only after results are visible (Ctrl-C to stop): ")
            # Capture visible links, not an undocumented search endpoint or hidden app state.
            links = page.locator("a[href]").evaluate_all("""elements => elements
                .filter(a => a.getBoundingClientRect().width > 0 && a.getBoundingClientRect().height > 0)
                .map(a => ({title: a.innerText.trim(), url: a.href}))
                .filter(a => a.title && /^https?:/.test(a.url)).slice(0, 150)""")
            record["links"] = list({x["url"]: x for x in links}.values())
            record["status"] = "captured_unverified"
        except (KeyboardInterrupt, EOFError):
            record["status"] = "interrupted"
        finally:
            try:
                record["url"] = page.url
                page.screenshot(path=str(asset_path(case, screenshot)), full_page=False)
            finally:
                save_data = load(case)
                save_data["searches"].append(record)
                save(case, save_data)
                context.close()
                browser.close()
    return record
