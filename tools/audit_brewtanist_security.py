"""Bounded, non-destructive security assessment for the owner's Brewtanist site.

Read-only status/headers only; NEVER read private response bodies, POST a lead,
authenticate, brute force, enumerate identifiers, or crawl arbitrary paths.
Seven fixed HTTPS probes, no redirects, at most 10 seconds each.

This is NOT a full penetration test. Findings are triage signals, not proof of
data leakage or of an exploit. Do not publish credentials or customer data.
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
ORIGIN = "https://brewtanist.github.io"
BACKEND = "brewtanist-oem-requests.pumplcrs.chatgpt.site"
OTHER_ORIGIN = "https://security-check.invalid"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def endpoint():
    text = (ROOT / "_data/oem_intake.yml").read_text(encoding="utf-8")
    matches = re.findall(r"^endpoint:\s*(\S+)\s*$", text, re.MULTILINE)
    if len(matches) != 1:
        raise ValueError("Expected exactly one configured OEM endpoint")
    url = urllib.parse.urlsplit(matches[0])
    if (url.scheme, url.netloc, url.path, url.query, url.fragment) != (
        "https", BACKEND, "/api/requests", "", ""
    ):
        raise ValueError("Endpoint changed; require owner review before probing")
    return matches[0]


def probe(url: str, method: str, supplied: dict[str, str] | None = None):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc not in (BACKEND, "brewtanist.github.io"):
        raise ValueError("Probe host outside owner-approved allowlist")
    if method not in ("GET", "HEAD", "OPTIONS"):
        raise ValueError("Only non-mutating methods may be used")
    opener = urllib.request.build_opener(NoRedirect())
    req = urllib.request.Request(
        url, method=method,
        headers={"User-Agent": "Brewtanist-Bounded-Security-Check/1.0", **(supplied or {})},
    )
    try:
        # Deliberately never call response.read(); for sensitive routes we
        # examine status and a fixed list of security header names only.
        with opener.open(req, timeout=10) as response:
            return response.status, response.headers
    except urllib.error.HTTPError as error:
        try:
            return error.code, error.headers
        finally:
            error.close()


def methods(value):
    return {part.strip().upper() for part in (value or "").split(",") if part.strip()}


def add_finding(report, severity: str, code: str, summary: str):
    report["findings"].append({"severity": severity, "code": code, "summary": summary})


def perform():
    api = endpoint()
    backend = "https://" + BACKEND
    report = {
        "kind": "bounded_non_destructive_oem_security_review",
        "at_utc": datetime.now(timezone.utc).isoformat(),
        "result": "COMPLETED",
        "target": "Brewtanist public website and configured OEM service",
        "scope": "7 fixed HTTPS requests: only GET / HEAD / OPTIONS; no response body read",
        "private_body_read": False,
        "auth_attempted": False,
        "rfq_created": False,
        "rate_limit_tested": False,
        "privilege_escalation_tested": False,
        "tests": {},
        "findings": [],
    }
    queries = [
        ("valid_origin_preflight", api, "OPTIONS", {
            "Origin": ORIGIN, "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        }),
        ("foreign_origin_preflight", api, "OPTIONS", {
            "Origin": OTHER_ORIGIN, "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        }),
        ("forbidden_method_preflight", api, "OPTIONS", {
            "Origin": ORIGIN, "Access-Control-Request-Method": "DELETE",
            "Access-Control-Request-Headers": "content-type",
        }),
        ("anonymous_api_collection_get", api, "GET", {}),
        ("anonymous_staff_get", backend + "/staff/", "GET", {}),
        ("anonymous_staff_head", backend + "/staff/", "HEAD", {}),
        ("public_oem_page_get", ORIGIN + "/oem/", "GET", {}),
    ]
    responses = {}
    for name, url, method, headers in queries:
        try:
            code, response_headers = probe(url, method, headers)
            responses[name] = (code, response_headers)
            report["tests"][name] = {"status": code, "request_completed": True}
        except (OSError, TimeoutError, urllib.error.URLError, ValueError) as exc:
            report["tests"][name] = {
                "request_completed": False, "error_class": type(exc).__name__
            }
            add_finding(report, "review", "CONNECTIVITY_" + name.upper(),
                        "Probe could not be completed; network or service needs checking")

    if "valid_origin_preflight" in responses:
        code, h = responses["valid_origin_preflight"]
        allowed = (h.get("Access-Control-Allow-Origin") or "").strip()
        post = "POST" in methods(h.get("Access-Control-Allow-Methods"))
        content_type = ("content-type" in
                        {v.strip().lower() for v in (h.get("Access-Control-Allow-Headers") or "").split(",")})
        okay = 200 <= code < 300 and allowed in (ORIGIN, "*") and post and content_type
        report["tests"]["valid_origin_preflight"]["browser_cors_valid"] = okay
        if not okay:
            add_finding(report, "high", "EXPECTED_ORIGIN_BLOCKED",
                        "Customer website may fail JSON POST due to CORS configuration")
        if allowed == "*":
            add_finding(report, "review", "BROAD_WRITE_ORIGIN",
                        "Public OEM form accepts cross-origin requests; confirm spam and abuse controls")
        if h.get("Access-Control-Allow-Credentials", "").strip().lower() == "true" and allowed == "*":
            add_finding(report, "review", "WILDCARD_WITH_CREDENTIALS",
                        "CORS credentials settings should be reviewed")

    if "foreign_origin_preflight" in responses:
        _, h = responses["foreign_origin_preflight"]
        other = (h.get("Access-Control-Allow-Origin") or "").strip()
        rejected = other not in ("*", OTHER_ORIGIN)
        report["tests"]["foreign_origin_preflight"]["origin_not_authorized"] = rejected
        if not rejected:
            add_finding(report, "review", "FOREIGN_ORIGIN_ALLOWED",
                        "Foreign Origin is accepted by preflight; confirm unauthenticated form design and rate limits")

    if "forbidden_method_preflight" in responses:
        _, h = responses["forbidden_method_preflight"]
        allowed = methods(h.get("Access-Control-Allow-Methods"))
        if "DELETE" in allowed or "*" in allowed:
            add_finding(report, "review", "BROAD_PREFLIGHT_METHODS",
                        "Preflight advertises DELETE; review API method restrictions")
        report["tests"]["forbidden_method_preflight"]["advertises_delete"] = (
            "DELETE" in allowed or "*" in allowed
        )

    if "anonymous_api_collection_get" in responses:
        code, _ = responses["anonymous_api_collection_get"]
        denied = code in (401, 403, 404, 405)
        report["tests"]["anonymous_api_collection_get"]["anonymous_data_not_exposed_by_status"] = denied
        if code in (200, 206):
            add_finding(report, "high", "PUBLIC_API_GET_REVIEW",
                        "Anonymous API collection returned success; investigate possible data exposure privately (body was NOT read)")
        elif not denied:
            add_finding(report, "review", "API_GET_UNEXPECTED_STATUS",
                        "Unexpected anonymous collection response; verify service authentication")

    if "anonymous_staff_get" in responses:
        code, h = responses["anonymous_staff_get"]
        denied = code in (401, 403)
        report["tests"]["anonymous_staff_get"]["anonymous_denied_by_status"] = denied
        if not denied:
            add_finding(report, "high" if code in (200, 206) else "review",
                        "STAFF_ANONYMOUS_BOUNDARY",
                        "Staff route did not explicitly deny anonymous GET; inspect authentication without exposing private data")
        frame_csp = h.get("Content-Security-Policy", "").lower()
        xframe = h.get("X-Frame-Options", "").strip().lower()
        framed = "frame-ancestors" in frame_csp or xframe in ("deny", "sameorigin")
        report["tests"]["anonymous_staff_get"]["anti_framing_header_present"] = framed
        if not framed:
            add_finding(report, "review", "STAFF_FRAME_PROTECTION",
                        "Staff response lacks clear anti-framing headers; check logged-in pages as well")
        hsts = bool(h.get("Strict-Transport-Security"))
        report["tests"]["anonymous_staff_get"]["hsts_present"] = hsts
        if not hsts:
            add_finding(report, "info", "BACKEND_HSTS_ABSENT",
                        "HSTS not visible on anonymous staff response")

    if "public_oem_page_get" in responses:
        code, h = responses["public_oem_page_get"]
        report["tests"]["public_oem_page_get"]["page_available"] = code == 200
        report["tests"]["public_oem_page_get"]["csp_header_present"] = bool(
            h.get("Content-Security-Policy")
        )
        if code != 200:
            add_finding(report, "review", "OEM_PAGE_NOT_OK",
                        "Public OEM page did not respond with HTTP 200")
        if not h.get("Content-Security-Policy"):
            add_finding(report, "info", "PUBLIC_CSP_HEADER_ABSENT",
                        "No CSP response header on public static OEM page; GitHub Pages header control is limited")

    severities = {x["severity"] for x in report["findings"]}
    report["result"] = ("REVIEW_HIGH" if "high" in severities else
                        "REVIEW" if "review" in severities else "PASS_WITH_NOTES")
    report["limit"] = (
        "No authenticated session, input fuzzing, SQL injection, exploit attempts,"
        " request body collection, denial-of-service, or live lead submission."
    )
    return report


def self_test():
    assert methods("GET, POST, OPTIONS") == {"GET", "POST", "OPTIONS"}
    assert "DELETE" not in methods("GET,POST")
    assert "DELETE" in methods("DELETE, POST")
    assert endpoint().startswith("https://" + BACKEND)
    for url in ("https://example.invalid/", "http://" + BACKEND):
        try:
            probe(url, "HEAD")
        except ValueError:
            pass
        else:
            raise AssertionError("Unexpected target was accepted")
    try:
        probe("https://" + BACKEND, "POST")
    except ValueError:
        pass
    else:
        raise AssertionError("A mutating method was accepted")
    print("PASS: allowlist, method restriction and non-network fixtures")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    report = perform()
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("## Brewtanist — bounded security check\n\n")
            fh.write("Result: **" + report["result"] + "**\n\n")
            fh.write("Probes: " + str(len(report["tests"])) + " (GET / HEAD / OPTIONS only)\n\n")
            for finding in report["findings"]:
                fh.write("- " + finding["severity"] + " / " +
                         finding["code"] + ": " + finding["summary"] + "\n")
            fh.write("\nNo live lead or authenticated data was accessed.\n")
    # A high finding does not mutate production; fail CI as an alert.
    return 1 if report["result"] == "REVIEW_HIGH" else 0


if __name__ == "__main__":
    sys.exit(main())
