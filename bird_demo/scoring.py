"""Score a Predicted SQL against the Ground-truth SQL, the way BIRD's official evaluation does."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from bird_demo.runner import TIMEOUT_S, RunResult, Rows, SqlError, Timeout, run


class Verdict(StrEnum):
    MATCH = "Match"
    MISMATCH = "Mismatch"
    SQL_ERROR = "SQL error"
    TIMEOUT = "Timeout"
    NO_SQL = "No SQL in reply"


class GroundTruthError(RuntimeError):
    """The Ground-truth SQL failed. Never a Verdict: after the Subset assert it means a broken setup."""


@dataclass(frozen=True)
class ScoredRun:
    verdict: Verdict
    predicted: RunResult | None
    ground_truth: Rows
    only_in_predicted: int = 0
    only_in_ground_truth: int = 0
    note: str = ""  # one-line reason shown next to the Verdict


def score(db_path: Path | str, predicted_sql: str | None, ground_truth_sql: str, timeout_s: float = TIMEOUT_S) -> ScoredRun:
    """Run both SQLs and give the Verdict. `predicted_sql=None` means extract_sql found none.

    Verdicts are checked in order: No SQL in reply, SQL error, Timeout, Match, Mismatch.
    """
    ground_truth = run(db_path, ground_truth_sql, timeout_s)
    if not isinstance(ground_truth, Rows):
        raise GroundTruthError(f"Ground-truth SQL failed on {db_path}: {ground_truth}")
    if predicted_sql is None:
        return ScoredRun(Verdict.NO_SQL, None, ground_truth)

    predicted = run(db_path, predicted_sql, timeout_s)
    if isinstance(predicted, SqlError):
        return ScoredRun(Verdict.SQL_ERROR, predicted, ground_truth, note=predicted.message)
    if isinstance(predicted, Timeout):
        return ScoredRun(Verdict.TIMEOUT, predicted, ground_truth, note=f"ran past {predicted.timeout_s:g} s")

    # BIRD's rule: compare as sets, so row order and duplicate rows don't count.
    pred_set, gt_set = set(predicted.rows), set(ground_truth.rows)
    if pred_set == gt_set:
        return ScoredRun(Verdict.MATCH, predicted, ground_truth)
    pred_cols, gt_cols = len(predicted.columns), len(ground_truth.columns)
    return ScoredRun(
        verdict=Verdict.MISMATCH,
        predicted=predicted,
        ground_truth=ground_truth,
        only_in_predicted=len(pred_set - gt_set),
        only_in_ground_truth=len(gt_set - pred_set),
        note=f"column count differs ({pred_cols} vs {gt_cols})" if pred_cols != gt_cols else "",
    )
