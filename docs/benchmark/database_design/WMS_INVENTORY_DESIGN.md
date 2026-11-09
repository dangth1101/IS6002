# WMS Inventory — Logical Schema Design

| Thuộc tính | Giá trị |
|---|---|
| Version / status | 0.1.0 — Draft, logic-only |
| Phạm vi dự kiến | 25 Semantic Groups của WMS Inventory |
| Domain authority | Chưa có WMS cụ thể hoặc Domain Owner được chỉ định; status/business rules dưới đây là mô phỏng |

## 1. Phạm vi nghiệp vụ

Mô phỏng quản lý SKU, kho/vị trí, đối tác và chứng từ nhập, xuất, điều chỉnh, chuyển kho, khách trả hàng. INVENTORY_MOVEMENTS là ledger quantity có dấu; tồn tại thời điểm/snapshot suy ra từ tổng movement đã post. Thiết kế hỗ trợ filter, aggregate, grouping, ranking/ties, joins, date boundaries, NULL/zero/absence và conditional metrics.

**Out of scope:** wave/pick/pack, serial tracking, lot/expiry/FEFO, reservations, replenishment, cycle count workflow, unit conversions, multi-currency valuation, FIFO/average costing, reversal audit trail, warehouse calendars. Cần bổ sung mô hình và rule nếu các khái niệm này xuất hiện trong Intent Cards.

## 2. ERD logic

~~~mermaid
erDiagram
    PRODUCT_CATEGORIES o|--o{ PRODUCTS : classifies
    PRODUCTS ||--o{ INVENTORY_DOCUMENT_LINES : references
    SUPPLIERS o|--o{ INVENTORY_DOCUMENTS : supplies
    CUSTOMERS o|--o{ INVENTORY_DOCUMENTS : receives
    WAREHOUSES ||--o{ LOCATIONS : contains
    WAREHOUSES o|--o{ INVENTORY_DOCUMENTS : operates
    WAREHOUSES o|--o{ INVENTORY_DOCUMENTS : transfer_from
    WAREHOUSES o|--o{ INVENTORY_DOCUMENTS : transfer_to
    INVENTORY_DOCUMENTS ||--|{ INVENTORY_DOCUMENT_LINES : contains
    INVENTORY_DOCUMENT_LINES ||--o{ INVENTORY_MOVEMENTS : posts
    LOCATIONS ||--o{ INVENTORY_MOVEMENTS : records_at

    PRODUCT_CATEGORIES {
      INTEGER category_id PK
      TEXT category_name UK
      INTEGER parent_category_id FK
    }
    PRODUCTS {
      INTEGER product_id PK
      TEXT sku UK
      TEXT product_name
      INTEGER category_id FK
      TEXT base_unit
      INTEGER standard_cost_vnd
      INTEGER is_active
    }
    SUPPLIERS {
      INTEGER supplier_id PK
      TEXT supplier_code UK
      TEXT supplier_name
      TEXT region
      INTEGER is_active
    }
    CUSTOMERS {
      INTEGER customer_id PK
      TEXT customer_code UK
      TEXT customer_name
      TEXT region
      INTEGER is_active
    }
    WAREHOUSES {
      INTEGER warehouse_id PK
      TEXT warehouse_code UK
      TEXT warehouse_name
      TEXT region
      INTEGER is_active
    }
    LOCATIONS {
      INTEGER location_id PK
      INTEGER warehouse_id FK
      TEXT location_code
      TEXT location_type
      INTEGER is_active
    }
    INVENTORY_DOCUMENTS {
      INTEGER document_id PK
      TEXT document_no UK
      TEXT document_type
      TEXT document_status
      INTEGER supplier_id FK
      INTEGER customer_id FK
      INTEGER warehouse_id FK
      INTEGER from_warehouse_id FK
      INTEGER to_warehouse_id FK
      TEXT business_date
      TEXT created_at_utc
      TEXT posted_at_utc
    }
    INVENTORY_DOCUMENT_LINES {
      INTEGER document_line_id PK
      INTEGER document_id FK
      INTEGER line_no
      INTEGER product_id FK
      INTEGER planned_qty_milli
    }
    INVENTORY_MOVEMENTS {
      INTEGER movement_id PK
      INTEGER document_line_id FK
      INTEGER location_id FK
      INTEGER qty_delta_milli
      INTEGER unit_cost_vnd
      TEXT moved_at_utc
    }
~~~

### Cardinality và integrity notes

- Một warehouse có 1..N locations; (warehouse_id,location_code) duy nhất. Mỗi movement ở đúng một location.
- Document có 1..N lines; line có một product. Một line có 0..N movements; document draft/cancelled không có movement hiệu lực.
- Receipt/customer return tạo movement dương; shipment tạo âm; adjustment +/-; transfer có leg âm ở nguồn, leg dương ở đích và tổng lượng bằng 0.
- warehouse_id dùng cho RECEIPT/SHIPMENT/ADJUSTMENT/CUSTOMER_RETURN; from_warehouse_id/to_warehouse_id chỉ dùng cho TRANSFER.
- Supplier hợp lệ với RECEIPT; customer hợp lệ với SHIPMENT/CUSTOMER_RETURN. Type-dependent và location/warehouse checks là cross-row rules.
- Không có bảng balance snapshot. On-hand theo product/location là SUM movement tới cutoff; warehouse balance là tổng locations.
- FK ON DELETE RESTRICT; benchmark dataset được freeze, không xóa historical documents.

## 3. Data Dictionary

SQLite affinity và date/time encoding là lựa chọn thiết kế; SQLite không có storage class riêng cho DATE/TIME. [SQLite Datatypes](https://www.sqlite.org/datatype3.html). FK enforcement cần bật theo từng connection khi triển khai. [SQLite Foreign Key Support](https://www.sqlite.org/foreignkeys.html).

### PRODUCT_CATEGORIES

| Thuộc tính | SQLite type | NULL | Key/constraint | Miền / ý nghĩa |
|---|---|---:|---|---|
| category_id | INTEGER | No | PK | ID danh mục |
| category_name | TEXT | No | UNIQUE | Tên không rỗng |
| parent_category_id | INTEGER | Yes | FK self | NULL nếu root; không self-parent/cycle |

### PRODUCTS

| Thuộc tính | SQLite type | NULL | Key/constraint | Miền / ý nghĩa |
|---|---|---:|---|---|
| product_id | INTEGER | No | PK | ID sản phẩm |
| sku | TEXT | No | UNIQUE | SKU synthetic, ổn định |
| product_name | TEXT | No | — | Tên hiển thị |
| category_id | INTEGER | Yes | FK → PRODUCT_CATEGORIES | NULL nếu chưa phân loại |
| base_unit | TEXT | No | CHECK | EA / KG / L theo whitelist |
| standard_cost_vnd | INTEGER | No | CHECK ≥ 0 | Cost tham chiếu mô phỏng, không phải FIFO/average valuation |
| is_active | INTEGER | No | CHECK 0/1 | Active tại snapshot; không đồng nghĩa còn hàng |

### SUPPLIERS và CUSTOMERS

| Bảng.thuộc tính | SQLite type | NULL | Key/constraint | Miền / ý nghĩa |
|---|---|---:|---|---|
| SUPPLIERS.supplier_id | INTEGER | No | PK | ID supplier |
| SUPPLIERS.supplier_code | TEXT | No | UNIQUE | Mã synthetic |
| SUPPLIERS.supplier_name | TEXT | No | — | Tên supplier |
| SUPPLIERS.region | TEXT | Yes | — | Region mô phỏng |
| SUPPLIERS.is_active | INTEGER | No | CHECK 0/1 | Trạng thái snapshot |
| CUSTOMERS.customer_id | INTEGER | No | PK | ID customer |
| CUSTOMERS.customer_code | TEXT | No | UNIQUE | Mã customer synthetic |
| CUSTOMERS.customer_name | TEXT | No | — | Tên customer |
| CUSTOMERS.region | TEXT | Yes | — | Region mô phỏng |
| CUSTOMERS.is_active | INTEGER | No | CHECK 0/1 | Trạng thái snapshot |

### WAREHOUSES và LOCATIONS

| Bảng.thuộc tính | SQLite type | NULL | Key/constraint | Miền / ý nghĩa |
|---|---|---:|---|---|
| WAREHOUSES.warehouse_id | INTEGER | No | PK | ID kho |
| WAREHOUSES.warehouse_code | TEXT | No | UNIQUE | Mã kho |
| WAREHOUSES.warehouse_name | TEXT | No | — | Tên kho |
| WAREHOUSES.region | TEXT | Yes | — | Region mô phỏng |
| WAREHOUSES.is_active | INTEGER | No | CHECK 0/1 | Active không khẳng định có tồn |
| LOCATIONS.location_id | INTEGER | No | PK | ID vị trí |
| LOCATIONS.warehouse_id | INTEGER | No | FK → WAREHOUSES | Kho sở hữu |
| LOCATIONS.location_code | TEXT | No | UNIQUE with warehouse_id | Mã duy nhất trong kho |
| LOCATIONS.location_type | TEXT | No | CHECK | RECEIVING / STORAGE / PICKING / STAGING / QUARANTINE |
| LOCATIONS.is_active | INTEGER | No | CHECK 0/1 | Trạng thái snapshot |

### INVENTORY_DOCUMENTS

| Thuộc tính | SQLite type | NULL | Key/constraint | Miền / ý nghĩa |
|---|---|---:|---|---|
| document_id | INTEGER | No | PK | ID chứng từ |
| document_no | TEXT | No | UNIQUE | Mã chứng từ |
| document_type | TEXT | No | CHECK | RECEIPT / SHIPMENT / ADJUSTMENT / TRANSFER / CUSTOMER_RETURN |
| document_status | TEXT | No | CHECK | DRAFT / POSTED / CANCELLED; dùng chung cho receipt/shipment/adjustment/transfer |
| supplier_id | INTEGER | Yes | FK → SUPPLIERS | Required cho RECEIPT, nếu không NULL |
| customer_id | INTEGER | Yes | FK → CUSTOMERS | Required cho SHIPMENT/CUSTOMER_RETURN |
| warehouse_id | INTEGER | Yes | FK → WAREHOUSES | Required cho non-TRANSFER |
| from_warehouse_id | INTEGER | Yes | FK → WAREHOUSES | Required chỉ với TRANSFER |
| to_warehouse_id | INTEGER | Yes | FK → WAREHOUSES | Required chỉ với TRANSFER, khác from |
| business_date | TEXT | No | YYYY-MM-DD | Ngày local Asia/Ho_Chi_Minh |
| created_at_utc | TEXT | No | ISO-8601 UTC | Thời điểm tạo document |
| posted_at_utc | TEXT | Yes | ISO-8601 UTC | Bắt buộc khi POSTED; không trước created |

### INVENTORY_DOCUMENT_LINES

| Thuộc tính | SQLite type | NULL | Key/constraint | Miền / ý nghĩa |
|---|---|---:|---|---|
| document_line_id | INTEGER | No | PK | ID dòng |
| document_id | INTEGER | No | FK → INVENTORY_DOCUMENTS | Header sở hữu |
| line_no | INTEGER | No | UNIQUE with document_id; > 0 | Thứ tự dòng |
| product_id | INTEGER | No | FK → PRODUCTS | SKU liên quan |
| planned_qty_milli | INTEGER | No | CHECK > 0 | Quantity × 1000, magnitude trên chứng từ |

### INVENTORY_MOVEMENTS

| Thuộc tính | SQLite type | NULL | Key/constraint | Miền / ý nghĩa |
|---|---|---:|---|---|
| movement_id | INTEGER | No | PK | ID ledger movement |
| document_line_id | INTEGER | No | FK → INVENTORY_DOCUMENT_LINES | Source line |
| location_id | INTEGER | No | FK → LOCATIONS | Vị trí nhận/trừ stock |
| qty_delta_milli | INTEGER | No | CHECK <> 0 | Dương tăng tồn; âm giảm tồn |
| unit_cost_vnd | INTEGER | Yes | CHECK ≥ 0 | Cost snapshot/base unit; NULL nếu không định giá |
| moved_at_utc | TEXT | No | ISO-8601 UTC | Thời điểm movement post |

Cross-row validation: movement chỉ thuộc document POSTED; receipt/shipment/adjustment line có tổng absolute movement bằng planned quantity; transfer có tổng signed quantity 0, đủ source leg âm và destination leg dương; location thuộc warehouse phù hợp. Field-level CHECK không thay các invariant này.

## 4. Business Rules

> Mọi quy tắc dưới đây là **Mô phỏng — đề xuất cần Benchmark Owner xác nhận**, không phải chuẩn WMS phổ quát.

| ID | Quy tắc mô phỏng | Cách diễn giải / truy vấn |
|---|---|---|
| WMS-BR-01 | Chỉ POSTED documents ảnh hưởng stock | DRAFT/CANCELLED không có movement hiệu lực. Receipt/shipment không có thêm trạng thái packed, in-transit hoặc quality inspection trong mô hình này. |
| WMS-BR-02 | Signed movement là nguồn quantity | Receipt/return dương; shipment âm; transfer có hai legs đối dấu; adjustment tùy kiểm kê. |
| WMS-BR-03 | On-hand tại T = tổng movement đã post | Filter moved_at_utc < cutoff_utc; kết quả có thể bằng 0. No movement và movement net 0 khác nhau với truy vấn lịch sử. |
| WMS-BR-04 | Không có balance snapshot | Không cache on-hand; warehouse quantity là tổng locations cùng SKU/base unit. |
| WMS-BR-05 | Tồn âm không hợp lệ trong fixture chuẩn | Chỉ dùng negative-balance case như counterexample nếu Owner chấp thuận. |
| WMS-BR-06 | Transfer không đổi tổng tồn toàn hệ thống | Phải tính cả hai legs; tồn ở warehouse nguồn/đích thay đổi riêng. |
| WMS-BR-07 | Quantity cùng base unit của product | Không cộng quantity khác base_unit; không có conversion table. |
| WMS-BR-08 | Inventory value không mặc định là accounting valuation | Nếu dùng, metric riêng bằng movement unit_cost_vnd snapshot; không gọi FIFO/average valuation. |
| WMS-BR-09 | Time range dùng [start,end) | Timestamp UTC; business day biên quy đổi từ Asia/Ho_Chi_Minh. |
| WMS-BR-10 | No movement khác movement net 0 | COUNT movement, SUM signed qty và on-hand là câu hỏi khác nhau. |
| WMS-BR-11 | Một document line có thể có nhiều movement legs | Aggregate đúng grain; không SUM planned_qty sau join movements. |
| WMS-BR-12 | Active flags không tự lọc lịch sử | Chỉ filter current active nếu Intent Card yêu cầu. |

## 5. Business Glossary — đề xuất mô phỏng

| Thuật ngữ tiếng Việt | Nghĩa đề xuất | Tránh nhập nhằng |
|---|---|---|
| Chứng từ kho | INVENTORY_DOCUMENTS header | Khác movement ledger |
| Dòng chứng từ | SKU và quantity kế hoạch | Có thể tạo nhiều movement |
| Biến động tồn | Ledger row signed quantity tại location | Grain của movement count |
| Nhập kho | RECEIPT posted, movement dương | Draft không làm tăng tồn |
| Xuất kho | SHIPMENT posted, movement âm | Không nhầm với order ERP |
| Điều chuyển | TRANSFER có leg giảm nguồn/tăng đích | Tổng network giữ nguyên theo mô hình |
| Điều chỉnh | ADJUSTMENT do kiểm kê mô phỏng | Dấu movement chỉ tăng/giảm |
| Tồn hiện tại | Tổng signed movements đến snapshot cutoff | Khác tổng nhập trừ xuất nếu bỏ adjustment/transfer |
| Tồn theo vị trí | On-hand SKU tại một location | Có thể zero dù có history |
| Tồn theo kho | Tổng on-hand locations của warehouse | Không cộng quantity nhiều base units |
| Supplier/Customer | Đối tác trên receipt/shipment/return | Region/active là thuộc tính mô phỏng |

## 6. Edge-case Plan — chưa tạo dữ liệu

| Case cần fixture | Biến thể cần phân biệt | Lỗi SQL có thể phát hiện |
|---|---|---|
| Một SKU ở nhiều locations/warehouses | Product vs product-location grain | SUM stock bị nhân khi join category/location |
| Hai movement hợp lệ cùng product/location nhưng khác document | Lặp khóa nghiệp vụ ở nhiều giao dịch | DISTINCT product/location làm mất movement hoặc tổng quantity |
| Lặp movement bất thường với cùng document line/location/amount | Duplicate transaction | SUM không phát hiện duplicate posting; fixture phải kiểm tra source identity và expected movement count |
| Transfer có hai legs cùng line | Source/destination signs | Chỉ lấy một leg hoặc đếm quantity hai lần |
| DRAFT document có planned lines, không movement | Planned vs posted | Tính tồn từ planned quantity |
| Hai movement trái dấu tổng bằng 0 | Zero vs absence | Coi no-movement giống stock zero có history |
| Movement ngay trước/đúng cutoff | As-of semantics | < cutoff và <= cutoff khác kết quả |
| UTC/local nửa đêm | Timezone boundary | Lọc UTC date thay local business date |
| Hai SKU cùng tên | Identity/grouping | Group theo name thay product_id/SKU |
| NULL unit cost và cost zero | Unknown vs zero | Coi cost chưa biết là zero value |
| Nhiều movement trên một document line | Join fan-out | COUNT line hoặc SUM planned qty sau join |
| Hai SKU cùng on-hand | Ranking ties | Top-1 tùy ý; cần explicit tie policy |
| SKU active nhưng chưa movement | Entity absence | INNER JOIN loại SKU khỏi no-movement query |
| Inactive/quarantine location | Location inclusion | Tự loại location khi hỏi total stock |
| Adjustment đưa tồn về zero | Explicit zero | HAVING SUM(qty)>0 làm mất zero stock |
| Transfer giữa locations cùng warehouse | Location vs warehouse grain | Gọi transfer là nhập/xuất ở cấp kho |

Truy vấn về available/sellable/reserved/valuation bị chặn tới khi có model và rule bổ sung. Với mỗi Intent Card, chọn edge cases liên quan và ghi expected output trước SQL execution theo [ANNOTATION_REVIEW_TEMPLATE.md](../ANNOTATION_REVIEW_TEMPLATE.md).

## 7. Source vs simulation register

| Nội dung | Nguồn | Trạng thái |
|---|---|---|
| 25 WMS groups; competency/complexity quota; SQLite/split/metrics | BENCHMARK_SPEC.md §2/§6; Decision Review D2, D4, D11 | Project decision; approved for benchmark scope |
| SQLite affinity/date-time/FK behavior | Official SQLite docs linked in database_design README | External technical fact |
| Document types/statuses, movement signs, on-hand, UOM, cost meaning, timezone | No WMS-specific source supplied | Synthetic simulation; pending owner/domain review |
