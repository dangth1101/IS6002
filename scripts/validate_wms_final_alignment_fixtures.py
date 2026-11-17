"""Validate WMS Final time boundaries and zero-receipt exclusion on temp copies."""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from typing import Any

from bird_demo.benchmark.metrics import result_equal
from bird_demo.benchmark.registry import sha256_file
from bird_demo.data import ROOT
from bird_vn_benchmark.final_oracles import FINAL_ORACLES

TARGETS = ("WMS-AG-04", "WMS-RK-01", "WMS-RK-02", "WMS-RK-03", "WMS-CD-01")
PHYSICAL = ROOT / "benchmark_data/physical"
ARTIFACTS = ROOT / "benchmark_data/authoring"


def digest_rows(rows: list[list[Any]]) -> str:
    normalized = [list(row) for row in sorted(set(map(tuple, rows)), key=repr)]
    return hashlib.sha256(json.dumps(normalized, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def add_posted_movement(db: Path, *, kind: str, at: str, qty: int, tag: str) -> None:
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        doc_id = conn.execute("SELECT COALESCE(MAX(document_id),0)+1 FROM INVENTORY_DOCUMENTS").fetchone()[0]
        line_id = conn.execute("SELECT COALESCE(MAX(document_line_id),0)+1 FROM INVENTORY_DOCUMENT_LINES").fetchone()[0]
        move_id = conn.execute("SELECT COALESCE(MAX(movement_id),0)+1 FROM INVENTORY_MOVEMENTS").fetchone()[0]
        seq = conn.execute("SELECT COALESCE(MAX(posting_seq),0)+1 FROM INVENTORY_DOCUMENTS").fetchone()[0]
        if kind == "RECEIPT":
            supplier_id, customer_id, warehouse_id = 1, None, 1
            role, location_id = "MAIN", 1
        else:
            supplier_id, customer_id, warehouse_id = None, 1, 1
            role, location_id = "MAIN", 1
        created = "2025-01-01T00:00:00.000Z"
        business_day = at[:10]
        conn.execute(
            "INSERT INTO INVENTORY_DOCUMENTS VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (doc_id, f"WMS-FIX-{tag}-{doc_id}", kind, "POSTED", supplier_id, customer_id,
             warehouse_id, None, None, business_day, created, at, seq),
        )
        product_id = conn.execute("SELECT product_id FROM PRODUCTS WHERE sku='W-SKU-001'").fetchone()[0]
        conn.execute("INSERT INTO INVENTORY_DOCUMENT_LINES VALUES (?,?,?,?,?)", (line_id, doc_id, 1, product_id, abs(qty)))
        conn.execute(
            "INSERT INTO INVENTORY_MOVEMENTS VALUES (?,?,?,?,?,?,?,?)",
            (move_id, line_id, 1, role, f"WMS-FIX-{tag}-{move_id}", location_id, qty, at),
        )
        conn.commit()
        if conn.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError(f"FK check failed for temporary fixture {tag}")


def add_zero_receipt_supplier(db: Path) -> int:
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        supplier_id = conn.execute("SELECT COALESCE(MAX(supplier_id),0)+1 FROM SUPPLIERS").fetchone()[0]
        conn.execute("INSERT INTO SUPPLIERS VALUES (?,?,?,?,?)", (supplier_id, f"SUP-FIX-{supplier_id}", "Fixture supplier without receipts", None, 1))
        conn.commit()
        return supplier_id


def run_sql(db: Path, sql: str) -> list[list[Any]]:
    uri = db.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as conn:
        return [list(row) for row in conn.execute(sql).fetchall()]


def main() -> None:
    registry = json.loads((ARTIFACTS / "dataset.json").read_text(encoding="utf-8"))
    groups = {g["group_id"]: g for g in registry["groups"]}
    rows = []
    with tempfile.TemporaryDirectory(prefix="wms-final-alignment-") as temp:
        root = Path(temp)
        for gid in TARGETS:
            group = groups[gid]
            source = PHYSICAL / "wms_inventory.sqlite"
            group_temp = root / gid
            group_temp.mkdir()
            db = group_temp / "wms_inventory.sqlite"
            shutil.copy2(source, db)
            mutations: list[str] = []
            oracle = FINAL_ORACLES[gid]
            if gid in {"WMS-AG-04", "WMS-RK-01", "WMS-RK-03"}:
                baseline = oracle(db)
                add_posted_movement(db, kind="RECEIPT", at="2025-04-01T00:00:00.000Z", qty=7_777, tag=f"{gid}-AT")
                add_posted_movement(db, kind="RECEIPT", at="2025-04-01T00:00:00.001Z", qty=8_888, tag=f"{gid}-AFTER")
                expected = oracle(db)
                if not result_equal(baseline, expected):
                    raise AssertionError(f"{gid}: exact-cutoff/after-cutoff fixtures changed as-of expected results")
                mutations.extend(["posted movement exactly at cutoff; must be excluded", "posted movement 1ms after cutoff; must be excluded"])
            elif gid == "WMS-CD-01":
                for tag, at, qty in (
                    ("BEFORE-START", "2025-01-31T23:59:59.999Z", 1_111),
                    ("AT-START", "2025-02-01T00:00:00.000Z", 2_222),
                    ("BEFORE-END", "2025-02-28T23:59:59.999Z", 3_333),
                    ("AT-END", "2025-03-01T00:00:00.000Z", 4_444),
                ):
                    add_posted_movement(db, kind="RECEIPT", at=at, qty=qty, tag=tag)
                    mutations.append(f"receipt {tag} at {at}")
                expected = oracle(db)
            else:
                supplier_id = add_zero_receipt_supplier(db)
                mutations.append(f"supplier {supplier_id} with no posted receipts")
                expected = oracle(db)
                if any(row[0] == supplier_id for row in expected):
                    raise AssertionError("Zero-receipt supplier appeared in ranking oracle")
            actual = run_sql(db, group["canonical_sql_draft"])
            matches = result_equal(actual, expected)
            rows.append({
                "group_id": gid,
                "status": "PASS" if matches else "FAIL",
                "snapshot_sha256": sha256_file(source),
                "temporary_db_sha256": sha256_file(db),
                "mutations": mutations,
                "expected_row_count": len(expected),
                "actual_row_count": len(actual),
                "expected_rows_sha256": digest_rows(expected),
                "actual_rows_sha256": digest_rows(actual),
                "rows_match_set_comparator": matches,
                "human_review_status": "NEEDS_HUMAN_REVIEW",
            })
            if not matches:
                raise AssertionError(f"{gid}: SQL result differs from independent oracle on temporary fixture")
    artifact = {
        "artifact_version": 1,
        "created_by": "scripts/validate_wms_final_alignment_fixtures.py",
        "scope": "Temporary-copy boundary and zero-receipt checks; frozen snapshots unchanged; automated evidence only",
        "groups": rows,
    }
    out = ARTIFACTS / "wms_final_alignment_fixture_validation.json"
    out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"groups": len(rows), "passed": sum(x["status"] == "PASS" for x in rows), "artifact": str(out.relative_to(ROOT))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
