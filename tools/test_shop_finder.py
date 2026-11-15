"""Browser checks for the built-in, multilingual Brewtanist Coffee Finder.

Runs only against a local Jekyll build. Never submits real orders or RFQs.
"""
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

from playwright.sync_api import expect, sync_playwright

PATHS = {"th": "/shop/", "en": "/en/shop/", "zh": "/zh/shop/"}


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        return


def check(build: Path) -> dict:
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(build)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = "http://127.0.0.1:" + str(server.server_address[1])
    checks = []
    errors = []
    unsafe_requests = []
    try:
        with sync_playwright() as playwright:
            for engine in ("chromium", "webkit"):
                browser = getattr(playwright, engine).launch()
                page = browser.new_page(viewport={"width": 390, "height": 900})
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("request", lambda request: unsafe_requests.append(request.url) if request.method not in ("GET", "HEAD") else None)
                for lang, route in PATHS.items():
                    page.goto(origin + route, wait_until="domcontentloaded")
                    form = page.locator("[data-finder-form]")
                    result = page.locator("[data-finder-result]")
                    expect(form).to_be_visible()
                    expect(page.locator("[data-finder-static]")).to_be_hidden()
                    finder_data = page.evaluate("JSON.parse(document.getElementById('coffee-finder-products').textContent)")
                    assert len(finder_data) == 3, (lang, finder_data)
                    assert {item["id"] for item in finder_data} == {"plantman", "ozmo", "lazybug"}

                    def choose(format_value, taste=None, drink=None):
                        page.locator('[data-finder-form] [name="format"][value="' + format_value + '"]').check()
                        if taste is not None:
                            page.locator('[data-finder-form] [name="taste"][value="' + taste + '"]').check()
                        if drink is not None:
                            page.locator('[data-finder-form] [name="drink"][value="' + drink + '"]').check()
                        form.locator("button[type=submit]").click()
                        expect(result).to_be_visible()

                    def reset():
                        page.locator("[data-finder-restart]").click()
                        expect(form).to_be_visible()
                        expect(result).to_be_hidden()

                    choose("beans", "chocolate", "milk")
                    expect(result.locator(".finder-match h4").first).to_have_text("Mr. Plantman")
                    assert result.locator(".finder-result-link[href^='https://shopee.co.th/']").count() > 0
                    for width in (320, 390, 768, 1440):
                        page.set_viewport_size({"width": width, "height": 900})
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (engine, lang, width)
                    if engine == "chromium" and lang == "th":
                        page.screenshot(path=str(build.parent / "qa" / "finder-mobile.png"), full_page=True)
                    reset()
                    choose("beans", "fruity", "black")
                    expect(result.locator(".finder-match h4").first).to_have_text("Ms. Lazybug")
                    reset()
                    choose("beans", "sweet", "milk")
                    expect(result.locator(".finder-match h4").first).to_have_text("Mr. Ozmo")
                    reset()
                    choose("beans", "unsure", "unsure")
                    expect(result.locator(".finder-match")).to_have_count(3)
                    reset()
                    choose("capsules")
                    expect(result.locator(".finder-match")).to_have_count(0)
                    capsule_link = result.locator('a[href*="category=capsules"]')
                    expect(capsule_link).to_have_count(1)
                    capsule_link.click()
                    expect(page.locator('[data-filter="capsules"]')).to_have_attribute("aria-pressed", "true")
                    assert page.locator('[data-shop-card]:visible').count() == 3
                    page.goto(origin + route)
                    choose("drip")
                    expect(result.locator('a[href*="category=drip"]')).to_have_count(1)
                    checks.append(engine + ": " + lang + " beans, capsules, drip, uncertain answers and layouts")

                page.goto(origin + "/shop/#coffee-finder")
                switcher = page.locator("[data-language-menu]")
                switcher.locator("summary").click()
                switcher.locator('a[hreflang="en"]').click()
                assert page.url.endswith("/en/shop/#coffee-finder"), page.url
                checks.append(engine + ": language switch preserves Coffee Finder section")
                context = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 900})
                nojs = context.new_page()
                nojs.goto(origin + "/shop/#coffee-finder")
                expect(nojs.locator("[data-finder-static]")).to_be_visible()
                expect(nojs.locator("[data-finder-form]")).to_be_hidden()
                assert nojs.locator('[data-finder-static] a[href*="category=house"]').count() == 1
                context.close()
                checks.append(engine + ": usable category links without JavaScript")
                browser.close()
        assert not errors, errors
        assert not unsafe_requests, unsafe_requests
        checks.append("No browser errors or non-GET requests")
        return {"result": "PASS", "checks": checks, "languages": list(PATHS), "engines": ["chromium", "webkit"]}
    finally:
        server.shutdown()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("build", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    build = args.build.resolve()
    (build.parent / "qa").mkdir(exist_ok=True)
    try:
        report = check(build)
    except Exception as error:
        report = {"result": "FAIL", "error": type(error).__name__ + ": " + str(error)}
        raise
    finally:
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(locals().get("report", {"result":"FAIL"}), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
