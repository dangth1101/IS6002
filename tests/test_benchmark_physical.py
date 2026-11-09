from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from bird_vn_benchmark.schema import initialize
from bird_vn_benchmark.seed import seed_erp, seed_wms
from bird_vn_benchmark.validate import connect_db, validate_database


def make_db(path: Path, domain: str, seed: int = 6002) -> Path:
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        initialize(conn, domain)
        (seed_erp if domain == "erp_sales" else seed_wms)(conn, seed if domain == "erp_sales" else seed ^ 0x5A17)
        conn.commit()
    finally:
        conn.close()
    return path


def mutate(path: Path, sql: str, parameters=(), *, ignore_checks=False, foreign_keys=True):
    conn = sqlite3.connect(path)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute(f"PRAGMA foreign_keys = {'ON' if foreign_keys else 'OFF'}")
        if ignore_checks:
            conn.execute("PRAGMA ignore_check_constraints = ON")
        result = conn.execute(sql, parameters)
        conn.commit()
        return result
    finally:
        conn.close()


def check(report, invariant_id):
    return next(item for item in report["checks"] if item["invariant_id"] == invariant_id)


@pytest.mark.parametrize("domain", ["erp_sales", "wms_inventory"])
def test_valid_seed_passes_all_invariants(tmp_path, domain):
    path = make_db(tmp_path / f"{domain}.sqlite", domain)
    report = validate_database(path, domain)
    assert report["status"] == "PASS"
    assert report["invariants_failed"] == 0
    assert all(item["status"] == "PASS" for item in report["checks"])


def test_same_seed_produces_identical_database_bytes(tmp_path):
    first = make_db(tmp_path / "first.sqlite", "wms_inventory", seed=991)
    second = make_db(tmp_path / "second.sqlite", "wms_inventory", seed=991)
    assert hashlib.sha256(first.read_bytes()).digest() == hashlib.sha256(second.read_bytes()).digest()


def test_repeated_valid_business_movements_keep_distinct_identity(tmp_path):
    path = make_db(tmp_path / "wms.sqlite", "wms_inventory")
    with connect_db(path) as conn:
        count = conn.execute("""
            SELECT COUNT(*) FROM (
              SELECT location_id,qty_delta_milli,moved_at_utc
              FROM INVENTORY_MOVEMENTS
              GROUP BY location_id,qty_delta_milli,moved_at_utc
              HAVING COUNT(*) > 1
            )
        """).fetchone()[0]
    assert count >= 1
    assert validate_database(path, "wms_inventory")["status"] == "PASS"


def test_refund_above_captured_prefix_fails(tmp_path):
    path = make_db(tmp_path / "erp.sqlite", "erp_sales")
    with sqlite3.connect(path) as conn:
        row = conn.execute("""
            SELECT r.payment_txn_id,r.order_id,
                   (SELECT SUM(amount_vnd) FROM PAYMENT_TRANSACTIONS c
                    WHERE c.order_id=r.order_id AND c.txn_type='CAPTURE' AND c.txn_status='POSTED') captured
            FROM PAYMENT_TRANSACTIONS r WHERE r.txn_type='REFUND' AND r.txn_status='POSTED' LIMIT 1
        """).fetchone()
    assert row is not None
    mutate(path, "UPDATE PAYMENT_TRANSACTIONS SET amount_vnd=? WHERE payment_txn_id=?", (row[2] + 1, row[0]))
    assert check(validate_database(path, "erp_sales"), "ERP-PAY-001")["status"] == "FAIL"


def test_return_quantity_over_sold_fails(tmp_path):
    path = make_db(tmp_path / "erp.sqlite", "erp_sales")
    with sqlite3.connect(path) as conn:
        row = conn.execute("""
            SELECT rl.return_line_id,l.ordered_qty_milli
            FROM SALES_RETURN_LINES rl JOIN SALES_ORDER_LINES l USING(order_line_id)
            JOIN SALES_RETURNS r USING(return_id) WHERE r.return_status='RECEIVED' LIMIT 1
        """).fetchone()
    assert row is not None
    mutate(path, "UPDATE SALES_RETURN_LINES SET return_qty_milli=? WHERE return_line_id=?",
           (row[1] + 1, row[0]), ignore_checks=True)
    assert check(validate_database(path, "erp_sales"), "ERP-RETURN-001")["status"] == "FAIL"


def test_transfer_missing_leg_fails(tmp_path):
    path = make_db(tmp_path / "wms.sqlite", "wms_inventory")
    with sqlite3.connect(path) as conn:
        movement_id = conn.execute("""
            SELECT m.movement_id FROM INVENTORY_MOVEMENTS m
            JOIN INVENTORY_DOCUMENT_LINES l USING(document_line_id)
            JOIN INVENTORY_DOCUMENTS d USING(document_id)
            WHERE d.document_type='TRANSFER' LIMIT 1
        """).fetchone()[0]
    mutate(path, "DELETE FROM INVENTORY_MOVEMENTS WHERE movement_id=?", (movement_id,))
    assert check(validate_database(path, "wms_inventory"), "WMS-MOV-001")["status"] == "FAIL"


def test_duplicate_source_leg_identity_is_rejected_by_schema(tmp_path):
    path = make_db(tmp_path / "wms.sqlite", "wms_inventory")
    with connect_db(path) as conn:
        row = conn.execute("SELECT * FROM INVENTORY_MOVEMENTS LIMIT 1").fetchone()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("""
                INSERT INTO INVENTORY_MOVEMENTS
                (document_line_id,movement_leg_no,movement_role,source_movement_ref,location_id,qty_delta_milli,moved_at_utc)
                VALUES (?,?,?,?,?,?,?)
            """, (row["document_line_id"], row["movement_leg_no"], row["movement_role"], row["source_movement_ref"],
                  row["location_id"], row["qty_delta_milli"], row["moved_at_utc"]))


def test_negative_stock_prefix_fails(tmp_path):
    path = make_db(tmp_path / "wms.sqlite", "wms_inventory")
    with sqlite3.connect(path) as conn:
        movement_id = conn.execute("""
            SELECT m.movement_id FROM INVENTORY_MOVEMENTS m
            JOIN INVENTORY_DOCUMENT_LINES l USING(document_line_id)
            JOIN INVENTORY_DOCUMENTS d USING(document_id)
            WHERE d.document_type='SHIPMENT' AND m.qty_delta_milli<0 LIMIT 1
        """).fetchone()[0]
    mutate(path, "UPDATE INVENTORY_MOVEMENTS SET qty_delta_milli=-900000000 WHERE movement_id=?", (movement_id,))
    assert check(validate_database(path, "wms_inventory"), "WMS-STOCK-001")["status"] == "FAIL"


def test_bad_timezone_format_fails(tmp_path):
    path = make_db(tmp_path / "wms.sqlite", "wms_inventory")
    with sqlite3.connect(path) as conn:
        movement_id = conn.execute("SELECT movement_id FROM INVENTORY_MOVEMENTS LIMIT 1").fetchone()[0]
    mutate(path, "UPDATE INVENTORY_MOVEMENTS SET moved_at_utc='2025-01-01T00:00:00.000+07:00' WHERE movement_id=?",
           (movement_id,), ignore_checks=True)
    assert check(validate_database(path, "wms_inventory"), "DB-TIME-001")["status"] == "FAIL"


def test_aggregate_overflow_fails(tmp_path):
    path = make_db(tmp_path / "erp.sqlite", "erp_sales")
    with sqlite3.connect(path) as conn:
        line_ids = [row[0] for row in conn.execute("SELECT order_line_id FROM SALES_ORDER_LINES LIMIT 2")]
    mutate(path, "UPDATE SALES_ORDER_LINES SET gross_vnd=8000000000000000000 WHERE order_line_id=?",
           (line_ids[0],), ignore_checks=True)
    mutate(path, "UPDATE SALES_ORDER_LINES SET gross_vnd=8000000000000000000 WHERE order_line_id=?",
           (line_ids[1],), ignore_checks=True)
    report = validate_database(path, "erp_sales")
    assert check(report, "ERP-CAPS-001")["status"] == "FAIL"


def test_foreign_key_violation_is_detected_and_connections_enable_fk(tmp_path):
    path = make_db(tmp_path / "erp.sqlite", "erp_sales")
    with connect_db(path) as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    mutate(path, """
        INSERT INTO SALES_ORDERS
        (order_id,order_no,customer_id,sales_rep_id,order_date,order_status,currency_code,created_at_utc)
        VALUES (99999,'BROKEN-ORDER',99999,NULL,'2025-01-01','DRAFT','VND','2025-01-01T00:00:00.000Z')
    """, foreign_keys=False)
    assert check(validate_database(path, "erp_sales"), "DB-FK-001")["status"] == "FAIL"


def test_incorrect_status_fails(tmp_path):
    path = make_db(tmp_path / "wms.sqlite", "wms_inventory")
    with sqlite3.connect(path) as conn:
        document_id = conn.execute("SELECT document_id FROM INVENTORY_DOCUMENTS WHERE document_status='POSTED' LIMIT 1").fetchone()[0]
    mutate(path, "UPDATE INVENTORY_DOCUMENTS SET document_status='BROKEN' WHERE document_id=?",
           (document_id,), ignore_checks=True)
    assert check(validate_database(path, "wms_inventory"), "WMS-DOC-001")["status"] == "FAIL"


@pytest.mark.parametrize("domain", ["erp_sales", "wms_inventory"])
def test_category_parent_cycle_fails(tmp_path, domain):
    path = make_db(tmp_path / f"{domain}.sqlite", domain)
    mutate(path, "UPDATE PRODUCT_CATEGORIES SET parent_category_id=2 WHERE category_id=1")
    mutate(path, "UPDATE PRODUCT_CATEGORIES SET parent_category_id=1 WHERE category_id=2")
    domain_code = "ERP" if domain == "erp_sales" else "WMS"
    assert check(validate_database(path, domain), f"{domain_code}-CATEGORY-001")["status"] == "FAIL"


def test_database_check_rejects_amount_over_cap(tmp_path):
    path = make_db(tmp_path / "erp.sqlite", "erp_sales")
    with connect_db(path) as conn:
        row = conn.execute("SELECT * FROM PAYMENT_TRANSACTIONS LIMIT 1").fetchone()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE PAYMENT_TRANSACTIONS SET amount_vnd=1000000000001 WHERE payment_txn_id=?", (row["payment_txn_id"],))
