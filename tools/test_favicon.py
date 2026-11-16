"""Check public Brewtanist favicon and avoid missing /favicon.ico browser requests.

Uses a local Jekyll build; never visits external sites or sends customer data.
"""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import argparse
import threading
import xml.etree.ElementTree as ET
from test_storefront import Page, require

ROUTES = [
    "/", "/shop/", "/oem/",
    "/en/", "/en/shop/", "/en/oem/",
    "/zh/", "/zh/shop/", "/zh/oem/",
]


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args): pass


def inspect(build):
    # Some browser engines request /favicon.ico even with an SVG icon link.
    # The binary ICO fallback is intentionally served at the root, not via a fake SVG extension.
    ico = build / "favicon.ico"
    require(ico.is_file(), "Missing /favicon.ico fallback")
    data = ico.read_bytes()
    require(len(data) >= 22 and data[:4] == b"\x00\x00\x01\x00",
            "Root favicon.ico is not a valid icon file")
    require(int.from_bytes(data[4:6], "little") >= 1, "ICO must contain at least one image")
    icon = build / "favicon.svg"
    require(icon.is_file(), "Missing local /favicon.svg")
    root = ET.parse(icon).getroot()
    require(root.tag == "{http://www.w3.org/2000/svg}svg", "Favicon must be valid SVG")
    require(root.attrib.get("viewBox") == "0 0 64 64", "Unexpected favicon canvas")
    for route in ROUTES:
        path = build / route.lstrip("/") / "index.html"
        if route == "/": path = build / "index.html"
        require(path.is_file(), "Missing localized page " + route)
        page = Page(path.read_text(encoding="utf-8"), route)
        links = [x for x in page.select(tag="link") if x.attrs.get("rel") == "icon"]
        require(len(links) == 1, route + ": exactly one site icon required")
        require(links[0].attrs.get("type") == "image/svg+xml", route + ": incorrect icon format")
        require(links[0].attrs.get("href") == "/favicon.svg", route + ": incorrect icon path")
    print("PASS: valid SVG + genuine ICO fallback and nine public routes", flush=True)


def browser_inspect(build):
    from playwright.sync_api import sync_playwright
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(build)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = "http://127.0.0.1:" + str(server.server_address[1])
    try:
        with sync_playwright() as p:
            for engine in ("chromium", "webkit"):
                browser = getattr(p, engine).launch()
                for route in ROUTES:
                    page = browser.new_page()
                    failures = []
                    icon_status = []
                    page.on("response", lambda response: icon_status.append(response.status) if
                            response.url.split("?")[0].endswith("/favicon.svg") else None)
                    page.on("response", lambda response: failures.append((response.url, response.status))
                            if response.url.endswith("/favicon.ico") and response.status >= 400 else None)
                    response = page.goto(origin + route, wait_until="load")
                    require(response.status == 200, engine + ": page failed " + route)
                    page.wait_for_timeout(100)
                    require(not failures, engine + " " + route + ": default favicon 404 " + str(failures))
                    # Some browser engines do not fetch tab icons in headless mode.
                    require(all(status == 200 for status in icon_status), engine + ": SVG icon request failed")
                    page.close()
                browser.close()
                print("PASS: " + engine + " site icon loads without default favicon errors", flush=True)
    finally:
        server.shutdown()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("build", type=Path)
    parser.add_argument("--browser", action="store_true")
    opts = parser.parse_args()
    inspect(opts.build.resolve())
    if opts.browser:
        browser_inspect(opts.build.resolve())


if __name__ == "__main__":
    main()
