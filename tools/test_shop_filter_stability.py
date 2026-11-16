"""Ensure the existing Shop filters stay on one stable desktop row.

The filter group can scroll horizontally at narrower desktop widths.
On mobile it keeps the existing wrapped chip layout. Real rendered pages
are checked with Chromium and WebKit, without any external requests.
"""
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading

from playwright.sync_api import expect, sync_playwright


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        return


def check(build: Path) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(build)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = "http://127.0.0.1:" + str(server.server_address[1])
    try:
        with sync_playwright() as p:
            for engine in ("chromium", "webkit"):
                browser = getattr(p, engine).launch()
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                for language in ("", "en/", "zh/"):
                    route = "/" + language + "shop/"
                    for width in (390, 1024, 1440):
                        page.set_viewport_size({"width": width, "height": 900})
                        response = page.goto(origin + route, wait_until="load")
                        assert response.status == 200
                        filters = page.locator(".shop-filters")
                        expect(filters).to_be_visible()
                        chips = filters.locator(".shop-filter")
                        expect(chips).to_have_count(7)
                        mode = filters.evaluate("(node) => getComputedStyle(node).flexWrap")
                        if width >= 801:
                            assert mode == "nowrap", (engine, language, width, mode)
                            tops = chips.evaluate_all(
                                "nodes => nodes.map(n => Math.round(n.getBoundingClientRect().top))"
                            )
                            assert len(set(tops)) == 1, (engine, language, width, tops)
                            last = chips.last
                            last.focus()
                            assert last.evaluate("n => n === document.activeElement")
                            assert last.evaluate(
                                "n => n.getBoundingClientRect().right <= n.parentElement.getBoundingClientRect().right + 2"
                            ), "Last filter must remain keyboard reachable inside its strip"
                        else:
                            assert mode == "wrap", (engine, language, width, mode)
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (
                            engine, language, width, "page overflow"
                        )
                    page.set_viewport_size({"width": 390, "height": 900})
                    page.goto(origin + route, wait_until="load")
                    page.locator('[data-filter="capsules"]').click()
                    expect(page.locator('[data-shop-card]:visible')).to_have_count(3)
                browser.close()
                print("PASS: " + engine + " filters stable across all three languages and screen widths")
    finally:
        server.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("build", type=Path)
    arguments = parser.parse_args()
    check(arguments.build.resolve())


if __name__ == "__main__":
    main()
