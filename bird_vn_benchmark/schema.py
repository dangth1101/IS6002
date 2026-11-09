"""SQLite schemas for the physical benchmark databases."""

from __future__ import annotations

ERP_SCHEMA = r"""
PRAGMA foreign_keys = ON;
CREATE TABLE CUSTOMERS (
  customer_id INTEGER PRIMARY KEY,
  customer_code TEXT NOT NULL UNIQUE CHECK(length(trim(customer_code)) > 0),
  customer_name TEXT NOT NULL CHECK(length(trim(customer_name)) > 0),
  segment TEXT CHECK(segment IS NULL OR segment IN ('RETAIL','SMB','ENTERPRISE')),
  region TEXT,
  created_at_utc TEXT NOT NULL CHECK(created_at_utc GLOB '????-??-??T??:??:??.???Z'),
  is_active INTEGER NOT NULL CHECK(is_active IN (0,1))
);
CREATE TABLE EMPLOYEES (
  employee_id INTEGER PRIMARY KEY,
  employee_code TEXT NOT NULL UNIQUE CHECK(length(trim(employee_code)) > 0),
  full_name TEXT NOT NULL CHECK(length(trim(full_name)) > 0),
  team TEXT,
  is_active INTEGER NOT NULL CHECK(is_active IN (0,1))
);
CREATE TABLE PRODUCT_CATEGORIES (
  category_id INTEGER PRIMARY KEY,
  category_name TEXT NOT NULL UNIQUE CHECK(length(trim(category_name)) > 0),
  parent_category_id INTEGER REFERENCES PRODUCT_CATEGORIES(category_id) ON DELETE RESTRICT,
  CHECK(parent_category_id IS NULL OR parent_category_id <> category_id)
);
CREATE TABLE PRODUCTS (
  product_id INTEGER PRIMARY KEY,
  sku TEXT NOT NULL UNIQUE CHECK(length(trim(sku)) > 0),
  product_name TEXT NOT NULL CHECK(length(trim(product_name)) > 0),
  category_id INTEGER REFERENCES PRODUCT_CATEGORIES(category_id) ON DELETE RESTRICT,
  base_unit TEXT NOT NULL CHECK(base_unit IN ('EA','KG','L')),
  list_price_vnd INTEGER NOT NULL CHECK(list_price_vnd >= 0),
  is_active INTEGER NOT NULL CHECK(is_active IN (0,1))
);
CREATE TABLE SALES_ORDERS (
  order_id INTEGER PRIMARY KEY,
  order_no TEXT NOT NULL UNIQUE CHECK(length(trim(order_no)) > 0),
  customer_id INTEGER NOT NULL REFERENCES CUSTOMERS(customer_id) ON DELETE RESTRICT,
  sales_rep_id INTEGER REFERENCES EMPLOYEES(employee_id) ON DELETE RESTRICT,
  order_date TEXT NOT NULL CHECK(order_date GLOB '????-??-??'),
  order_status TEXT NOT NULL CHECK(order_status IN ('DRAFT','CONFIRMED','CANCELLED')),
  currency_code TEXT NOT NULL CHECK(currency_code = 'VND'),
  created_at_utc TEXT NOT NULL CHECK(created_at_utc GLOB '????-??-??T??:??:??.???Z')
);
CREATE TABLE SALES_ORDER_LINES (
  order_line_id INTEGER PRIMARY KEY,
  order_id INTEGER NOT NULL REFERENCES SALES_ORDERS(order_id) ON DELETE RESTRICT,
  line_no INTEGER NOT NULL CHECK(line_no > 0),
  product_id INTEGER NOT NULL REFERENCES PRODUCTS(product_id) ON DELETE RESTRICT,
  ordered_qty_milli INTEGER NOT NULL CHECK(ordered_qty_milli BETWEEN 1 AND 1000000),
  unit_price_vnd INTEGER NOT NULL CHECK(unit_price_vnd BETWEEN 0 AND 1000000000),
  discount_bps INTEGER NOT NULL CHECK(discount_bps BETWEEN 0 AND 10000),
  gross_vnd INTEGER NOT NULL CHECK(gross_vnd BETWEEN 0 AND 1000000000000),
  discount_vnd INTEGER NOT NULL CHECK(discount_vnd BETWEEN 0 AND gross_vnd),
  net_vnd INTEGER NOT NULL CHECK(net_vnd = gross_vnd - discount_vnd),
  UNIQUE(order_id,line_no)
);
CREATE TABLE SALES_SHIPMENTS (
  shipment_id INTEGER PRIMARY KEY,
  shipment_no TEXT NOT NULL UNIQUE CHECK(length(trim(shipment_no)) > 0),
  order_id INTEGER NOT NULL UNIQUE REFERENCES SALES_ORDERS(order_id) ON DELETE RESTRICT,
  shipment_status TEXT NOT NULL CHECK(shipment_status IN ('PENDING','SHIPPED','DELIVERED','FAILED')),
  shipped_at_utc TEXT CHECK(shipped_at_utc IS NULL OR shipped_at_utc GLOB '????-??-??T??:??:??.???Z'),
  delivered_at_utc TEXT CHECK(delivered_at_utc IS NULL OR delivered_at_utc GLOB '????-??-??T??:??:??.???Z'),
  CHECK((shipment_status IN ('PENDING','FAILED') AND shipped_at_utc IS NULL AND delivered_at_utc IS NULL)
     OR (shipment_status = 'SHIPPED' AND shipped_at_utc IS NOT NULL AND delivered_at_utc IS NULL)
     OR (shipment_status = 'DELIVERED' AND shipped_at_utc IS NOT NULL AND delivered_at_utc IS NOT NULL
         AND delivered_at_utc >= shipped_at_utc))
);
CREATE TABLE SALES_RETURNS (
  return_id INTEGER PRIMARY KEY,
  return_no TEXT NOT NULL UNIQUE CHECK(length(trim(return_no)) > 0),
  order_id INTEGER NOT NULL REFERENCES SALES_ORDERS(order_id) ON DELETE RESTRICT,
  return_status TEXT NOT NULL CHECK(return_status IN ('REQUESTED','APPROVED','RECEIVED','REJECTED')),
  requested_at_utc TEXT NOT NULL CHECK(requested_at_utc GLOB '????-??-??T??:??:??.???Z'),
  received_at_utc TEXT CHECK(received_at_utc IS NULL OR received_at_utc GLOB '????-??-??T??:??:??.???Z'),
  CHECK((return_status = 'RECEIVED' AND received_at_utc IS NOT NULL) OR
        (return_status <> 'RECEIVED' AND received_at_utc IS NULL))
);
CREATE TABLE SALES_RETURN_LINES (
  return_line_id INTEGER PRIMARY KEY,
  return_id INTEGER NOT NULL REFERENCES SALES_RETURNS(return_id) ON DELETE RESTRICT,
  order_line_id INTEGER NOT NULL REFERENCES SALES_ORDER_LINES(order_line_id) ON DELETE RESTRICT,
  return_qty_milli INTEGER NOT NULL CHECK(return_qty_milli BETWEEN 1 AND 1000000),
  UNIQUE(return_id,order_line_id)
);
CREATE TABLE PAYMENT_TRANSACTIONS (
  payment_txn_id INTEGER PRIMARY KEY,
  order_id INTEGER NOT NULL REFERENCES SALES_ORDERS(order_id) ON DELETE RESTRICT,
  return_id INTEGER REFERENCES SALES_RETURNS(return_id) ON DELETE RESTRICT,
  txn_seq INTEGER NOT NULL CHECK(txn_seq > 0),
  transaction_ref TEXT NOT NULL UNIQUE CHECK(length(trim(transaction_ref)) > 0),
  txn_type TEXT NOT NULL CHECK(txn_type IN ('CAPTURE','REFUND')),
  txn_status TEXT NOT NULL CHECK(txn_status IN ('PENDING','POSTED','FAILED','VOIDED')),
  amount_vnd INTEGER NOT NULL CHECK(amount_vnd BETWEEN 1 AND 1000000000000),
  payment_method TEXT NOT NULL CHECK(payment_method IN ('CASH','BANK_TRANSFER','CARD','E_WALLET')),
  occurred_at_utc TEXT NOT NULL CHECK(occurred_at_utc GLOB '????-??-??T??:??:??.???Z'),
  UNIQUE(order_id,txn_seq),
  CHECK((txn_type = 'CAPTURE' AND return_id IS NULL) OR
        (txn_type = 'REFUND' AND return_id IS NOT NULL))
);
CREATE INDEX idx_orders_customer_date ON SALES_ORDERS(customer_id,order_date);
CREATE INDEX idx_orders_status_date ON SALES_ORDERS(order_status,order_date);
CREATE INDEX idx_order_lines_product ON SALES_ORDER_LINES(product_id,order_id);
CREATE INDEX idx_shipments_status_delivered ON SALES_SHIPMENTS(shipment_status,delivered_at_utc);
CREATE INDEX idx_payments_order_time ON PAYMENT_TRANSACTIONS(order_id,occurred_at_utc,txn_seq);
CREATE INDEX idx_payments_type_status_time ON PAYMENT_TRANSACTIONS(txn_type,txn_status,occurred_at_utc);
CREATE INDEX idx_returns_order_status ON SALES_RETURNS(order_id,return_status);
CREATE INDEX idx_return_lines_order_line ON SALES_RETURN_LINES(order_line_id,return_id);
"""

WMS_SCHEMA = r"""
PRAGMA foreign_keys = ON;
CREATE TABLE PRODUCT_CATEGORIES (
  category_id INTEGER PRIMARY KEY,
  category_name TEXT NOT NULL UNIQUE CHECK(length(trim(category_name)) > 0),
  parent_category_id INTEGER REFERENCES PRODUCT_CATEGORIES(category_id) ON DELETE RESTRICT,
  CHECK(parent_category_id IS NULL OR parent_category_id <> category_id)
);
CREATE TABLE PRODUCTS (
  product_id INTEGER PRIMARY KEY,
  sku TEXT NOT NULL UNIQUE CHECK(length(trim(sku)) > 0),
  product_name TEXT NOT NULL CHECK(length(trim(product_name)) > 0),
  category_id INTEGER REFERENCES PRODUCT_CATEGORIES(category_id) ON DELETE RESTRICT,
  base_unit TEXT NOT NULL CHECK(base_unit IN ('EA','KG','L')),
  is_active INTEGER NOT NULL CHECK(is_active IN (0,1))
);
CREATE TABLE SUPPLIERS (
  supplier_id INTEGER PRIMARY KEY,
  supplier_code TEXT NOT NULL UNIQUE CHECK(length(trim(supplier_code)) > 0),
  supplier_name TEXT NOT NULL CHECK(length(trim(supplier_name)) > 0),
  region TEXT,
  is_active INTEGER NOT NULL CHECK(is_active IN (0,1))
);
CREATE TABLE CUSTOMERS (
  customer_id INTEGER PRIMARY KEY,
  customer_code TEXT NOT NULL UNIQUE CHECK(length(trim(customer_code)) > 0),
  customer_name TEXT NOT NULL CHECK(length(trim(customer_name)) > 0),
  region TEXT,
  is_active INTEGER NOT NULL CHECK(is_active IN (0,1))
);
CREATE TABLE WAREHOUSES (
  warehouse_id INTEGER PRIMARY KEY,
  warehouse_code TEXT NOT NULL UNIQUE CHECK(length(trim(warehouse_code)) > 0),
  warehouse_name TEXT NOT NULL CHECK(length(trim(warehouse_name)) > 0),
  region TEXT,
  is_active INTEGER NOT NULL CHECK(is_active IN (0,1))
);
CREATE TABLE LOCATIONS (
  location_id INTEGER PRIMARY KEY,
  warehouse_id INTEGER NOT NULL REFERENCES WAREHOUSES(warehouse_id) ON DELETE RESTRICT,
  location_code TEXT NOT NULL CHECK(length(trim(location_code)) > 0),
  location_type TEXT NOT NULL CHECK(location_type IN ('RECEIVING','STORAGE','PICKING','STAGING','QUARANTINE')),
  is_active INTEGER NOT NULL CHECK(is_active IN (0,1)),
  UNIQUE(warehouse_id,location_code)
);
CREATE TABLE INVENTORY_DOCUMENTS (
  document_id INTEGER PRIMARY KEY,
  document_no TEXT NOT NULL UNIQUE CHECK(length(trim(document_no)) > 0),
  document_type TEXT NOT NULL CHECK(document_type IN ('RECEIPT','SHIPMENT','ADJUSTMENT','TRANSFER','CUSTOMER_RETURN')),
  document_status TEXT NOT NULL CHECK(document_status IN ('DRAFT','POSTED','CANCELLED')),
  supplier_id INTEGER REFERENCES SUPPLIERS(supplier_id) ON DELETE RESTRICT,
  customer_id INTEGER REFERENCES CUSTOMERS(customer_id) ON DELETE RESTRICT,
  warehouse_id INTEGER REFERENCES WAREHOUSES(warehouse_id) ON DELETE RESTRICT,
  from_warehouse_id INTEGER REFERENCES WAREHOUSES(warehouse_id) ON DELETE RESTRICT,
  to_warehouse_id INTEGER REFERENCES WAREHOUSES(warehouse_id) ON DELETE RESTRICT,
  business_date TEXT NOT NULL CHECK(business_date GLOB '????-??-??'),
  created_at_utc TEXT NOT NULL CHECK(created_at_utc GLOB '????-??-??T??:??:??.???Z'),
  posted_at_utc TEXT CHECK(posted_at_utc IS NULL OR posted_at_utc GLOB '????-??-??T??:??:??.???Z'),
  posting_seq INTEGER UNIQUE CHECK(posting_seq IS NULL OR posting_seq > 0),
  CHECK((document_type = 'TRANSFER' AND supplier_id IS NULL AND customer_id IS NULL AND warehouse_id IS NULL
          AND from_warehouse_id IS NOT NULL AND to_warehouse_id IS NOT NULL AND from_warehouse_id <> to_warehouse_id)
     OR (document_type = 'RECEIPT' AND supplier_id IS NOT NULL AND customer_id IS NULL AND warehouse_id IS NOT NULL
          AND from_warehouse_id IS NULL AND to_warehouse_id IS NULL)
     OR (document_type = 'SHIPMENT' AND supplier_id IS NULL AND customer_id IS NOT NULL AND warehouse_id IS NOT NULL
          AND from_warehouse_id IS NULL AND to_warehouse_id IS NULL)
     OR (document_type = 'CUSTOMER_RETURN' AND supplier_id IS NULL AND customer_id IS NOT NULL AND warehouse_id IS NOT NULL
          AND from_warehouse_id IS NULL AND to_warehouse_id IS NULL)
     OR (document_type = 'ADJUSTMENT' AND supplier_id IS NULL AND customer_id IS NULL AND warehouse_id IS NOT NULL
          AND from_warehouse_id IS NULL AND to_warehouse_id IS NULL)),
  CHECK((document_status = 'POSTED' AND posted_at_utc IS NOT NULL AND posting_seq IS NOT NULL
          AND posted_at_utc >= created_at_utc)
     OR (document_status <> 'POSTED' AND posted_at_utc IS NULL AND posting_seq IS NULL))
);
CREATE TABLE INVENTORY_DOCUMENT_LINES (
  document_line_id INTEGER PRIMARY KEY,
  document_id INTEGER NOT NULL REFERENCES INVENTORY_DOCUMENTS(document_id) ON DELETE RESTRICT,
  line_no INTEGER NOT NULL CHECK(line_no > 0),
  product_id INTEGER NOT NULL REFERENCES PRODUCTS(product_id) ON DELETE RESTRICT,
  planned_qty_milli INTEGER NOT NULL CHECK(planned_qty_milli BETWEEN 1 AND 1000000000),
  UNIQUE(document_id,line_no)
);
CREATE TABLE INVENTORY_MOVEMENTS (
  movement_id INTEGER PRIMARY KEY,
  document_line_id INTEGER NOT NULL REFERENCES INVENTORY_DOCUMENT_LINES(document_line_id) ON DELETE RESTRICT,
  movement_leg_no INTEGER NOT NULL CHECK(movement_leg_no > 0),
  movement_role TEXT NOT NULL CHECK(movement_role IN ('MAIN','SOURCE','DESTINATION')),
  source_movement_ref TEXT NOT NULL UNIQUE CHECK(length(trim(source_movement_ref)) > 0),
  location_id INTEGER NOT NULL REFERENCES LOCATIONS(location_id) ON DELETE RESTRICT,
  qty_delta_milli INTEGER NOT NULL CHECK(qty_delta_milli <> 0 AND abs(qty_delta_milli) <= 1000000000),
  moved_at_utc TEXT NOT NULL CHECK(moved_at_utc GLOB '????-??-??T??:??:??.???Z'),
  UNIQUE(document_line_id,movement_leg_no)
);
CREATE INDEX idx_products_category ON PRODUCTS(category_id);
CREATE INDEX idx_locations_warehouse ON LOCATIONS(warehouse_id,location_type);
CREATE INDEX idx_documents_status_date ON INVENTORY_DOCUMENTS(document_status,business_date);
CREATE INDEX idx_documents_posted_seq ON INVENTORY_DOCUMENTS(posted_at_utc,posting_seq);
CREATE INDEX idx_document_lines_product ON INVENTORY_DOCUMENT_LINES(product_id,document_id);
CREATE INDEX idx_movements_location_time ON INVENTORY_MOVEMENTS(location_id,moved_at_utc);
CREATE INDEX idx_movements_line_role ON INVENTORY_MOVEMENTS(document_line_id,movement_role);
"""

SCHEMAS = {"erp_sales": ERP_SCHEMA, "wms_inventory": WMS_SCHEMA}


def initialize(connection, domain: str) -> None:
    """Create the selected schema and verify FK enforcement is active."""
    connection.execute("PRAGMA foreign_keys = ON")
    if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise RuntimeError("SQLite foreign key enforcement could not be enabled")
    connection.executescript(SCHEMAS[domain])
    if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise RuntimeError("SQLite schema initialization lost foreign key enforcement")
