"""Keep OEM quote references stable when delivery is uncertain.

All API requests are intercepted and answered by Playwright. Never connects to
the production OEM intake or sends fictional contact details to a live service.
"""
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
LOCALES = {"th": "/oem/", "en": "/en/oem/", "zh": "/zh/oem/"}


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        return


def inspect(build: Path) -> list[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(build)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = "http://127.0.0.1:" + str(server.server_address[1])
    checks = []
    cors = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "content-type",
    }

    def fill_form(page):
        page.locator('[name="beanQuantity"]').fill("3.5")
        page.locator('[name="name"]').fill("QA Example")
        page.locator('[name="email"]').fill("qa@example.invalid")
        page.locator("#oem-form button[type=submit]").click()
        reference = page.locator("#oem-ref").inner_text()
        assert reference.startswith("RFQ-") and reference in page.locator("#oem-summary").input_value()
        return reference

    try:
        with sync_playwright() as playwright:
            for engine in ("chromium", "webkit"):
                browser = getattr(playwright, engine).launch()
                for lang, path in LOCALES.items():
                    page = browser.new_page()
                    requests = []
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))

                    def conflict(route):
                        if route.request.method == "OPTIONS":
                            return route.fulfill(status=204, headers=cors)
                        assert route.request.method == "POST"
                        body = json.loads(route.request.post_data)
                        requests.append(body)
                        route.fulfill(status=409, headers=cors, content_type="application/json",
                                      body='{"ok":false,"error":"duplicate_reference"}')

                    page.route("**/api/requests", conflict)
                    page.goto(origin + path, wait_until="domcontentloaded")
                    reference = fill_form(page)
                    page.locator("#oem-submit").click()

                    text = json.loads((ROOT / "_data/oem_form" / (lang + ".json")).read_text(encoding="utf-8"))
                    expect(page.locator("#oem-status")).to_have_text(text["ref_conflict"])
                    expect(page.locator("#oem-ref")).to_have_text(reference)
                    expect(page.locator("#oem-submit")).to_be_hidden()
                    expect(page.locator("#oem-email")).to_be_visible()
                    assert reference in page.locator("#oem-email").get_attribute("href")
                    assert len(requests) == 1 and requests[0]["reference"] == reference

                    # A customer returning to edit without changing anything should
                    # not be offered another one-click submission for a 409.
                    page.locator("#oem-edit").click()
                    page.locator("#oem-form button[type=submit]").click()
                    expect(page.locator("#oem-ref")).to_have_text(reference)
                    expect(page.locator("#oem-submit")).to_be_hidden()
                    assert len(requests) == 1, "Unexpected duplicate network submission"
                    assert not errors, errors
                    page.close()
                    checks.append(engine + " " + lang + ": 409 preserves reference, no blind resubmission")

                # Recoverable rate limits must still allow a retry using the same
                # reference. The mocked second response is the server receipt.
                page = browser.new_page()
                attempts = []

                def rate_limit_then_success(route):
                    if route.request.method == "OPTIONS":
                        return route.fulfill(status=204, headers=cors)
                    body = json.loads(route.request.post_data)
                    attempts.append(body["reference"])
                    if len(attempts) == 1:
                        return route.fulfill(status=429, headers=cors)
                    route.fulfill(status=200, headers=cors, content_type="application/json",
                                  body=json.dumps({"ok": True, "reference": body["reference"]}))

                page.route("**/api/requests", rate_limit_then_success)
                page.goto(origin + "/oem/", wait_until="domcontentloaded")
                reference = fill_form(page)
                page.locator("#oem-submit").click()
                text = json.loads((ROOT / "_data/oem_form/th.json").read_text(encoding="utf-8"))
                expect(page.locator("#oem-status")).to_have_text(text["rate_limit"])
                expect(page.locator("#oem-submit")).to_be_visible()
                expect(page.locator("#oem-ref")).to_have_text(reference)
                page.locator("#oem-submit").click()
                expect(page.locator("#oem-next")).to_have_text(text["success"])
                assert attempts == [reference, reference], attempts
                expect(page.locator("#oem-submit")).to_be_hidden()
                page.close()
                checks.append(engine + ": rate limit retry keeps original reference and confirms one receipt")
                browser.close()
    finally:
        server.shutdown()
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path)
    args = parser.parse_args()
    for check in inspect(args.build.resolve()):
        print("PASS: " + check, flush=True)


if __name__ == "__main__":
    main()
