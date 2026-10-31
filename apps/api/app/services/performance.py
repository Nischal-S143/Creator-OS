"""Performance comparison done entirely in code, so every figure shown is measured and not invented by AI."""

from statistics import median

METRICS = ("views", "reach", "likes", "comments", "shares", "saves")
MIN_SAMPLE = 3


def compare_to_baseline(current: dict, others: list[dict]) -> dict:
    """Compares one post's results with the brand's other posts at the same review window."""
    metrics = {}
    for name in METRICS:
        value = current.get(name)
        if value is None:
            continue
        history = [item[name] for item in others if item.get(name) is not None]
        baseline = median(history) if history else None
        metrics[name] = {
            "value": value,
            "baseline_median": baseline,
            "ratio_to_baseline": round(value / baseline, 2) if baseline else None,
            "sample_size": len(history),
        }
    sample = max((item["sample_size"] for item in metrics.values()), default=0)
    return {
        "metrics": metrics,
        "sample_size": sample,
        "verdict": "compared" if sample >= MIN_SAMPLE else "insufficient_data",
    }
