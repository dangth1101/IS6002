# BIRD-VN-Robust-50 physical database build

- Build: **PASS**
- Seed: `6002`
- Python: `3.12.6`
- SQLite: `3.45.3`
- Reproducibility: byte-identical SHA-256 on two clean builds

| Database | Rows by table | SHA-256 | Validator |
|---|---|---|---|
| erp_sales | CUSTOMERS=24, EMPLOYEES=5, PRODUCT_CATEGORIES=5, PRODUCTS=12, SALES_ORDERS=72, SALES_ORDER_LINES=216, SALES_SHIPMENTS=48, SALES_RETURNS=4, SALES_RETURN_LINES=4, PAYMENT_TRANSACTIONS=44 | `347c0e7b663d74c740c6b1fba4a2b89a6ca21beeb4148bd8bff41ed3a4ca888b` | PASS |
| wms_inventory | PRODUCT_CATEGORIES=4, PRODUCTS=18, SUPPLIERS=4, CUSTOMERS=8, WAREHOUSES=2, LOCATIONS=8, INVENTORY_DOCUMENTS=46, INVENTORY_DOCUMENT_LINES=80, INVENTORY_MOVEMENTS=90 | `c55c41e8755dccd1e0d77aaaf86b0dcf2895b75ae8a8d5b1891774e26cf589d5` | PASS |

See `validation/` for per-invariant evidence and `build_manifest.json` for versions and hashes.
No benchmark questions or canonical SQL were created.
