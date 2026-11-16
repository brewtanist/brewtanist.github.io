"""Read-only transport/CORS smoke test for Brewtanist OEM intake.

This script NEVER sends POST, customer data, credentials, or test RFQs.
It probes only:
- OPTIONS /api/requests with the same CORS preflight as the customer form
- GET /staff/ with redirects disabled (does not authenticate or read its body)

Passing does NOT prove a quote request is persisted or visible to staff.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_HOST = "brewtanist-oem-requests.pumplcrs.chatgpt.site"
SITE_ORIGIN = "https://brewtanist.github.io"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def configured_endpoint() -> str:
    source = (ROOT / "_data/oem_intake.yml").read_text(encoding="utf-8")
    matches = re.findall(r"^endpoint:\s*(\S+)\s*$", source, re.MULTILINE)
    if len(matches) != 1:
        raise ValueError("Expected exactly one OEM endpoint setting")
    endpoint = matches[0]
    parsed = urllib.parse.urlsplit(endpoint)
    if (parsed.scheme, parsed.netloc, parsed.path, parsed.query, parsed.fragment) != (
        "https", EXPECTED_HOST, "/api/requests", "", ""
    ):
        raise ValueError("Unexpected OEM endpoint host/path; owner review required")
    return endpoint


def assess_preflight(status: int, headers) -> tuple[bool, list[str]]:
    failures = []
    if status < 200 or status >= 300:
        failures.append("OPTIONS did not return 2xx")
    origin = (headers.get("Access-Control-Allow-Origin") or "").strip()
    if origin not in (SITE_ORIGIN, "*"):
        failures.append("CORS origin does not allow the Brewtanist site")
    methods = {
        x.strip().upper() for x in (headers.get("Access-Control-Allow-Methods") or "").split(",")
    }
    if "POST" not in methods and "*" not in methods:
        failures.append("CORS methods do not include POST")
    names = {
        x.strip().lower() for x in (headers.get("Access-Control-Allow-Headers") or "").split(",")
    }
    if "content-type" not in names and "*" not in names:
        failures.append("CORS request headers do not allow content-type")
    return not failures, failures


def request_headers(endpoint: str, method: str, headers: dict[str, str]) -> tuple[int, object]:
    # Do not read response body: a backend might contain sensitive information.
    request = urllib.request.Request(
        endpoint,
        method=method,
        headers={"User-Agent": "Brewtanist-OEM-Transport-Check/1.0", **headers},
    )
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=12) as response:
            return response.status, response.headers
    except urllib.error.HTTPError as error:
        return error.code, error.headers


def check() -> dict:
    endpoint = configured_endpoint()
    parsed = urllib.parse.urlsplit(endpoint)
    base = parsed.scheme + "://" + parsed.netloc
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "result": "FAIL",
        "kind": "read_only_oem_transport",
        "backend_host": EXPECTED_HOST,
        "site_origin": SITE_ORIGIN,
        "live_test_rfq_created": False,
        "request_persisted_verified": False,
        "staff_authentication_verified": False,
        "staff_inbox_delivery_verified": False,
        "checks": {},
    }
    try:
        status, headers = request_headers(
            endpoint, "OPTIONS", {
                "Origin": SITE_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        ok, problems = assess_preflight(status, headers)
        report["checks"]["browser_preflight"] = {
            "status": status, "pass": ok, "problems": problems
        }
    except (OSError, ValueError, TimeoutError, urllib.error.URLError) as error:
        report["checks"]["browser_preflight"] = {
            "pass": False, "problems": ["Connection failed: " + type(error).__name__]
        }

    # This is a public staff page reachability check only. A 200 or redirect
    # does NOT prove the private inbox is authenticated or safe.
    try:
        status, headers = request_headers(base + "/staff/", "GET", {})
        reachable = status in (200, 301, 302, 303, 307, 308, 401, 403)
        report["checks"]["staff_page_reachable"] = {
            "status": status,
            "pass": reachable,
            "problems": [] if reachable else ["Unexpected staff route HTTP status"],
        }
    except (OSError, ValueError, TimeoutError, urllib.error.URLError) as error:
        report["checks"]["staff_page_reachable"] = {
            "pass": False, "problems": ["Connection failed: " + type(error).__name__]
        }

    if all(item.get("pass") for item in report["checks"].values()):
        report["result"] = "PASS"
    report["interpretation"] = (
        "Checks public transport and CORS only. Actual request persistence, "
        "staff authorization and inbox receipt still require an owner-approved end-to-end test."
    )
    return report


def self_test():
    ok = {
        "Access-Control-Allow-Origin": SITE_ORIGIN,
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, X-Requested-With",
    }
    assert assess_preflight(204, ok)[0]
    assert not assess_preflight(405, ok)[0]
    assert not assess_preflight(204, {**ok, "Access-Control-Allow-Origin": "https://wrong.invalid"})[0]
    assert not assess_preflight(204, {**ok, "Access-Control-Allow-Methods": "GET"})[0]
    assert not assess_preflight(204, {**ok, "Access-Control-Allow-Headers": "X-Requested-With"})[0]
    assert configured_endpoint().startswith("https://" + EXPECTED_HOST + "/")
    print("PASS: CORS validator fixtures and endpoint allowlist", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    report = check()
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        preflight = report["checks"].get("browser_preflight", {})
        staff = report["checks"].get("staff_page_reachable", {})
        with open(summary, "a", encoding="utf-8") as output:
            output.write("## Brewtanist OEM transport (read-only)\n\n")
            output.write(f"Overall: **{report['result']}**\n\n")
            output.write(f"Browser CORS preflight: {preflight.get('pass')} (HTTP {preflight.get('status', 'N/A')})\n\n")
            output.write(f"Staff page reachable: {staff.get('pass')} (HTTP {staff.get('status', 'N/A')})\n\n")
            output.write("**Not tested:** POST delivery, storage, staff login, inbox visibility or customer data.\n")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
