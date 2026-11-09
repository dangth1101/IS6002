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
