"""Independent Python reference outputs for Final intents.

Each function scans source tables and implements the written business rule in
Python. It never imports, executes, or parses the candidate SQL.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bird_vn_benchmark.intent_oracles import _distinct, _utc, table_rows


def _tables(db: Path, *names: str) -> list[list[dict[str, Any]]]:
    return [table_rows(db, name) for name in names]


def _half_up(total: int, count: int) -> int | None:
    if not count:
        return None
    sign = -1 if total < 0 else 1
    return sign * ((2 * abs(total) + count) // (2 * count))


def _ranked(rows: list[tuple], value_index: int, *, top: int | None = None) -> list[tuple]:
    ordered = sorted(rows, key=lambda row: (-row[value_index], repr(row)))
    result = []
    previous = object()
    rank = 0
    for position, row in enumerate(ordered, 1):
        value = row[value_index]
        if value != previous:
            rank, previous = position, value
        if top is None or rank <= top:
            result.append((*row, rank))
    return result


def erp_ef_02(db: Path) -> list[list[Any]]:
    orders = table_rows(db, "SALES_ORDERS")
    return _distinct([(o["order_id"], o["order_no"], o["customer_id"], o["order_date"], o["sales_rep_id"])
                      for o in orders if o["order_status"] == "CONFIRMED" and o["sales_rep_id"] is not None
                      and "2025-01-01" <= o["order_date"] < "2026-01-01"])


def erp_ef_03(db: Path) -> list[list[Any]]:
    products = table_rows(db, "PRODUCTS")
    return _distinct([(p["product_id"], p["sku"], p["product_name"], p["category_id"], p["base_unit"])
                      for p in products if p["category_id"] is not None])


def erp_ef_04(db: Path) -> list[list[Any]]:
    orders, shipments, lines = _tables(db, "SALES_ORDERS", "SALES_SHIPMENTS", "SALES_ORDER_LINES")
    order_by_id = {o["order_id"]: o for o in orders if o["order_status"] == "CONFIRMED"}
    line_total: Counter[int] = Counter()
    for line in lines:
        if line["order_id"] in order_by_id:
            line_total[line["order_id"]] += line["net_vnd"]
    rows = []
    start, end = "2025-09-30T17:00:00.000Z", "2025-12-31T17:00:00.000Z"
    for shipment in shipments:
        oid, instant = shipment["order_id"], shipment["delivered_at_utc"]
        if (oid in order_by_id and shipment["shipment_status"] == "DELIVERED" and instant
                and start <= instant < end and line_total[oid] > 100_000_000):
            order = order_by_id[oid]
            local_day = (_utc(instant) + timedelta(hours=7)).date().isoformat()
            rows.append((oid, order["order_no"], local_day, order["customer_id"], line_total[oid]))
    return _distinct(rows)


def erp_ag_01(db: Path) -> list[list[Any]]:
    customers = table_rows(db, "CUSTOMERS")
    counts = Counter(c["segment"] for c in customers)
    return _distinct([(segment, count) for segment, count in counts.items()])


def erp_ag_02(db: Path) -> list[list[Any]]:
    orders, lines = _tables(db, "SALES_ORDERS", "SALES_ORDER_LINES")
    eligible = {o["order_id"] for o in orders if o["order_status"] == "CONFIRMED" and "2025-01-01" <= o["order_date"] < "2026-01-01"}
    amounts = [line["net_vnd"] for line in lines if line["order_id"] in eligible]
    return [[sum(amounts) if amounts else None]]


def erp_ag_03(db: Path) -> list[list[Any]]:
    orders, lines = _tables(db, "SALES_ORDERS", "SALES_ORDER_LINES")
    eligible = {o["order_id"] for o in orders if o["order_status"] == "CONFIRMED" and "2025-01-01" <= o["order_date"] < "2026-01-01"}
    totals: Counter[int] = Counter()
    for line in lines:
        if line["order_id"] in eligible:
            totals[line["order_id"]] += line["net_vnd"]
    return [[_half_up(sum(totals.values()), len(totals))]]


def erp_ag_04(db: Path) -> list[list[Any]]:
    payments = table_rows(db, "PAYMENT_TRANSACTIONS")
    start, end = "2024-12-31T17:00:00.000Z", "2025-12-31T17:00:00.000Z"
    by_order: Counter[int] = Counter()
    for txn in payments:
        if txn["txn_status"] == "POSTED" and start <= txn["occurred_at_utc"] < end:
            direction = 1 if txn["txn_type"] == "CAPTURE" else -1
            by_order[txn["order_id"]] += direction * txn["amount_vnd"]
    return [[_half_up(sum(by_order.values()), len(by_order))]]


def erp_gb_01(db: Path) -> list[list[Any]]:
    orders = table_rows(db, "SALES_ORDERS")
    counts = Counter(o["order_status"] for o in orders)
    return _distinct([(status, count) for status, count in counts.items()])


def erp_gb_02(db: Path) -> list[list[Any]]:
    customers, orders, lines = _tables(db, "CUSTOMERS", "SALES_ORDERS", "SALES_ORDER_LINES")
    customer_totals: Counter[int] = Counter()
    order_by_id = {o["order_id"]: o for o in orders if o["order_status"] == "CONFIRMED"}
    for line in lines:
        order = order_by_id.get(line["order_id"])
        if order:
            customer_totals[order["customer_id"]] += line["net_vnd"]
    return _distinct([(c["customer_id"], c["customer_name"], customer_totals.get(c["customer_id"], 0)) for c in customers])


def erp_gb_04(db: Path) -> list[list[Any]]:
    orders, shipments, lines = _tables(db, "SALES_ORDERS", "SALES_SHIPMENTS", "SALES_ORDER_LINES")
    eligible_orders = {o["order_id"] for o in orders if o["order_status"] == "CONFIRMED"}
    totals: Counter[str] = Counter()
    start, end = "2024-12-31T17:00:00.000Z", "2025-06-30T17:00:00.000Z"
    month_by_order: dict[int, str] = {}
    for shipment in shipments:
        instant = shipment["delivered_at_utc"]
        if shipment["order_id"] in eligible_orders and shipment["shipment_status"] == "DELIVERED" and instant and start <= instant < end:
            month_by_order[shipment["order_id"]] = (_utc(instant) + timedelta(hours=7)).strftime("%Y-%m")
    for line in lines:
        month = month_by_order.get(line["order_id"])
        if month:
            totals[month] += line["net_vnd"]
    return _distinct([(month, amount) for month, amount in totals.items()])


def erp_rk_01(db: Path) -> list[list[Any]]:
    orders, shipments, lines, customers = _tables(db, "SALES_ORDERS", "SALES_SHIPMENTS", "SALES_ORDER_LINES", "CUSTOMERS")
    order_by_id = {o["order_id"]: o for o in orders if o["order_status"] == "CONFIRMED"}
    delivered = set()
    start, end = "2024-12-31T17:00:00.000Z", "2025-12-31T17:00:00.000Z"
    for s in shipments:
        if s["order_id"] in order_by_id and s["shipment_status"] == "DELIVERED" and s["delivered_at_utc"] and start <= s["delivered_at_utc"] < end:
            delivered.add(s["order_id"])
    revenue: Counter[int] = Counter()
    for line in lines:
        order = order_by_id.get(line["order_id"])
        if order and line["order_id"] in delivered:
            revenue[order["customer_id"]] += line["net_vnd"]
    names = {c["customer_id"]: c["customer_name"] for c in customers}
    base = [(cid, names[cid], amount) for cid, amount in revenue.items() if amount is not None]
    return _distinct(_ranked(base, 2, top=5))


def erp_rk_03(db: Path) -> list[list[Any]]:
    orders, payments, customers = _tables(db, "SALES_ORDERS", "PAYMENT_TRANSACTIONS", "CUSTOMERS")
    order_customer = {o["order_id"]: o["customer_id"] for o in orders}
    amounts: Counter[int] = Counter()
    seen: set[int] = set()
    start, end = "2024-12-31T17:00:00.000Z", "2025-12-31T17:00:00.000Z"
    for txn in payments:
        if txn["txn_status"] == "POSTED" and start <= txn["occurred_at_utc"] < end:
            cid = order_customer.get(txn["order_id"])
            if cid is not None:
                seen.add(cid)
                amounts[cid] += txn["amount_vnd"] if txn["txn_type"] == "CAPTURE" else -txn["amount_vnd"]
    if not seen:
        return []
    maximum = max(amounts[cid] for cid in seen)
    names = {c["customer_id"]: c["customer_name"] for c in customers}
    return _distinct([(cid, names[cid], amounts[cid], 1) for cid in seen if amounts[cid] == maximum])


def erp_jn_01(db: Path) -> list[list[Any]]:
    customers, orders = _tables(db, "CUSTOMERS", "SALES_ORDERS")
    counts = Counter(o["customer_id"] for o in orders if o["order_status"] == "CONFIRMED")
    return _distinct([(c["customer_id"], c["customer_name"], counts.get(c["customer_id"], 0)) for c in customers])


def erp_jn_03(db: Path) -> list[list[Any]]:
    orders, shipments, lines, customers, products = _tables(db, "SALES_ORDERS", "SALES_SHIPMENTS", "SALES_ORDER_LINES", "CUSTOMERS", "PRODUCTS")
    order_by_id = {o["order_id"]: o for o in orders if o["order_status"] == "CONFIRMED"}
    delivered = {s["order_id"] for s in shipments if s["shipment_status"] == "DELIVERED" and s["order_id"] in order_by_id}
    customer_names = {c["customer_id"]: c["customer_name"] for c in customers}
    product_by_id = {p["product_id"]: p for p in products}
    totals: Counter[tuple[int, str | None]] = Counter()
    for line in lines:
        order = order_by_id.get(line["order_id"])
        if order and order["order_id"] in delivered:
            product = product_by_id[line["product_id"]]
            totals[(order["customer_id"], product["category_id"])] += line["net_vnd"]
    return _distinct([(cid, customer_names[cid], category, amount) for (cid, category), amount in totals.items()])


def erp_jn_04(db: Path) -> list[list[Any]]:
    returns, ret_lines, orders, order_lines, products, customers = _tables(db, "SALES_RETURNS", "SALES_RETURN_LINES", "SALES_ORDERS", "SALES_ORDER_LINES", "PRODUCTS", "CUSTOMERS")
    return_by_id = {r["return_id"]: r for r in returns if r["return_status"] == "RECEIVED"}
    line_by_id = {l["order_line_id"]: l for l in order_lines}
    order_by_id = {o["order_id"]: o for o in orders}
    product_by_id = {p["product_id"]: p for p in products}
    customer_names = {c["customer_id"]: c["customer_name"] for c in customers}
    totals: Counter[tuple[int, int]] = Counter()
    for rl in ret_lines:
        ret = return_by_id.get(rl["return_id"])
        source_line = line_by_id.get(rl["order_line_id"])
        if not ret or not source_line or source_line["order_id"] != ret["order_id"]:
            continue
        order = order_by_id[ret["order_id"]]
        totals[(order["customer_id"], source_line["product_id"])] += rl["return_qty_milli"]
    sku = {p["product_id"]: p["sku"] for p in products}
    return _distinct([(cid, customer_names[cid], pid, sku[pid], qty) for (cid, pid), qty in totals.items()])


def erp_tm_01(db: Path) -> list[list[Any]]:
    orders = table_rows(db, "SALES_ORDERS")
    return _distinct([(o["order_id"], o["order_no"], o["customer_id"], o["order_date"])
                      for o in orders if o["order_status"] == "CONFIRMED" and "2025-01-01" <= o["order_date"] < "2025-04-01"])


def erp_na_01(db: Path) -> list[list[Any]]:
    customers, orders = _tables(db, "CUSTOMERS", "SALES_ORDERS")
    ordered = {o["customer_id"] for o in orders if o["order_status"] == "CONFIRMED"}
    return _distinct([(c["customer_id"], c["customer_name"]) for c in customers if c["customer_id"] not in ordered])


def erp_na_02(db: Path) -> list[list[Any]]:
    orders, payments = _tables(db, "SALES_ORDERS", "PAYMENT_TRANSACTIONS")
    by_order: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for txn in payments:
        if txn["txn_status"] == "POSTED":
            by_order[txn["order_id"]].append(txn)
    rows = []
    for order in orders:
        if order["order_status"] != "CONFIRMED":
            continue
        txns = by_order.get(order["order_id"], [])
        net = sum(t["amount_vnd"] if t["txn_type"] == "CAPTURE" else -t["amount_vnd"] for t in txns)
        if not txns or net == 0:
            rows.append((order["order_id"], order["order_no"], "NO_POSTED_CASH" if not txns else "ZERO_NET_CASH"))
    return _distinct(rows)


def erp_cd_01(db: Path) -> list[list[Any]]:
    orders, shipments, lines = _tables(db, "SALES_ORDERS", "SALES_SHIPMENTS", "SALES_ORDER_LINES")
    order_by_id = {o["order_id"]: o for o in orders}
    order_cohort = {o["order_id"] for o in orders if o["order_status"] == "CONFIRMED" and "2025-01-01" <= o["order_date"] < "2026-01-01"}
    order_value = sum(l["net_vnd"] for l in lines if l["order_id"] in order_cohort)
    start, end = "2024-12-31T17:00:00.000Z", "2025-12-31T17:00:00.000Z"
    delivered = {s["order_id"] for s in shipments if s["shipment_status"] == "DELIVERED" and s["order_id"] in order_by_id and s["delivered_at_utc"] and start <= s["delivered_at_utc"] < end and order_by_id[s["order_id"]]["order_status"] == "CONFIRMED"}
    revenue = sum(l["net_vnd"] for l in lines if l["order_id"] in delivered)
    return [["ORDER_VALUE", order_value], ["RECOGNIZED_REVENUE", revenue]]


def erp_cd_02(db: Path) -> list[list[Any]]:
    payments = table_rows(db, "PAYMENT_TRANSACTIONS")
    totals: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for txn in payments:
        if txn["txn_status"] != "POSTED":
            continue
        bucket = totals[txn["payment_method"]]
        if txn["txn_type"] == "CAPTURE":
            bucket[0] += txn["amount_vnd"]
            bucket[2] += txn["amount_vnd"]
        elif txn["txn_type"] == "REFUND":
            bucket[1] += txn["amount_vnd"]
            bucket[2] -= txn["amount_vnd"]
    return _distinct([(method, *values) for method, values in totals.items()])


def wms_ef_03(db: Path) -> list[list[Any]]:
    moves, lines, docs, products, locations = _tables(db, "INVENTORY_MOVEMENTS", "INVENTORY_DOCUMENT_LINES", "INVENTORY_DOCUMENTS", "PRODUCTS", "LOCATIONS")
    line_by_id = {x["document_line_id"]: x for x in lines}
    doc_by_id = {x["document_id"]: x for x in docs}
    product_by_id = {x["product_id"]: x for x in products}
    location_by_id = {x["location_id"]: x for x in locations}
    rows = []
    for m in moves:
        line = line_by_id[m["document_line_id"]]
        doc = doc_by_id[line["document_id"]]
        loc = location_by_id[m["location_id"]]
        if doc["document_status"] == "POSTED" and loc["location_type"] == "STORAGE":
            rows.append((m["movement_id"], product_by_id[line["product_id"]]["sku"], loc["location_code"], m["moved_at_utc"], m["qty_delta_milli"]))
    return _distinct(rows)


def wms_ef_04(db: Path) -> list[list[Any]]:
    moves, lines, docs, products, locations = _tables(db, "INVENTORY_MOVEMENTS", "INVENTORY_DOCUMENT_LINES", "INVENTORY_DOCUMENTS", "PRODUCTS", "LOCATIONS")
    line_by_id = {x["document_line_id"]: x for x in lines}
    doc_by_id = {x["document_id"]: x for x in docs}
    balances: Counter[tuple[int, int]] = Counter()
    cutoff = "2025-04-01T00:00:00.000Z"
    history = set()
    for m in moves:
        line = line_by_id[m["document_line_id"]]
        doc = doc_by_id[line["document_id"]]
        if doc["document_status"] == "POSTED" and doc["posted_at_utc"] < cutoff:
            key = (line["product_id"], m["location_id"])
            history.add(key)
            balances[key] += m["qty_delta_milli"]
    p_by_id = {p["product_id"]: p for p in products}
    l_by_id = {l["location_id"]: l for l in locations}
    return _distinct([(pid, p_by_id[pid]["sku"], lid, l_by_id[lid]["location_code"], qty)
                      for (pid, lid), qty in balances.items() if (pid, lid) in history
                      and l_by_id[lid]["location_type"] == "QUARANTINE" and qty > 0])


def wms_ag_01(db: Path) -> list[list[Any]]:
    docs = table_rows(db, "INVENTORY_DOCUMENTS")
    count = len({d["document_id"] for d in docs if d["document_status"] == "POSTED" and d["document_type"] == "RECEIPT"})
    return [[count]]


def wms_ag_03(db: Path) -> list[list[Any]]:
    moves, lines, docs, products = _tables(db, "INVENTORY_MOVEMENTS", "INVENTORY_DOCUMENT_LINES", "INVENTORY_DOCUMENTS", "PRODUCTS")
    line_by_id = {x["document_line_id"]: x for x in lines}
    doc_by_id = {x["document_id"]: x for x in docs}
    product_by_id = {x["product_id"]: x for x in products}
    balances: Counter[tuple[int, int]] = Counter()
    cutoff = "2025-04-01T00:00:00.000Z"
    for m in moves:
        line = line_by_id[m["document_line_id"]]
        doc = doc_by_id[line["document_id"]]
        if doc["document_status"] == "POSTED" and doc["posted_at_utc"] < cutoff:
            balances[(line["product_id"], m["location_id"])] += m["qty_delta_milli"]
    by_product: dict[int, list[int]] = defaultdict(list)
    for (pid, _lid), balance in balances.items():
        by_product[pid].append(balance)
    rows = []
    for pid, values in by_product.items():
        p = product_by_id[pid]
        rows.append((pid, p["sku"], p["base_unit"], _half_up(sum(values), len(values))))
    return _distinct(rows)


def wms_ag_04(db: Path) -> list[list[Any]]:
    moves, lines, docs, products, locations = _tables(db, "INVENTORY_MOVEMENTS", "INVENTORY_DOCUMENT_LINES", "INVENTORY_DOCUMENTS", "PRODUCTS", "LOCATIONS")
    line_by_id = {x["document_line_id"]: x for x in lines}
    doc_by_id = {x["document_id"]: x for x in docs}
    product_by_id = {x["product_id"]: x for x in products}
    location_by_id = {x["location_id"]: x for x in locations}
    balances: Counter[tuple[int, str, int, int]] = Counter()
    cutoff = "2025-04-01T00:00:00.000Z"
    for m in moves:
        line = line_by_id[m["document_line_id"]]
        doc = doc_by_id[line["document_id"]]
        if doc["document_status"] == "POSTED" and m["moved_at_utc"] < cutoff:
            product, location = product_by_id[line["product_id"]], location_by_id[m["location_id"]]
            balances[(product["product_id"], product["base_unit"], location["warehouse_id"], location["location_id"])] += m["qty_delta_milli"]
    groups: dict[tuple[int, str, int], list[int]] = defaultdict(list)
    for (pid, unit, wid, _lid), qty in balances.items():
        groups[(pid, unit, wid)].append(qty)
    rows = []
    for (pid, unit, wid), values in groups.items():
        total, count = sum(values), len(values)
        rows.append((pid, unit, wid, sum(qty * count < total for qty in values)))
    return _distinct(rows)


def wms_gb_01(db: Path) -> list[list[Any]]:
    docs = table_rows(db, "INVENTORY_DOCUMENTS")
    counts = Counter(d["document_status"] for d in docs)
    return _distinct([(status, count) for status, count in counts.items()])


def wms_gb_02(db: Path) -> list[list[Any]]:
    moves, lines, docs, products = _tables(db, "INVENTORY_MOVEMENTS", "INVENTORY_DOCUMENT_LINES", "INVENTORY_DOCUMENTS", "PRODUCTS")
    line_by_id = {x["document_line_id"]: x for x in lines}
    doc_by_id = {x["document_id"]: x for x in docs}
    product_by_id = {x["product_id"]: x for x in products}
    sums: Counter[tuple[str, str]] = Counter()
    for m in moves:
        line = line_by_id[m["document_line_id"]]
        doc = doc_by_id[line["document_id"]]
        if doc["document_status"] == "POSTED":
            sums[(doc["document_type"], product_by_id[line["product_id"]]["base_unit"])] += m["qty_delta_milli"]
    return _distinct([(kind, unit, qty) for (kind, unit), qty in sums.items()])


def wms_gb_03(db: Path) -> list[list[Any]]:
    suppliers, docs = _tables(db, "SUPPLIERS", "INVENTORY_DOCUMENTS")
    counts = Counter(d["supplier_id"] for d in docs if d["document_status"] == "POSTED" and d["document_type"] == "RECEIPT")
    return _distinct([(s["supplier_id"], s["supplier_name"], counts.get(s["supplier_id"], 0)) for s in suppliers])


def wms_gb_04(db: Path) -> list[list[Any]]:
    moves, lines, docs, products, locations, warehouses = _tables(db, "INVENTORY_MOVEMENTS", "INVENTORY_DOCUMENT_LINES", "INVENTORY_DOCUMENTS", "PRODUCTS", "LOCATIONS", "WAREHOUSES")
    line_by_id = {x["document_line_id"]: x for x in lines}
    doc_by_id = {x["document_id"]: x for x in docs}
    product_by_id = {x["product_id"]: x for x in products}
    location_by_id = {x["location_id"]: x for x in locations}
    warehouse_by_id = {x["warehouse_id"]: x for x in warehouses}
    balances: Counter[tuple[int, int]] = Counter()
    cutoff = "2025-04-01T00:00:00.000Z"
    for m in moves:
        line = line_by_id[m["document_line_id"]]
        doc = doc_by_id[line["document_id"]]
        if doc["document_status"] == "POSTED" and doc["posted_at_utc"] < cutoff:
            balances[(line["product_id"], m["location_id"])] += m["qty_delta_milli"]
    totals: Counter[tuple[int, int]] = Counter()
    for (pid, lid), qty in balances.items():
        totals[(location_by_id[lid]["warehouse_id"], pid)] += qty
    return _distinct([(wid, warehouse_by_id[wid]["warehouse_code"], pid, product_by_id[pid]["sku"], product_by_id[pid]["base_unit"], qty)
                      for (wid, pid), qty in totals.items()])


def wms_rk_01(db: Path) -> list[list[Any]]:
    moves, lines, docs, products, locations, warehouses = _tables(db, "INVENTORY_MOVEMENTS", "INVENTORY_DOCUMENT_LINES", "INVENTORY_DOCUMENTS", "PRODUCTS", "LOCATIONS", "WAREHOUSES")
    line_by_id = {x["document_line_id"]: x for x in lines}
    doc_by_id = {x["document_id"]: x for x in docs}
    product_by_id = {x["product_id"]: x for x in products}
    location_by_id = {x["location_id"]: x for x in locations}
    warehouse_id = next(w["warehouse_id"] for w in warehouses if w["warehouse_code"] == "WH-SG")
    totals: Counter[int] = Counter()
    cutoff = "2025-04-01T00:00:00.000Z"
    for m in moves:
        line = line_by_id[m["document_line_id"]]
        doc = doc_by_id[line["document_id"]]
        product, location = product_by_id[line["product_id"]], location_by_id[m["location_id"]]
        if (doc["document_status"] == "POSTED" and m["moved_at_utc"] < cutoff
                and product["base_unit"] == "EA" and location["warehouse_id"] == warehouse_id):
            totals[product["product_id"]] += m["qty_delta_milli"]
    if not totals:
        return []
    high = max(totals.values())
    return _distinct([(pid, product_by_id[pid]["sku"], product_by_id[pid]["product_name"], "EA", warehouse_id, qty, 1)
                      for pid, qty in totals.items() if qty == high])


def wms_rk_02(db: Path) -> list[list[Any]]:
    suppliers, docs = _tables(db, "SUPPLIERS", "INVENTORY_DOCUMENTS")
    counts = Counter(d["supplier_id"] for d in docs if d["document_type"] == "RECEIPT" and d["document_status"] == "POSTED")
    rows = [(s["supplier_id"], s["supplier_name"], counts[s["supplier_id"]]) for s in suppliers if counts[s["supplier_id"]] > 0]
    return _distinct(_ranked(rows, 2, top=3))


def wms_rk_03(db: Path) -> list[list[Any]]:
    moves, lines, docs, products, locations = _tables(db, "INVENTORY_MOVEMENTS", "INVENTORY_DOCUMENT_LINES", "INVENTORY_DOCUMENTS", "PRODUCTS", "LOCATIONS")
    line_by_id = {x["document_line_id"]: x for x in lines}
    doc_by_id = {x["document_id"]: x for x in docs}
    product = next(p for p in table_rows(db, "PRODUCTS") if p["sku"] == "W-SKU-001")
    location_by_id = {x["location_id"]: x for x in locations}
    totals: Counter[int] = Counter()
    cutoff = "2025-04-01T00:00:00.000Z"
    for m in moves:
        line = line_by_id[m["document_line_id"]]
        doc = doc_by_id[line["document_id"]]
        location = location_by_id[m["location_id"]]
        if (line["product_id"] == product["product_id"] and doc["document_status"] == "POSTED"
                and m["moved_at_utc"] < cutoff and location["location_type"] == "STORAGE"):
            totals[m["location_id"]] += m["qty_delta_milli"]
    base = [(product["product_id"], product["sku"], product["base_unit"], lid, location_by_id[lid]["location_code"], qty)
            for lid, qty in totals.items()]
    return _distinct(_ranked(base, 5, top=3))


def wms_jn_01(db: Path) -> list[list[Any]]:
    docs, suppliers = _tables(db, "INVENTORY_DOCUMENTS", "SUPPLIERS")
    supplier_by_id = {s["supplier_id"]: s for s in suppliers}
    return _distinct([(d["document_id"], d["document_no"], d["business_date"], d["supplier_id"], supplier_by_id[d["supplier_id"]]["supplier_name"])
                      for d in docs if d["document_type"] == "RECEIPT" and d["document_status"] == "POSTED"])


def wms_jn_02(db: Path) -> list[list[Any]]:
    docs, lines, products = _tables(db, "INVENTORY_DOCUMENTS", "INVENTORY_DOCUMENT_LINES", "PRODUCTS")
    doc_by_id = {d["document_id"]: d for d in docs}
    product_by_id = {p["product_id"]: p for p in products}
    return _distinct([(doc_by_id[line["document_id"]]["document_no"], line["line_no"], product_by_id[line["product_id"]]["sku"],
                       product_by_id[line["product_id"]]["product_name"], product_by_id[line["product_id"]]["base_unit"], line["planned_qty_milli"])
                      for line in lines if doc_by_id[line["document_id"]]["document_type"] == "RECEIPT" and doc_by_id[line["document_id"]]["document_status"] == "POSTED"])


def wms_jn_03(db: Path) -> list[list[Any]]:
    moves, lines, docs, products, locations, warehouses = _tables(db, "INVENTORY_MOVEMENTS", "INVENTORY_DOCUMENT_LINES", "INVENTORY_DOCUMENTS", "PRODUCTS", "LOCATIONS", "WAREHOUSES")
    line_by_id = {x["document_line_id"]: x for x in lines}
    doc_by_id = {x["document_id"]: x for x in docs}
    product_by_id = {x["product_id"]: x for x in products}
    location_by_id = {x["location_id"]: x for x in locations}
    warehouse_by_id = {x["warehouse_id"]: x for x in warehouses}
    totals: Counter[tuple[int, str, str]] = Counter()
    for m in moves:
        line = line_by_id[m["document_line_id"]]
        if doc_by_id[line["document_id"]]["document_status"] == "POSTED":
            product, location = product_by_id[line["product_id"]], location_by_id[m["location_id"]]
            totals[(location["warehouse_id"], location["location_type"], product["base_unit"])] += m["qty_delta_milli"]
    return _distinct([(wid, warehouse_by_id[wid]["warehouse_name"], kind, unit, qty)
                      for (wid, kind, unit), qty in totals.items()])


def wms_tm_01(db: Path) -> list[list[Any]]:
    docs = table_rows(db, "INVENTORY_DOCUMENTS")
    return _distinct([(d["document_id"], d["document_no"], d["document_type"], d["document_status"], d["business_date"])
                      for d in docs if d["document_status"] == "POSTED" and d["business_date"] and "2025-01-01" <= d["business_date"] < "2025-02-01"])


def wms_tm_02(db: Path) -> list[list[Any]]:
    moves, lines, docs = _tables(db, "INVENTORY_MOVEMENTS", "INVENTORY_DOCUMENT_LINES", "INVENTORY_DOCUMENTS")
    line_by_id = {x["document_line_id"]: x for x in lines}
    doc_by_id = {x["document_id"]: x for x in docs}
    totals: Counter[tuple[int, int]] = Counter()
    for m in moves:
        line = line_by_id[m["document_line_id"]]
        doc = doc_by_id[line["document_id"]]
        if doc["document_status"] == "POSTED" and doc["posted_at_utc"] < "2025-04-01T00:00:00.000Z":
            totals[(line["product_id"], m["location_id"])] += m["qty_delta_milli"]
    return _distinct([(pid, lid, qty) for (pid, lid), qty in totals.items()])


def wms_na_01(db: Path) -> list[list[Any]]:
    products, locations, moves, lines, docs = _tables(db, "PRODUCTS", "LOCATIONS", "INVENTORY_MOVEMENTS", "INVENTORY_DOCUMENT_LINES", "INVENTORY_DOCUMENTS")
    line_by_id = {x["document_line_id"]: x for x in lines}
    doc_by_id = {x["document_id"]: x for x in docs}
    moved = set()
    for m in moves:
        line = line_by_id[m["document_line_id"]]
        if doc_by_id[line["document_id"]]["document_status"] == "POSTED":
            moved.add((line["product_id"], m["location_id"]))
    return _distinct([(p["product_id"], p["sku"], loc["location_id"], loc["location_code"])
                      for p in products for loc in locations if loc["location_type"] == "PICKING" and loc["is_active"] == 1
                      and (p["product_id"], loc["location_id"]) not in moved])


def wms_na_02(db: Path) -> list[list[Any]]:
    products, locations, moves, lines, docs = _tables(db, "PRODUCTS", "LOCATIONS", "INVENTORY_MOVEMENTS", "INVENTORY_DOCUMENT_LINES", "INVENTORY_DOCUMENTS")
    line_by_id = {x["document_line_id"]: x for x in lines}
    doc_by_id = {x["document_id"]: x for x in docs}
    balances: Counter[tuple[int, int]] = Counter()
    for m in moves:
        line = line_by_id[m["document_line_id"]]
        if doc_by_id[line["document_id"]]["document_status"] == "POSTED":
            balances[(line["product_id"], m["location_id"])] += m["qty_delta_milli"]
    pids = {p["product_id"]: p["sku"] for p in products}
    rows = []
    for p in products:
        for loc in locations:
            key = (p["product_id"], loc["location_id"])
            if key not in balances:
                rows.append((p["product_id"], p["sku"], loc["location_id"], loc["location_code"], "NO_HISTORY", 0))
            elif balances[key] == 0:
                rows.append((p["product_id"], p["sku"], loc["location_id"], loc["location_code"], "ZERO_WITH_HISTORY", 0))
    return _distinct(rows)


def wms_cd_01(db: Path) -> list[list[Any]]:
    moves, lines, docs, products = _tables(db, "INVENTORY_MOVEMENTS", "INVENTORY_DOCUMENT_LINES", "INVENTORY_DOCUMENTS", "PRODUCTS")
    line_by_id = {x["document_line_id"]: x for x in lines}
    doc_by_id = {x["document_id"]: x for x in docs}
    product_by_id = {x["product_id"]: x for x in products}
    totals: dict[tuple[int, str, str], list[int]] = defaultdict(lambda: [0, 0])
    start, end = "2025-02-01T00:00:00.000Z", "2025-03-01T00:00:00.000Z"
    for m in moves:
        line = line_by_id[m["document_line_id"]]
        doc = doc_by_id[line["document_id"]]
        if (doc["document_status"] != "POSTED" or not start <= m["moved_at_utc"] < end):
            continue
        product = product_by_id[line["product_id"]]
        bucket = totals[(product["product_id"], product["sku"], product["base_unit"])]
        if doc["document_type"] == "SHIPMENT" and m["qty_delta_milli"] < 0:
            bucket[0] += -m["qty_delta_milli"]
        bucket[1] += m["qty_delta_milli"]
    return _distinct([(pid, sku, unit, values[0], values[1]) for (pid, sku, unit), values in totals.items()])


FINAL_ORACLES = {
    "ERP-EF-02": erp_ef_02, "ERP-EF-03": erp_ef_03, "ERP-EF-04": erp_ef_04,
    "ERP-AG-01": erp_ag_01, "ERP-AG-02": erp_ag_02, "ERP-AG-03": erp_ag_03, "ERP-AG-04": erp_ag_04,
    "ERP-GB-01": erp_gb_01, "ERP-GB-02": erp_gb_02, "ERP-GB-04": erp_gb_04,
    "ERP-RK-01": erp_rk_01, "ERP-RK-03": erp_rk_03,
    "ERP-JN-01": erp_jn_01, "ERP-JN-03": erp_jn_03, "ERP-JN-04": erp_jn_04,
    "ERP-TM-01": erp_tm_01, "ERP-NA-01": erp_na_01, "ERP-NA-02": erp_na_02,
    "ERP-CD-01": erp_cd_01, "ERP-CD-02": erp_cd_02,
    "WMS-EF-03": wms_ef_03, "WMS-EF-04": wms_ef_04,
    "WMS-AG-01": wms_ag_01, "WMS-AG-03": wms_ag_03, "WMS-AG-04": wms_ag_04,
    "WMS-GB-01": wms_gb_01, "WMS-GB-02": wms_gb_02, "WMS-GB-03": wms_gb_03, "WMS-GB-04": wms_gb_04,
    "WMS-RK-01": wms_rk_01, "WMS-RK-02": wms_rk_02, "WMS-RK-03": wms_rk_03,
    "WMS-JN-01": wms_jn_01, "WMS-JN-02": wms_jn_02, "WMS-JN-03": wms_jn_03,
    "WMS-TM-01": wms_tm_01, "WMS-TM-02": wms_tm_02, "WMS-NA-01": wms_na_01, "WMS-NA-02": wms_na_02,
    "WMS-CD-01": wms_cd_01,
}
