"""The measured comparison needs no database or AI."""

from app.services.performance import compare_to_baseline


def test_ratio_uses_the_median_of_other_posts():
    others = [{"views": 100}, {"views": 200}, {"views": 10000}]
    result = compare_to_baseline({"views": 400}, others)
    assert result["metrics"]["views"] == {
        "value": 400,
        "baseline_median": 200,
        "ratio_to_baseline": 2.0,
        "sample_size": 3,
    }
    assert result["verdict"] == "compared"


def test_too_few_posts_is_labelled_as_insufficient():
    result = compare_to_baseline({"views": 400}, [{"views": 100}])
    assert result["verdict"] == "insufficient_data" and result["sample_size"] == 1


def test_no_history_gives_no_invented_comparison():
    result = compare_to_baseline({"views": 400}, [])
    assert result["metrics"]["views"]["baseline_median"] is None
    assert result["metrics"]["views"]["ratio_to_baseline"] is None


def test_missing_values_are_not_treated_as_zero():
    result = compare_to_baseline({"views": 400}, [{"likes": 5}, {"views": 200}])
    assert "likes" not in result["metrics"]
    assert result["metrics"]["views"]["sample_size"] == 1


def test_zero_baseline_does_not_crash():
    result = compare_to_baseline({"saves": 5}, [{"saves": 0}, {"saves": 0}, {"saves": 0}])
    assert result["metrics"]["saves"]["ratio_to_baseline"] is None
