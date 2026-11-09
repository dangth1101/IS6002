-- DRAFT ONLY: not owner-approved; expected outputs not independently derived.

-- ERP-EF-01 | erp_sales | Simple | NEEDS_HUMAN_REVIEW
SELECT order_id, order_no, customer_id, order_date, order_status FROM SALES_ORDERS WHERE order_status='CONFIRMED' ORDER BY order_id;

-- ERP-EF-02 | erp_sales | Simple | NEEDS_HUMAN_REVIEW
SELECT order_id, order_no, customer_id, order_date, sales_rep_id FROM SALES_ORDERS WHERE order_status='CONFIRMED' AND order_date >= '2025-01-01' AND order_date < '2026-01-01' AND sales_rep_id IS NOT NULL ORDER BY order_id;

-- ERP-EF-03 | erp_sales | Simple | NEEDS_HUMAN_REVIEW
SELECT product_id, sku, product_name, category_id, base_unit FROM PRODUCTS WHERE category_id IS NOT NULL ORDER BY product_id;

-- ERP-EF-04 | erp_sales | Challenging | NEEDS_HUMAN_REVIEW
SELECT o.order_id, o.order_no, date(s.delivered_at_utc, '+7 hours') AS delivered_date_local, o.customer_id, SUM(l.net_vnd) AS net_vnd FROM SALES_ORDERS o JOIN SALES_SHIPMENTS s ON s.order_id=o.order_id JOIN SALES_ORDER_LINES l ON l.order_id=o.order_id WHERE o.order_status='CONFIRMED' AND s.shipment_status='DELIVERED' AND s.delivered_at_utc >= '2025-09-30T17:00:00.000Z' AND s.delivered_at_utc < '2025-12-31T17:00:00.000Z' GROUP BY o.order_id, o.order_no, s.delivered_at_utc, o.customer_id HAVING SUM(l.net_vnd)>100000000 ORDER BY o.order_id;

-- ERP-AG-01 | erp_sales | Simple | NEEDS_HUMAN_REVIEW
SELECT segment, COUNT(DISTINCT customer_id) AS customer_count FROM CUSTOMERS GROUP BY segment ORDER BY segment;

-- ERP-AG-02 | erp_sales | Moderate | NEEDS_HUMAN_REVIEW
SELECT SUM(l.net_vnd) AS order_value_vnd FROM SALES_ORDERS o JOIN SALES_ORDER_LINES l ON l.order_id=o.order_id WHERE o.order_status='CONFIRMED' AND o.order_date >= '2025-01-01' AND o.order_date < '2026-01-01';

-- ERP-AG-03 | erp_sales | Moderate | NEEDS_HUMAN_REVIEW
WITH per_order AS (SELECT o.order_id, SUM(l.net_vnd) AS order_value_vnd FROM SALES_ORDERS o JOIN SALES_ORDER_LINES l ON l.order_id=o.order_id WHERE o.order_status='CONFIRMED' AND o.order_date >= '2025-01-01' AND o.order_date < '2026-01-01' GROUP BY o.order_id) SELECT CAST((2*SUM(order_value_vnd)+COUNT(*))/(2*COUNT(*)) AS INTEGER) AS avg_order_value_vnd FROM per_order;

-- ERP-AG-04 | erp_sales | Moderate | NEEDS_HUMAN_REVIEW
WITH cash_by_order AS (SELECT p.order_id, SUM(CASE p.txn_type WHEN 'CAPTURE' THEN p.amount_vnd ELSE -p.amount_vnd END) AS net_cash_vnd FROM PAYMENT_TRANSACTIONS p WHERE p.txn_status='POSTED' AND p.occurred_at_utc >= '2024-12-31T17:00:00.000Z' AND p.occurred_at_utc < '2025-12-31T17:00:00.000Z' GROUP BY p.order_id), totals AS (SELECT SUM(net_cash_vnd) AS s,COUNT(*) AS n FROM cash_by_order) SELECT CASE WHEN s IS NULL THEN NULL WHEN s>=0 THEN CAST((2*s+n)/(2*n) AS INTEGER) ELSE -CAST((2*ABS(s)+n)/(2*n) AS INTEGER) END AS avg_net_cash_vnd FROM totals;

-- ERP-GB-01 | erp_sales | Simple | NEEDS_HUMAN_REVIEW
SELECT order_status, COUNT(order_id) AS order_count FROM SALES_ORDERS GROUP BY order_status ORDER BY order_status;

-- ERP-GB-02 | erp_sales | Moderate | NEEDS_HUMAN_REVIEW
WITH per_customer AS (SELECT o.customer_id, SUM(l.net_vnd) AS value_vnd FROM SALES_ORDERS o JOIN SALES_ORDER_LINES l ON l.order_id=o.order_id WHERE o.order_status='CONFIRMED' GROUP BY o.customer_id) SELECT c.customer_id, c.customer_name, COALESCE(p.value_vnd,0) AS order_value_vnd FROM CUSTOMERS c LEFT JOIN per_customer p ON p.customer_id=c.customer_id ORDER BY c.customer_id;

-- ERP-GB-03 | erp_sales | Moderate | NEEDS_HUMAN_REVIEW
SELECT o.sales_rep_id, e.full_name, COUNT(o.order_id) AS confirmed_order_count FROM SALES_ORDERS o LEFT JOIN EMPLOYEES e ON e.employee_id=o.sales_rep_id WHERE o.order_status='CONFIRMED' GROUP BY o.sales_rep_id, e.full_name ORDER BY o.sales_rep_id;

-- ERP-GB-04 | erp_sales | Challenging | NEEDS_HUMAN_REVIEW
SELECT strftime('%Y-%m', s.delivered_at_utc, '+7 hours') AS delivery_month_local, SUM(l.net_vnd) AS recognized_revenue_vnd FROM SALES_ORDERS o JOIN SALES_SHIPMENTS s ON s.order_id=o.order_id JOIN SALES_ORDER_LINES l ON l.order_id=o.order_id WHERE o.order_status='CONFIRMED' AND s.shipment_status='DELIVERED' AND s.delivered_at_utc >= '2024-12-31T17:00:00.000Z' AND s.delivered_at_utc < '2025-06-30T17:00:00.000Z' GROUP BY delivery_month_local ORDER BY delivery_month_local;

-- ERP-RK-01 | erp_sales | Moderate | NEEDS_HUMAN_REVIEW
WITH per_customer AS (SELECT o.customer_id, SUM(l.net_vnd) AS revenue_vnd FROM SALES_ORDERS o JOIN SALES_SHIPMENTS s ON s.order_id=o.order_id JOIN SALES_ORDER_LINES l ON l.order_id=o.order_id WHERE o.order_status='CONFIRMED' AND s.shipment_status='DELIVERED' AND s.delivered_at_utc >= '2024-12-31T17:00:00.000Z' AND s.delivered_at_utc < '2025-12-31T17:00:00.000Z' GROUP BY o.customer_id), ranked AS (SELECT *, RANK() OVER(ORDER BY revenue_vnd DESC) AS revenue_rank FROM per_customer) SELECT c.customer_id, c.customer_name, r.revenue_vnd, r.revenue_rank FROM ranked r JOIN CUSTOMERS c ON c.customer_id=r.customer_id WHERE r.revenue_rank<=5 ORDER BY r.revenue_rank,c.customer_id;

-- ERP-RK-02 | erp_sales | Challenging | NEEDS_HUMAN_REVIEW
WITH sku_qty AS (SELECT p.product_id,p.sku,p.product_name,p.base_unit,SUM(l.ordered_qty_milli) AS sold_qty_milli FROM PRODUCTS p JOIN SALES_ORDER_LINES l ON l.product_id=p.product_id JOIN SALES_ORDERS o ON o.order_id=l.order_id WHERE o.order_status='CONFIRMED' GROUP BY p.product_id,p.sku,p.product_name,p.base_unit), ranked AS (SELECT *,RANK() OVER(ORDER BY sold_qty_milli DESC) AS rnk FROM sku_qty) SELECT product_id,sku,product_name,base_unit,sold_qty_milli,rnk FROM ranked WHERE rnk<=3 ORDER BY rnk,product_id;

-- ERP-RK-03 | erp_sales | Challenging | NEEDS_HUMAN_REVIEW
WITH cash_customer AS (SELECT o.customer_id,SUM(CASE p.txn_type WHEN 'CAPTURE' THEN p.amount_vnd ELSE -p.amount_vnd END) AS net_cash_vnd FROM PAYMENT_TRANSACTIONS p JOIN SALES_ORDERS o ON o.order_id=p.order_id WHERE p.txn_status='POSTED' AND p.occurred_at_utc >= '2024-12-31T17:00:00.000Z' AND p.occurred_at_utc < '2025-12-31T17:00:00.000Z' GROUP BY o.customer_id), ranked AS (SELECT *,RANK() OVER(ORDER BY net_cash_vnd DESC) AS rnk FROM cash_customer) SELECT c.customer_id,c.customer_name,r.net_cash_vnd,r.rnk FROM ranked r JOIN CUSTOMERS c ON c.customer_id=r.customer_id WHERE r.rnk=1 ORDER BY c.customer_id;

-- ERP-JN-01 | erp_sales | Simple | NEEDS_HUMAN_REVIEW
WITH order_counts AS (SELECT customer_id,COUNT(order_id) AS n FROM SALES_ORDERS WHERE order_status='CONFIRMED' GROUP BY customer_id) SELECT c.customer_id,c.customer_name,COALESCE(o.n,0) AS confirmed_order_count FROM CUSTOMERS c LEFT JOIN order_counts o ON o.customer_id=c.customer_id ORDER BY c.customer_id;

-- ERP-JN-02 | erp_sales | Moderate | NEEDS_HUMAN_REVIEW
SELECT o.order_no,o.order_date,p.sku,p.product_name,l.ordered_qty_milli,l.net_vnd FROM SALES_ORDERS o JOIN SALES_ORDER_LINES l ON l.order_id=o.order_id JOIN PRODUCTS p ON p.product_id=l.product_id WHERE o.order_status='CONFIRMED' ORDER BY o.order_id,l.line_no;

-- ERP-JN-03 | erp_sales | Moderate | NEEDS_HUMAN_REVIEW
SELECT c.customer_id,c.customer_name,p.category_id,SUM(l.net_vnd) AS recognized_revenue_vnd FROM SALES_ORDERS o JOIN SALES_SHIPMENTS s ON s.order_id=o.order_id JOIN SALES_ORDER_LINES l ON l.order_id=o.order_id JOIN CUSTOMERS c ON c.customer_id=o.customer_id JOIN PRODUCTS p ON p.product_id=l.product_id WHERE o.order_status='CONFIRMED' AND s.shipment_status='DELIVERED' GROUP BY c.customer_id,c.customer_name,p.category_id ORDER BY c.customer_id,p.category_id;

-- ERP-JN-04 | erp_sales | Challenging | NEEDS_HUMAN_REVIEW
SELECT c.customer_id,c.customer_name,p.product_id,p.sku,SUM(rl.return_qty_milli) AS received_return_qty_milli FROM SALES_RETURNS r JOIN SALES_RETURN_LINES rl ON rl.return_id=r.return_id JOIN SALES_ORDERS o ON o.order_id=r.order_id JOIN SALES_ORDER_LINES ol ON ol.order_line_id=rl.order_line_id AND ol.order_id=o.order_id JOIN PRODUCTS p ON p.product_id=ol.product_id JOIN CUSTOMERS c ON c.customer_id=o.customer_id WHERE r.return_status='RECEIVED' GROUP BY c.customer_id,c.customer_name,p.product_id,p.sku ORDER BY c.customer_id,p.product_id;

-- ERP-TM-01 | erp_sales | Simple | NEEDS_HUMAN_REVIEW
SELECT order_id,order_no,customer_id,order_date FROM SALES_ORDERS WHERE order_status='CONFIRMED' AND order_date >= '2025-01-01' AND order_date < '2025-04-01' ORDER BY order_date,order_id;

-- ERP-TM-02 | erp_sales | Moderate | NEEDS_HUMAN_REVIEW
SELECT date(delivered_at_utc,'+7 hours') AS delivered_local_date,COUNT(shipment_id) AS delivered_shipment_count FROM SALES_SHIPMENTS WHERE shipment_status='DELIVERED' AND delivered_at_utc >= '2024-12-31T17:00:00.000Z' AND delivered_at_utc < '2025-12-31T17:00:00.000Z' GROUP BY delivered_local_date ORDER BY delivered_local_date;

-- ERP-NA-01 | erp_sales | Simple | NEEDS_HUMAN_REVIEW
SELECT c.customer_id,c.customer_name FROM CUSTOMERS c WHERE NOT EXISTS (SELECT 1 FROM SALES_ORDERS o WHERE o.customer_id=c.customer_id AND o.order_status='CONFIRMED') ORDER BY c.customer_id;

-- ERP-NA-02 | erp_sales | Moderate | NEEDS_HUMAN_REVIEW
WITH posted AS (SELECT order_id,COUNT(*) AS txn_count,SUM(CASE txn_type WHEN 'CAPTURE' THEN amount_vnd ELSE -amount_vnd END) AS net_cash_vnd FROM PAYMENT_TRANSACTIONS WHERE txn_status='POSTED' GROUP BY order_id) SELECT o.order_id,o.order_no,CASE WHEN p.order_id IS NULL THEN 'NO_POSTED_CASH' ELSE 'ZERO_NET_CASH' END AS cash_state FROM SALES_ORDERS o LEFT JOIN posted p ON p.order_id=o.order_id WHERE o.order_status='CONFIRMED' AND (p.order_id IS NULL OR p.net_cash_vnd=0) ORDER BY o.order_id;

-- ERP-CD-01 | erp_sales | Moderate | NEEDS_HUMAN_REVIEW
WITH order_value AS (SELECT SUM(l.net_vnd) AS value_vnd FROM SALES_ORDERS o JOIN SALES_ORDER_LINES l ON l.order_id=o.order_id WHERE o.order_status='CONFIRMED' AND o.order_date >= '2025-01-01' AND o.order_date < '2026-01-01'), recognized AS (SELECT SUM(l.net_vnd) AS value_vnd FROM SALES_ORDERS o JOIN SALES_SHIPMENTS s ON s.order_id=o.order_id JOIN SALES_ORDER_LINES l ON l.order_id=o.order_id WHERE o.order_status='CONFIRMED' AND s.shipment_status='DELIVERED' AND s.delivered_at_utc >= '2024-12-31T17:00:00.000Z' AND s.delivered_at_utc < '2025-12-31T17:00:00.000Z') SELECT 'ORDER_VALUE' AS metric,value_vnd FROM order_value UNION ALL SELECT 'RECOGNIZED_REVENUE',value_vnd FROM recognized ORDER BY metric;

-- ERP-CD-02 | erp_sales | Moderate | NEEDS_HUMAN_REVIEW
SELECT payment_method,SUM(CASE WHEN txn_type='CAPTURE' THEN amount_vnd ELSE 0 END) AS posted_capture_vnd,SUM(CASE WHEN txn_type='REFUND' THEN amount_vnd ELSE 0 END) AS posted_refund_vnd,SUM(CASE txn_type WHEN 'CAPTURE' THEN amount_vnd ELSE -amount_vnd END) AS posted_net_cash_vnd FROM PAYMENT_TRANSACTIONS WHERE txn_status='POSTED' GROUP BY payment_method ORDER BY payment_method;

-- WMS-EF-01 | wms_inventory | Simple | NEEDS_HUMAN_REVIEW
SELECT document_id,document_no,document_type,document_status,business_date FROM INVENTORY_DOCUMENTS WHERE document_status='POSTED' ORDER BY document_id;

-- WMS-EF-02 | wms_inventory | Simple | NEEDS_HUMAN_REVIEW
SELECT product_id,sku,product_name,base_unit,category_id FROM PRODUCTS WHERE base_unit='KG' ORDER BY product_id;

-- WMS-EF-03 | wms_inventory | Moderate | NEEDS_HUMAN_REVIEW
SELECT m.movement_id,p.sku,l.location_code,m.moved_at_utc,m.qty_delta_milli FROM INVENTORY_MOVEMENTS m JOIN INVENTORY_DOCUMENT_LINES dl ON dl.document_line_id=m.document_line_id JOIN INVENTORY_DOCUMENTS d ON d.document_id=dl.document_id JOIN PRODUCTS p ON p.product_id=dl.product_id JOIN LOCATIONS l ON l.location_id=m.location_id WHERE d.document_status='POSTED' AND l.location_type='STORAGE' ORDER BY m.moved_at_utc,m.movement_id;

-- WMS-EF-04 | wms_inventory | Challenging | NEEDS_HUMAN_REVIEW
WITH balances AS (SELECT dl.product_id,m.location_id,SUM(m.qty_delta_milli) AS on_hand_milli FROM INVENTORY_MOVEMENTS m JOIN INVENTORY_DOCUMENT_LINES dl ON dl.document_line_id=m.document_line_id JOIN INVENTORY_DOCUMENTS d ON d.document_id=dl.document_id WHERE d.document_status='POSTED' AND d.posted_at_utc < '2025-04-01T00:00:00.000Z' GROUP BY dl.product_id,m.location_id) SELECT p.product_id,p.sku,l.location_id,l.location_code,b.on_hand_milli FROM balances b JOIN PRODUCTS p ON p.product_id=b.product_id JOIN LOCATIONS l ON l.location_id=b.location_id WHERE l.location_type='QUARANTINE' AND b.on_hand_milli>0 ORDER BY p.product_id,l.location_id;

-- WMS-AG-01 | wms_inventory | Simple | NEEDS_HUMAN_REVIEW
SELECT COUNT(DISTINCT document_id) AS posted_receipt_count FROM INVENTORY_DOCUMENTS WHERE document_status='POSTED' AND document_type='RECEIPT';

-- WMS-AG-02 | wms_inventory | Moderate | NEEDS_HUMAN_REVIEW
SELECT p.product_id,p.sku,p.base_unit,SUM(-m.qty_delta_milli) AS shipped_qty_milli FROM INVENTORY_MOVEMENTS m JOIN INVENTORY_DOCUMENT_LINES dl ON dl.document_line_id=m.document_line_id JOIN INVENTORY_DOCUMENTS d ON d.document_id=dl.document_id JOIN PRODUCTS p ON p.product_id=dl.product_id WHERE d.document_status='POSTED' AND d.document_type='SHIPMENT' AND p.base_unit='KG' AND m.qty_delta_milli<0 GROUP BY p.product_id,p.sku,p.base_unit ORDER BY p.product_id;

-- WMS-AG-03 | wms_inventory | Moderate | NEEDS_HUMAN_REVIEW
WITH per_location AS (SELECT dl.product_id,p.sku,p.base_unit,m.location_id,SUM(m.qty_delta_milli) AS on_hand_milli FROM INVENTORY_MOVEMENTS m JOIN INVENTORY_DOCUMENT_LINES dl ON dl.document_line_id=m.document_line_id JOIN INVENTORY_DOCUMENTS d ON d.document_id=dl.document_id JOIN PRODUCTS p ON p.product_id=dl.product_id WHERE d.document_status='POSTED' AND d.posted_at_utc<'2025-04-01T00:00:00.000Z' GROUP BY dl.product_id,p.sku,p.base_unit,m.location_id) SELECT product_id,sku,base_unit,CAST((2*SUM(on_hand_milli)+COUNT(*))/(2*COUNT(*)) AS INTEGER) AS avg_location_on_hand_milli FROM per_location GROUP BY product_id,sku,base_unit ORDER BY product_id;

-- WMS-AG-04 | wms_inventory | Challenging | NEEDS_HUMAN_REVIEW
WITH per_location AS (SELECT dl.product_id,p.base_unit,l.warehouse_id,m.location_id,SUM(m.qty_delta_milli) AS q FROM INVENTORY_MOVEMENTS m JOIN INVENTORY_DOCUMENT_LINES dl ON dl.document_line_id=m.document_line_id JOIN INVENTORY_DOCUMENTS d ON d.document_id=dl.document_id JOIN PRODUCTS p ON p.product_id=dl.product_id JOIN LOCATIONS l ON l.location_id=m.location_id WHERE d.document_status='POSTED' GROUP BY dl.product_id,p.base_unit,l.warehouse_id,m.location_id), means AS (SELECT product_id,base_unit,warehouse_id,SUM(q) AS total_q,COUNT(*) AS n FROM per_location GROUP BY product_id,base_unit,warehouse_id) SELECT m.product_id,m.base_unit,m.warehouse_id,SUM(CASE WHEN p.q*m.n<m.total_q THEN 1 ELSE 0 END) AS locations_below_mean FROM per_location p JOIN means m USING(product_id,base_unit,warehouse_id) GROUP BY m.product_id,m.base_unit,m.warehouse_id ORDER BY m.product_id,m.warehouse_id;

-- WMS-GB-01 | wms_inventory | Simple | NEEDS_HUMAN_REVIEW
SELECT document_status,COUNT(DISTINCT document_id) AS document_count FROM INVENTORY_DOCUMENTS GROUP BY document_status ORDER BY document_status;

-- WMS-GB-02 | wms_inventory | Moderate | NEEDS_HUMAN_REVIEW
SELECT d.document_type,p.base_unit,SUM(m.qty_delta_milli) AS net_movement_qty_milli FROM INVENTORY_MOVEMENTS m JOIN INVENTORY_DOCUMENT_LINES dl ON dl.document_line_id=m.document_line_id JOIN INVENTORY_DOCUMENTS d ON d.document_id=dl.document_id JOIN PRODUCTS p ON p.product_id=dl.product_id WHERE d.document_status='POSTED' GROUP BY d.document_type,p.base_unit ORDER BY d.document_type,p.base_unit;

-- WMS-GB-03 | wms_inventory | Moderate | NEEDS_HUMAN_REVIEW
WITH receipt_counts AS (SELECT supplier_id,COUNT(DISTINCT document_id) AS n FROM INVENTORY_DOCUMENTS WHERE document_status='POSTED' AND document_type='RECEIPT' GROUP BY supplier_id) SELECT s.supplier_id,s.supplier_name,COALESCE(r.n,0) AS posted_receipt_count FROM SUPPLIERS s LEFT JOIN receipt_counts r ON r.supplier_id=s.supplier_id ORDER BY s.supplier_id;

-- WMS-GB-04 | wms_inventory | Challenging | NEEDS_HUMAN_REVIEW
WITH loc_balance AS (SELECT dl.product_id,p.base_unit,l.warehouse_id,m.location_id,SUM(m.qty_delta_milli) AS q FROM INVENTORY_MOVEMENTS m JOIN INVENTORY_DOCUMENT_LINES dl ON dl.document_line_id=m.document_line_id JOIN INVENTORY_DOCUMENTS d ON d.document_id=dl.document_id JOIN PRODUCTS p ON p.product_id=dl.product_id JOIN LOCATIONS l ON l.location_id=m.location_id WHERE d.document_status='POSTED' AND d.posted_at_utc<'2025-04-01T00:00:00.000Z' GROUP BY dl.product_id,p.base_unit,l.warehouse_id,m.location_id) SELECT w.warehouse_id,w.warehouse_code,p.product_id,p.sku,p.base_unit,SUM(b.q) AS on_hand_milli FROM loc_balance b JOIN WAREHOUSES w ON w.warehouse_id=b.warehouse_id JOIN PRODUCTS p ON p.product_id=b.product_id GROUP BY w.warehouse_id,w.warehouse_code,p.product_id,p.sku,p.base_unit ORDER BY w.warehouse_id,p.product_id;

-- WMS-RK-01 | wms_inventory | Simple | NEEDS_HUMAN_REVIEW
WITH stock AS (SELECT p.product_id,p.sku,p.product_name,p.base_unit,l.warehouse_id,SUM(m.qty_delta_milli) AS on_hand_milli FROM INVENTORY_MOVEMENTS m JOIN INVENTORY_DOCUMENT_LINES dl ON dl.document_line_id=m.document_line_id JOIN INVENTORY_DOCUMENTS d ON d.document_id=dl.document_id JOIN PRODUCTS p ON p.product_id=dl.product_id JOIN LOCATIONS l ON l.location_id=m.location_id WHERE d.document_status='POSTED' AND p.base_unit='EA' GROUP BY p.product_id,p.sku,p.product_name,p.base_unit,l.warehouse_id), ranked AS (SELECT *,RANK() OVER(PARTITION BY warehouse_id ORDER BY on_hand_milli DESC) AS rnk FROM stock) SELECT product_id,sku,product_name,base_unit,warehouse_id,on_hand_milli,rnk FROM ranked WHERE rnk=1 AND warehouse_id=(SELECT warehouse_id FROM WAREHOUSES WHERE warehouse_code='WH-SG') ORDER BY product_id;

-- WMS-RK-02 | wms_inventory | Moderate | NEEDS_HUMAN_REVIEW
WITH counts AS (SELECT s.supplier_id,s.supplier_name,COUNT(DISTINCT d.document_id) AS receipt_count FROM SUPPLIERS s LEFT JOIN INVENTORY_DOCUMENTS d ON d.supplier_id=s.supplier_id AND d.document_type='RECEIPT' AND d.document_status='POSTED' GROUP BY s.supplier_id,s.supplier_name), ranked AS (SELECT *,RANK() OVER(ORDER BY receipt_count DESC) AS rnk FROM counts) SELECT supplier_id,supplier_name,receipt_count,rnk FROM ranked WHERE rnk<=3 ORDER BY rnk,supplier_id;

-- WMS-RK-03 | wms_inventory | Challenging | NEEDS_HUMAN_REVIEW
WITH stock AS (SELECT p.product_id,p.sku,p.base_unit,l.location_id,l.location_code,SUM(m.qty_delta_milli) AS on_hand_milli FROM INVENTORY_MOVEMENTS m JOIN INVENTORY_DOCUMENT_LINES dl ON dl.document_line_id=m.document_line_id JOIN INVENTORY_DOCUMENTS d ON d.document_id=dl.document_id JOIN PRODUCTS p ON p.product_id=dl.product_id JOIN LOCATIONS l ON l.location_id=m.location_id WHERE d.document_status='POSTED' AND l.location_type='STORAGE' AND p.sku='W-SKU-001' GROUP BY p.product_id,p.sku,p.base_unit,l.location_id,l.location_code), ranked AS (SELECT *,RANK() OVER(ORDER BY on_hand_milli DESC) AS rnk FROM stock) SELECT product_id,sku,base_unit,location_id,location_code,on_hand_milli,rnk FROM ranked WHERE rnk<=3 ORDER BY rnk,location_id;

-- WMS-JN-01 | wms_inventory | Simple | NEEDS_HUMAN_REVIEW
SELECT d.document_id,d.document_no,d.business_date,s.supplier_id,s.supplier_name FROM INVENTORY_DOCUMENTS d JOIN SUPPLIERS s ON s.supplier_id=d.supplier_id WHERE d.document_type='RECEIPT' AND d.document_status='POSTED' ORDER BY d.document_id;

-- WMS-JN-02 | wms_inventory | Moderate | NEEDS_HUMAN_REVIEW
SELECT d.document_no,dl.line_no,p.sku,p.product_name,p.base_unit,dl.planned_qty_milli FROM INVENTORY_DOCUMENTS d JOIN INVENTORY_DOCUMENT_LINES dl ON dl.document_id=d.document_id JOIN PRODUCTS p ON p.product_id=dl.product_id WHERE d.document_type='RECEIPT' AND d.document_status='POSTED' ORDER BY d.document_id,dl.line_no;

-- WMS-JN-03 | wms_inventory | Moderate | NEEDS_HUMAN_REVIEW
SELECT w.warehouse_id,w.warehouse_name,l.location_type,p.base_unit,SUM(m.qty_delta_milli) AS net_qty_milli FROM INVENTORY_MOVEMENTS m JOIN INVENTORY_DOCUMENT_LINES dl ON dl.document_line_id=m.document_line_id JOIN INVENTORY_DOCUMENTS d ON d.document_id=dl.document_id JOIN PRODUCTS p ON p.product_id=dl.product_id JOIN LOCATIONS l ON l.location_id=m.location_id JOIN WAREHOUSES w ON w.warehouse_id=l.warehouse_id WHERE d.document_status='POSTED' GROUP BY w.warehouse_id,w.warehouse_name,l.location_type,p.base_unit ORDER BY w.warehouse_id,l.location_type,p.base_unit;

-- WMS-JN-04 | wms_inventory | Challenging | NEEDS_HUMAN_REVIEW
SELECT d.document_id,d.document_no,dl.line_no,p.sku,m.movement_leg_no,m.movement_role,src.warehouse_code AS source_warehouse,dst.warehouse_code AS destination_warehouse,m.qty_delta_milli,m.moved_at_utc FROM INVENTORY_DOCUMENTS d JOIN INVENTORY_DOCUMENT_LINES dl ON dl.document_id=d.document_id JOIN PRODUCTS p ON p.product_id=dl.product_id JOIN INVENTORY_MOVEMENTS m ON m.document_line_id=dl.document_line_id JOIN LOCATIONS loc ON loc.location_id=m.location_id JOIN WAREHOUSES src ON src.warehouse_id=d.from_warehouse_id JOIN WAREHOUSES dst ON dst.warehouse_id=d.to_warehouse_id WHERE d.document_type='TRANSFER' AND d.document_status='POSTED' ORDER BY d.document_id,dl.line_no,m.movement_leg_no;

-- WMS-TM-01 | wms_inventory | Simple | NEEDS_HUMAN_REVIEW
SELECT document_id,document_no,document_type,document_status,business_date FROM INVENTORY_DOCUMENTS WHERE document_status='POSTED' AND business_date>='2025-01-01' AND business_date<'2025-02-01' ORDER BY business_date,document_id;

-- WMS-TM-02 | wms_inventory | Moderate | NEEDS_HUMAN_REVIEW
SELECT dl.product_id,m.location_id,SUM(m.qty_delta_milli) AS on_hand_change_milli FROM INVENTORY_MOVEMENTS m JOIN INVENTORY_DOCUMENT_LINES dl ON dl.document_line_id=m.document_line_id JOIN INVENTORY_DOCUMENTS d ON d.document_id=dl.document_id WHERE d.document_status='POSTED' AND d.posted_at_utc<'2025-04-01T00:00:00.000Z' GROUP BY dl.product_id,m.location_id ORDER BY dl.product_id,m.location_id;

-- WMS-NA-01 | wms_inventory | Simple | NEEDS_HUMAN_REVIEW
SELECT p.product_id,p.sku,l.location_id,l.location_code FROM PRODUCTS p CROSS JOIN LOCATIONS l WHERE l.location_type='PICKING' AND l.is_active=1 AND NOT EXISTS (SELECT 1 FROM INVENTORY_MOVEMENTS m JOIN INVENTORY_DOCUMENT_LINES dl ON dl.document_line_id=m.document_line_id JOIN INVENTORY_DOCUMENTS d ON d.document_id=dl.document_id WHERE dl.product_id=p.product_id AND m.location_id=l.location_id AND d.document_status='POSTED') ORDER BY p.product_id,l.location_id;

-- WMS-NA-02 | wms_inventory | Moderate | NEEDS_HUMAN_REVIEW
WITH movement_balance AS (SELECT dl.product_id,m.location_id,COUNT(*) AS movement_count,SUM(m.qty_delta_milli) AS q FROM INVENTORY_MOVEMENTS m JOIN INVENTORY_DOCUMENT_LINES dl ON dl.document_line_id=m.document_line_id JOIN INVENTORY_DOCUMENTS d ON d.document_id=dl.document_id WHERE d.document_status='POSTED' GROUP BY dl.product_id,m.location_id) SELECT p.product_id,p.sku,l.location_id,l.location_code,CASE WHEN b.product_id IS NULL THEN 'NO_HISTORY' WHEN b.q=0 THEN 'ZERO_WITH_HISTORY' ELSE 'NONZERO' END AS balance_state,COALESCE(b.q,0) AS on_hand_milli FROM PRODUCTS p CROSS JOIN LOCATIONS l LEFT JOIN movement_balance b ON b.product_id=p.product_id AND b.location_id=l.location_id WHERE b.product_id IS NULL OR b.q=0 ORDER BY p.product_id,l.location_id;

-- WMS-CD-01 | wms_inventory | Moderate | NEEDS_HUMAN_REVIEW
SELECT p.product_id,p.sku,p.base_unit,SUM(CASE WHEN d.document_type='SHIPMENT' AND m.qty_delta_milli<0 THEN -m.qty_delta_milli ELSE 0 END) AS shipped_qty_milli,SUM(m.qty_delta_milli) AS all_net_movement_milli FROM INVENTORY_MOVEMENTS m JOIN INVENTORY_DOCUMENT_LINES dl ON dl.document_line_id=m.document_line_id JOIN INVENTORY_DOCUMENTS d ON d.document_id=dl.document_id JOIN PRODUCTS p ON p.product_id=dl.product_id WHERE d.document_status='POSTED' GROUP BY p.product_id,p.sku,p.base_unit ORDER BY p.product_id;

-- WMS-CD-02 | wms_inventory | Moderate | NEEDS_HUMAN_REVIEW
WITH planned AS (SELECT document_id,product_id,SUM(planned_qty_milli) AS planned_qty_milli FROM INVENTORY_DOCUMENT_LINES GROUP BY document_id,product_id), moved AS (SELECT dl.document_id,dl.product_id,SUM(ABS(m.qty_delta_milli)) AS posted_movement_qty_milli FROM INVENTORY_MOVEMENTS m JOIN INVENTORY_DOCUMENT_LINES dl ON dl.document_line_id=m.document_line_id JOIN INVENTORY_DOCUMENTS d ON d.document_id=dl.document_id WHERE d.document_status='POSTED' GROUP BY dl.document_id,dl.product_id) SELECT d.document_id,d.document_no,d.document_type,p.sku,p.base_unit,pl.planned_qty_milli,COALESCE(mv.posted_movement_qty_milli,0) AS posted_movement_qty_milli FROM INVENTORY_DOCUMENTS d JOIN planned pl ON pl.document_id=d.document_id JOIN PRODUCTS p ON p.product_id=pl.product_id LEFT JOIN moved mv ON mv.document_id=pl.document_id AND mv.product_id=pl.product_id WHERE d.document_status='POSTED' ORDER BY d.document_id,p.product_id;
