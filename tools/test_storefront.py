"""Validate the rendered Jekyll storefront against the current saved shop data.

No browser, network requests, third-party packages, or source modifications.
The optional positional argument points at _site or a local rendered preview.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs, unquote, urljoin, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://brewtanist.github.io"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def compact(value):
    return " ".join(str(value).split())


@dataclass
class Element:
    tag: str
    attrs: dict = field(default_factory=dict)
    content: list = field(default_factory=list)
    parent: "Element | None" = None

    def descendants(self):
        for child in self.content:
            if isinstance(child, Element):
                yield child
                yield from child.descendants()

    def select(self, tag=None, class_name=None, attribute=None):
        return [node for node in self.descendants()
                if (tag is None or node.tag == tag)
                and (class_name is None or class_name in node.attrs.get("class", "").split())
                and (attribute is None or attribute in node.attrs)]

    def text(self):
        return "".join(child.text() if isinstance(child, Element) else child for child in self.content)

    def decorative(self):
        node = self
        while node is not None:
            if node.attrs.get("aria-hidden") == "true":
                return True
            node = node.parent
        return False


class Page(HTMLParser):
    def __init__(self, html, location):
        super().__init__(convert_charrefs=True)
        self.location = location
        self.html = html
        self.root = Element("document")
        self.stack = [self.root]
        self.feed(html)
        self.close()
        ids = [node.attrs["id"] for node in self.root.descendants() if "id" in node.attrs]
        require(len(ids) == len(set(ids)), f"{location}: duplicate element IDs")
        self.ids = set(ids)

    def handle_starttag(self, tag, attrs):
        node = Element(tag, dict(attrs), parent=self.stack[-1])
        self.stack[-1].content.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        node = Element(tag, dict(attrs), parent=self.stack[-1])
        self.stack[-1].content.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].content.append(data)

    def select(self, **kwargs):
        return self.root.select(**kwargs)


def read_data(name):
    return json.loads((ROOT / "_data" / "brewtanist" / (name + ".json")).read_text(encoding="utf-8"))


def single(nodes, message):
    require(len(nodes) == 1, message)
    return nodes[0]


def check(build):
    report = {"result": "FAIL", "build_directory": str(build), "checks": [],
              "browser_interactions_tested": False, "live_shopee_price_or_inventory_tested": False}
    checks = report["checks"]
    marketplace = read_data("marketplace")
    houses = {item["id"]: item for item in read_data("products")["items"]}
    home = read_data("home")
    settings = read_data("settings")
    items = marketplace["items"]
    require(isinstance(items, list), "Marketplace items must be a list")
    require(str(marketplace.get("shopId", "")).isdigit(), "Missing numeric Shopee shop ID")
    require(all(type(item.get("visible")) is bool for item in items), "Every item needs explicit boolean visibility")
    require(len({item["id"] for item in items}) == len(items), "Duplicate saved catalogue IDs")
    require(len({item["shopeeItemId"] for item in items}) == len(items), "Duplicate saved Shopee item IDs")
    require(all(str(item.get("shopeeItemId", "")).isdigit() for item in items), "Invalid Shopee item ID")
    visible = {item["id"]: item for item in items if item["visible"] is True}
    categories = Counter(item["category"] for item in visible.values())
    report.update(visible_products=len(visible), category_counts=dict(sorted(categories.items())))
    cache = {}

    def page_at(path):
        path = path.resolve()
        require(path.is_relative_to(build), "A rendered page escapes the build directory")
        require(path.is_file(), f"Missing rendered page: {path.relative_to(build)}")
        if path not in cache:
            cache[path] = Page(path.read_text(encoding="utf-8"), str(path.relative_to(build)))
        return cache[path]

    pages = {"/": page_at(build / "index.html"), "/shop/": page_at(build / "shop" / "index.html")}
    for route, page in pages.items():
        require(not re.search(r"\{[{%]-?", page.html), f"{route}: unrendered Liquid remains")
        h1 = single(page.select(tag="h1"), f"{route}: expected one H1")
        require(compact(h1.text()), f"{route}: empty H1")
        canonical = single([node for node in page.select(tag="link") if node.attrs.get("rel") == "canonical"],
                           f"{route}: expected one canonical URL")
        require(canonical.attrs.get("href") == ORIGIN + route, f"{route}: incorrect canonical URL")
        og_url = single([node for node in page.select(tag="meta") if node.attrs.get("property") == "og:url"],
                        f"{route}: expected Open Graph URL")
        require(og_url.attrs.get("content") == ORIGIN + route, f"{route}: incorrect Open Graph URL")
        require(compact(single(page.select(tag="title"), f"{route}: expected title").text()), f"{route}: empty title")
        for script in page.select(tag="script"):
            if script.attrs.get("type") == "application/ld+json":
                json.loads(script.text())
        for image in page.select(tag="img"):
            require("alt" in image.attrs, f"{route}: image missing alt attribute")
            require(image.decorative() or compact(image.attrs.get("alt", "")), f"{route}: non-decorative image has empty alt")
    require(compact(pages["/"].select(tag="h1")[0].text()) == compact(home["hero_title"]),
            "Homepage hero differs from current saved CMS copy")
    checks.append("Rendered pages: complete Liquid output, saved hero copy, one H1, canonical/OG URLs and valid JSON-LD")

    shop = pages["/shop/"]
    for nodes, key in ((shop.select(tag="h1"), "title"),
                       (single(shop.select(class_name="shop-hero"), "Missing shop hero").select(tag="p"), "intro"),
                       (shop.select(class_name="shop-price-note"), "notice")):
        node = single(nodes, f"Shop missing CMS field {key}")
        require(compact(node.text()) == compact(marketplace[key]), f"Shop {key} differs from current CMS data")
    grid = single(shop.select(attribute="data-shop-grid"), "Shop must have one product grid")
    cards = grid.select(attribute="data-shop-card")
    require(len(cards) == len(visible), f"Shop rendered {len(cards)} cards; saved data expects {len(visible)}")
    rendered_ids = [card.attrs.get("id", "").removeprefix("shop-") for card in cards]
    require(set(rendered_ids) == set(visible) and len(rendered_ids) == len(set(rendered_ids)),
            "Rendered catalogue IDs do not match current visible saved products")
    require(Counter(card.attrs.get("data-category") for card in cards) == categories,
            "Rendered product categories differ from current saved data")
    image_count = 0
    fallback_count = 0

    def check_card(card):
        item_id = card.attrs.get("id", "").removeprefix("shop-")
        require(item_id in visible, f"Card {item_id!r} is absent or hidden in saved data")
        item = visible[item_id]
        require("hidden" not in card.attrs, f"{item_id}: server-rendered product must remain available without JavaScript")
        require(card.attrs.get("data-category") == item["category"], f"{item_id}: wrong category")
        title = single(card.select(tag="h3"), f"{item_id}: expected one product heading")
        require(compact(title.text()) == compact(item["name"]), f"{item_id}: name differs from saved data")
        body = single(card.select(class_name="shop-card-body"), f"{item_id}: missing product body")
        description = single(body.select(tag="p"), f"{item_id}: expected one product description")
        require(compact(description.text()) == compact(item["description"]), f"{item_id}: description differs from saved data")
        expected_url = f"https://shopee.co.th/product/{marketplace['shopId']}/{item['shopeeItemId']}"
        for class_name in ("shop-image", "shop-buy"):
            link = single(card.select(tag="a", class_name=class_name), f"{item_id}: missing {class_name} link")
            require(link.attrs.get("href") == expected_url, f"{item_id}: {class_name} points to the wrong Shopee SKU")
            require(link.attrs.get("target") == "_blank", f"{item_id}: Shopee link should open separately")
            require({"noopener", "noreferrer"} <= set(link.attrs.get("rel", "").split()),
                    f"{item_id}: external link missing rel protection")
        house = houses.get(item.get("houseId"), {})
        expected_image = item.get("image") or house.get("image") or ""
        images = card.select(tag="img")
        if expected_image:
            image = single(images, f"{item_id}: expected its configured product image")
            require(image.attrs.get("src") == expected_image, f"{item_id}: wrong product image or include variable leakage")
            require(expected_image.startswith("/brewtanist/assets/"), f"{item_id}: product image must use stored local assets")
            require((ROOT / expected_image.lstrip("/")).is_file(), f"{item_id}: configured image absent from source")
            expected_alt = item.get("alt") or house.get("alt") or item["name"]
            require(image.attrs.get("alt") == expected_alt, f"{item_id}: wrong product image alt text")
            return True
        require(not images, f"{item_id}: an unconfigured product image is being substituted")
        fallback = single(card.select(class_name="shop-image-note"), f"{item_id}: missing image needs a clear fallback")
        require("Shopee" in fallback.text(), f"{item_id}: fallback must point visitors to the Shopee image")
        return False

    for card in cards:
        if check_card(card): image_count += 1
        else: fallback_count += 1
    featured = pages["/"].select(attribute="data-shop-card")
    for card in featured:
        check_card(card)
    report.update(product_images=image_count, image_fallbacks=fallback_count, homepage_featured_products=len(featured))
    checks.append("Product IDs, categories, copy, configured images/fallbacks and exact Shopee SKU links match saved data")

    filter_buttons = shop.select(tag="button", attribute="data-filter")
    filter_keys = [button.attrs["data-filter"] for button in filter_buttons]
    require(len(filter_keys) == len(set(filter_keys)), "Duplicate category filter buttons")
    require({"all", *categories.keys()} <= set(filter_keys), "A saved category has no filter button")
    for button in filter_buttons:
        category = button.attrs["data-filter"]
        count = len(visible) if category == "all" else categories[category]
        badge = single(button.select(tag="span"), f"{category}: expected one category count")
        require(compact(badge.text()) == str(count), f"{category}: category badge differs from current data")
        require(button.attrs.get("aria-pressed") == ("true" if category == "all" else "false"),
                f"{category}: incorrect initial filter selection")
    result = single(shop.select(attribute="data-result-count"), "Missing search result count")
    require(compact(result.text()) == f"{len(visible)} รายการ", "Initial result count differs from saved data")
    require(result.attrs.get("role") == "status", "Result count must announce filter changes")
    require(shop.select(tag="input", attribute="id") and "shop-search" in shop.ids, "Missing search field")
    checks.append("Filter categories and displayed counts derive from current visible products")

    for route, page in pages.items():
        require(any(node.attrs.get("href") == "/shop/" for node in page.select(tag="a")),
                f"{route}: missing storefront navigation link")
    for class_name in ("nav-links", "mobile-nav"):
        navigation = single(shop.select(class_name=class_name), f"Shop missing {class_name}")
        require(any(link.attrs.get("href") == "/" for link in navigation.select(tag="a")), "Shop menu cannot return home")
        require(any(link.attrs.get("href") == "/shop/" and link.attrs.get("aria-current") == "page"
                    for link in navigation.select(tag="a")), "Shop menu missing current-page navigation")
        menu_links = {link.attrs.get("href") for link in navigation.select(tag="a")}
        for section in ("coffee", "gallery"):
            visible_section = read_data(section).get("visible") is not False
            require((section in pages["/"].ids) == visible_section,
                    f"Homepage {section} does not respect CMS visibility")
            require((f"/#{section}" in menu_links) == visible_section,
                    f"Shop {class_name}: {section} link does not match CMS visibility")
    if not settings.get("catalogue_url", "").startswith("https://") and read_data("products").get("visible") is not False:
        for class_name in ("nav-links", "mobile-nav"):
            navigation = single(pages["/"].select(class_name=class_name), f"Homepage missing {class_name}")
            require(any(link.attrs.get("href") == "/shop/" for link in navigation.select(tag="a")),
                    f"Homepage {class_name} does not lead to the new shop")
    checks.append("Homepage links and desktop/mobile shop navigation connect both pages")

    checked_references = set()
    for route, page in pages.items():
        for node in page.root.descendants():
            references = []
            if node.tag in {"a", "link"} and node.attrs.get("href"):
                references.append(node.attrs["href"])
            if node.tag in {"img", "script", "source", "video"} and node.attrs.get("src"):
                references.append(node.attrs["src"])
            for reference in references:
                resolved = urlsplit(urljoin(ORIGIN + route, reference))
                if resolved.scheme not in {"http", "https"} or resolved.netloc != urlsplit(ORIGIN).netloc:
                    continue
                target = (build / unquote(resolved.path).lstrip("/")).resolve()
                require(target.is_relative_to(build), f"{route}: internal URL escapes build: {reference}")
                if resolved.path.endswith("/") or target.is_dir():
                    target = target / "index.html"
                require(target.is_file(), f"{route}: broken internal link/asset {reference}")
                if resolved.fragment and target.suffix == ".html":
                    require(unquote(resolved.fragment) in page_at(target).ids,
                            f"{route}: missing anchor in internal link {reference}")
                if resolved.path.rstrip("/") == "/shop":
                    requested_category = parse_qs(resolved.query).get("category", ["all"])[0]
                    require(requested_category in filter_keys, f"{route}: link to an unsupported category")
                checked_references.add(resolved.path + ("#" + resolved.fragment if resolved.fragment else ""))
    sitemap = ET.parse(build / "sitemap.xml")
    sitemap_urls = {element.text for element in sitemap.findall(".//{*}loc")}
    require({ORIGIN + "/", ORIGIN + "/shop/"} <= sitemap_urls, "Sitemap does not include homepage and shop")
    report["internal_references_checked"] = len(checked_references)
    checks.append("Internal page links, anchors, local images/CSS/JS and sitemap routes exist in the rendered build")
    report["result"] = "PASS"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build_directory", nargs="?", default=str(ROOT / "_site"))
    parser.add_argument("--report", type=Path, help="Optional JSON report path (outside source is recommended)")
    args = parser.parse_args()
    build = Path(args.build_directory).resolve()
    try:
        report = check(build)
        status = 0
    except Exception as error:
        report = {"result": "FAIL", "build_directory": str(build),
                  "error": f"{type(error).__name__}: {error}", "browser_interactions_tested": False}
        status = 1
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return status


if __name__ == "__main__":
    sys.exit(main())
