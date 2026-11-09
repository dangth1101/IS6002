# erp_sales validation report

- Status: **PASS**
- Database SHA-256: `347c0e7b663d74c740c6b1fba4a2b89a6ca21beeb4148bd8bff41ed3a4ca888b`
- Python: 3.12.6
- SQLite: 3.45.3

## Row counts

| Table | Rows |
|---|---:|
| CUSTOMERS | 24 |
| EMPLOYEES | 5 |
| PRODUCT_CATEGORIES | 5 |
| PRODUCTS | 12 |
| SALES_ORDERS | 72 |
| SALES_ORDER_LINES | 216 |
| SALES_SHIPMENTS | 48 |
| SALES_RETURNS | 4 |
| SALES_RETURN_LINES | 4 |
| PAYMENT_TRANSACTIONS | 44 |

## Invariant results

| ID | Status | Checked | Failures | Description |
|---|---|---:|---:|---|
| DB-FK-001 | PASS | 434 | 0 | Foreign key enforcement enabled and referential integrity clean |
| DB-TIME-001 | PASS | 278 | 0 | All timestamps and business dates use valid canonical formats |
| ERP-CATEGORY-001 | PASS | 5 | 0 | Category hierarchy contains no cycles |
| ERP-MONEY-001 | PASS | 216 | 0 | Line arithmetic and HALF_UP calculations |
| ERP-CAPS-001 | PASS | 260 | 0 | Row caps and aggregate overflow bounds |
| ERP-ORDER-001 | PASS | 72 | 0 | Orders have valid statuses and at least one line |
| ERP-SHIP-001 | PASS | 48 | 0 | Shipment state and event timestamp invariants |
| ERP-PAY-001 | PASS | 44 | 0 | Payment type, return/order identity, sequence and refund cap |
| ERP-RETURN-001 | PASS | 4 | 0 | Return line ownership, received timestamps and cumulative quantity |
| ERP-METRIC-001 | PASS | 72 | 0 | Independent order value/revenue/cash measures and business dates are distinguishable |
