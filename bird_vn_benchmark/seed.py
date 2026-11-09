"""Deterministic, synthetic seed data for both logical databases."""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone


def iso_utc(day_offset: int = 0, hour: int = 9, minute: int = 0, millis: int = 0) -> str:
    value = datetime(2025, 1, 1, hour, minute, tzinfo=timezone.utc) + timedelta(days=day_offset, milliseconds=millis)
    return value.strftime("%Y-%m-%dT%H:%M:%S.") + f"{value.microsecond // 1000:03d}Z"


def line_amounts(qty_milli: int, price_vnd: int, discount_bps: int) -> tuple[int, int, int]:
    gross = (qty_milli * price_vnd + 500) // 1000
    discount = (gross * discount_bps + 5000) // 10000
    return gross, discount, gross - discount


def seed_erp(conn, seed: int) -> None:
    rng = random.Random(seed)
    conn.executemany("INSERT INTO PRODUCT_CATEGORIES VALUES (?,?,?)", [
        (1, "Thiết bị", None), (2, "Phụ kiện", 1), (3, "Vật tư", None),
        (4, "Đồ gia dụng", None), (5, "Thiết bị nhỏ", 1),
    ])
    conn.executemany("INSERT INTO EMPLOYEES VALUES (?,?,?,?,?)", [
        (i, f"E{i:03}", f"Nhân viên {i:02}", None if i == 5 else ("Sales A" if i < 3 else "Sales B"), int(i != 5))
        for i in range(1, 6)
    ])
    conn.executemany("INSERT INTO CUSTOMERS VALUES (?,?,?,?,?,?,?)", [
        (i, f"C{i:04}", f"Khách hàng {i:02}", ("RETAIL", "SMB", "ENTERPRISE")[i % 3],
         None if i in (4, 17) else ("Miền Nam" if i % 2 else "Miền Bắc"), iso_utc(i), int(i % 9 != 0))
        for i in range(1, 25)
    ])
    products = [
        (i, f"SKU-{i:03}", ("Máy quét" if i in (1, 2) else f"Sản phẩm {i:02}"),
         None if i == 12 else (i % 5) + 1, ("EA", "KG", "L")[(i - 1) % 3],
         (i * 175_000) % 4_000_000, int(i % 7 != 0))
        for i in range(1, 13)
    ]
    conn.executemany("INSERT INTO PRODUCTS VALUES (?,?,?,?,?,?,?)", products)

    statuses = ["CONFIRMED", "CONFIRMED", "DRAFT", "CANCELLED", "CONFIRMED", "CONFIRMED"]
    orders: dict[int, dict] = {}
    order_rows, line_rows, shipment_rows = [], [], []
    line_id = 1
    for order_id in range(1, 73):
        status = statuses[(order_id - 1) % len(statuses)]
        customer_id = rng.randint(1, 24)
        order_day = date(2024, 12, 15) + timedelta(days=(order_id * 11) % 450)
        created = iso_utc(order_id % 70, (order_id % 18), order_id % 60)
        rep = None if order_id % 8 == 0 else (order_id % 5) + 1
        order_rows.append((order_id, f"SO-{order_id:05}", customer_id, rep, order_day.isoformat(), status, "VND", created))
        nlines = 2 + (order_id % 3)
        order_lines = []
        for j in range(1, nlines + 1):
            product_id = ((order_id + j * 3) % 12) + 1
            qty = 1000 * (1 + ((order_id + j) % 7)) + ((order_id + j) % 10) * 100
            price = products[product_id - 1][5]
            discount_bps = (0, 500, 1250, 2500, 10000)[(order_id + j) % 5]
            gross, discount, net = line_amounts(qty, price, discount_bps)
            line_rows.append((line_id, order_id, j, product_id, qty, price, discount_bps, gross, discount, net))
            order_lines.append((line_id, qty, net))
            line_id += 1
        orders[order_id] = {"status": status, "lines": order_lines, "created": created}
        if status == "CONFIRMED" and order_id % 4 != 0:
            if order_id % 13 == 0:
                shipment_rows.append((len(shipment_rows) + 1, f"SH-{order_id:05}", order_id, "FAILED", None, None))
            else:
                shipped = iso_utc(100 + order_id, 8, order_id % 60)
                delivered = iso_utc(102 + order_id, 11, order_id % 60) if order_id % 5 != 0 else None
                ship_status = "DELIVERED" if delivered else "SHIPPED"
                shipment_rows.append((len(shipment_rows) + 1, f"SH-{order_id:05}", order_id, ship_status, shipped, delivered))
        elif status == "CONFIRMED" and order_id % 4 == 0:
            shipment_rows.append((len(shipment_rows) + 1, f"SH-{order_id:05}", order_id, "PENDING", None, None))
    conn.executemany("INSERT INTO SALES_ORDERS VALUES (?,?,?,?,?,?,?,?)", order_rows)
    conn.executemany("INSERT INTO SALES_ORDER_LINES VALUES (?,?,?,?,?,?,?,?,?,?)", line_rows)
    conn.executemany("INSERT INTO SALES_SHIPMENTS VALUES (?,?,?,?,?,?)", shipment_rows)

    return_rows, return_line_rows, payment_rows = [], [], []
    return_id = return_line_id = payment_id = 1
    for order_id, order in orders.items():
        if order["status"] != "CONFIRMED":
            continue
        posted_capture = 0
        txn_seq = 1
        if order_id % 3 != 0:
            capture = 25_000 + (order_id * 1_111) % 250_000
            posted_capture += capture
            payment_rows.append((payment_id, order_id, None, txn_seq, f"TX-{payment_id:06}", "CAPTURE", "POSTED", capture,
                                 ("CARD", "BANK_TRANSFER", "CASH", "E_WALLET")[order_id % 4], iso_utc(110 + order_id, 12)))
            payment_id += 1
            txn_seq += 1
        if order_id % 7 == 0:
            payment_rows.append((payment_id, order_id, None, txn_seq, f"TX-{payment_id:06}", "CAPTURE", "PENDING", 5_000,
                                 "CARD", iso_utc(112 + order_id, 12)))
            payment_id += 1
            txn_seq += 1
        if order_id % 11 == 0 and order["lines"]:
            status = "REJECTED" if order_id % 22 == 0 else ("RECEIVED" if posted_capture >= 10_000 else "REQUESTED")
            rtime = iso_utc(120 + order_id, 10) if status == "RECEIVED" else None
            return_rows.append((return_id, f"RT-{return_id:05}", order_id, status, iso_utc(118 + order_id, 10), rtime))
            source_line, sold_qty, net = order["lines"][0]
            return_line_rows.append((return_line_id, return_id, source_line, max(1, sold_qty // 2)))
            if status == "RECEIVED":
                refund = min(8_000 + (order_id % 3) * 1_000, posted_capture)
                payment_rows.append((payment_id, order_id, return_id, txn_seq, f"TX-{payment_id:06}", "REFUND", "POSTED", refund,
                                     "BANK_TRANSFER", iso_utc(121 + order_id, 12)))
                payment_id += 1
                txn_seq += 1
            return_id += 1
            return_line_id += 1
    conn.executemany("INSERT INTO SALES_RETURNS VALUES (?,?,?,?,?,?)", return_rows)
    conn.executemany("INSERT INTO SALES_RETURN_LINES VALUES (?,?,?,?)", return_line_rows)
    conn.executemany("INSERT INTO PAYMENT_TRANSACTIONS VALUES (?,?,?,?,?,?,?,?,?,?)", payment_rows)


def seed_wms(conn, seed: int) -> None:
    rng = random.Random(seed)
    conn.executemany("INSERT INTO PRODUCT_CATEGORIES VALUES (?,?,?)", [
        (1, "Thực phẩm", None), (2, "Đồ uống", None), (3, "Gia dụng", None), (4, "Vật tư", None),
    ])
    units = ["EA", "KG", "L"]
    products = [(i, f"W-SKU-{i:03}", ("Bình nước" if i in (1, 2) else f"Hàng kho {i:02}"),
                 None if i == 18 else ((i - 1) % 4) + 1, units[(i - 1) % 3], int(i % 8 != 0))
                for i in range(1, 19)]
    conn.executemany("INSERT INTO PRODUCTS VALUES (?,?,?,?,?,?)", products)
    conn.executemany("INSERT INTO SUPPLIERS VALUES (?,?,?,?,?)", [
        (i, f"SUP-{i:03}", f"Nhà cung cấp {i:02}", None if i == 3 else ("Miền Nam" if i % 2 else "Miền Bắc"), 1)
        for i in range(1, 5)
    ])
    conn.executemany("INSERT INTO CUSTOMERS VALUES (?,?,?,?,?)", [
        (i, f"WC-{i:03}", f"Điểm nhận {i:02}", None if i == 4 else ("Miền Trung" if i % 2 else "Miền Nam"), int(i != 7))
        for i in range(1, 9)
    ])
    conn.executemany("INSERT INTO WAREHOUSES VALUES (?,?,?,?,?)", [
        (1, "WH-SG", "Kho Sài Gòn", "Miền Nam", 1), (2, "WH-HN", "Kho Hà Nội", "Miền Bắc", 1),
    ])
    location_rows = []
    location_map = {}
    loc_id = 1
    for wh_id in (1, 2):
        for code, kind in (("RCV", "RECEIVING"), ("STO", "STORAGE"), ("PICK", "PICKING"), ("QTN", "QUARANTINE")):
            location_rows.append((loc_id, wh_id, code, kind, int(code != "QTN")))
            location_map[(wh_id, code)] = loc_id
            loc_id += 1
    conn.executemany("INSERT INTO LOCATIONS VALUES (?,?,?,?,?)", location_rows)

    docs, lines, moves = [], [], []
    doc_id = line_id = move_id = 1
    posting_seq = 1
    base = date(2024, 11, 1)

    def add_doc(kind, status, business_day, created_day_offset, post_day_offset=None, *, supplier=None, customer=None,
                warehouse=None, from_wh=None, to_wh=None, line_specs=(), same_stamp=None):
        nonlocal doc_id, line_id, move_id, posting_seq
        created = iso_utc(created_day_offset, 7)
        if status == "POSTED":
            posted = same_stamp or iso_utc(post_day_offset if post_day_offset is not None else created_day_offset + 1, 9)
            seq = posting_seq
            posting_seq += 1
        else:
            posted, seq = None, None
        docs.append((doc_id, f"WD-{doc_id:05}", kind, status, supplier, customer, warehouse, from_wh, to_wh,
                     business_day.isoformat(), created, posted, seq))
        for spec in line_specs:
            product_id, qty, legs = spec
            this_line = line_id
            lines.append((line_id, doc_id, len([x for x in lines if x[1] == doc_id]) + 1, product_id, qty))
            line_id += 1
            for leg_no, role, location_id, delta in legs:
                moves.append((move_id, this_line, leg_no, role, f"SRC-{move_id:07}", location_id, delta, posted))
                move_id += 1
        doc_id += 1
        return doc_id - 1

    # Opening stock is recorded as two POSTED receipt batches, one per warehouse.
    for wh_id in (1, 2):
        specs = []
        for product_id in range(1, 19):
            qty = 500_000
            specs.append((product_id, qty, [(1, "MAIN", location_map[(wh_id, "STO")], qty)]))
        add_doc("RECEIPT", "POSTED", base + timedelta(days=1), 1, 3 + wh_id, supplier=wh_id,
                warehouse=wh_id, line_specs=specs)

    # A legitimate duplicate-valued receipt remains distinct through source identity.
    repeated_qty = 10_000
    shared_time = iso_utc(8, 9)
    for wh_id in (1, 2):
        for _ in range(2):
            add_doc("RECEIPT", "POSTED", base + timedelta(days=8), 7, 8, supplier=1,
                    warehouse=wh_id, line_specs=[(1, repeated_qty, [(1, "MAIN", location_map[(wh_id, "STO")], repeated_qty)])],
                    same_stamp=shared_time)

    # Transfers are atomically represented by exactly two legs between warehouses.
    for product_id in range(1, 13):
        qty = 20_000 + product_id * 1_000
        specs = [(product_id, qty, [
            (1, "SOURCE", location_map[(1, "STO")], -qty),
            (2, "DESTINATION", location_map[(2, "STO")], qty),
        ])]
        add_doc("TRANSFER", "POSTED", base + timedelta(days=15 + product_id), 14 + product_id,
                18 + product_id, from_wh=1, to_wh=2, line_specs=specs)

    # Posted shipments leave positive balances and create movement history.
    for n in range(1, 21):
        wh_id = 1 if n % 2 else 2
        product_id = rng.randint(1, 12)
        qty = 15_000 + n * 100 + rng.randrange(0, 100)
        specs = [(product_id, qty, [(1, "MAIN", location_map[(wh_id, "STO")], -qty)])]
        add_doc("SHIPMENT", "POSTED", base + timedelta(days=40 + n), 39 + n,
                42 + n, customer=(n % 8) + 1, warehouse=wh_id, line_specs=specs)

    # Customer returns and signed adjustments exercise status and zero/threshold handling.
    for n in range(1, 5):
        wh_id = 1 if n % 2 else 2
        product_id = n + 2
        qty = 5_000 + n * 100
        add_doc("CUSTOMER_RETURN", "POSTED", base + timedelta(days=70 + n), 69 + n,
                72 + n, customer=n, warehouse=wh_id,
                line_specs=[(product_id, qty, [(1, "MAIN", location_map[(wh_id, "STO")], qty)])])
    add_doc("ADJUSTMENT", "POSTED", base + timedelta(days=80), 79, 82, warehouse=1,
            line_specs=[(18, 1_000, [(1, "MAIN", location_map[(1, "STO")], 1_000)])])
    add_doc("ADJUSTMENT", "POSTED", base + timedelta(days=81), 80, 83, warehouse=2,
            line_specs=[(18, 500, [(1, "MAIN", location_map[(2, "STO")], -500)])])
    # DRAFT and CANCELLED retain planned lines but never create effective movements.
    add_doc("RECEIPT", "DRAFT", base + timedelta(days=90), 89, supplier=2, warehouse=1,
            line_specs=[(1, 20_000, [])])
    add_doc("SHIPMENT", "CANCELLED", base + timedelta(days=91), 90, customer=2, warehouse=2,
            line_specs=[(2, 12_000, [])])

    conn.executemany("INSERT INTO INVENTORY_DOCUMENTS VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", docs)
    conn.executemany("INSERT INTO INVENTORY_DOCUMENT_LINES VALUES (?,?,?,?,?)", lines)
    conn.executemany("INSERT INTO INVENTORY_MOVEMENTS VALUES (?,?,?,?,?,?,?,?)", moves)
