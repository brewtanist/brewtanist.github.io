"""Offline fixtures for the OEM mobile Lighthouse repeatability report."""
from copy import deepcopy
from summarize_performance_samples import summarize


def sample(n, tbt, score, bench=2500):
    return {
        "audit": "Lighthouse 13.6.0",
        "sample_number": n,
        "url": "https://brewtanist.github.io/oem/",
        "device": "mobile",
        "field_core_web_vitals_measured": False,
        "runner_benchmark_index": bench,
        "scores_0_to_100": {
            "performance": score, "accessibility": 100,
            "best-practices": 100, "seo": 100
        },
        "lab_metrics": {"TBT_ms": tbt, "LCP_ms": 950, "CLS": 0,
                        "StyleLayout_ms": 500, "ScriptEvaluation_ms": 50}
    }


def must_fail(rows):
    try:
        summarize(rows)
    except ValueError:
        return
    raise AssertionError("Invalid measurements were accepted")


good = [sample(1, 15, 99), sample(2, 20, 98), sample(3, 24, 99)]
report = summarize(good)
assert report["sample_count"] == 3
assert report["score_0_to_100"]["median"] == 99
assert report["lab_metrics"]["TBT_ms"]["median"] == 20
assert report["lab_variability_flag"] is False
assert report["field_core_web_vitals_measured"] is False
assert report["production_code_changed"] is False

noisy = [sample(1, 25, 99, 2800),
         sample(2, 606, 85, 2150),
         sample(3, 30, 98, 2750)]
report = summarize(noisy)
assert report["lab_variability_flag"] is True
assert report["TBT_spread_ms"] == 581
assert report["lab_metrics"]["TBT_ms"]["median"] == 30
assert report["score_0_to_100"]["median"] == 98

must_fail(good[:2])
for field, invalid in [
    ("url", "https://example.invalid/oem/"),
    ("device", "desktop"),
    ("audit", "Different version"),
    ("sample_number", 1),
    ("field_core_web_vitals_measured", True),
]:
    changed = deepcopy(good)
    changed[2][field] = invalid
    must_fail(changed)
changed = deepcopy(good)
changed[0]["lab_metrics"]["TBT_ms"] = None
must_fail(changed)
changed = deepcopy(good)
changed[0]["scores_0_to_100"]["performance"] = float("nan")
must_fail(changed)
print("PASS: Lighthouse repeated-sample stats and safety fixtures")
