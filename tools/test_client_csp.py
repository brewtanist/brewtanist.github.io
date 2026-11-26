"""Verify CSP is enforced on every public page, without contacting external systems.

Offline Jekyll / Playwright regression tests. No login, credentials, or live RFQ.
A harmless inline-script marker is inserted into LOCAL pages to ensure it is
blocked. External requests are aborted and never reach the network.
"""
from __future__ import annotations

import argparse
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading

from test_storefront import Page, require

LOCALES = ("", "/en", "/zh")
PUBLIC = ("/", "/shop/", "/oem/")
ADMIN = ("/admin/", "/admin/quotes/")
BACKEND = "https://brewtanist-oem-requests.pumplcrs.chatgpt.site"
POLICY_META = "Content-Security-Policy"


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        return


def directives(content: str) -> dict[str, list[str]]:
    parsed = {}
    for part in content.split(";"):
        tokens = part.strip().split()
        if tokens:
            require(tokens[0] not in parsed, "Repeated CSP directive: " + tokens[0])
            parsed[tokens[0]] = tokens[1:]
    return parsed


def static_check(build: Path):
    checked = []
    for prefix in LOCALES:
        for route in PUBLIC + ADMIN:
            path = prefix + route
            htmlfile = build / path.lstrip("/") / "index.html"
            if path == "/":
                htmlfile = build / "index.html"
            require(htmlfile.is_file(), "Missing compiled site route: " + path)
            source = htmlfile.read_text(encoding="utf-8")
            page = Page(source, path)
            meta = [el for el in page.select(tag="meta")
                    if el.attrs.get("http-equiv", "").lower() == POLICY_META.lower()]
            require(len(meta) == 1, path + ": expected exactly one CSP policy")
            policy = directives(meta[0].attrs.get("content", ""))
            for directive, value in (
                ("default-src", ["'self'"]),
                ("base-uri", ["'none'"]),
                ("object-src", ["'none'"]),
                ("frame-src", ["'none'"]),
                ("script-src", ["'self'"]),
                ("script-src-attr", ["'none'"]),
                ("form-action", ["'self'"]),
                ("font-src", ["'self'"]),
            ):
                require(policy.get(directive) == value,
                        path + ": unexpected " + directive + ": " + repr(policy.get(directive)))
            expected_connect = ["'self'"]
            if route == "/oem/":
                expected_connect.append(BACKEND)
            require(policy.get("connect-src") == expected_connect,
                    path + ": unexpected outbound XHR destinations " + repr(policy.get("connect-src")))
            require("unsafe-eval" not in source.lower(), path + ": unexpected eval directive")
            require(not any(key in policy for key in ("frame-ancestors", "sandbox", "report-uri")),
                    path + ": these security directives are not supported in META CSP")
            pos = source.lower().find('http-equiv="content-security-policy"')
            require(pos > 0 and pos < source.lower().find('<script'),
                    path + ": CSP must be placed before scripts")
            ref = [el.attrs.get("content") for el in page.select(tag="meta")
                   if el.attrs.get("name") == "referrer"]
            require(len(ref) == 1, path + ": Referrer-Policy metadata missing/duplicated")
            if route in ("/oem/", "/admin/quotes/"):
                require(ref[0] == "no-referrer", path + ": private document referrer policy is too broad")
            else:
                require(ref[0] in ("no-referrer", "strict-origin-when-cross-origin"),
                        path + ": expected a safe referrer policy")
            checked.append(path)
    return checked


def browser_check(build: Path):
    from playwright.sync_api import expect, sync_playwright
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(build)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = "http://127.0.0.1:" + str(server.server_address[1])
    result = []
    try:
        with sync_playwright() as playwright:
            for engine in ("chromium", "webkit"):
                browser = getattr(playwright, engine).launch()
                for prefix in LOCALES:
                    for route in PUBLIC + ADMIN:
                        page = browser.new_page()
                        failures = []
                        outside = []
                        page.on("pageerror", lambda error: failures.append(str(error)))
                        def intercept(hop):
                            if hop.request.url.startswith(origin + "/"):
                                hop.continue_()
                            else:
                                outside.append(hop.request.url)
                                hop.abort()
                        page.route("**/*", intercept)
                        response = page.goto(origin + prefix + route, wait_until="load")
                        require(response is not None and response.status == 200,
                                engine + ": page did not load " + prefix + route)
                        if route == "/shop/":
                            expect(page.locator("[data-shop-controls]")).to_be_visible()
                            expect(page.locator("[data-finder-form]")).to_be_visible()
                        elif route == "/oem/":
                            expect(page.locator("#oem-form")).to_be_visible()
                        elif route == "/admin/quotes/":
                            expect(page.locator("#quote-app")).to_be_visible()
                        elif route == "/":
                            expect(page.locator("#hero-heading")).to_be_visible()

                        page.evaluate("""() => {
                            window.__security_marker = 0;
                            window.__csp_violations = [];
                            document.addEventListener('securitypolicyviolation',
                                e => window.__csp_violations.push(e.effectiveDirective));
                            const injected = document.createElement('script');
                            injected.textContent = 'window.__security_marker = 1';
                            document.head.append(injected);
                        }""")
                        page.wait_for_function("window.__csp_violations.some(x => x.startsWith('script-src'))")
                        require(page.evaluate("window.__security_marker") == 0,
                                engine + " " + prefix + route + ": inline script executed")
                        require(not failures, engine + " " + prefix + route + ": " + repr(failures))
                        require(not outside, engine + " " + prefix + route + ": unexpected external request")
                        page.close()
                    result.append(engine + " " + (prefix or "/th") +
                                  ": five pages functional, injected JavaScript blocked")

                # Make sure the OEM backend remains an allowed connect-src
                # destination while testing against a mocked response only.
                customer = browser.new_page()
                external = []
                customer.route("**/*", lambda route:
                    route.continue_() if route.request.url.startswith(origin + "/")
                    else (external.append(route.request.url), route.abort()))
                cors = {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST, OPTIONS",
                    "Access-Control-Allow-Headers": "content-type",
                }
                posts = []
                def fake_oem(route):
                    if route.request.method == "OPTIONS":
                        route.fulfill(status=204, headers=cors)
                        return
                    assert route.request.method == "POST", route.request.method
                    posts.append(json.loads(route.request.post_data)["reference"])
                    route.fulfill(status=200, headers=cors, content_type="application/json",
                                  body='{"ok":true,"reference":"' + posts[-1] + '"}')
                customer.route("**/api/requests", fake_oem)
                customer.goto(origin + "/oem/", wait_until="load")
                customer.locator('[name="beanQuantity"]').fill("2.5")
                customer.locator('[name="name"]').fill("QA No External Requests")
                customer.locator('[name="email"]').fill("qa@example.invalid")
                customer.locator("#oem-form button[type=submit]").click()
                customer.locator("#oem-submit").click()
                expect(customer.locator("#oem-submit")).to_be_hidden()
                require(len(posts) == 1 and posts[0].startswith("RFQ-"),
                        "Legitimate OEM request was blocked by CSP")
                require(not external, "Unexpected external request escaped mock transport")
                customer.close()
                result.append(engine + ": OEM confirmed receipt using mocked endpoint only")

                nojs = browser.new_context(java_script_enabled=False)
                page = nojs.new_page()
                page.goto(origin + "/oem/", wait_until="load")
                expect(page.locator("#oem-form")).to_be_hidden()
                expect(page.locator(".oem-grid noscript").first).to_be_visible()
                nojs.close()
                result.append(engine + ": OEM no-JavaScript fallback retained")
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path)
    parser.add_argument("--browser", action="store_true")
    args = parser.parse_args()
    compiled = args.build.resolve()
    pages = static_check(compiled)
    print("PASS: policy, isolated OEM connect-src, and referrer on " +
          str(len(pages)) + " routes", flush=True)
    if args.browser:
        for item in browser_check(compiled):
            print("PASS: " + item, flush=True)


if __name__ == "__main__":
    main()
