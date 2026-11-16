"""Check that CLS-targeted font preloads apply only to the Thai desktop Shop.

This is an HTML/asset validation, not a claim of improved field Core Web Vitals.
Lighthouse must be re-run on the published site to compare CLS numerically.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from test_storefront import Page, require

DESKTOP_ONLY = {
    "/brewtanist/fonts/baijamjuree-500-thai.woff2",
    "/brewtanist/fonts/baijamjuree-600-latin.woff2",
    "/brewtanist/fonts/lexend-400-700-latin.woff2",
    "/brewtanist/fonts/baijamjuree-400-latin.woff2",
}
DEFAULT = {
    "th": {"/brewtanist/fonts/baijamjuree-600-thai.woff2"},
    "en": {"/brewtanist/fonts/baijamjuree-600-latin.woff2"},
    "zh": set(),
}


def verify(build: Path) -> None:
    for lang, prefix in (("th", ""), ("en", "en/"), ("zh", "zh/")):
        path = build / prefix / "shop" / "index.html"
        require(path.is_file(), f"No Shop build for {lang}")
        page = Page(path.read_text(encoding="utf-8"), str(path))
        links = [node for node in page.select(tag="link")
                 if node.attrs.get("rel") == "preload" and node.attrs.get("as") == "font"]
        hrefs = [node.attrs.get("href", "") for node in links]
        require(len(hrefs) == len(set(hrefs)), f"{lang}: duplicate font preloads")
        expected = DEFAULT[lang] | (DESKTOP_ONLY if lang == "th" else set())
        require(set(hrefs) == expected, f"{lang}: unexpected font preloads: {hrefs}")
        for node in links:
            attrs = node.attrs
            require(attrs.get("type") == "font/woff2", f"{lang}: wrong preload font type")
            require("crossorigin" in attrs, f"{lang}: missing font preload CORS mode")
            name = attrs["href"]
            require((build / name.lstrip("/")).is_file(), f"{lang}: missing font asset {name}")
            if name in DESKTOP_ONLY:
                require(attrs.get("media") == "(min-width: 801px)",
                        f"{lang}: CLS font preload must be desktop-only: {name}")
            else:
                require("media" not in attrs, f"{lang}: existing font preload was changed")
        print(f"PASS: {lang} Shop has {len(links)} valid, nonduplicated font preloads")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("build", type=Path)
    args = parser.parse_args()
    verify(args.build.resolve())


if __name__ == "__main__":
    main()
