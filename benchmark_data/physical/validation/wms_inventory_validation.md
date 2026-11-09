# wms_inventory validation report

- Status: **PASS**
- Database SHA-256: `c55c41e8755dccd1e0d77aaaf86b0dcf2895b75ae8a8d5b1891774e26cf589d5`
- Python: 3.12.6
- SQLite: 3.45.3

## Row counts

| Table | Rows |
|---|---:|
| PRODUCT_CATEGORIES | 4 |
| PRODUCTS | 18 |
| SUPPLIERS | 4 |
| CUSTOMERS | 8 |
| WAREHOUSES | 2 |
| LOCATIONS | 8 |
| INVENTORY_DOCUMENTS | 46 |
| INVENTORY_DOCUMENT_LINES | 80 |
| INVENTORY_MOVEMENTS | 90 |

## Invariant results

| ID | Status | Checked | Failures | Description |
|---|---|---:|---:|---|
| DB-FK-001 | PASS | 260 | 0 | Foreign key enforcement enabled and referential integrity clean |
| DB-TIME-001 | PASS | 226 | 0 | All timestamps and business dates use valid canonical formats |
| WMS-CATEGORY-001 | PASS | 4 | 0 | Category hierarchy contains no cycles |
| WMS-DOC-001 | PASS | 46 | 0 | Document type/status, posting state and lifecycle |
| WMS-MOV-001 | PASS | 80 | 0 | Movement direction, line totals and transfer pair invariants |
| WMS-SEQ-001 | PASS | 44 | 0 | Every posted document has a unique batch sequence |
| WMS-CAPS-001 | PASS | 90 | 0 | Movement caps and signed 64-bit aggregate bounds |
| WMS-ID-001 | PASS | 90 | 0 | Stable source/leg identities are unique |
| WMS-STOCK-001 | PASS | 44 | 0 | Stock is nonnegative after each atomic posting batch |
| WMS-UOM-001 | PASS | 36 | 0 | On-hand aggregation retains base unit and includes a meaningful ranking tie |
