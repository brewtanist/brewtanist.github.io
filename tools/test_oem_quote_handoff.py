"""Offline browser test: accepted RFQ -> downloaded JSON -> local quotation.

Playwright intercepts every /api/requests call and returns a synthetic receipt.
It NEVER sends leads or credentials to the production OEM intake, and it
does not test the authenticated private Staff Inbox or backend persistence.
"""
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

from playwright.sync_api import expect, sync_playwright


LOCALES = {
    "th": ("/oem/", "/admin/quotes/"),
    "en": ("/en/oem/", "/en/admin/quotes/"),
    "zh": ("/zh/oem/", "/zh/admin/quotes/"),
}


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        return


def inspect(build: Path) -> list[str]:
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(Quiet, directory=str(build))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = "http://127.0.0.1:" + str(server.server_address[1])
    results: list[str] = []
    cors = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "content-type",
    }
    try:
        with sync_playwright() as playwright:
            for engine in ("chromium", "webkit"):
                browser = getattr(playwright, engine).launch()
                try:
                    for language, (form_path, desk_path) in LOCALES.items():
                        customer = browser.new_page(accept_downloads=True)
                        errors: list[str] = []
                        requests: list[dict] = []
                        customer.on("pageerror", lambda error: errors.append(str(error)))

                        def mock_intake(route):
                            if route.request.method == "OPTIONS":
                                return route.fulfill(status=204, headers=cors)
                            assert route.request.method == "POST"
                            rfq = json.loads(route.request.post_data)
                            requests.append(rfq)
                            route.fulfill(
                                status=200,
                                content_type="application/json",
                                headers=cors,
                                body=json.dumps({"ok": True, "reference": rfq["reference"]}),
                            )

                        customer.route("**/api/requests", mock_intake)
                        customer.goto(origin + form_path, wait_until="domcontentloaded")
                        customer.locator('input[name="productType"][value="both"]').check()
                        customer.locator('[name="beanQuantity"]').fill("2.5")
                        customer.locator('[name="packGrams"]').fill("250")
                        customer.locator('[name="capsuleQuantity"]').fill("120")
                        customer.locator('[name="perBox"]').fill("10")
                        customer.locator('[name="system"]').fill("Nespresso Original")
                        customer.locator('[name="name"]').fill("QA Example")
                        customer.locator('[name="company"]').fill("Test Only Co")
                        customer.locator('[name="email"]').fill("qa@example.invalid")
                        customer.locator("#oem-form button[type=submit]").click()
                        reference = customer.locator("#oem-ref").inner_text()
                        customer.locator("#oem-submit").click()
                        expect(customer.locator("#oem-submit")).to_be_hidden()
                        assert len(requests) == 1
                        assert requests[0]["reference"] == reference
                        with customer.expect_download() as download_info:
                            customer.locator("#oem-download").click()
                        download = download_info.value
                        assert download.suggested_filename == reference + ".json"
                        rfq = json.loads(Path(download.path()).read_text(encoding="utf-8"))
                        assert rfq["reference"] == reference
                        assert rfq["language"] == language
                        assert rfq["contact"]["email"] == "qa@example.invalid"
                        assert rfq["products"]["beans"]["quantityKg"] == 2.5
                        assert rfq["products"]["capsules"]["quantityUnits"] == 120

                        # Public Quote Desk imports a downloaded RFQ locally.
                        # Private Staff Inbox must be tested separately by the owner.
                        desk = browser.new_page(accept_downloads=True)
                        desk.on("pageerror", lambda error: errors.append(str(error)))
                        desk.goto(origin + desk_path, wait_until="domcontentloaded")
                        expect(desk.locator("#quote-app")).to_be_visible()
                        desk.locator("#file").set_input_files({
                            "name": "rfq.json",
                            "mimeType": "application/json",
                            "buffer": json.dumps(rfq, ensure_ascii=False).encode("utf-8"),
                        })
                        expect(desk.locator('input[name="rfq"]')).to_have_value(reference)
                        expect(desk.locator('input[name="name"]')).to_have_value("QA Example")
                        expect(desk.locator("#lines .quote-line")).to_have_count(2)
                        first = desk.locator("#lines .quote-line").nth(0)
                        second = desk.locator("#lines .quote-line").nth(1)
                        expect(first.locator('input[type="number"]').first).to_have_value("2.5")
                        expect(second.locator('input[type="number"]').first).to_have_value("120")
                        first.locator('input[type="number"]').nth(1).fill("100")
                        second.locator('input[type="number"]').nth(1).fill("2")
                        expect(desk.locator("#totals")).to_contain_text("490.00")
                        with desk.expect_download() as offer_info:
                            desk.locator("#save").click()
                        offer = json.loads(Path(offer_info.value.path()).read_text(encoding="utf-8"))
                        assert offer["kind"] == "brewtanist-oem-quote"
                        assert offer["current"]["rfq"] == reference
                        assert offer["current"]["lines"][0]["price"] == "100"
                        assert offer["current"]["lines"][1]["price"] == "2"
                        desk.locator("#new-revision").click()
                        expect(desk.locator("#history li")).to_have_count(1)
                        expect(desk.locator('input[name="revision"]')).to_have_value("2")
                        assert not errors, errors
                        desk.close()
                        customer.close()
                        results.append(
                            engine + " " + language
                            + ": accepted RFQ, file import, quote totals, save and revision"
                        )
                finally:
                    browser.close()
    finally:
        server.shutdown()
        server.server_close()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path)
    args = parser.parse_args()
    for result in inspect(args.build.resolve()):
        print("PASS: " + result, flush=True)


if __name__ == "__main__":
    main()
