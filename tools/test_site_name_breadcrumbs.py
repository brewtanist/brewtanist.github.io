"""Validate site-name and localized breadcrumb schema against a built Jekyll site.

Reads rendered static HTML only: no network access or authenticated services.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from test_storefront import Page, require

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://brewtanist.github.io"
LOCALES = {"th": "", "en": "/en", "zh": "/zh"}


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def inspect(build: Path) -> dict:
    settings = read(ROOT / "_data/brewtanist/settings.json")
    checks = []

    def page(route: str) -> Page:
        file = build / route.lstrip("/") / "index.html"
        if route == "/":
            file = build / "index.html"
        require(file.is_file(), f"Missing published page: {route}")
        return Page(file.read_text(encoding="utf-8"), route)

    def schemas(doc: Page, kind: str) -> list[dict]:
        blocks = [json.loads(node.text()) for node in doc.select(tag="script")
                  if node.attrs.get("type") == "application/ld+json"]
        return [block for block in blocks
                if isinstance(block, dict) and block.get("@type") == kind]

    home = page("/")
    sites = schemas(home, "WebSite")
    cafes = schemas(home, "CafeOrCoffeeShop")
    require(len(sites) == 1 and len(cafes) == 1,
            "Thai canonical homepage must contain one WebSite and one CafeOrCoffeeShop")
    site, cafe = sites[0], cafes[0]
    require(site.get("@context") == "https://schema.org", "WebSite schema.org context missing")
    require(site.get("@id") == ORIGIN + "/#website", "WebSite id must be stable")
    require(site.get("url") == ORIGIN + "/", "WebSite URL must be canonical root")
    require(site.get("name") == settings["brand"], "WebSite name differs from saved brand")
    require(site.get("alternateName") == "Brewtanist", "Missing commonly used short name")
    require(site.get("publisher", {}).get("@id") == cafe.get("@id"),
            "WebSite publisher must reference existing café entity")
    checks.append("Single root WebSite identity agrees with current café and brand")

    for language in ("en", "zh"):
        doc = page("/" + language + "/")
        require(len(schemas(doc, "WebSite")) == 0,
                "Do not invent distinct site names for language subdirectories")
        require(len(schemas(doc, "CafeOrCoffeeShop")) == 1,
                f"{language}: keep the existing café entity")
    checks.append("Localized homepages retain one café entity without duplicate site names")

    for language, prefix in LOCALES.items():
        ui = read(ROOT / "_data" / "ui" / (language + ".json"))
        oem = read(ROOT / "_data" / "oem_form" / (language + ".json"))
        for slug, expected_name in (("shop", ui["shop"]), ("oem", oem["nav"])):
            route = prefix + "/" + slug + "/"
            doc = page(route)
            all_breadcrumbs = schemas(doc, "BreadcrumbList")
            require(len(all_breadcrumbs) == 1, f"{route}: expected one BreadcrumbList")
            crumbs = all_breadcrumbs[0].get("itemListElement")
            require(isinstance(crumbs, list) and len(crumbs) == 2,
                    f"{route}: expected a two-step breadcrumb")
            expected = [(1, ui["home"], ORIGIN + prefix + "/"),
                        (2, expected_name, ORIGIN + route)]
            for actual, (position, name, url) in zip(crumbs, expected, strict=True):
                require(actual.get("@type") == "ListItem", f"{route}: invalid ListItem type")
                require(actual.get("position") == position, f"{route}: invalid breadcrumb position")
                require(actual.get("name") == name, f"{route}: breadcrumb label differs from navigation")
                require(actual.get("item") == url, f"{route}: breadcrumb URL differs from canonical")
            canonicals = [link.attrs.get("href") for link in doc.select(tag="link")
                          if link.attrs.get("rel") == "canonical"]
            require(canonicals == [ORIGIN + route],
                    f"{route}: breadcrumb must resolve to a canonical page")
    checks.append("Six Shop/OEM breadcrumbs agree with their language navigation and canonical URLs")
    return {"result": "PASS", "checks": checks, "routes_checked": 9}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path)
    arguments = parser.parse_args()
    report = inspect(arguments.build.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
