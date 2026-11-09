"""Derive expected rows for Development groups using independent Python oracles."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from bird_vn_benchmark.intent_oracles import DEV_ORACLES
from bird_demo.data import ROOT
from bird_demo.benchmark.registry import sha256_file

ORACLE_METHODS = {
    "ERP-EF-01": "Scan SALES_ORDERS; retain CONFIRMED and project order identifiers/customer/date/status.",
    "ERP-GB-03": "Scan confirmed orders, map nullable sales_rep_id to employee name in Python, and count orders by rep bucket.",
    "ERP-JN-02": "Scan order/line/product tables and join by keys; retain lines whose parent order is CONFIRMED.",
    "ERP-TM-02": "Parse delivered UTC instants, apply the Ho Chi Minh 2025 half-open interval, convert to UTC+7 date, and count shipments by day.",
    "ERP-RK-02": "Sum confirmed order-line milli-quantity by product within each base_unit; calculate competition rank per unit and retain all rank <= 3.",
    "WMS-EF-01": "Scan inventory documents and retain POSTED status at document grain.",
    "WMS-EF-02": "Scan products and retain base_unit KG, preserving product/category fields.",
    "WMS-AG-02": "Scan posted SHIPMENT links; sum negative movement magnitudes for KG products only.",
    "WMS-CD-02": "Sum planned lines per document/product; executed is zero unless POSTED; TRANSFER uses SOURCE once, other types sum absolute movement under the approved direction rules.",
    "WMS-JN-04": "Scan posted transfer document/line/movement links and retain both SOURCE and DESTINATION leg identities and signed quantities.",
}


def main() -> None:
    source_path = ROOT / "benchmark_data/authoring/dataset.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    groups = {group["group_id"]: group for group in source["groups"]}
    expectations = []
    for intent_id, oracle in DEV_ORACLES.items():
        group = groups[intent_id]
        db_path = ROOT / "benchmark_data/physical" / f"{group['db_id']}.sqlite"
        rows = oracle(db_path)
        encoded = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        expectations.append({
            "group_id": intent_id,
            "database_sha256": sha256_file(db_path),
            "expected_rows": rows,
            "expected_rows_sha256": hashlib.sha256(encoded).hexdigest(),
            "row_count_before_set_comparison": len(rows),
            "oracle_id": f"bird_vn_benchmark.intent_oracles:{oracle.__name__}",
            "oracle_method": ORACLE_METHODS[intent_id] + " Candidate SQL is not imported or executed by the oracle.",
            "derived_before_canonical_sql_execution": True,
        })
    artifact = {
        "artifact_version": 1,
        "benchmark_version": source["benchmark_version"],
        "derived_at_utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "source_registry_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "source_oracle_sha256": sha256_file(ROOT / "bird_vn_benchmark/intent_oracles.py"),
        "scope": "10 proposed Development groups only; not a final or human-approved gold output",
        "expected_outputs": expectations,
    }
    out = ROOT / "benchmark_data/authoring/expected_outputs_dev.json"
    out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Derived {len(expectations)} independent Development outputs before canonical SQL execution: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
