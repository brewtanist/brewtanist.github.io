"""Run a read-only Lighthouse lab audit of the live Brewtanist site.

These are lab scores from one simulated load on a GitHub-hosted runner, NOT
Chrome UX Report field Core Web Vitals, user traffic, rankings, or conversions.
Reports are intentionally informational: a low score is diagnostic, not a
reason to break an otherwise healthy production deployment.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://brewtanist.github.io"
ROUTES = {"home": "/", "shop": "/shop/", "oem": "/oem/"}
METRICS = {
    "first-contentful-paint": "FCP_ms",
    "largest-contentful-paint": "LCP_ms",
    "total-blocking-time": "TBT_ms",
    "cumulative-layout-shift": "CLS",
    "speed-index": "SpeedIndex_ms",
}
CATEGORIES = ("performance", "accessibility", "best-practices", "seo")


def measure(page: str, device: str, sample: int = 1) -> dict:
    route = ROUTES[page]
    url = ORIGIN + route
    report_dir = ROOT / "qa" / "performance-lab"
    report_dir.mkdir(parents=True, exist_ok=True)
    suffix = "" if sample == 1 else f".sample{sample}"
    full_report = report_dir / f"{page}-{device}{suffix}.lhr.json"
    summary_file = report_dir / f"{page}-{device}{suffix}.summary.json"

    cmd = [
        str(ROOT / "node_modules" / ".bin" / "lighthouse"),
        url,
        "--only-categories=performance,accessibility,best-practices,seo",
        "--output=json",
        "--output-path=" + str(full_report),
        "--max-wait-for-load=45000",
        "--throttling-method=simulate",
        "--chrome-flags=--headless=new --no-sandbox --disable-dev-shm-usage",
        "--quiet",
    ]
    if device == "desktop":
        cmd.append("--preset=desktop")

    # Do not log page content or query strings. Run only trusted, fixed paths.
    subprocess.run(cmd, cwd=ROOT, check=True, timeout=360)
    report = json.loads(full_report.read_text(encoding="utf-8"))
    if report.get("runtimeError"):
        raise RuntimeError("Lighthouse runtime failure: " + str(report["runtimeError"].get("code")))
    observed = urlsplit(report.get("finalDisplayedUrl") or report.get("finalUrl") or "")
    if (observed.scheme, observed.netloc, observed.path) != ("https", "brewtanist.github.io", route):
        raise RuntimeError(f"Unexpected final audit URL for {page}: {observed.scheme}://{observed.netloc}{observed.path}")

    scores = {}
    for name in CATEGORIES:
        entry = report.get("categories", {}).get(name, {})
        score = entry.get("score")
        scores[name] = round(score * 100) if isinstance(score, (int, float)) else None

    timing = {}
    for code, label in METRICS.items():
        value = report.get("audits", {}).get(code, {}).get("numericValue")
        timing[label] = round(value, 3) if isinstance(value, (int, float)) else None

    savings = []
    for code, entry in report.get("audits", {}).items():
        details = entry.get("details") if isinstance(entry, dict) else None
        ms = details.get("overallSavingsMs") if isinstance(details, dict) else None
        if isinstance(ms, (int, float)) and ms >= 100:
            savings.append({"audit": code, "title": entry.get("title"), "estimatedSavingsMs": round(ms)})
    savings.sort(key=lambda x: -x["estimatedSavingsMs"])

    mainthread = report.get("audits", {}).get("mainthread-work-breakdown", {})
    work = (mainthread.get("details") or {}).get("items") or []
    by_group = {row.get("group"): row.get("duration") for row in work}
    for group, label in (("styleLayout", "StyleLayout_ms"),
                         ("scriptEvaluation", "ScriptEvaluation_ms")):
        value = by_group.get(group)
        timing[label] = round(value, 3) if isinstance(value, (int, float)) else None

    result = {
        "audit": "Lighthouse 13.6.0",
        "sample_number": sample,
        "runner_benchmark_index": report.get("environment", {}).get("benchmarkIndex"),
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "url": url,
        "device": device,
        "audit_workflow_sha": os.environ.get("GITHUB_SHA", ""),
        "tested_site": "currently published production pages (not the PR preview)",
        "scores_0_to_100": scores,
        "lab_metrics": timing,
        "opportunities": savings[:5],
        "run_warnings": report.get("runWarnings", [])[:8],
        "field_core_web_vitals_measured": False,
        "interpretation": "One simulated lab load; not real visitor LCP, INP or CLS. No GA4 or GSC access was used.",
    }
    summary_file.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)

    gh_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if gh_summary:
        with open(gh_summary, "a", encoding="utf-8") as file:
            file.write(f"### Brewtanist: {page} · {device}\n")
            file.write(f"URL: {url}\n\n")
            file.write("| Measure | Value |\n|---|---:|\n")
            for label, value in scores.items():
                file.write(f"| {label} score | {value if value is not None else 'N/A'}/100 |\n")
            for label, value in timing.items():
                file.write(f"| {label} | {value if value is not None else 'N/A'} |\n")
            file.write("\nOne simulated Lighthouse run, **not field Core Web Vitals or a rankings guarantee**.\n")
            if savings:
                file.write("\nEstimated lab opportunities:\n")
                for item in savings[:3]:
                    file.write(f"- {item['title']}: {item['estimatedSavingsMs']} ms (estimate)\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--page", choices=ROUTES, required=True)
    parser.add_argument("--device", choices=("mobile", "desktop"), required=True)
    parser.add_argument("--sample", type=int, choices=(1, 2, 3), default=1,
                        help="Keep sample 1 filenames backward-compatible; 2/3 use distinct files.")
    args = parser.parse_args()
    measure(args.page, args.device, args.sample)


if __name__ == "__main__":
    main()
