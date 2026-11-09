"""BIRD-VN metrics over a single replicate of paired question outcomes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Any

SUCCESS = "success"
MODEL_FAILURES = frozenset({"sql_error", "timeout", "no_sql"})
INFRA_FAILURE = "infra_error"
KNOWN_STATUSES = MODEL_FAILURES | {SUCCESS, INFRA_FAILURE}


@dataclass(frozen=True)
class Observation:
    """One model outcome. Infrastructure failures are unknown; model failures score zero."""

    status: str
    rows: Sequence[Sequence[Any]] | None = None
    correct: bool | None = None

    def __post_init__(self) -> None:
        if self.status not in KNOWN_STATUSES:
            raise ValueError(f"Unknown outcome status: {self.status}")
        if self.status == SUCCESS and self.rows is None:
            raise ValueError("Successful execution must carry rows (including an empty list)")
        if self.status == SUCCESS and self.correct is None:
            raise ValueError("Successful model execution must be compared with gold and carry correctness")
        if self.status == INFRA_FAILURE and (self.rows is not None or self.correct is not None):
            raise ValueError("Infrastructure failure has unknown rows and correctness")

    @property
    def outcome_known(self) -> bool:
        return self.status != INFRA_FAILURE

    @property
    def is_correct(self) -> bool | None:
        if self.status == INFRA_FAILURE:
            return None
        if self.correct is not None:
            return self.correct
        return False


@dataclass(frozen=True)
class Rate:
    numerator: int
    denominator: int

    @property
    def percent(self) -> float | None:
        return (100.0 * self.numerator / self.denominator) if self.denominator else None

    def as_dict(self) -> dict[str, int | float | None]:
        return {"numerator": self.numerator, "denominator": self.denominator, "percent": self.percent}


def result_equal(left: Sequence[Sequence[Any]], right: Sequence[Sequence[Any]]) -> bool:
    """BIRD-compatible set comparison: ignore row order and duplicates, preserve tuple column order."""
    if any(len(row) != len(left[0]) for row in left[1:]) or any(len(row) != len(right[0]) for row in right[1:]):
        raise ValueError("Rows in a result set must have a consistent number of columns")
    if left and right and len(left[0]) != len(right[0]):
        return False
    return set(map(tuple, left)) == set(map(tuple, right))


def correctness_rate(observations: Sequence[Observation]) -> Rate:
    eligible = [item for item in observations if item.outcome_known]
    return Rate(sum(item.is_correct is True for item in eligible), len(eligible))


def metric_summary(
    group_ids: Sequence[str],
    question_ids_by_group: Mapping[str, Sequence[str]],
    observations: Mapping[str, Observation],
) -> dict[str, Any]:
    """Compute EX Original/Variants/Overall, RSS, CA, PRA and Robust EX (All).

    Call separately for every replicate. Missing registry outcomes are rejected; an
    explicit infra_error observation is required to distinguish unknown from omitted.
    """
    expected = {question_id for group_id in group_ids for question_id in question_ids_by_group[group_id]}
    if set(observations) != expected:
        missing = sorted(expected - set(observations))
        extra = sorted(set(observations) - expected)
        raise ValueError(f"Outcome registry mismatch: missing={missing[:5]}, extra={extra[:5]}")

    original: list[Observation] = []
    variants: list[Observation] = []
    all_questions: list[Observation] = []
    rss_numerator = rss_denominator = ca_numerator = ca_denominator = 0
    pra_numerator = pra_denominator = 0
    robust_numerator = robust_denominator = 0
    per_group: dict[str, Any] = {}

    for group_id in group_ids:
        qids = list(question_ids_by_group[group_id])
        if len(qids) != 11:
            raise ValueError(f"Group {group_id} has {len(qids)} questions; expected 11")
        q0 = observations[qids[0]]
        qvars = [observations[qid] for qid in qids[1:]]
        original.append(q0)
        variants.extend(qvars)
        all_questions.extend([q0, *qvars])
        gr_n = gr_d = ca_n = ca_d = pra_n = pra_d = 0
        for qi in qvars:
            if not q0.outcome_known or not qi.outcome_known:
                continue
            rss_denominator += 1
            gr_d += 1
            stable = (
                q0.status == SUCCESS
                and qi.status == SUCCESS
                and result_equal(q0.rows or [], qi.rows or [])
            )
            rss_numerator += int(stable)
            gr_n += int(stable)
            ca_d += 1
            ca_n += int(q0.is_correct == qi.is_correct)
            pra_d += 1
            pra_n += int(q0.is_correct is True and qi.is_correct is True)
        ca_numerator += ca_n
        ca_denominator += ca_d
        pra_numerator += pra_n
        pra_denominator += pra_d
        group_known = all(item.outcome_known for item in [q0, *qvars])
        if group_known:
            robust_denominator += 1
            robust_numerator += int(all(item.is_correct is True for item in [q0, *qvars]))
        robust_value = all(item.is_correct is True for item in [q0, *qvars]) if group_known else None
        per_group[group_id] = {
            "rss": Rate(gr_n, gr_d).as_dict(),
            "correctness_agreement": Rate(ca_n, ca_d).as_dict(),
            "pairwise_robust_accuracy": Rate(pra_n, pra_d).as_dict(),
            "rss_pairs_known": gr_d,
            "robust_ex_all": robust_value,
            "complete": group_known,
            "correct": sum(item.is_correct is True for item in [q0, *qvars] if item.outcome_known),
            "known_questions": sum(item.outcome_known for item in [q0, *qvars]),
        }

    return {
        "ex_original": correctness_rate(original).as_dict(),
        "ex_variants": correctness_rate(variants).as_dict(),
        "ex_overall": correctness_rate(all_questions).as_dict(),
        "rss": Rate(rss_numerator, rss_denominator).as_dict(),
        "correctness_agreement": Rate(ca_numerator, ca_denominator).as_dict(),
        "pairwise_robust_accuracy": Rate(pra_numerator, pra_denominator).as_dict(),
        "robust_ex_all": Rate(robust_numerator, robust_denominator).as_dict(),
        "missing_questions": sum(item.status == INFRA_FAILURE for item in observations.values()),
        "per_group": per_group,
    }


def summarize_replicates(summaries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Describe independent replicate metrics without pooling question outcomes."""
    if not summaries:
        raise ValueError("At least one replicate summary is required")
    metric_names = (
        "ex_original", "ex_variants", "ex_overall", "rss",
        "correctness_agreement", "pairwise_robust_accuracy", "robust_ex_all",
    )
    result: dict[str, Any] = {"replicates": len(summaries), "metrics": {}}
    for name in metric_names:
        values = [summary[name]["percent"] for summary in summaries if summary[name]["percent"] is not None]
        result["metrics"][name] = {
            "per_replicate": [summary[name] for summary in summaries],
            "mean_percent": mean(values) if values else None,
            "min_percent": min(values) if values else None,
            "max_percent": max(values) if values else None,
            "population_sd_percent": pstdev(values) if values else None,
        }
    return result
