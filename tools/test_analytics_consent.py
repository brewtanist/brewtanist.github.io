"""Verify basic-consent analytics against a local Jekyll build without external writes."""
from __future__ import annotations
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from playwright.sync_api import expect, sync_playwright

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        return

def run(build: Path, enabled: bool):
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(build)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = "http://127.0.0.1:" + str(server.server_address[1])
    checks = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            if not enabled:
                page = browser.new_page()
                external = []
                page.on("request", lambda r: external.append(r.url) if "googletagmanager.com" in r.url or "google-analytics.com" in r.url else None)
                for route in ("/", "/en/shop/", "/zh/oem/"):
                    page.goto(origin + route, wait_until="load")
                    assert page.evaluate("window.BrewtanistAnalytics?.track('generate_lead')") is False
                    assert page.locator(".brew-analytics-banner").count() == 0
                    assert page.locator("script[src*='googletagmanager.com']").count() == 0
                assert not external, external
                checks.append("Disabled config: no consent prompt, Google tag, or analytics requests")
                browser.close()
                return {"result": "PASS", "checks": checks}

            for route, expected_label in [
                ("/", "การวัดผลการใช้งานเว็บไซต์"),
                ("/en/shop/", "Website analytics consent"),
                ("/zh/oem/", "网站统计同意设置"),
            ]:
                context = browser.new_context()
                page = context.new_page()
                external = []
                page.on("request", lambda q: external.append(q.url) if "googletagmanager.com" in q.url else None)
                page.goto(origin + route, wait_until="load")
                banner = page.locator(".brew-analytics-banner")
                expect(banner).to_be_visible()
                expect(banner).to_have_attribute("aria-label", expected_label)
                assert not external
                assert page.evaluate("window.BrewtanistAnalytics.track('generate_lead')") is False
                banner.locator("button").first.click()
                expect(banner).to_be_hidden()
                assert not external
                context.close()
            checks.append("Three languages: consent prompt, reject, and zero pre-consent tag requests")

            context = browser.new_context(viewport={"width": 390, "height": 860})
            page = context.new_page()
            external = []
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("request", lambda q: external.append(q.url) if "googletagmanager.com" in q.url else None)
            page.route("https://www.googletagmanager.com/**", lambda route: route.fulfill(status=200, content_type="text/javascript", body=""))
            page.goto(origin + "/shop/?q=qa@example.invalid", wait_until="load")
            assert not external
            page.locator(".brew-analytics-banner button").first.click()
            page.locator(".brew-analytics-manage").click()
            page.locator(".brew-analytics-accept").click()
            assert page.evaluate("window.BrewtanistAnalytics.track('contact_click',{method:'phone'})") is True
            page.wait_for_function("window.dataLayer && window.dataLayer.length >= 6")
            assert len(external) == 1, external
            assert page.locator("script[src^='https://www.googletagmanager.com/gtag/js?id=']").count() == 1

            page.evaluate("""() => {
                document.querySelector('.shop-buy').addEventListener('click', e => e.preventDefault(), {once:true});
                document.querySelector('.shop-buy').dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));
            }""")
            page.locator('[data-finder-form] [name="format"][value="beans"]').check()
            page.locator('[data-finder-form] [name="taste"][value="fruity"]').check()
            page.locator('[data-finder-form] [name="drink"][value="black"]').check()
            page.locator('[data-finder-form] button[type=submit]').click()
            events = page.evaluate("""() => Array.from(window.dataLayer).map(a => Array.from(a)).filter(a=>a[0]==='event')""")
            names = [event[1] for event in events]
            assert "page_view" in names and "shop_outbound" in names and "finder_complete" in names, names
            view = next(e[2] for e in events if e[1] == "page_view")
            assert view["page_location"] == origin + "/shop/" and "@" not in view["page_location"], view
            shop = next(e[2] for e in events if e[1] == "shop_outbound")
            assert shop.get("item_id","").isdigit(), shop
            coffee = next(e[2] for e in events if e[1] == "finder_complete")
            assert coffee == {"coffee_type": "beans"}, coffee
            checks.append("Consent: only after opt-in, safe page URL and safe Shop/Finder event parameters")

            def fake_oem(route):
                headers = {"Access-Control-Allow-Origin": "*",
                           "Access-Control-Allow-Methods": "POST, OPTIONS",
                           "Access-Control-Allow-Headers": "content-type"}
                if route.request.method == "OPTIONS":
                    route.fulfill(status=204, headers=headers)
                    return
                body = json.loads(route.request.post_data)
                assert body["contact"]["email"] == "qa@example.invalid"
                route.fulfill(status=200, headers=headers, content_type="application/json",
                              body=json.dumps({"ok": True, "reference": body["reference"]}))
            page.route("**/api/requests", fake_oem)
            page.goto(origin + "/oem/", wait_until="load")
            page.locator('[name="beanQuantity"]').fill("2.5")
            page.locator('[name="name"]').fill("QA Test")
            page.locator('[name="email"]').fill("qa@example.invalid")
            page.locator("#oem-form button[type=submit]").click()
            page.locator("#oem-submit").click()
            expect(page.locator("#oem-next")).to_contain_text("โรงคั่วจะติดต่อกลับ")
            events = page.evaluate("""() => Array.from(window.dataLayer).map(a=>Array.from(a)).filter(a=>a[0]==='event'&&a[1]==='generate_lead')""")
            assert len(events) == 1 and events[0][2] == {"lead_source":"oem_form"}, events
            sent = json.dumps(page.evaluate("Array.from(window.dataLayer).map(a=>Array.from(a)).filter(a=>a[0]===\'event\')"), ensure_ascii=False)
            assert "QA Test" not in sent and "qa@example.invalid" not in sent and "2.5" not in sent
            checks.append("Fake OEM receipt: one generate_lead event, no form values in analytics payload")

            before = len(external)
            page.locator(".brew-analytics-manage").click()
            page.locator(".brew-analytics-banner button").first.click()
            page.wait_for_load_state("load")
            assert page.evaluate("window.BrewtanistAnalytics.track('generate_lead')") is False
            assert page.locator("script[src*='googletagmanager.com']").count() == 0
            assert len(external) == before, external
            assert not errors, errors
            checks.append("Revocation reloads without a Google tag; no browser errors")
            context.close()
            browser.close()
        return {"result": "PASS", "checks": checks}
    finally:
        server.shutdown()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("build", type=Path)
    parser.add_argument("--enabled", action="store_true")
    args = parser.parse_args()
    report = run(args.build.resolve(), args.enabled)
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
