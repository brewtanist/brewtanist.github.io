"""Verify the responsive hero preload uses the SAME source as its <picture>.

Runs on a local Jekyll build. With --browser, checks actual image requests
in Chromium/WebKit to catch double downloads or missing fallback images.
No public website, analytics, OEM, or Shopee requests are made.
"""
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import threading
from urllib.parse import urlsplit

from test_storefront import Page, require

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ("", "/en", "/zh")
HEROES = (
    ("/", "hero-visual", "brewtanist-storefront-cover"),
    ("/shop/", "shop-hero-photo", "brewtanist-products"),
)
ITEM = re.compile(r"(/brewtanist/assets/photos/[^\s,]+\.avif)\s+(\d+)w")


def candidates(value: str):
    parts = [item.strip() for item in value.split(",")]
    parsed = []
    for part in parts:
        match = ITEM.fullmatch(part)
        require(bool(match), "Invalid responsive AVIF preload or source: " + part)
        parsed.append((match[1], int(match[2])))
    require(len(parsed) == len(set(parsed)), "Duplicate responsive image source")
    return parsed


def static_check(build: Path):
    checks = []
    for prefix in LOCALES:
        for suffix, class_name, basename in HEROES:
            route = prefix + suffix
            file = build / route.lstrip("/") / "index.html"
            if route == "/":
                file = build / "index.html"
            require(file.is_file(), "Missing rendered route: " + route)
            page = Page(file.read_text(encoding="utf-8"), route)
            preloads = [
                node for node in page.select(tag="link")
                if node.attrs.get("rel") == "preload" and node.attrs.get("as") == "image"
            ]
            require(len(preloads) == 1, route + ": expected ONE responsive hero preload")
            link = preloads[0]
            require(link.attrs.get("type") == "image/avif", route + ": preload must use AVIF")
            require(link.attrs.get("fetchpriority") == "high", route + ": not high priority")
            require("href" not in link.attrs, route + ": fallback href may download an extra JPEG")
            figure = page.select(class_name=class_name)
            require(len(figure) == 1, route + ": missing hero figure")
            pictures = figure[0].select(tag="picture")
            require(len(pictures) == 1, route + ": missing responsive picture")
            images = pictures[0].select(tag="img")
            sources = pictures[0].select(tag="source")
            require(len(images) == 1 and len(sources) == 1, route + ": malformed picture")
            img, source = images[0], sources[0]
            require(img.attrs.get("fetchpriority") == "high" and "loading" not in img.attrs,
                    route + ": hero must be loaded eagerly at high priority")
            require(source.attrs.get("type") == "image/avif", route + ": source is not AVIF")
            a = candidates(link.attrs.get("imagesrcset", ""))
            b = candidates(source.attrs.get("srcset", ""))
            require(a == b, route + ": preload differs from the actual picture candidates")
            require(link.attrs.get("imagesizes") == source.attrs.get("sizes"),
                    route + ": preload and picture have different responsive sizes")
            require(all(basename in path for path, _ in a),
                    route + ": preload references unrelated assets")
            for path, width in a:
                require(width > 0 and (build / path.lstrip("/")).is_file(),
                        route + ": missing preloaded AVIF " + path)
            checks.append(route + ": consistent hero preload and picture with " + str(len(a)) + " AVIF sizes")

    for prefix in LOCALES:
        route = prefix + "/oem/"
        page = Page((build / route.lstrip("/") / "index.html").read_text(encoding="utf-8"), route)
        preloads = [node for node in page.select(tag="link")
                    if node.attrs.get("rel") == "preload" and node.attrs.get("as") == "image"]
        require(not preloads, route + ": don't preload the optional OEM hero image")
    checks.append("No unnecessary hero image preload on OEM pages")
    return checks


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        return


def browser_check(build: Path):
    from playwright.sync_api import sync_playwright

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(build)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = "http://127.0.0.1:" + str(server.server_address[1])
    checks = []
    try:
        with sync_playwright() as playwright:
            for engine, sizes in (("chromium", (390, 1440)), ("webkit", (390,))):
                browser = getattr(playwright, engine).launch()
                for width in sizes:
                    page = browser.new_page(viewport={"width":width,"height":850})
                    for prefix in LOCALES:
                        for suffix, class_name, basename in HEROES:
                            route = prefix + suffix
                            images_requested = []
                            handler = lambda request: images_requested.append(urlsplit(request.url).path) if request.resource_type == "image" else None
                            page.on("request", handler)
                            response = page.goto(origin + route, wait_until="load")
                            require(response.status == 200, "Unable to load " + route)
                            figure = page.locator("." + class_name + " picture img")
                            src = urlsplit(figure.evaluate("(img) => img.currentSrc")).path
                            require(src.startswith("/brewtanist/assets/photos/") and basename in src,
                                    engine + " " + route + ": browser selected unexpected hero: " + src)
                            require(images_requested.count(src) == 1,
                                    engine + " " + route + ": hero should be requested exactly once; " + repr(images_requested))
                            duplicates = [path for path in images_requested
                                          if basename in path and path != src]
                            require(not duplicates, engine + " " + route + ": redundant hero downloads: " + repr(duplicates))
                            page.remove_listener("request", handler)
                    checks.append(engine + " " + str(width) + "px: six pages load one responsive hero each")
                    page.close()
                browser.close()
    finally:
        server.shutdown()
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path)
    parser.add_argument("--browser", action="store_true")
    args = parser.parse_args()
    build = args.build.resolve()
    checks = static_check(build)
    if args.browser:
        checks += browser_check(build)
    for check in checks:
        print("PASS: " + check)
    print("PASS: " + str(len(checks)) + " image preload checks")


if __name__ == "__main__":
    main()
