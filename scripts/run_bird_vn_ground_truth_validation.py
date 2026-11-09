"""Compare candidate SQL for Development groups against prior Python-oracle outputs."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone

from bird_demo.benchmark.registry import sha256_file
from bird_demo.data import ROOT
from bird_demo.runner import Rows, SqlError, Timeout, run


def row_hash(rows: list[list[object]]) -> str:
    normalized = [list(row) for row in sorted(set(map(tuple, rows)), key=repr)]
    payload = json.dumps(normalized, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    source_path = ROOT / "benchmark_data/authoring/dataset.json"
    expected_path = ROOT / "benchmark_data/authoring/expected_outputs_dev.json"
    validation_path = ROOT / "benchmark_data/authoring/validation_records.json"
    registry = json.loads(source_path.read_text(encoding="utf-8"))
    expectations = json.loads(expected_path.read_text(encoding="utf-8"))
    expected_by_group = {item["group_id"]: item for item in expectations["expected_outputs"]}
    group_by_id = {item["group_id"]: item for item in registry["groups"]}
    validation_records = {item["group_id"]: item for item in json.loads(validation_path.read_text(encoding="utf-8"))}
    audit_path = ROOT / "docs/benchmark/intent_cards/COVERAGE_AUDIT.md"
    coverage: dict[str, str] = {}
    for line in audit_path.read_text(encoding="utf-8").splitlines():
        if line.startswith(("| ERP-", "| WMS-")):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) >= 5 and cells[-1] in {"SUPPORTED", "NEEDS FIXTURE", "BLOCKED"}:
                coverage[cells[0]] = cells[-1]

    results = []
    fixture_path = ROOT / "benchmark_data/authoring/dev_fixture_validation.json"
    fixture_doc = json.loads(fixture_path.read_text(encoding="utf-8")) if fixture_path.exists() else {"results": []}
    fixture_by_group = {item["group_id"]: item for item in fixture_doc.get("results", [])}
    for group_id, expected in expected_by_group.items():
        group = group_by_id[group_id]
        db_path = ROOT / "benchmark_data/physical" / f"{group['db_id']}.sqlite"
        actual_db_hash = sha256_file(db_path)
        if actual_db_hash != expected["database_sha256"]:
            raise RuntimeError(f"Frozen snapshot hash changed for {group_id}; expected output is stale")
        if not expected["derived_before_canonical_sql_execution"]:
            raise RuntimeError(f"Expected output for {group_id} was not recorded before SQL execution")
        sql = group["canonical_sql_draft"]
        sql_hash = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        if sql_hash != group["canonical_sql_sha256"]:
            raise RuntimeError(f"SQL candidate hash mismatch for {group_id}")
        observed = run(db_path, sql)
        business_rule_checks: dict[str, bool] = {}
        if isinstance(observed, Timeout):
            status, actual_rows, error = "BLOCKED", None, f"timeout at {observed.timeout_s}s"
        elif isinstance(observed, SqlError):
            status, actual_rows, error = "BLOCKED", None, observed.message
        elif isinstance(observed, Rows):
            actual_rows = [list(row) for row in observed.rows]
            equal = set(map(tuple, actual_rows)) == set(map(tuple, expected["expected_rows"]))
            if group_id == "ERP-RK-02":
                business_rule_checks = {
                    "all_base_units_ranked": {row[3] for row in actual_rows} == {"EA", "KG", "L"},
                    "no_rank_beyond_three": all(row[5] <= 3 for row in actual_rows),
                }
            elif group_id == "WMS-CD-02":
                transfer_rows = [row for row in actual_rows if row[2] == "TRANSFER"]
                posted_rows = [row for row in actual_rows if row[3] == "POSTED"]
                nonposted_rows = [row for row in actual_rows if row[3] != "POSTED"]
                business_rule_checks = {
                    "all_statuses_present": {row[3] for row in actual_rows} == {"DRAFT", "POSTED", "CANCELLED"},
                    "nonposted_executed_zero": all(row[7] == 0 for row in nonposted_rows),
                    "posted_matches_movement_invariant": all(row[6] == row[7] for row in posted_rows),
                    "transfer_source_once_matches_planned": bool(transfer_rows)
                    and all(row[6] == row[7] for row in transfer_rows),
                }
            rules_pass = all(business_rule_checks.values())
            if not equal:
                status, error = "BLOCKED", "candidate result differs from independent Python oracle"
            elif not rules_pass:
                status, error = "BLOCKED", f"candidate output violates business-rule assertions: {business_rule_checks}"
            elif coverage.get(group_id) == "SUPPORTED" and (
                group_id not in fixture_by_group or fixture_by_group[group_id].get("status") == "PASS"
            ):
                status, error = "VALIDATED_BY_AUTOMATION", None
            else:
                status, error = "NEEDS_HUMAN_REVIEW", "snapshot rows match oracle, but fixture evidence is missing or did not pass"
        else:
            status, actual_rows, error = "BLOCKED", None, "unknown runner outcome"
        record = {
            "group_id": group_id,
            "database_sha256": actual_db_hash,
            "canonical_sql_sha256": sql_hash,
            "expected_rows_sha256": expected["expected_rows_sha256"],
            "actual_rows_sha256": row_hash(actual_rows) if actual_rows is not None else None,
            "actual_row_count_before_set_comparison": len(actual_rows) if actual_rows is not None else None,
            "actual_rows": actual_rows,
            "business_rule_checks": business_rule_checks,
            "python_oracle_id": expected["oracle_id"],
            "coverage_audit": coverage.get(group_id, "BLOCKED"),
            "status": status,
            "error": error,
        }
        results.append(record)
        validation_record = validation_records[group_id]
        questions = sorted((item for item in registry["questions"] if item["group_id"] == group_id),
                           key=lambda item: item["q_index"])
        validation_record["semantic_slots"] = group["card_fields"]
        validation_record["canonical_sql_candidate"] = sql
        validation_record["expected_outputs"] = {
            "path": str(expected_path.relative_to(ROOT)),
            "sha256": expected["expected_rows_sha256"],
            "row_count": expected["row_count_before_set_comparison"],
            "oracle_id": expected["oracle_id"],
            "derivation": expected["oracle_method"],
            "database_sha256": expected["database_sha256"],
            "derived_before_sql_execution": expected["derived_before_canonical_sql_execution"],
        }
        validation_record["expected_outputs_derived_before_sql"] = True
        validation_record["alternative_check"] = {"type": "PYTHON_ORACLE", "id": expected["oracle_id"], "source_sha256": expectations["source_oracle_sha256"]}
        validation_record["execution_evidence"] = {"database_sha256": actual_db_hash, "sql_sha256": sql_hash,
                                                    "actual_rows_sha256": record["actual_rows_sha256"], "status": status,
                                                    "row_count": record["actual_row_count_before_set_comparison"],
                                                    "business_rule_checks": business_rule_checks}
        validation_record["machine_validation_status"] = status
        validation_record["ground_truth_status"] = "NEEDS_HUMAN_REVIEW" if status != "BLOCKED" else "BLOCKED"
        validation_record["human_review_status"] = "NEEDS_HUMAN_REVIEW"
        validation_record["question_reviews"] = [
            {"question_id": question["question_id"], "question": question["question"],
             "q_index": question["q_index"], "role": question["role"],
             "variant_type": question["variant_type"],
             "semantic_slots_inherited": question.get("semantic_slots_inherited", False),
             "review_status": "NEEDS_HUMAN_REVIEW", "owner_decision": None}
            for question in questions
        ]
        fixture_evidence = fixture_by_group.get(group_id)
        validation_record["fixture_validation"] = (
            {"path": str(fixture_path.relative_to(ROOT)), "status": fixture_evidence["status"],
             "row_count": fixture_evidence["row_count"],
             "expected_rows_sha256": fixture_evidence["expected_rows_sha256"],
             "actual_rows_sha256": fixture_evidence["actual_rows_sha256"],
             "checks": fixture_evidence["checks"]}
            if fixture_evidence else None
        )
        validation_record["outstanding_issues"] = [
            "Benchmark Owner must review and decide Intent Card, canonical SQL and Q0–Q10; automation is not approval."
        ]
        if fixture_evidence and fixture_evidence.get("status") != "PASS":
            validation_record["outstanding_issues"].append("Development temporary fixture validation did not pass.")
        validation_record["owner_approval"] = {"status": "PENDING", "approver": None, "date": None, "rationale": None}

    for group_id, record in validation_records.items():
        if group_id not in expected_by_group:
            record["machine_validation_status"] = "BLOCKED"
            record["ground_truth_status"] = "BLOCKED"
            record["blocker"] = "No independent expected output/oracle artifact yet; do not execute candidate SQL on frozen snapshot."
    validation_path.write_text(json.dumps(list(validation_records.values()), ensure_ascii=False, indent=2), encoding="utf-8")
    all_statuses = Counter(record.get("machine_validation_status", "BLOCKED") for record in validation_records.values())
    output = {
        "artifact_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "expected_outputs_sha256": sha256_file(expected_path),
        "validation_records_sha256": sha256_file(validation_path),
        "scope": "Development only; SQL candidates compared after expected outputs were frozen",
        "summary": {status: sum(item["status"] == status for item in results) for status in ("VALIDATED_BY_AUTOMATION", "NEEDS_HUMAN_REVIEW", "BLOCKED")},
        "all_group_status_summary": {status: all_statuses.get(status, 0) for status in ("VALIDATED_BY_AUTOMATION", "NEEDS_HUMAN_REVIEW", "BLOCKED")},
        "results": results,
    }
    out = ROOT / "benchmark_data/authoring/ground_truth_validation.json"
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output["summary"], ensure_ascii=False))
    print(f"Validation evidence: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
