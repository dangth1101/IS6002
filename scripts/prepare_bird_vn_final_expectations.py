"""Derive Final expected outputs from independent Python table-scan oracles.

This script never reads or executes canonical SQL. Run it before the separate
Final SQL comparison script so expected rows are frozen first.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from bird_demo.data import ROOT
from bird_demo.benchmark.registry import sha256_file
from bird_vn_benchmark.final_oracles import FINAL_ORACLES


def digest_rows(rows: list[list[object]]) -> str:
    payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def digest_card(card: dict) -> str:
    payload = json.dumps(card, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    registry_path = ROOT / "benchmark_data/authoring/dataset.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    groups = {group["group_id"]: group for group in registry["groups"] if group["split"] == "final"}
    if set(groups) != set(FINAL_ORACLES):
        raise SystemExit(f"Final oracle coverage mismatch: missing={sorted(set(groups)-set(FINAL_ORACLES))}; extra={sorted(set(FINAL_ORACLES)-set(groups))}")
    expected = []
    for group_id, oracle in FINAL_ORACLES.items():
        group = groups[group_id]
        db_path = ROOT / "benchmark_data/physical" / f"{group['db_id']}.sqlite"
        rows = oracle(db_path)
        expected.append({
            "group_id": group_id,
            "split": "final",
            "database_sha256": sha256_file(db_path),
            "intent_card_sha256": digest_card(group["card_fields"]),
            "canonical_sql_sha256_at_derivation": hashlib.sha256(group["canonical_sql_draft"].encode("utf-8")).hexdigest(),
            "expected_rows": rows,
            "expected_rows_sha256": digest_rows(rows),
            "row_count_before_set_comparison": len(rows),
            "oracle_id": f"bird_vn_benchmark.final_oracles:{oracle.__name__}",
            "oracle_method": f"Independent Python table scan implementing the recorded Final Intent Card; candidate SQL was not imported, parsed, or executed. See {oracle.__module__}.{oracle.__name__}.",
            "derived_before_sql_execution": True,
            "human_review_status": "NEEDS_HUMAN_REVIEW",
        })
    artifact = {
        "artifact_version": 1,
        "benchmark_version": registry["benchmark_version"],
        "registry_revision_at_derivation": registry.get("authoring_revision"),
        "source_registry_sha256": sha256_file(registry_path),
        "source_oracle_sha256": sha256_file(ROOT / "bird_vn_benchmark/final_oracles.py"),
        "shared_table_reader_sha256": sha256_file(ROOT / "bird_vn_benchmark/intent_oracles.py"),
        "derived_at_utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "scope": "40 Final groups; independent expected outputs only; no approval, tuning, or official evaluation",
        "expected_outputs": expected,
    }
    out = ROOT / "benchmark_data/authoring/expected_outputs_final.json"
    out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Derived {len(expected)} Final outputs from independent Python oracles before candidate SQL execution: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
