"""Read-only static/registry audit for BIRD-VN authoring drafts.

Candidate SQL is passed to SQLite's EXPLAIN QUERY PLAN only; result rows are
not fetched from the frozen snapshots before independent expected outputs exist.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from bird_demo.data import ROOT
from bird_demo.benchmark.registry import load_registry, sha256_file

AUTHORING = ROOT / "benchmark_data/authoring"
PHYSICAL = ROOT / "benchmark_data/physical"


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[\w]+", text.casefold()))


def jaccard(a: str, b: str) -> float:
    left, right = tokens(a), tokens(b)
    return len(left & right) / len(left | right) if left | right else 1.0


def jaccard_tokens(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left | right else 1.0


def main() -> None:
    path = AUTHORING / "dataset.json"
    registry = load_registry(path, allow_draft=True)
    groups = registry["groups"]
    questions = registry["questions"]
    group_counts = Counter(g["competency"] for g in groups)
    complexity_counts = Counter((g["db_id"], g["complexity"]) for g in groups)
    split_domain = Counter((g["split"], g["db_id"]) for g in groups)
    taxonomy = Counter(q["variant_type"] for q in questions if q["q_index"] > 0)
    checks: dict[str, object] = {
        "registry_counts": {"groups": len(groups), "questions": len(questions), "dev_questions": sum(q["split"] == "development" for q in questions)},
        "competency_counts": dict(group_counts),
        "complexity_counts": {f"{domain}/{level}": count for (domain, level), count in complexity_counts.items()},
        "split_domain_counts": {f"{split}/{domain}": count for (split, domain), count in split_domain.items()},
        "taxonomy_variant_counts": dict(taxonomy),
        "question_text_unique": len({q["question"].casefold() for q in questions}) == len(questions),
        "static_sql": {},
        "near_duplicate_candidates": [],
        "variant_slot_inheritance": "PASS structurally; natural-language equivalence requires human review",
        "database_hashes": {},
    }
    for db_id in ("erp_sales", "wms_inventory"):
        db = PHYSICAL / f"{db_id}.sqlite"
        schema = PHYSICAL / f"schema_{db_id}.sql"
        checks["database_hashes"][db_id] = {"database": sha256_file(db), "schema": sha256_file(schema)}
    for group in groups:
        db_id = group["db_id"]
        db_path = PHYSICAL / f"{db_id}.sqlite"
        sql = group["canonical_sql_draft"]
        uri = db_path.resolve().as_uri() + "?mode=ro"
        try:
            with sqlite3.connect(uri, uri=True) as conn:
                conn.execute("EXPLAIN QUERY PLAN " + sql).fetchall()
            result = {"status": "PASS", "message": "SQLite prepare/plan only; candidate rows not executed"}
        except sqlite3.Error as error:
            result = {"status": "FAIL", "message": str(error)}
        checks["static_sql"][group["group_id"]] = result
    by_group = {g["group_id"]: sorted((q for q in questions if q["group_id"] == g["group_id"]), key=lambda q: q["q_index"]) for g in groups}
    near = []
    for gid, qitems in by_group.items():
        for q in qitems[1:]:
            similarity = jaccard(qitems[0]["question"], q["question"])
            if similarity >= 0.78:
                near.append({"scope": "within_group_variant", "left": qitems[0]["question_id"], "right": q["question_id"], "jaccard": round(similarity, 4)})
    question_tokens = {item["question_id"]: tokens(item["question"]) for item in questions}
    for index, left in enumerate(questions):
        for right in questions[index + 1:]:
            if left["group_id"] == right["group_id"]:
                continue
            similarity = jaccard_tokens(question_tokens[left["question_id"]], question_tokens[right["question_id"]])
            if similarity >= 0.72:
                near.append({"scope": "between_groups", "left": left["question_id"], "right": right["question_id"],
                             "left_split": left["split"], "right_split": right["split"],
                             "jaccard": round(similarity, 4)})
    checks["near_duplicate_candidates"] = near
    checks["static_sql_summary"] = {
        "pass": sum(item["status"] == "PASS" for item in checks["static_sql"].values()),
        "fail": sum(item["status"] == "FAIL" for item in checks["static_sql"].values()),
        "rows_executed": False,
    }
    checks["created_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (AUTHORING / "draft_validation.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")

    audit = (ROOT / "docs/benchmark/intent_cards/COVERAGE_AUDIT.md").read_text(encoding="utf-8")
    card_rows = [line for line in audit.splitlines() if line.startswith(("| ERP-", "| WMS-")) and line.rstrip().endswith(("SUPPORTED |", "NEEDS FIXTURE |", "BLOCKED |"))]
    defects = []
    for line in card_rows:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells[-1] == "NEEDS FIXTURE":
            defects.append({"intent_id": cells[0], "status": "OPEN", "coverage_status": cells[-1], "snapshot_evidence": cells[1], "gap": cells[3], "fixture_proposal": "Prepare an isolated test fixture in a temporary copy; preserve both frozen snapshots.", "human_review": "NEEDS_HUMAN_REVIEW"})
    (AUTHORING / "defect_report.json").write_text(json.dumps({"snapshot_immutable": True, "open_defect_count": len(defects), "defects": defects}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(checks["static_sql_summary"], ensure_ascii=False))
    print(f"Near-duplicate candidates flagged: {len(near)}; fixture defects: {len(defects)}")


if __name__ == "__main__":
    main()
