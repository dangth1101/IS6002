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
