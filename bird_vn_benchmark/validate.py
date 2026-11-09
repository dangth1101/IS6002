"""Independent invariant checks for BIRD-VN-Robust-50 SQLite snapshots."""

from __future__ import annotations

import hashlib
import json
import platform
import re
import sqlite3
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

MAX_I64 = 2**63 - 1
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def connect_db(path: str | Path) -> sqlite3.Connection:
    """Open a connection with foreign-key enforcement explicitly enabled."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if conn.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        conn.close()
        raise RuntimeError("PRAGMA foreign_keys did not return 1")
    return conn


def _timestamp_valid(value) -> bool:
    if not isinstance(value, str) or not TIMESTAMP_RE.fullmatch(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
        return True
    except ValueError:
        return False


def _date_valid(value) -> bool:
    if not isinstance(value, str) or not DATE_RE.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


class CheckBook:
    def __init__(self):
        self.checks = []

    def add(self, invariant_id, description, checked_count, failures=(), evidence=None):
        failures = list(failures)
        self.checks.append({
            "invariant_id": invariant_id,
            "description": description,
            "status": "FAIL" if failures else "PASS",
            "records_checked": int(checked_count),
            "failing_count": len(failures),
            "failures": failures[:100],
            "evidence": evidence or {},
        })

    def report(self, path: Path, domain: str):
        failed = [item for item in self.checks if item["status"] == "FAIL"]
        return {
            "validator_version": "0.1.0",
            "domain": domain,
            "database_path": str(path.resolve()),
            "database_sha256": sha256_file(path),
            "environment": {
                "python": platform.python_version(),
                "sqlite": sqlite3.sqlite_version,
                "platform": platform.platform(),
            },
            "status": "FAIL" if failed else "PASS",
            "invariants_passed": len(self.checks) - len(failed),
            "invariants_failed": len(failed),
            "checks": self.checks,
        }


def _rowcount(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _check_fk(conn, book):
    enabled = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    violations = [dict(row) for row in conn.execute("PRAGMA foreign_key_check")]
    checked = sum(_rowcount(conn, row[0]) for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
    failures = []
    if enabled != 1:
        failures.append({"key": "connection", "reason": f"foreign_keys={enabled}, expected 1"})
    failures.extend({"key": f"{x.get('table')}:{x.get('rowid')}", "reason": "foreign key violation", "parent": x.get("parent")}
                    for x in violations)
    book.add("DB-FK-001", "Foreign key enforcement enabled and referential integrity clean", checked, failures,
             {"pragma_foreign_keys": enabled, "foreign_key_violations": len(violations), "rows_in_fk_checked_tables": checked})


def _check_dates(conn, domain, book):
    fields = ([("CUSTOMERS", "created_at_utc"), ("SALES_ORDERS", "created_at_utc"),
               ("SALES_SHIPMENTS", "shipped_at_utc"), ("SALES_SHIPMENTS", "delivered_at_utc"),
               ("PAYMENT_TRANSACTIONS", "occurred_at_utc"), ("SALES_RETURNS", "requested_at_utc"),
               ("SALES_RETURNS", "received_at_utc")]
              if domain == "erp_sales" else
              [("INVENTORY_DOCUMENTS", "created_at_utc"), ("INVENTORY_DOCUMENTS", "posted_at_utc"),
               ("INVENTORY_MOVEMENTS", "moved_at_utc")])
    failures, checked = [], 0
    for table, column in fields:
        for row in conn.execute(f"SELECT rowid AS _rowid,{column} AS value FROM {table} WHERE {column} IS NOT NULL"):
            checked += 1
            if not _timestamp_valid(row["value"]):
                failures.append({"key": f"{table}:{row['_rowid']}", "reason": f"invalid UTC millisecond timestamp: {row['value']}"})
    date_fields = [("SALES_ORDERS", "order_date")] if domain == "erp_sales" else [("INVENTORY_DOCUMENTS", "business_date")]
    for table, column in date_fields:
        for row in conn.execute(f"SELECT rowid AS _rowid,{column} AS value FROM {table}"):
            checked += 1
            if not _date_valid(row["value"]):
                failures.append({"key": f"{table}:{row['_rowid']}", "reason": f"invalid business date: {row['value']}"})
    book.add("DB-TIME-001", "All timestamps and business dates use valid canonical formats", checked, failures)


def _check_category_cycles(conn, domain, book):
    rows = conn.execute("SELECT category_id,parent_category_id FROM PRODUCT_CATEGORIES").fetchall()
    parents = {row["category_id"]: row["parent_category_id"] for row in rows}
    failures = []
    for category_id in parents:
        seen = set()
        current = category_id
        while current is not None and current in parents:
            if current in seen:
                failures.append({"key": category_id, "reason": f"category parent cycle includes {current}"})
                break
            seen.add(current)
            current = parents[current]
    domain_code = "ERP" if domain == "erp_sales" else "WMS"
    book.add(f"{domain_code}-CATEGORY-001", "Category hierarchy contains no cycles", len(rows), failures)


def _erp_checks(conn, book):
    lines = list(conn.execute("SELECT * FROM SALES_ORDER_LINES ORDER BY order_line_id"))
    failures = []
    for row in lines:
        q, p, bps = row["ordered_qty_milli"], row["unit_price_vnd"], row["discount_bps"]
        gross = (q * p + 500) // 1000
        discount = (gross * bps + 5000) // 10000
        if (gross, discount, gross - discount) != (row["gross_vnd"], row["discount_vnd"], row["net_vnd"]):
            failures.append({"key": row["order_line_id"], "reason": "stored gross/discount/net do not match integer HALF_UP formula"})
        if q < 1 or q > 1_000_000 or p < 0 or p > 1_000_000_000 or bps < 0 or bps > 10_000:
            failures.append({"key": row["order_line_id"], "reason": "line quantity/price/discount cap exceeded"})
    book.add("ERP-MONEY-001", "Line arithmetic and HALF_UP calculations", len(lines), failures)

    numeric_failures = []
    line_count = _rowcount(conn, "SALES_ORDER_LINES")
    payment_count = _rowcount(conn, "PAYMENT_TRANSACTIONS")
    if line_count > 100_000:
        numeric_failures.append({"key": "SALES_ORDER_LINES", "reason": f"row cap exceeded: {line_count}"})
    if payment_count > 100_000:
        numeric_failures.append({"key": "PAYMENT_TRANSACTIONS", "reason": f"row cap exceeded: {payment_count}"})
    for table, column in (("SALES_ORDER_LINES", "gross_vnd"), ("SALES_ORDER_LINES", "discount_vnd"),
                          ("SALES_ORDER_LINES", "net_vnd"), ("PAYMENT_TRANSACTIONS", "amount_vnd")):
        value = sum(row[0] for row in conn.execute(f"SELECT {column} FROM {table}"))
        if abs(value) > MAX_I64:
            numeric_failures.append({"key": table, "reason": f"aggregate overflow in {column}"})
    book.add("ERP-CAPS-001", "Row caps and aggregate overflow bounds", line_count + payment_count, numeric_failures,
             {"order_lines": line_count, "payment_transactions": payment_count, "signed_64_bit_max": MAX_I64})

    order_failures = []
    for row in conn.execute("SELECT o.order_id,o.order_status,COUNT(l.order_line_id) AS n FROM SALES_ORDERS o LEFT JOIN SALES_ORDER_LINES l USING(order_id) GROUP BY o.order_id"):
        if row["order_status"] not in ("DRAFT", "CONFIRMED", "CANCELLED"):
            order_failures.append({"key": row["order_id"], "reason": f"unknown order status {row['order_status']}"})
        if row["n"] < 1:
            order_failures.append({"key": row["order_id"], "reason": "order has no line"})
    book.add("ERP-ORDER-001", "Orders have valid statuses and at least one line", _rowcount(conn, "SALES_ORDERS"), order_failures)

    ship_failures = []
    for row in conn.execute("SELECT * FROM SALES_SHIPMENTS"):
        status = row["shipment_status"]
        shipped, delivered = row["shipped_at_utc"], row["delivered_at_utc"]
        valid = ((status in ("PENDING", "FAILED") and shipped is None and delivered is None)
                 or (status == "SHIPPED" and shipped is not None and delivered is None)
                 or (status == "DELIVERED" and shipped is not None and delivered is not None and delivered >= shipped))
        if not valid:
            ship_failures.append({"key": row["shipment_id"], "reason": "status/timestamp combination invalid"})
    book.add("ERP-SHIP-001", "Shipment state and event timestamp invariants", _rowcount(conn, "SALES_SHIPMENTS"), ship_failures)

    pay_failures = []
    returns = {r["return_id"]: r for r in conn.execute("SELECT return_id,order_id FROM SALES_RETURNS")}
    payments_by_order = defaultdict(list)
    for row in conn.execute("SELECT * FROM PAYMENT_TRANSACTIONS ORDER BY order_id,txn_seq"):
        payments_by_order[row["order_id"]].append(row)
        if row["txn_type"] not in ("CAPTURE", "REFUND") or row["txn_status"] not in ("PENDING", "POSTED", "FAILED", "VOIDED"):
            pay_failures.append({"key": row["payment_txn_id"], "reason": "unknown transaction type or status"})
        valid_type = ((row["txn_type"] == "CAPTURE" and row["return_id"] is None)
                      or (row["txn_type"] == "REFUND" and row["return_id"] is not None))
        if not valid_type:
            pay_failures.append({"key": row["payment_txn_id"], "reason": "capture/refund return identity invalid"})
        if row["txn_type"] == "REFUND":
            ret = returns.get(row["return_id"])
            if ret is None or ret["order_id"] != row["order_id"]:
                pay_failures.append({"key": row["payment_txn_id"], "reason": "refund return does not belong to same order"})
        if row["amount_vnd"] <= 0 or row["amount_vnd"] > 1_000_000_000_000:
            pay_failures.append({"key": row["payment_txn_id"], "reason": "payment amount outside cap"})
    for order_id, group in payments_by_order.items():
        last_time, captured, refunded = None, 0, 0
        for row in group:
            if last_time is not None and row["occurred_at_utc"] < last_time:
                pay_failures.append({"key": row["payment_txn_id"], "reason": "occurred timestamp decreases with txn_seq"})
            last_time = row["occurred_at_utc"]
            if row["txn_status"] == "POSTED":
                if row["txn_type"] == "CAPTURE":
                    captured += row["amount_vnd"]
                else:
                    refunded += row["amount_vnd"]
                if refunded > captured:
                    pay_failures.append({"key": row["payment_txn_id"], "reason": f"posted refund prefix {refunded} exceeds captures {captured} for order {order_id}"})
    book.add("ERP-PAY-001", "Payment type, return/order identity, sequence and refund cap", payment_count, pay_failures)

    ret_failures = []
    order_lines = {r["order_line_id"]: (r["order_id"], r["ordered_qty_milli"]) for r in conn.execute("SELECT order_line_id,order_id,ordered_qty_milli FROM SALES_ORDER_LINES")}
    received_by_line = defaultdict(int)
    ret_heads = {r["return_id"]: r for r in conn.execute("SELECT * FROM SALES_RETURNS")}
    for row in conn.execute("SELECT rl.*,r.order_id AS return_order,r.return_status,r.received_at_utc FROM SALES_RETURN_LINES rl JOIN SALES_RETURNS r USING(return_id)"):
        original = order_lines.get(row["order_line_id"])
        if original is None or original[0] != row["return_order"]:
            ret_failures.append({"key": row["return_line_id"], "reason": "return line points to an order line from another order"})
        if row["return_status"] == "RECEIVED":
            received_by_line[row["order_line_id"]] += row["return_qty_milli"]
        if (row["return_status"] == "RECEIVED") != (row["received_at_utc"] is not None):
            ret_failures.append({"key": row["return_line_id"], "reason": "RECEIVED status and received_at_utc disagree"})
    for line_id, total in received_by_line.items():
        sold = order_lines.get(line_id, (None, 0))[1]
        if total > sold:
            ret_failures.append({"key": line_id, "reason": f"received return quantity {total} exceeds sold quantity {sold}"})
    book.add("ERP-RETURN-001", "Return line ownership, received timestamps and cumulative quantity", _rowcount(conn, "SALES_RETURN_LINES"), ret_failures)

    orders = {r["order_id"]: r["order_status"] for r in conn.execute("SELECT order_id,order_status FROM SALES_ORDERS")}
    values = defaultdict(int)
    for row in conn.execute("SELECT l.order_id,l.net_vnd,o.order_status,s.shipment_status FROM SALES_ORDER_LINES l JOIN SALES_ORDERS o USING(order_id) LEFT JOIN SALES_SHIPMENTS s USING(order_id)"):
        if row["order_status"] == "CONFIRMED":
            values["order_value_vnd"] += row["net_vnd"]
            values["order_value_lines"] += 1
            if row["shipment_status"] == "DELIVERED":
                values["recognized_revenue_vnd"] += row["net_vnd"]
                values["recognized_revenue_lines"] += 1
    for row in conn.execute("SELECT txn_type,amount_vnd FROM PAYMENT_TRANSACTIONS WHERE txn_status='POSTED'"):
        values["posted_cash_vnd"] += row["amount_vnd"] if row["txn_type"] == "CAPTURE" else -row["amount_vnd"]
        values["posted_cash_transactions"] += 1
    metric_failures = []
    if not values["order_value_lines"] or not values["recognized_revenue_lines"] or not values["posted_cash_transactions"]:
        metric_failures.append({"key": "metric cohorts", "reason": "one of order value, delivered revenue or posted cash has no qualifying data"})
    if len({values["order_value_vnd"], values["recognized_revenue_vnd"], values["posted_cash_vnd"]}) < 3:
        metric_failures.append({"key": "metric totals", "reason": "synthetic seed does not distinguish order value, recognized revenue and cash totals"})
    business_date_differences = conn.execute("SELECT COUNT(*) FROM SALES_ORDERS WHERE order_date <> substr(created_at_utc,1,10)").fetchone()[0]
    if business_date_differences == 0:
        metric_failures.append({"key": "order_date", "reason": "seed has no order whose business date differs from created timestamp local/UTC day"})
    book.add("ERP-METRIC-001", "Independent order value/revenue/cash measures and business dates are distinguishable", len(orders), metric_failures,
             {**{key: values[key] for key in sorted(values)}, "order_dates_differ_from_created_day": business_date_differences})


def _wms_checks(conn, book):
    docs = {row["document_id"]: row for row in conn.execute("SELECT * FROM INVENTORY_DOCUMENTS")}
    lines = {row["document_line_id"]: row for row in conn.execute("SELECT * FROM INVENTORY_DOCUMENT_LINES")}
    products = {row["product_id"]: row["base_unit"] for row in conn.execute("SELECT product_id,base_unit FROM PRODUCTS")}
    locations = {row["location_id"]: row["warehouse_id"] for row in conn.execute("SELECT location_id,warehouse_id FROM LOCATIONS")}
    movements_by_line = defaultdict(list)
    movements_by_doc = defaultdict(list)
    for row in conn.execute("SELECT m.*,l.document_id,l.product_id FROM INVENTORY_MOVEMENTS m JOIN INVENTORY_DOCUMENT_LINES l USING(document_line_id)"):
        movements_by_line[row["document_line_id"]].append(row)
        movements_by_doc[row["document_id"]].append(row)

    state_failures, movement_failures = [], []
    for doc_id, doc in docs.items():
        movements = movements_by_doc.get(doc_id, [])
        doc_lines = [line for line in lines.values() if line["document_id"] == doc_id]
        if doc["document_status"] not in ("DRAFT", "POSTED", "CANCELLED"):
            state_failures.append({"key": doc_id, "reason": f"unknown document status {doc['document_status']}"})
        if doc["document_type"] not in ("RECEIPT", "SHIPMENT", "ADJUSTMENT", "TRANSFER", "CUSTOMER_RETURN"):
            state_failures.append({"key": doc_id, "reason": f"unknown document type {doc['document_type']}"})
        dtype = doc["document_type"]
        if dtype == "TRANSFER":
            header_valid = (doc["supplier_id"] is None and doc["customer_id"] is None and doc["warehouse_id"] is None
                            and doc["from_warehouse_id"] is not None and doc["to_warehouse_id"] is not None
                            and doc["from_warehouse_id"] != doc["to_warehouse_id"])
        elif dtype == "RECEIPT":
            header_valid = (doc["supplier_id"] is not None and doc["customer_id"] is None and doc["warehouse_id"] is not None
                            and doc["from_warehouse_id"] is None and doc["to_warehouse_id"] is None)
        elif dtype in ("SHIPMENT", "CUSTOMER_RETURN"):
            header_valid = (doc["supplier_id"] is None and doc["customer_id"] is not None and doc["warehouse_id"] is not None
                            and doc["from_warehouse_id"] is None and doc["to_warehouse_id"] is None)
        elif dtype == "ADJUSTMENT":
            header_valid = (doc["supplier_id"] is None and doc["customer_id"] is None and doc["warehouse_id"] is not None
                            and doc["from_warehouse_id"] is None and doc["to_warehouse_id"] is None)
        else:
            header_valid = False
        if not header_valid:
            state_failures.append({"key": doc_id, "reason": "document type and partner/warehouse header fields disagree"})
        if doc["document_status"] in ("DRAFT", "CANCELLED") and movements:
            state_failures.append({"key": doc_id, "reason": f"{doc['document_status']} document has effective movements"})
        if doc["document_status"] == "POSTED" and (doc["posted_at_utc"] is None or doc["posting_seq"] is None):
            state_failures.append({"key": doc_id, "reason": "POSTED document lacks posted timestamp or posting sequence"})
        if doc["document_status"] != "POSTED" and (doc["posted_at_utc"] is not None or doc["posting_seq"] is not None):
            state_failures.append({"key": doc_id, "reason": "unposted document has posting metadata"})
        if doc["document_status"] == "POSTED" and not doc_lines:
            state_failures.append({"key": doc_id, "reason": "posted document has no lines"})
        if doc["document_status"] == "POSTED" and doc["posted_at_utc"] < doc["created_at_utc"]:
            state_failures.append({"key": doc_id, "reason": "posted time precedes created time"})
        for line in doc_lines:
            legs = movements_by_line.get(line["document_line_id"], [])
            if doc["document_status"] != "POSTED":
                continue
            if not legs:
                movement_failures.append({"key": line["document_line_id"], "reason": "posted line has no movement"})
                continue
            if doc["document_type"] == "TRANSFER":
                if len(legs) != 2:
                    movement_failures.append({"key": line["document_line_id"], "reason": f"transfer needs exactly 2 legs, found {len(legs)}"})
                    continue
                src = [m for m in legs if m["movement_role"] == "SOURCE"]
                dst = [m for m in legs if m["movement_role"] == "DESTINATION"]
                if len(src) != 1 or len(dst) != 1:
                    movement_failures.append({"key": line["document_line_id"], "reason": "transfer roles must be one SOURCE and one DESTINATION"})
                    continue
                s, d = src[0], dst[0]
                if (s["qty_delta_milli"] >= 0 or d["qty_delta_milli"] <= 0
                    or abs(s["qty_delta_milli"]) != abs(d["qty_delta_milli"])
                    or abs(s["qty_delta_milli"]) != line["planned_qty_milli"]
                    or locations.get(s["location_id"]) != doc["from_warehouse_id"]
                    or locations.get(d["location_id"]) != doc["to_warehouse_id"]
                    or doc["from_warehouse_id"] == doc["to_warehouse_id"]):
                    movement_failures.append({"key": line["document_line_id"], "reason": "transfer signs, quantities or warehouse endpoints invalid"})
            else:
                if any(m["movement_role"] != "MAIN" for m in legs):
                    movement_failures.append({"key": line["document_line_id"], "reason": "non-transfer movement role must be MAIN"})
                total_abs = sum(abs(m["qty_delta_milli"]) for m in legs)
                if total_abs != line["planned_qty_milli"]:
                    movement_failures.append({"key": line["document_line_id"], "reason": f"movement magnitude {total_abs} != planned {line['planned_qty_milli']}"})
                for m in legs:
                    if doc["document_type"] in ("RECEIPT", "CUSTOMER_RETURN") and m["qty_delta_milli"] <= 0:
                        movement_failures.append({"key": m["movement_id"], "reason": "receipt/return movement must be positive"})
                    if doc["document_type"] == "SHIPMENT" and m["qty_delta_milli"] >= 0:
                        movement_failures.append({"key": m["movement_id"], "reason": "shipment movement must be negative"})
                    if locations.get(m["location_id"]) != doc["warehouse_id"]:
                        movement_failures.append({"key": m["movement_id"], "reason": "movement location does not belong to document warehouse"})
        for movement in movements:
            if movement["moved_at_utc"] != doc["posted_at_utc"]:
                movement_failures.append({"key": movement["movement_id"], "reason": "movement timestamp differs from document posting timestamp"})
    book.add("WMS-DOC-001", "Document type/status, posting state and lifecycle", len(docs), state_failures)
    book.add("WMS-MOV-001", "Movement direction, line totals and transfer pair invariants", len(lines), movement_failures)

    seq_failures = []
    seen_seq = set()
    posted_docs = [d for d in docs.values() if d["document_status"] == "POSTED"]
    for doc in posted_docs:
        seq = doc["posting_seq"]
        if seq is None or seq <= 0 or seq in seen_seq:
            seq_failures.append({"key": doc["document_id"], "reason": "missing, invalid or duplicate posting_seq"})
        seen_seq.add(seq)
    book.add("WMS-SEQ-001", "Every posted document has a unique batch sequence", len(posted_docs), seq_failures,
             {"posted_documents": len(posted_docs), "same_timestamp_batches": len(posted_docs) - len({d['posted_at_utc'] for d in posted_docs})})

    cap_failures = []
    movement_count = _rowcount(conn, "INVENTORY_MOVEMENTS")
    if movement_count > 100_000:
        cap_failures.append({"key": "INVENTORY_MOVEMENTS", "reason": f"movement cap exceeded: {movement_count}"})
    for row in conn.execute("SELECT movement_id,qty_delta_milli FROM INVENTORY_MOVEMENTS"):
        if abs(row["qty_delta_milli"]) > 1_000_000_000:
            cap_failures.append({"key": row["movement_id"], "reason": "movement magnitude cap exceeded"})
    total_abs = sum(abs(row["qty_delta_milli"]) for row in conn.execute("SELECT qty_delta_milli FROM INVENTORY_MOVEMENTS"))
    if total_abs > MAX_I64:
        cap_failures.append({"key": "all movements", "reason": "aggregate absolute quantity exceeds signed 64-bit"})
    book.add("WMS-CAPS-001", "Movement caps and signed 64-bit aggregate bounds", movement_count, cap_failures,
             {"movements": movement_count, "aggregate_absolute_milli": total_abs, "signed_64_bit_max": MAX_I64})

    identity_failures = []
    for column in ("source_movement_ref",):
        duplicates = conn.execute(f"SELECT {column},COUNT(*) n FROM INVENTORY_MOVEMENTS GROUP BY {column} HAVING COUNT(*)>1").fetchall()
        identity_failures.extend({"key": row[0], "reason": f"duplicate {column}"} for row in duplicates)
    duplicates = conn.execute("SELECT document_line_id,movement_leg_no,COUNT(*) n FROM INVENTORY_MOVEMENTS GROUP BY document_line_id,movement_leg_no HAVING COUNT(*)>1").fetchall()
    identity_failures.extend({"key": f"{row[0]}:{row[1]}", "reason": "duplicate line/leg identity"} for row in duplicates)
    book.add("WMS-ID-001", "Stable source/leg identities are unique", movement_count, identity_failures)

    stock_failures = []
    balances = defaultdict(int)
    for doc in sorted(posted_docs, key=lambda d: (d["posted_at_utc"], d["posting_seq"])):
        batch_delta = defaultdict(int)
        for movement in movements_by_doc.get(doc["document_id"], []):
            product_id = movement["product_id"]
            batch_delta[(product_id, movement["location_id"], products.get(product_id))] += movement["qty_delta_milli"]
        prospective = {key: balances[key] + delta for key, delta in batch_delta.items()}
        for (product_id, location_id, unit), balance in prospective.items():
            if balance < 0:
                stock_failures.append({"key": f"product={product_id},location={location_id},document={doc['document_id']}",
                                       "reason": f"negative stock {balance} {unit} after atomic posting batch"})
        balances.update(prospective)
    book.add("WMS-STOCK-001", "Stock is nonnegative after each atomic posting batch", len(posted_docs), stock_failures,
             {"product_location_balances_checked": len(balances)})

    unit_failures = []
    bad_products = conn.execute("SELECT product_id FROM PRODUCTS WHERE base_unit NOT IN ('EA','KG','L')").fetchall()
    unit_failures.extend({"key": row[0], "reason": "unsupported or missing base unit"} for row in bad_products)
    # Warehouse totals are calculated only within a product's fixed base unit.
    unit_aggregates = defaultdict(int)
    for (product_id, location_id, unit), qty in balances.items():
        unit_aggregates[(product_id, unit)] += qty
    if any(unit is None for _, unit in unit_aggregates):
        unit_failures.append({"key": "aggregate", "reason": "quantity aggregated without a product base unit"})
    tie_groups = conn.execute("""
        WITH balances AS (
          SELECT l.location_id,p.product_id,p.base_unit,SUM(m.qty_delta_milli) balance
          FROM INVENTORY_MOVEMENTS m JOIN INVENTORY_DOCUMENT_LINES dl USING(document_line_id)
          JOIN PRODUCTS p USING(product_id) JOIN LOCATIONS l USING(location_id)
          GROUP BY l.location_id,p.product_id,p.base_unit
        )
        SELECT location_id,base_unit,balance,COUNT(*) products FROM balances
        GROUP BY location_id,base_unit,balance HAVING COUNT(*) > 1 AND balance > 0
    """).fetchall()
    if not tie_groups:
        unit_failures.append({"key": "ranking fixtures", "reason": "seed lacks a positive stock tie among products with the same base unit"})
    book.add("WMS-UOM-001", "On-hand aggregation retains base unit and includes a meaningful ranking tie", len(products) + len(unit_aggregates), unit_failures,
             {"warehouse_stock_groups": len(unit_aggregates), "units": sorted(set(products.values())),
              "positive_same_unit_tie_groups": len(tie_groups)})


def validate_database(path: str | Path, domain: str) -> dict:
    path = Path(path)
    if domain not in ("erp_sales", "wms_inventory"):
        raise ValueError(f"Unknown domain: {domain}")
    book = CheckBook()
    with connect_db(path) as conn:
        _check_fk(conn, book)
        _check_dates(conn, domain, book)
        _check_category_cycles(conn, domain, book)
        (_erp_checks if domain == "erp_sales" else _wms_checks)(conn, book)
        tables = (["CUSTOMERS", "EMPLOYEES", "PRODUCT_CATEGORIES", "PRODUCTS", "SALES_ORDERS", "SALES_ORDER_LINES",
                   "SALES_SHIPMENTS", "SALES_RETURNS", "SALES_RETURN_LINES", "PAYMENT_TRANSACTIONS"]
                  if domain == "erp_sales" else
                  ["PRODUCT_CATEGORIES", "PRODUCTS", "SUPPLIERS", "CUSTOMERS", "WAREHOUSES", "LOCATIONS",
                   "INVENTORY_DOCUMENTS", "INVENTORY_DOCUMENT_LINES", "INVENTORY_MOVEMENTS"])
        row_counts = {table: _rowcount(conn, table) for table in tables}
    report = book.report(path, domain)
    report["row_counts"] = row_counts
    return report


def write_reports(report: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    domain = report["domain"]
    json_path = output_dir / f"{domain}_validation.json"
    markdown_path = output_dir / f"{domain}_validation.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [f"# {domain} validation report", "", f"- Status: **{report['status']}**",
             f"- Database SHA-256: `{report['database_sha256']}`", f"- Python: {report['environment']['python']}",
             f"- SQLite: {report['environment']['sqlite']}", "", "## Row counts", "", "| Table | Rows |", "|---|---:|"]
    lines.extend(f"| {table} | {count} |" for table, count in report["row_counts"].items())
    lines.extend(["", "## Invariant results", "", "| ID | Status | Checked | Failures | Description |", "|---|---|---:|---:|---|"])
    lines.extend(f"| {check['invariant_id']} | {check['status']} | {check['records_checked']} | {check['failing_count']} | {check['description']} |"
                 for check in report["checks"])
    for check in report["checks"]:
        if check["failures"]:
            lines.extend(["", f"### {check['invariant_id']} failures", "", "```json",
                          json.dumps(check["failures"], ensure_ascii=False, indent=2), "```"])
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
