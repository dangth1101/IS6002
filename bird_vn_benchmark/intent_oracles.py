"""Independent Python reference outputs for the ten proposed Development intents.

These functions scan source tables and apply the written business rule in Python;
they do not execute or inspect the corresponding candidate SQL.
"""

from __future__ import annotations

import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def table_rows(db_path: Path, table: str) -> list[dict[str, Any]]:
    allowed = {
        "erp_sales": {"SALES_ORDERS", "SALES_ORDER_LINES", "SALES_SHIPMENTS", "PRODUCTS", "EMPLOYEES"},
        "wms_inventory": {"INVENTORY_DOCUMENTS", "INVENTORY_DOCUMENT_LINES", "INVENTORY_MOVEMENTS", "PRODUCTS", "LOCATIONS", "WAREHOUSES"},
    }
    # Fixed table names only; there is no user-supplied SQL path here.
    if table not in allowed.get(db_path.stem.removesuffix(".sqlite"), set()):
        raise ValueError(f"Oracle table is not allowlisted: {db_path.name}:{table}")
    uri = db_path.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(f"SELECT * FROM {table}").fetchall()]


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _distinct(rows: list[tuple[Any, ...]]) -> list[list[Any]]:
    return [list(row) for row in sorted(set(rows), key=repr)]


def erp_ef_01(db: Path) -> list[list[Any]]:
    orders = table_rows(db, "SALES_ORDERS")
    return _distinct([(o["order_id"], o["order_no"], o["customer_id"], o["order_date"], o["order_status"])
                      for o in orders if o["order_status"] == "CONFIRMED"])


def erp_gb_03(db: Path) -> list[list[Any]]:
    orders, employees = table_rows(db, "SALES_ORDERS"), table_rows(db, "EMPLOYEES")
    employee_name = {e["employee_id"]: e["full_name"] for e in employees}
    counts: Counter[tuple[Any, Any]] = Counter((o["sales_rep_id"], employee_name.get(o["sales_rep_id"]))
                                                for o in orders if o["order_status"] == "CONFIRMED")
    return _distinct([(rep_id, name, count) for (rep_id, name), count in counts.items()])


def erp_jn_02(db: Path) -> list[list[Any]]:
    orders, lines, products = (table_rows(db, name) for name in ("SALES_ORDERS", "SALES_ORDER_LINES", "PRODUCTS"))
    order_by_id = {o["order_id"]: o for o in orders if o["order_status"] == "CONFIRMED"}
    product_by_id = {p["product_id"]: p for p in products}
    return _distinct([(order_by_id[line["order_id"]]["order_no"], order_by_id[line["order_id"]]["order_date"],
                       product_by_id[line["product_id"]]["sku"], product_by_id[line["product_id"]]["product_name"],
                       line["ordered_qty_milli"], line["net_vnd"])
                      for line in lines if line["order_id"] in order_by_id])


def erp_tm_02(db: Path) -> list[list[Any]]:
    shipments = table_rows(db, "SALES_SHIPMENTS")
    start = datetime(2024, 12, 31, 17, tzinfo=timezone.utc)
    end = datetime(2025, 12, 31, 17, tzinfo=timezone.utc)
    counts: Counter[str] = Counter()
    for shipment in shipments:
        instant = shipment["delivered_at_utc"]
        if shipment["shipment_status"] != "DELIVERED" or not instant:
            continue
        event = _utc(instant)
        if start <= event < end:
            counts[(event + timedelta(hours=7)).date().isoformat()] += 1
    return _distinct([(local_day, count) for local_day, count in counts.items()])


def erp_rk_02(db: Path) -> list[list[Any]]:
    orders, lines, products = (table_rows(db, name) for name in ("SALES_ORDERS", "SALES_ORDER_LINES", "PRODUCTS"))
    confirmed_ids = {o["order_id"] for o in orders if o["order_status"] == "CONFIRMED"}
    product_by_id = {p["product_id"]: p for p in products}
    totals: Counter[int] = Counter()
    for line in lines:
        if line["order_id"] in confirmed_ids:
            totals[line["product_id"]] += line["ordered_qty_milli"]
    ranked = sorted(((qty, product_id) for product_id, qty in totals.items()), reverse=True)
    cutoff = ranked[2][0] if len(ranked) >= 3 else (ranked[-1][0] if ranked else None)
    rows = []
    prior = None
    rank = 0
    for position, (qty, product_id) in enumerate(ranked, 1):
        if qty != prior:
            rank = position
            prior = qty
        if cutoff is None or qty < cutoff:
            continue
        product = product_by_id[product_id]
        rows.append((product_id, product["sku"], product["product_name"], product["base_unit"], qty, rank))
    return _distinct(rows)


def wms_ef_01(db: Path) -> list[list[Any]]:
    documents = table_rows(db, "INVENTORY_DOCUMENTS")
    return _distinct([(d["document_id"], d["document_no"], d["document_type"], d["document_status"], d["business_date"])
                      for d in documents if d["document_status"] == "POSTED"])


def wms_ef_02(db: Path) -> list[list[Any]]:
    products = table_rows(db, "PRODUCTS")
    return _distinct([(p["product_id"], p["sku"], p["product_name"], p["base_unit"], p["category_id"])
                      for p in products if p["base_unit"] == "KG"])


def wms_ag_02(db: Path) -> list[list[Any]]:
    docs, lines, moves, products = (table_rows(db, name) for name in
                                    ("INVENTORY_DOCUMENTS", "INVENTORY_DOCUMENT_LINES", "INVENTORY_MOVEMENTS", "PRODUCTS"))
    posted_shipments = {d["document_id"] for d in docs if d["document_type"] == "SHIPMENT" and d["document_status"] == "POSTED"}
    line_by_id = {line["document_line_id"]: line for line in lines if line["document_id"] in posted_shipments}
    product_by_id = {p["product_id"]: p for p in products}
    totals: Counter[int] = Counter()
    for move in moves:
        line = line_by_id.get(move["document_line_id"])
        if line and move["qty_delta_milli"] < 0 and product_by_id[line["product_id"]]["base_unit"] == "KG":
            totals[line["product_id"]] += -move["qty_delta_milli"]
    return _distinct([(pid, product_by_id[pid]["sku"], product_by_id[pid]["base_unit"], qty) for pid, qty in totals.items()])


def wms_cd_02(db: Path) -> list[list[Any]]:
    docs, lines, moves, products = (table_rows(db, name) for name in
                                    ("INVENTORY_DOCUMENTS", "INVENTORY_DOCUMENT_LINES", "INVENTORY_MOVEMENTS", "PRODUCTS"))
    posted = {d["document_id"]: d for d in docs if d["document_status"] == "POSTED"}
    product_by_id = {p["product_id"]: p for p in products}
    planned: Counter[tuple[int, int]] = Counter()
    for line in lines:
        if line["document_id"] in posted:
            planned[(line["document_id"], line["product_id"])] += line["planned_qty_milli"]
    line_by_id = {line["document_line_id"]: line for line in lines}
    moved: Counter[tuple[int, int]] = Counter()
    for move in moves:
        line = line_by_id[move["document_line_id"]]
        if line["document_id"] in posted:
            moved[(line["document_id"], line["product_id"])] += abs(move["qty_delta_milli"])
    rows = []
    for (doc_id, product_id), planned_qty in planned.items():
        doc, product = posted[doc_id], product_by_id[product_id]
        rows.append((doc_id, doc["document_no"], doc["document_type"], product["sku"], product["base_unit"],
                     planned_qty, moved.get((doc_id, product_id), 0)))
    return _distinct(rows)


def wms_jn_04(db: Path) -> list[list[Any]]:
    docs, lines, moves, products, locations, warehouses = (table_rows(db, name) for name in
        ("INVENTORY_DOCUMENTS", "INVENTORY_DOCUMENT_LINES", "INVENTORY_MOVEMENTS", "PRODUCTS", "LOCATIONS", "WAREHOUSES"))
    transfers = {d["document_id"]: d for d in docs if d["document_type"] == "TRANSFER" and d["document_status"] == "POSTED"}
    line_by_id = {line["document_line_id"]: line for line in lines if line["document_id"] in transfers}
    product_by_id = {p["product_id"]: p for p in products}
    location_by_id = {loc["location_id"]: loc for loc in locations}
    warehouse_code = {wh["warehouse_id"]: wh["warehouse_code"] for wh in warehouses}
    rows = []
    for move in moves:
        line = line_by_id.get(move["document_line_id"])
        if not line:
            continue
        doc, product = transfers[line["document_id"]], product_by_id[line["product_id"]]
        rows.append((doc["document_id"], doc["document_no"], line["line_no"], product["sku"],
                     move["movement_leg_no"], move["movement_role"], warehouse_code[doc["from_warehouse_id"]],
                     warehouse_code[doc["to_warehouse_id"]], move["qty_delta_milli"], move["moved_at_utc"]))
    return _distinct(rows)


DEV_ORACLES = {
    "ERP-EF-01": erp_ef_01,
    "ERP-GB-03": erp_gb_03,
    "ERP-JN-02": erp_jn_02,
    "ERP-TM-02": erp_tm_02,
    "ERP-RK-02": erp_rk_02,
    "WMS-EF-01": wms_ef_01,
    "WMS-EF-02": wms_ef_02,
    "WMS-AG-02": wms_ag_02,
    "WMS-CD-02": wms_cd_02,
    "WMS-JN-04": wms_jn_04,
}
