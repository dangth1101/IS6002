"""Compare Final SQL candidates with previously frozen independent Python outputs."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone

from bird_demo.benchmark.dashboard import read_only_query
from bird_demo.benchmark.metrics import result_equal
from bird_demo.benchmark.registry import sha256_file
from bird_demo.data import ROOT
from bird_demo.runner import Rows, SqlError, Timeout


def digest_rows(rows: list[list[object]]) -> str:
    normalized = [list(row) for row in sorted(set(map(tuple, rows)), key=repr)]
    payload = json.dumps(normalized, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    registry_path = ROOT / "benchmark_data/authoring/dataset.json"
    expected_path = ROOT / "benchmark_data/authoring/expected_outputs_final.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    expected_doc = json.loads(expected_path.read_text(encoding="utf-8"))
    if expected_doc.get("source_registry_sha256") != sha256_file(registry_path):
        raise SystemExit("Final expected outputs do not match the current registry source; re-derive only after confirming cards and SQL revisions.")
    groups = {g["group_id"]: g for g in registry["groups"]}
    results = []
    for expected in expected_doc["expected_outputs"]:
        gid = expected["group_id"]
        group = groups[gid]
        db_path = ROOT / "benchmark_data/physical" / f"{group['db_id']}.sqlite"
        if sha256_file(db_path) != expected["database_sha256"]:
            raise SystemExit(f"Snapshot hash changed after expected output derivation: {gid}")
        result = read_only_query(group["db_id"], group["canonical_sql_draft"])
        if isinstance(result, dict):
            outcome = result["result"]
            actual_rows = [list(row) for row in outcome.rows]
            matches = result_equal(actual_rows, expected["expected_rows"])
            status = "NEEDS_HUMAN_REVIEW" if matches else "BLOCKED_SQL_OR_INTENT_MISMATCH"
            error = None if matches else "Candidate SQL output differs from the frozen independent Python oracle."
            actual_columns = list(outcome.columns)
            actual_hash = digest_rows(actual_rows)
        elif isinstance(result, Timeout):
            actual_rows, actual_columns, actual_hash = None, None, None
            matches, status, error = None, "BLOCKED_SQL_TIMEOUT", f"timeout after {result.timeout_s}s"
        elif isinstance(result, SqlError):
            actual_rows, actual_columns, actual_hash = None, None, None
            matches, status, error = None, "BLOCKED_SQL_ERROR", result.message
        else:
            actual_rows, actual_columns, actual_hash = None, None, None
            matches, status, error = None, "BLOCKED_UNKNOWN_RUNNER_RESULT", "Unknown SQL runner result."
        issues = []
        if gid == "WMS-AG-04":
            issues.append("Intent Card requires balances as of 2025-04-01 UTC, but canonical SQL has no posted_at_utc cutoff.")
        elif gid in {"WMS-RK-01", "WMS-RK-03"}:
            issues.append("Intent Card requires an as-of snapshot cutoff, but canonical SQL has no posted_at_utc cutoff.")
        elif gid == "WMS-RK-02":
            issues.append("Intent Card excludes suppliers with zero receipts, but canonical SQL starts from all suppliers and can include zero-count rows.")
        elif gid == "WMS-CD-01":
            issues.append("Intent Card mentions a fixed time window but records no boundaries; canonical SQL has no time predicate.")
        if issues and status == "NEEDS_HUMAN_REVIEW":
            status = "BLOCKED_INTENT_SQL_ALIGNMENT_REVIEW"
        results.append({
            "group_id": gid,
            "split": "final",
            "database_sha256": expected["database_sha256"],
            "canonical_sql_sha256": expected["canonical_sql_sha256_at_derivation"],
            "expected_rows_sha256": expected["expected_rows_sha256"],
            "actual_rows_sha256": actual_hash,
            "expected_row_count": expected["row_count_before_set_comparison"],
            "actual_row_count": len(actual_rows) if actual_rows is not None else None,
            "expected_columns_count": len(expected["expected_rows"][0]) if expected["expected_rows"] else None,
            "actual_columns": actual_columns,
            "rows_match_set_comparator": matches,
            "candidate_sql_executed": True,
            "oracle_id": expected["oracle_id"],
            "status": status,
            "error": error,
            "human_review_status": "NEEDS_HUMAN_REVIEW",
            "known_intent_sql_issues": issues,
            "fixture_status": "NOT_RECORDED",
        })
    counts = Counter(item["status"] for item in results)
    artifact = {
        "artifact_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "registry_sha256": sha256_file(registry_path),
        "expected_outputs_sha256": sha256_file(expected_path),
        "scope": "Offline Final candidate comparison against frozen independent Python outputs; no LLM evaluation or approval",
        "summary": dict(counts),
        "results": results,
    }
    out = ROOT / "benchmark_data/authoring/ground_truth_validation_final.json"
    out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    print(f"Final validation evidence: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
