"""Validate the six Development edge-case proposals on disposable DB copies.

Reference outputs are computed and persisted before any candidate SQL in this
script is executed. The frozen physical snapshots are copied, never modified.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tempfile
from collections import Counter
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bird_demo.benchmark.registry import sha256_file
from bird_demo.data import ROOT
from bird_demo.runner import Rows, SqlError, Timeout, run
from bird_vn_benchmark.intent_oracles import DEV_ORACLES

AUTHORING = ROOT / "benchmark_data/authoring"
PHYSICAL = ROOT / "benchmark_data/physical"
ORACLE_METHODS = {
    "ERP-JN-02": "Python table scans; join order/line/product by keys and retain only confirmed parent orders.",
    "ERP-TM-02": "Parse UTC timestamps; apply half-open UTC interval for Ho Chi Minh 2025; group on UTC+7 local date.",
    "ERP-RK-02": "Sum confirmed line quantities by product/base_unit; rank independently per unit with competition rank and include rank <= 3.",
    "WMS-AG-02": "Scan posted shipment documents/lines/movements; sum negative movement magnitudes only for KG products.",
    "WMS-CD-02": "Sum planned per document/product; count executed only for POSTED; SOURCE once for transfer, ABS movement for other types.",
    "WMS-JN-04": "Join posted transfer legs from Python table scans; retain movement leg identity and both signed roles.",
}


def digest_rows(rows: list[list[Any]]) -> str:
    normalized = [list(row) for row in sorted(set(map(tuple, rows)), key=repr)]
    payload = json.dumps(normalized, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def add_wms_document(connection: sqlite3.Connection, *, kind: str, status: str,
                     product_id: int, planned_qty: int,
                     movements: list[tuple[str, int, int]] | None = None,
                     source_ref_prefix: str) -> int:
    movements = movements or []
    doc_id = connection.execute("SELECT COALESCE(MAX(document_id),0)+1 FROM INVENTORY_DOCUMENTS").fetchone()[0]
    line_id = connection.execute("SELECT COALESCE(MAX(document_line_id),0)+1 FROM INVENTORY_DOCUMENT_LINES").fetchone()[0]
    move_id = connection.execute("SELECT COALESCE(MAX(movement_id),0)+1 FROM INVENTORY_MOVEMENTS").fetchone()[0]
    posting_seq = connection.execute("SELECT COALESCE(MAX(posting_seq),0)+1 FROM INVENTORY_DOCUMENTS").fetchone()[0]
    created = "2025-04-10T08:00:00.000Z"
    posted = "2025-04-10T09:00:00.000Z" if status == "POSTED" else None
    supplier = 1 if kind == "RECEIPT" else None
    customer = 1 if kind in {"SHIPMENT", "CUSTOMER_RETURN"} else None
    warehouse = 1 if kind != "TRANSFER" else None
    from_wh, to_wh = (1, 2) if kind == "TRANSFER" else (None, None)
    connection.execute(
        "INSERT INTO INVENTORY_DOCUMENTS VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (doc_id, f"WD-FIX-{doc_id:05}", kind, status, supplier, customer, warehouse,
         from_wh, to_wh, "2025-04-10", created, posted, posting_seq if posted else None),
    )
    connection.execute(
        "INSERT INTO INVENTORY_DOCUMENT_LINES VALUES (?,?,?,?,?)",
        (line_id, doc_id, 1, product_id, planned_qty),
    )
    for leg_no, (role, location_id, delta) in enumerate(movements, 1):
        if status != "POSTED":
            raise ValueError("Non-posted fixture documents must not contain movements")
        connection.execute(
            "INSERT INTO INVENTORY_MOVEMENTS VALUES (?,?,?,?,?,?,?,?)",
            (move_id, line_id, leg_no, role, f"{source_ref_prefix}-{leg_no}", location_id, delta, posted),
        )
        move_id += 1
    return doc_id


def add_erp_ranking_ties(connection: sqlite3.Connection) -> None:
    next_line_id = connection.execute("SELECT MAX(order_line_id)+1 FROM SALES_ORDER_LINES").fetchone()[0]
    line_no = 20
    # EA: fourth and fifth product totals below these additions; two SKUs tie
    # at rank 3. Existing KG and L cohorts must still have their own top-3.
    for product_id, qty in ((1, 800_000), (4, 700_000), (7, 600_800), (10, 600_000)):
        connection.execute(
            "INSERT INTO SALES_ORDER_LINES VALUES (?,?,?,?,?,?,?,?,?,?)",
            (next_line_id, 1, line_no, product_id, qty, 0, 0, 0, 0, 0),
        )
        next_line_id += 1
        line_no += 1


def add_erp_time_boundaries(connection: sqlite3.Connection) -> dict[str, int]:
    ids = [row[0] for row in connection.execute(
        "SELECT shipment_id FROM SALES_SHIPMENTS WHERE shipment_status IN ('PENDING','FAILED') ORDER BY shipment_id LIMIT 4"
    )]
    if len(ids) != 4:
        raise RuntimeError("Need four non-delivered shipment rows for isolated boundary fixtures")
    delivered = [
        "2024-12-31T16:59:59.999Z",  # local year immediately before start
        "2024-12-31T17:00:00.000Z",  # local year start, inclusive
        "2025-12-31T16:59:59.999Z",  # local year end, included
        "2025-12-31T17:00:00.000Z",  # exact exclusive end
    ]
    for shipment_id, instant in zip(ids, delivered):
        prior = datetime.fromisoformat(instant.replace("Z", "+00:00")) - timedelta(hours=1)
        shipped = prior.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        connection.execute(
            "UPDATE SALES_SHIPMENTS SET shipment_status='DELIVERED',shipped_at_utc=?,delivered_at_utc=? WHERE shipment_id=?",
            (shipped, instant, shipment_id),
        )
    return dict(zip(("before_start", "at_start", "before_end", "at_end"), ids))


def make_fixture(intent_id: str, source_db: Path, work_dir: Path) -> tuple[Path, dict[str, Any]]:
    fixture_dir = work_dir / intent_id
    fixture_dir.mkdir(parents=True, exist_ok=True)
    fixture_db = fixture_dir / source_db.name
    shutil.copy2(source_db, fixture_db)
    metadata: dict[str, Any] = {"fixture_id": f"{intent_id}-temporary-v1", "mutations": []}
    with closing(sqlite3.connect(fixture_db)) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        if intent_id == "ERP-JN-02":
            # Existing DRAFT/CANCELLED parents have lines and the candidate must
            # return only confirmed-order lines. This is an immutable-data control.
            metadata["control"] = "existing 24 draft/cancelled orders and their lines must not appear"
        elif intent_id == "ERP-TM-02":
            metadata["boundary_shipment_ids"] = add_erp_time_boundaries(connection)
            metadata["mutations"].append("four non-delivered rows in the temp copy moved to the four UTC/local-year boundary instants")
        elif intent_id == "ERP-RK-02":
            add_erp_ranking_ties(connection)
            metadata["mutations"].append("four confirmed EA lines added; SKU-007/SKU-010 tie at rank 3")
        elif intent_id == "WMS-AG-02":
            adjustment = add_wms_document(connection, kind="ADJUSTMENT", status="POSTED", product_id=2,
                                           planned_qty=2_222, movements=[("MAIN", 2, -2_222)],
                                           source_ref_prefix="FIX-AG02-ADJ")
            transfer = add_wms_document(connection, kind="TRANSFER", status="POSTED", product_id=2,
                                        planned_qty=3_333,
                                        movements=[("SOURCE", 2, -3_333), ("DESTINATION", 6, 3_333)],
                                        source_ref_prefix="FIX-AG02-TRF")
            metadata["decoy_document_ids"] = [adjustment, transfer]
            metadata["mutations"].append("posted negative adjustment and transfer legs on a KG SKU; neither is a shipment")
        elif intent_id == "WMS-CD-02":
            fixture_ids = {}
            fixture_ids["draft_receipt"] = add_wms_document(
                connection, kind="RECEIPT", status="DRAFT", product_id=1, planned_qty=3_000,
                source_ref_prefix="FIX-CD02-DRAFT")
            fixture_ids["cancelled_shipment"] = add_wms_document(
                connection, kind="SHIPMENT", status="CANCELLED", product_id=2, planned_qty=4_000,
                source_ref_prefix="FIX-CD02-CANCEL")
            fixture_ids["posted_receipt"] = add_wms_document(
                connection, kind="RECEIPT", status="POSTED", product_id=3, planned_qty=6_000,
                movements=[("MAIN", 2, 6_000)], source_ref_prefix="FIX-CD02-RECEIPT")
            fixture_ids["posted_shipment"] = add_wms_document(
                connection, kind="SHIPMENT", status="POSTED", product_id=4, planned_qty=5_000,
                movements=[("MAIN", 2, -5_000)], source_ref_prefix="FIX-CD02-SHIP")
            fixture_ids["posted_adjustment"] = add_wms_document(
                connection, kind="ADJUSTMENT", status="POSTED", product_id=5, planned_qty=7_000,
                movements=[("MAIN", 2, -7_000)], source_ref_prefix="FIX-CD02-ADJ")
            fixture_ids["posted_return"] = add_wms_document(
                connection, kind="CUSTOMER_RETURN", status="POSTED", product_id=6, planned_qty=3_000,
                movements=[("MAIN", 2, 3_000)], source_ref_prefix="FIX-CD02-RETURN")
            fixture_ids["posted_transfer"] = add_wms_document(
                connection, kind="TRANSFER", status="POSTED", product_id=8, planned_qty=9_000,
                movements=[("SOURCE", 2, -9_000), ("DESTINATION", 6, 9_000)],
                source_ref_prefix="FIX-CD02-TRANSFER")
            metadata["fixture_document_ids"] = fixture_ids
            metadata["mutations"].append("two non-posted planned rows and posted receipt/shipment/adjustment/return/transfer invariant cases")
        elif intent_id == "WMS-JN-04":
            baseline = connection.execute(
                "SELECT d.from_warehouse_id,d.to_warehouse_id,d.posted_at_utc,dl.product_id,dl.planned_qty_milli "
                "FROM INVENTORY_DOCUMENTS d JOIN INVENTORY_DOCUMENT_LINES dl USING(document_id) "
                "WHERE d.document_type='TRANSFER' AND d.document_status='POSTED' ORDER BY d.document_id LIMIT 1"
            ).fetchone()
            if baseline is None:
                raise RuntimeError("No posted transfer available for duplicate-looking identity fixture")
            from_wh, to_wh, posted_at, product_id, qty = baseline
            doc_id = connection.execute("SELECT COALESCE(MAX(document_id),0)+1 FROM INVENTORY_DOCUMENTS").fetchone()[0]
            line_id = connection.execute("SELECT COALESCE(MAX(document_line_id),0)+1 FROM INVENTORY_DOCUMENT_LINES").fetchone()[0]
            next_move = connection.execute("SELECT COALESCE(MAX(movement_id),0)+1 FROM INVENTORY_MOVEMENTS").fetchone()[0]
            seq = connection.execute("SELECT COALESCE(MAX(posting_seq),0)+1 FROM INVENTORY_DOCUMENTS").fetchone()[0]
            connection.execute(
                "INSERT INTO INVENTORY_DOCUMENTS VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (doc_id, f"WD-FIX-{doc_id:05}", "TRANSFER", "POSTED", None, None, None,
                 from_wh, to_wh, "2025-01-20", "2025-01-19T08:00:00.000Z", posted_at, seq),
            )
            connection.execute("INSERT INTO INVENTORY_DOCUMENT_LINES VALUES (?,?,?,?,?)",
                               (line_id, doc_id, 1, product_id, qty))
            for offset, (role, loc, delta) in enumerate((("SOURCE", 2, -qty), ("DESTINATION", 6, qty))):
                connection.execute("INSERT INTO INVENTORY_MOVEMENTS VALUES (?,?,?,?,?,?,?,?)",
                                   (next_move + offset, line_id, offset + 1, role, f"FIX-JN04-{doc_id}-{offset+1}",
                                    loc, delta, posted_at))
            metadata["duplicate_looking_transfer_id"] = doc_id
            metadata["mutations"].append("valid second transfer with same SKU/quantity/timestamp but distinct document/line/source identities")
        connection.commit()
        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(f"Temporary fixture FK violations for {intent_id}: {violations[:3]}")
    metadata["database_sha256"] = sha256_file(fixture_db)
    return fixture_db, metadata


def main() -> None:
    registry = json.loads((AUTHORING / "dataset.json").read_text(encoding="utf-8"))
    group_by_id = {group["group_id"]: group for group in registry["groups"]}
    ids = ("ERP-JN-02", "ERP-TM-02", "ERP-RK-02", "WMS-AG-02", "WMS-CD-02", "WMS-JN-04")
    work_root = AUTHORING / "fixture_work"
    work_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dev-fixtures-", dir=work_root) as temp_name:
        work_dir = Path(temp_name)
        fixtures: dict[str, tuple[Path, dict[str, Any]]] = {}
        expected_records = []
        for intent_id in ids:
            group = group_by_id[intent_id]
            source_db = PHYSICAL / f"{group['db_id']}.sqlite"
            fixture_db, metadata = make_fixture(intent_id, source_db, work_dir)
            baseline_rows = DEV_ORACLES[intent_id](source_db)
            metadata["baseline_expected_rows_sha256"] = digest_rows(baseline_rows)
            if intent_id == "ERP-TM-02":
                metadata["baseline_date_counts"] = dict(Counter(row[0] for row in baseline_rows))
            fixtures[intent_id] = fixture_db, metadata
            oracle = DEV_ORACLES[intent_id]
            expected_rows = oracle(fixture_db)
            expected_records.append({
                "group_id": intent_id,
                "database_sha256": metadata["database_sha256"],
                "oracle_id": f"bird_vn_benchmark.intent_oracles:{oracle.__name__}",
                "oracle_method": ORACLE_METHODS[intent_id],
                "expected_rows": expected_rows,
                "expected_rows_sha256": digest_rows(expected_rows),
                "row_count": len(expected_rows),
                "metadata": metadata,
                "derived_before_candidate_sql_execution": True,
            })
        expected_artifact = {
            "artifact_version": 1,
            "scope": "Six Development edge-case fixtures; disposable copies of frozen snapshots",
            "stage": "EXPECTED_OUTPUTS_FROZEN_BEFORE_CANDIDATE_SQL_EXECUTION",
            "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "source_snapshot_hashes": {
                db_id: sha256_file(PHYSICAL / f"{db_id}.sqlite") for db_id in ("erp_sales", "wms_inventory")
            },
            "source_oracle_sha256": sha256_file(ROOT / "bird_vn_benchmark/intent_oracles.py"),
            "source_registry_sha256": sha256_file(AUTHORING / "dataset.json"),
            "expected_outputs": expected_records,
            "approval_status": "DRAFT — Python-derived, not human-approved",
        }
        expected_path = AUTHORING / "dev_fixture_expected_outputs.json"
        expected_path.write_text(json.dumps(expected_artifact, ensure_ascii=False, indent=2), encoding="utf-8")

        results = []
        for record in expected_records:
            intent_id = record["group_id"]
            fixture_db, metadata = fixtures[intent_id]
            group = group_by_id[intent_id]
            outcome = run(fixture_db, group["canonical_sql_draft"])
            if not isinstance(outcome, Rows):
                status = "FAIL"
                actual_rows, error = None, str(outcome)
            else:
                actual_rows = [list(row) for row in outcome.rows]
                status = "PASS" if set(map(tuple, actual_rows)) == set(map(tuple, record["expected_rows"])) else "FAIL"
                error = None if status == "PASS" else "candidate result differs from precomputed Python expected rows"
            checks: dict[str, Any] = {}
            if intent_id == "ERP-JN-02" and actual_rows is not None:
                with closing(sqlite3.connect(fixture_db)) as connection:
                    excluded_orders = {row[0] for row in connection.execute(
                        "SELECT order_no FROM SALES_ORDERS WHERE order_status<>'CONFIRMED'")}
                returned_orders = {row[0] for row in actual_rows}
                checks = {"returned_rows": len(actual_rows), "nonconfirmed_order_control_count": len(excluded_orders),
                          "nonconfirmed_excluded": not bool(returned_orders & excluded_orders)}
                if not checks["nonconfirmed_excluded"]:
                    status, error = "FAIL", "candidate includes lines from non-confirmed orders"
            if intent_id == "ERP-RK-02" and actual_rows is not None:
                units = {row[3] for row in actual_rows}
                rank3 = [row for row in actual_rows if row[5] == 3]
                checks = {"units_present": sorted(units), "rank3_rows": rank3,
                          "unit_partition_and_rank3_tie_pass": units == {"EA", "KG", "L"}
                          and {row[0] for row in rank3 if row[3] == "EA"} == {7, 10}}
                if not checks["unit_partition_and_rank3_tie_pass"]:
                    status, error = "FAIL", "fixture did not prove independent units and the third-place tie"
            if intent_id == "WMS-CD-02" and actual_rows is not None:
                by_id = {row[0]: row for row in actual_rows}
                fixture_ids = metadata["fixture_document_ids"]
                status_values = {name: (by_id[doc_id][3], by_id[doc_id][6], by_id[doc_id][7])
                                 for name, doc_id in fixture_ids.items()}
                nonposted_zero = all(status != "POSTED" and executed == 0 and planned > 0
                                     for status, planned, executed in status_values.values()
                                     if status != "POSTED")
                posted_equal = all(status == "POSTED" and planned == executed
                                   for status, planned, executed in status_values.values()
                                   if status == "POSTED")
                checks = {"fixture_values_by_role": status_values,
                          "nonposted_zero_pass": nonposted_zero, "posted_invariant_pass": posted_equal,
                          "transfer_not_double_counted": by_id[fixture_ids["posted_transfer"]][7] == 9_000}
                if not (nonposted_zero and posted_equal and checks["transfer_not_double_counted"]):
                    status, error = "FAIL", "WMS document status/type invariant check failed"
            if intent_id == "ERP-TM-02" and actual_rows is not None:
                date_counts = {row[0]: row[1] for row in actual_rows}
                baseline_counts = metadata["baseline_date_counts"]
                checks = {"boundary_shipment_ids": metadata["boundary_shipment_ids"],
                          "included_start_date": date_counts.get("2025-01-01", 0) == baseline_counts.get("2025-01-01", 0) + 1,
                          "included_last_date": date_counts.get("2025-12-31", 0) == baseline_counts.get("2025-12-31", 0) + 1,
                          "before_start_excluded": date_counts.get("2024-12-31", 0) == baseline_counts.get("2024-12-31", 0),
                          "exact_end_excluded": date_counts.get("2026-01-01", 0) == baseline_counts.get("2026-01-01", 0)}
                if not all(checks[key] for key in ("included_start_date", "included_last_date", "before_start_excluded", "exact_end_excluded")):
                    status, error = "FAIL", "local-year boundary fixture was not reflected in grouped output"
            results.append({"group_id": intent_id, "status": status, "actual_rows": actual_rows,
                            "actual_rows_sha256": digest_rows(actual_rows) if actual_rows is not None else None,
                            "expected_rows_sha256": record["expected_rows_sha256"],
                            "row_count": len(actual_rows) if actual_rows is not None else None,
                            "fixture_database_sha256": metadata["database_sha256"],
                            "checks": checks, "error": error})

    validation_artifact = {
        "artifact_version": 1,
        "expected_outputs_sha256": sha256_file(expected_path),
        "scope": "Candidate SQL executed only after dev_fixture_expected_outputs.json was written",
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "results": results,
        "summary": {"PASS": sum(item["status"] == "PASS" for item in results),
                    "FAIL": sum(item["status"] == "FAIL" for item in results)},
        "snapshot_immutable": True,
        "human_review": "NEEDS_HUMAN_REVIEW for every group",
    }
    out = AUTHORING / "dev_fixture_validation.json"
    out.write_text(json.dumps(validation_artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(validation_artifact["summary"], ensure_ascii=False))
    print(f"Expected outputs persisted before SQL execution: {expected_path.relative_to(ROOT)}")
    print(f"Fixture execution evidence: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
