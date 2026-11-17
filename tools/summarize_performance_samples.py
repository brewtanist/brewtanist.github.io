"""Summarize repeated *lab* Lighthouse samples from one live route/device.

Read only local Lighthouse summary JSON. This is not a Chrome UX Report,
field Core Web Vitals, SEO ranking, uptime or conversion measurement.
A large spread means that lab readings are noisy; it does not prove a regression.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
from statistics import median

METRICS = ("TBT_ms", "LCP_ms", "CLS", "StyleLayout_ms", "ScriptEvaluation_ms")
CATEGORIES = ("performance", "accessibility", "best-practices", "seo")


def _valid_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def summarize(samples: list[dict]) -> dict:
    if len(samples) < 3:
        raise ValueError("At least 3 measurements are required to report repeatability.")
    urls = {sample.get("url") for sample in samples}
    devices = {sample.get("device") for sample in samples}
    versions = {sample.get("audit") for sample in samples}
    if len(urls) != 1 or urls.pop() != "https://brewtanist.github.io/oem/":
        raise ValueError("Cannot compare different routes or untrusted hosts.")
    if devices != {"mobile"} or len(versions) != 1:
        raise ValueError("Samples must use the same mobile configuration and Lighthouse version.")
    ids = [sample.get("sample_number") for sample in samples]
    if ids != list(range(1, len(samples) + 1)):
        raise ValueError("Samples must have sequential and unique sample numbers.")
    if any(sample.get("field_core_web_vitals_measured") is not False for sample in samples):
        raise ValueError("Expected lab-only measurements.")

    for sample in samples:
        for category in CATEGORIES:
            value = sample.get("scores_0_to_100", {}).get(category)
            if not _valid_number(value) or not 0 <= value <= 100:
                raise ValueError("Incomplete Lighthouse score: " + category)
        for metric in ("TBT_ms", "LCP_ms", "CLS"):
            value = sample.get("lab_metrics", {}).get(metric)
            if not _valid_number(value) or value < 0:
                raise ValueError("Incomplete Lighthouse metric: " + metric)

    performance = [x["scores_0_to_100"]["performance"] for x in samples]
    tbt = [x["lab_metrics"]["TBT_ms"] for x in samples]
    spread = max(tbt) - min(tbt)
    score_spread = max(performance) - min(performance)
    # Diagnostic threshold, not a pass/fail Core Web Vitals threshold.
    unstable = spread >= 200 or score_spread >= 10

    def stats(values):
        values = [x for x in values if _valid_number(x)]
        if not values:
            return None
        return {"median": round(median(values), 2),
                "min": round(min(values), 2), "max": round(max(values), 2)}

    return {
        "kind": "brewtanist-oem-mobile-lab-repeatability",
        "sample_count": len(samples),
        "url": "https://brewtanist.github.io/oem/",
        "device": "mobile",
        "lighthouse_version": samples[0]["audit"],
        "score_0_to_100": stats(performance),
        "lab_metrics": {
            key: stats([s.get("lab_metrics", {}).get(key) for s in samples])
            for key in METRICS
        },
        "runner_benchmark_index": stats([s.get("runner_benchmark_index") for s in samples]),
        "TBT_spread_ms": round(spread, 2),
        "performance_score_spread": round(score_spread, 2),
        "lab_variability_flag": unstable,
        "recommendation": (
            "Investigate repeatability and runner noise before changing production code."
            if unstable else
            "No large spread in this run; continue weekly monitoring and compare field data when available."
        ),
        "production_code_changed": False,
        "field_core_web_vitals_measured": False,
        "interpretation": "Lighthouse simulated lab runs only; not real-user Core Web Vitals or proof of a regression.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("samples", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize([json.loads(path.read_text(encoding="utf-8")) for path in args.samples])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as file:
            file.write("## OEM mobile Lighthouse repeatability (lab only)\n\n")
            file.write(f"Samples: {result['sample_count']}; "
                       f"median Performance: {result['score_0_to_100']['median']}/100; "
                       f"median TBT: {result['lab_metrics']['TBT_ms']['median']} ms; "
                       f"TBT spread: {result['TBT_spread_ms']} ms.\n\n")
            file.write(f"Lab variability flagged: **{result['lab_variability_flag']}**. "
                       + result["recommendation"] + "\n\n")
            file.write("These are not field Core Web Vitals or proof of a user-facing regression.\n")


if __name__ == "__main__":
    main()
