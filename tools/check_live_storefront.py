"""Read-only health audit of Brewtanist's *published* GitHub Pages site.

This checks nine customer URLs, seven public admin/quote/redirect pages, the
sitemap and robots.txt. It never submits an OEM RFQ, reads customer data, opens
a login session, calls third-party Google/Shopee services, or sets analytics.
It is not Google Search Console indexing, Googlebot, or an uptime SLA.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
import json
import os
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET

ORIGIN = "https://brewtanist.github.io"
LANGUAGES = {"th": ("", "th"), "en": ("/en", "en"), "zh": ("/zh", "zh-Hans")}
SECTIONS = ("/", "/shop/", "/oem/")
CUSTOMER = {
    prefix + section: (tag, section)
    for prefix, tag in LANGUAGES.values() for section in SECTIONS
}
ADMIN = (
    "/admin/", "/admin/quotes/", "/en/admin/", "/en/admin/quotes/",
    "/zh/admin/", "/zh/admin/quotes/", "/brewtanist/admin/",
)
ROBOTS = "/robots.txt"
SITEMAP = "/sitemap.xml"
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


class HeadData(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lang = ""
        self.canonicals = []
        self.alternates = {}
        self.robots = []
        self.og_urls = []
        self.headings = 0
        self.mains = 0
        self.titles = 0
        self.in_head = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html":
            self.lang = attrs.get("lang", "")
        elif tag == "head":
            self.in_head = True
        elif tag == "title" and self.in_head:
            self.titles += 1
        elif tag == "main":
            self.mains += 1
        elif tag == "h1":
            self.headings += 1
        elif tag == "link" and self.in_head:
            rel = attrs.get("rel", "").lower().split()
            if "canonical" in rel:
                self.canonicals.append(attrs.get("href", ""))
            if "alternate" in rel and attrs.get("hreflang"):
                key = attrs["hreflang"]
                self.alternates.setdefault(key, []).append(attrs.get("href", ""))
        elif tag == "meta" and self.in_head:
            if attrs.get("name", "").lower() in ("robots", "googlebot"):
                self.robots.extend(t.strip().lower() for t in attrs.get("content", "").split(","))
            if attrs.get("property", "").lower() == "og:url":
                self.og_urls.append(attrs.get("content", ""))

    def handle_endtag(self, tag):
        if tag == "head":
            self.in_head = False


def extract(html):
    page = HeadData()
    page.feed(html)
    return page


def validate_customer(path, html):
    page = extract(html)
    lang, section = CUSTOMER[path]
    if page.lang != lang or page.titles != 1 or page.headings != 1 or page.mains != 1:
        raise ValueError(f"{path}: invalid HTML language, title, H1 or main count")
    if page.canonicals != [ORIGIN + path] or page.og_urls != [ORIGIN + path]:
        raise ValueError(f"{path}: canonical/og:url mismatch")
    if "noindex" in page.robots:
        raise ValueError(f"{path}: customer route mistakenly noindex")
    expected = {"x-default": ORIGIN + section}
    for prefix, tag in LANGUAGES.values():
        expected[tag] = ORIGIN + prefix + section
    for key, link in expected.items():
        if page.alternates.get(key) != [link]:
            raise ValueError(f"{path}: missing or incorrect hreflang {key}")
    return {"path": path, "html_lang": lang, "canonical": True, "hreflang": True}


def validate_admin(path, html):
    page = extract(html)
    if "noindex" not in page.robots:
        raise ValueError(f"{path}: public admin/quote route has no HTML noindex")
    return {"path": path, "noindex": True}


def validate_sitemap(xml):
    root = ET.fromstring(xml)
    actual = [entry.findtext(SITEMAP_NS + "loc") for entry in root.findall(SITEMAP_NS + "url")]
    expected = {ORIGIN + path for path in CUSTOMER}
    if len(actual) != len(expected) or set(actual) != expected:
        raise ValueError("sitemap: expected only nine localized customer routes")
    return {"path": SITEMAP, "url_count": len(actual)}


def validate_robots(text):
    robots = RobotFileParser()
    robots.parse(text.splitlines())
    for path in [*CUSTOMER, *ADMIN]:
        if not robots.can_fetch("Googlebot", ORIGIN + path):
            raise ValueError(f"robots.txt blocks reading noindex or customer content: {path}")
    if f"Sitemap: {ORIGIN}{SITEMAP}" not in text:
        raise ValueError("robots.txt is missing the published sitemap URL")
    return {"path": ROBOTS, "googlebot_crawlable": True}


def get_public(path):
    if path not in CUSTOMER and path not in ADMIN and path not in (ROBOTS, SITEMAP):
        raise ValueError("Refusing an unlisted URL")
    url = ORIGIN + path
    last_error = None
    for attempt in range(3):
        try:
            req = Request(url, headers={
                "User-Agent": "Brewtanist-Live-Health/1.0",
                "Accept": "text/html,application/xml,text/plain",
            })
            with urlopen(req, timeout=18) as response:
                parsed = urlsplit(response.geturl())
                if (parsed.scheme, parsed.netloc, parsed.path) != ("https", "brewtanist.github.io", path):
                    raise ValueError(f"{path}: unexpected redirect away from canonical route")
                if response.status != 200:
                    raise ValueError(f"{path}: HTTP {response.status}")
                body = response.read(2_000_001)
                if len(body) > 2_000_000:
                    raise ValueError(f"{path}: response exceeds 2 MB")
                return body.decode("utf-8-sig")
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504):
                raise ValueError(f"{path}: HTTP {error.code}") from error
            last_error = error
        except (TimeoutError, URLError) as error:
            last_error = error
        if attempt < 2:
            time.sleep(2)
    raise ValueError(f"{path}: public site request still unavailable after retries ({type(last_error).__name__})")


def check():
    results = []
    for path in CUSTOMER:
        results.append(validate_customer(path, get_public(path)))
    for path in ADMIN:
        results.append(validate_admin(path, get_public(path)))
    results.append(validate_sitemap(get_public(SITEMAP)))
    results.append(validate_robots(get_public(ROBOTS)))
    return {
        "result": "PASS",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "origin": ORIGIN,
        "customer_routes": len(CUSTOMER),
        "public_noindex_routes": len(ADMIN),
        "total_get_requests": len(results),
        "checks": results,
        "tested_site": "currently published production site (not a pull request preview)",
        "private_staff_inbox_tested": False,
        "rfq_posted": False,
        "google_indexing_verified": False,
    }


def self_test():
    for path in CUSTOMER:
        lang, section = CUSTOMER[path]
        alternates = "".join(
            f'<link rel="alternate" hreflang="{tag}" href="{ORIGIN + prefix + section}">'
            for prefix, tag in LANGUAGES.values()
        ) + f'<link rel="alternate" hreflang="x-default" href="{ORIGIN + section}">'
        html = (
            f'<html lang="{lang}"><head><title>Test</title>'
            f'<link rel="canonical" href="{ORIGIN + path}">{alternates}'
            f'<meta property="og:url" content="{ORIGIN + path}">'
            '</head><body><main><h1>Test page</h1></main></body></html>'
        )
        validate_customer(path, html)
        for broken in (
            html.replace('rel="canonical"', 'rel="not-canonical"'),
            html.replace('rel="alternate" hreflang="x-default"', 'rel="not-alternate" hreflang="x-default"'),
            html.replace('</head>', '<meta name="robots" content="noindex"></head>'),
        ):
            try:
                validate_customer(path, broken)
            except ValueError:
                pass
            else:
                raise AssertionError("Invalid customer HTML passed: " + path)
    for path in ADMIN:
        validate_admin(path, '<html><head><meta name="robots" content="noindex,nofollow"></head></html>')
        try:
            validate_admin(path, "<html><head></head></html>")
        except ValueError:
            pass
        else:
            raise AssertionError("Missing noindex was accepted: " + path)
    valid_sitemap = (
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(f'<url><loc>{ORIGIN + p}</loc></url>' for p in CUSTOMER)
        + "</urlset>"
    )
    validate_sitemap(valid_sitemap)
    try:
        validate_sitemap(valid_sitemap.replace("</urlset>", f"<url><loc>{ORIGIN}/admin/</loc></url></urlset>"))
    except ValueError:
        pass
    else:
        raise AssertionError("Admin route included in sitemap was accepted")
    validate_robots("User-agent: *\nAllow: /\n\nSitemap: " + ORIGIN + SITEMAP)
    try:
        validate_robots("User-agent: *\nDisallow: /admin/\nSitemap: " + ORIGIN + SITEMAP)
    except ValueError:
        pass
    else:
        raise AssertionError("Robots blocking Admin was accepted")
    print("PASS: synthetic customer metadata, admin noindex, sitemap and robots fixtures")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0

    try:
        report = check()
    except Exception as exc:
        report = {
            "result": "FAIL",
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "reason": str(exc)[:500],
            "private_staff_inbox_tested": False,
            "rfq_posted": False,
        }
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as target:
            target.write("## Brewtanist live public-site health (read-only)\n\n")
            target.write(f"Result: **{report['result']}**\n\n")
            target.write("9 customer routes, 7 public noindex routes, sitemap and robots.txt; "
                         "no customer requests, login or tracking.\n\n")
            if report["result"] != "PASS":
                target.write("Failed: " + report.get("reason", "Unknown error") + "\n")
            target.write("This check does not establish Google indexing or real visitor conversions.\n")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
