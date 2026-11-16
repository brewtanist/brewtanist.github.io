"""Verify OEM form reserves layout space with JS and retains a no-JS fallback.

Read-only, local Jekyll build only. No real request is sent to the OEM API.
"""
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading

from playwright.sync_api import expect, sync_playwright
from test_storefront import Page, require


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        return


def inspect(build: Path) -> None:
    for prefix in ("", "en/", "zh/"):
        file = build / prefix / "oem" / "index.html"
        require(file.is_file(), f"Missing OEM page: {file}")
        document = Page(file.read_text(encoding="utf-8"), str(file))
        forms = [node for node in document.select(tag="form") if node.attrs.get("id") == "oem-form"]
        require(len(forms) == 1, "Expected exactly one OEM form")
        require("hidden" not in forms[0].attrs,
                "OEM form must be present in the initial layout, not revealed after paint")
        noscript_styles = [node.text() for node in document.select(tag="style")
                           if node.parent and node.parent.tag == "noscript"]
        require(any("#oem-form" in css and "display: none" in css for css in noscript_styles),
                "Without JS the nonfunctional form must be hidden by a noscript stylesheet")
        print("PASS: initial OEM markup and no-JS style for " + (prefix or "th"))

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(build)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = "http://127.0.0.1:" + str(server.server_address[1])
    try:
        with sync_playwright() as p:
            for engine in ("chromium", "webkit"):
                browser = getattr(p, engine).launch()
                for prefix in ("", "en/", "zh/"):
                    url = origin + "/" + prefix + "oem/"
                    page = browser.new_page(viewport={"width": 390, "height": 844})
                    page.goto(url, wait_until="load")
                    expect(page.locator("#oem-form")).to_be_visible()
                    expect(page.locator("input[name='beanQuantity']")).to_be_visible()
                    require(page.locator("#oem-form").get_attribute("hidden") is None,
                            "Form was re-hidden during initialization")
                    page.close()
                ctx = browser.new_context(java_script_enabled=False, viewport={"width":390,"height":844})
                page = ctx.new_page()
                page.goto(origin + "/oem/", wait_until="load")
                expect(page.locator("#oem-form")).to_be_hidden()
                expect(page.locator(".oem-grid noscript").first).to_be_visible()
                ctx.close()
                browser.close()
                print("PASS: " + engine + " OEM form visible with JS, fallback visible without JS")
    finally:
        server.shutdown()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("build", type=Path)
    options = parser.parse_args()
    inspect(options.build.resolve())


if __name__ == "__main__":
    main()
