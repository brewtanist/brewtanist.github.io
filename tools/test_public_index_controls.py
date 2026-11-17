"""Guard the public site's robots/noindex contract in a rendered Jekyll build.

The site intentionally exposes static editing guides and a browser-local quote
desk, but asks compliant search engines not to index them. Google must be able
to crawl those PUBLIC pages to read their noindex meta tags. This script never
authenticates, contacts the private Staff Inbox or submits an OEM request.
"""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET


ORIGIN = "https://brewtanist.github.io"
CUSTOMER_ROUTES = (
    "/", "/shop/", "/oem/",
    "/en/", "/en/shop/", "/en/oem/",
    "/zh/", "/zh/shop/", "/zh/oem/",
)
NOINDEX_ROUTES = (
    "/admin/", "/admin/quotes/",
    "/en/admin/", "/en/admin/quotes/",
    "/zh/admin/", "/zh/admin/quotes/",
    "/brewtanist/admin/",
)
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


class RobotsMeta(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rules: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "meta":
            return
        values = dict(attrs)
        if (values.get("name") or "").strip().lower() in {"robots", "googlebot"}:
            self.rules.extend(
                item.strip().lower()
                for item in (values.get("content") or "").replace(";", ",").split(",")
                if item.strip()
            )


def check(output: Path) -> None:
    robots_path = output / "robots.txt"
    assert robots_path.is_file(), "Missing published robots.txt"
    robots_text = robots_path.read_text(encoding="utf-8")
    policy = RobotFileParser()
    policy.parse(robots_text.splitlines())

    for route in CUSTOMER_ROUTES + NOINDEX_ROUTES:
        assert policy.can_fetch("Googlebot", ORIGIN + route), (
            "robots.txt blocks Googlebot from reading HTML meta on " + route
        )
        page = output / route.lstrip("/") / "index.html"
        assert page.is_file(), f"Missing built HTML: {route}"
        meta = RobotsMeta()
        meta.feed(page.read_text(encoding="utf-8"))
        if route in NOINDEX_ROUTES:
            assert "noindex" in meta.rules, f"Missing noindex meta: {route}"
        else:
            assert "noindex" not in meta.rules, f"Customer page erroneously noindex: {route}"

    sitemap_path = output / "sitemap.xml"
    assert sitemap_path.is_file(), "Missing published sitemap"
    doc = ET.parse(sitemap_path)
    urls = [
        item.findtext(SITEMAP_NS + "loc")
        for item in doc.findall(SITEMAP_NS + "url")
    ]
    expected = {ORIGIN + route for route in CUSTOMER_ROUTES}
    assert len(urls) == len(expected) and set(urls) == expected, (
        "Sitemap must list only the nine indexable localized pages"
    )
    assert "Sitemap: " + ORIGIN + "/sitemap.xml" in robots_text, (
        "robots.txt must reference the correct public sitemap"
    )

    print(
        f"PASS: {len(CUSTOMER_ROUTES)} public customer pages indexable; "
        f"{len(NOINDEX_ROUTES)} crawler-readable admin/quote pages noindex; "
        "sitemap contains only indexable routes."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path)
    args = parser.parse_args()
    check(args.build)


if __name__ == "__main__":
    main()
