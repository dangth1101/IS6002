import pytest

from bird_demo.benchmark.metrics import INFRA_FAILURE, SUCCESS, Observation, metric_summary, result_equal, summarize_replicates


def test_bird_comparator_ignores_row_order_and_duplicates_but_keeps_column_order():
    assert result_equal([(1,), (2,), (2,)], [(2,), (1,)])
    assert not result_equal([(1, 2)], [(2, 1)])
    assert result_equal([], [])


def test_bird_comparator_rejects_inconsistent_row_widths():
    with pytest.raises(ValueError, match="consistent number of columns"):
        result_equal([(1,), (1, 2)], [(1,)])


def test_rss_can_be_one_for_same_wrong_results_while_correctness_is_zero():
    observations = {"q0": Observation(SUCCESS, [(8,)], correct=False)}
    observations.update({f"q{i}": Observation(SUCCESS, [(8,)], correct=False) for i in range(1, 11)})
    result = metric_summary(["g"], {"g": [f"q{i}" for i in range(11)]}, observations)
    assert result["rss"] == {"numerator": 10, "denominator": 10, "percent": 100.0}
    assert result["correctness_agreement"]["percent"] == 100.0
    assert result["pairwise_robust_accuracy"]["percent"] == 0.0
    assert result["robust_ex_all"]["percent"] == 0.0


@pytest.mark.parametrize("failure", ["sql_error", "timeout", "no_sql"])
def test_model_failure_is_known_zero_and_stability_zero(failure):
    observations = {"q0": Observation(SUCCESS, [], correct=True)}
    observations.update({f"q{i}": Observation(failure, correct=False) for i in range(1, 11)})
    result = metric_summary(["g"], {"g": [f"q{i}" for i in range(11)]}, observations)
    assert result["rss"]["numerator"] == 0
    assert result["rss"]["denominator"] == 10
    assert result["ex_variants"]["numerator"] == 0
    assert result["ex_variants"]["denominator"] == 10


def test_infrastructure_failure_is_excluded_and_makes_group_incomplete():
    observations = {"q0": Observation(INFRA_FAILURE)}
    observations.update({f"q{i}": Observation(SUCCESS, [(i,)], correct=True) for i in range(1, 11)})
    result = metric_summary(["g"], {"g": [f"q{i}" for i in range(11)]}, observations)
    assert result["ex_original"]["denominator"] == 0
    assert result["rss"]["denominator"] == 0
    assert result["robust_ex_all"]["denominator"] == 0
    assert result["missing_questions"] == 1
    assert result["per_group"]["g"]["robust_ex_all"] is None


def test_result_stability_requires_both_queries_to_succeed_even_for_empty_rows():
    observations = {"q0": Observation(SUCCESS, [], correct=True)}
    observations.update({f"q{i}": Observation("sql_error", correct=False) for i in range(1, 11)})
    result = metric_summary(["g"], {"g": [f"q{i}" for i in range(11)]}, observations)
    assert result["rss"] == {"numerator": 0, "denominator": 10, "percent": 0.0}


def test_question_coverage_must_be_explicit():
    with pytest.raises(ValueError, match="registry mismatch"):
        metric_summary(["g"], {"g": [f"q{i}" for i in range(11)]}, {})


def test_replicates_are_summarized_independently_without_pooling():
    all_correct = {f"q{i}": Observation(SUCCESS, [(1,)], correct=True) for i in range(11)}
    all_wrong = {f"q{i}": Observation(SUCCESS, [(2,)], correct=False) for i in range(11)}
    qids = {"g": [f"q{i}" for i in range(11)]}
    summaries = [metric_summary(["g"], qids, all_correct), metric_summary(["g"], qids, all_wrong)]
    result = summarize_replicates(summaries)
    assert result["replicates"] == 2
    assert result["metrics"]["ex_overall"]["mean_percent"] == 50.0
    assert [item["numerator"] for item in result["metrics"]["ex_overall"]["per_replicate"]] == [11, 0]
