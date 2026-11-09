# WMS Inventory — Logical Schema Design

| Thuộc tính | Giá trị |
|---|---|
| Version / status | 0.2.0 — Logic design accepted; physical schema v1 and snapshots accepted by Benchmark Owner, see [Bước 2B artifacts](../physical_database/README.md) |
| Phạm vi dự kiến | 25 Semantic Groups của WMS Inventory |
| Domain authority | Chưa có WMS cụ thể/Domain Owner; Benchmark Owner chấp nhận các simulation rules cho logic design ngày 2026-11-09 |

## 1. Phạm vi nghiệp vụ

Mô phỏng quản lý SKU, kho/vị trí, đối tác và chứng từ nhập, xuất, điều chỉnh, chuyển kho, khách trả hàng. INVENTORY_MOVEMENTS là ledger quantity có dấu; tồn tại thời điểm/snapshot suy ra từ tổng movement đã post. Thiết kế hỗ trợ filter, aggregate, grouping, ranking/ties, joins, date boundaries, NULL/zero/absence và conditional metrics.

**Out of scope:** inventory valuation (excluded from all 50 intents), wave/pick/pack, serial tracking, lot/expiry/FEFO, reservations, replenishment, cycle count workflow, unit conversions, FIFO/average costing, reversal audit trail, warehouse calendars. Cần bổ sung mô hình và rule nếu các khái niệm này xuất hiện trong Intent Cards.

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
      INTEGER posting_seq UK
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
      INTEGER movement_leg_no
      TEXT movement_role
      TEXT source_movement_ref UK
      INTEGER location_id FK
      INTEGER qty_delta_milli
      TEXT moved_at_utc
    }
~~~

### Cardinality và integrity notes

- Một warehouse có 1..N locations; (warehouse_id,location_code) duy nhất. Mỗi movement ở đúng một location.
- Document có 1..N lines; line có một product. Một line có 0..N movements; document draft/cancelled không có movement hiệu lực. POSTED transfer line phải có đúng 2 legs.
- Receipt/customer return tạo movement dương; shipment tạo âm; adjustment +/-; transfer có leg âm ở nguồn, leg dương ở đích và tổng lượng bằng 0.
- warehouse_id dùng cho RECEIPT/SHIPMENT/ADJUSTMENT/CUSTOMER_RETURN; from_warehouse_id/to_warehouse_id chỉ dùng cho TRANSFER.
- Transfer chỉ giữa hai warehouse khác nhau; đúng hai legs cho mỗi transfer line, không có transfer giữa locations cùng warehouse.
- Supplier hợp lệ với RECEIPT; customer hợp lệ với SHIPMENT/CUSTOMER_RETURN. Type-dependent và location/warehouse checks là cross-row rules.
- TRANSFER chỉ giữa hai warehouse khác nhau; không hỗ trợ transfer giữa locations thuộc cùng warehouse.
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
| document_status | TEXT | No | CHECK | DRAFT / POSTED / CANCELLED; dùng chung cho mọi document type |
| supplier_id | INTEGER | Yes | FK → SUPPLIERS | Required cho RECEIPT, nếu không NULL |
| customer_id | INTEGER | Yes | FK → CUSTOMERS | Required cho SHIPMENT/CUSTOMER_RETURN |
| warehouse_id | INTEGER | Yes | FK → WAREHOUSES | Required cho non-TRANSFER |
| from_warehouse_id | INTEGER | Yes | FK → WAREHOUSES | Required chỉ với TRANSFER |
| to_warehouse_id | INTEGER | Yes | FK → WAREHOUSES | Required chỉ với TRANSFER, khác from |
| business_date | TEXT | No | YYYY-MM-DD | Ngày nghiệp vụ ghi riêng; có thể khác ngày local khi tạo/post |
| created_at_utc | TEXT | No | ISO-8601 UTC milliseconds | Thời điểm tạo document |
| posted_at_utc | TEXT | Yes | ISO-8601 UTC milliseconds | Bắt buộc khi POSTED; không trước created; là event-time movement |
| posting_seq | INTEGER | Yes | UNIQUE; > 0 | Thứ tự posting batch; required khi POSTED và sắp batch cùng timestamp |

business_date không suy ra từ created_at_utc và không bắt buộc bằng ngày local posted_at_utc. Business-date reports lọc field này; as-of/on-hand theo event time dùng posted_at_utc/moved_at_utc.

### INVENTORY_DOCUMENT_LINES

| Thuộc tính | SQLite type | NULL | Key/constraint | Miền / ý nghĩa |
|---|---|---:|---|---|
| document_line_id | INTEGER | No | PK | ID dòng |
| document_id | INTEGER | No | FK → INVENTORY_DOCUMENTS | Header sở hữu |
| line_no | INTEGER | No | UNIQUE with document_id; > 0 | Thứ tự dòng |
| product_id | INTEGER | No | FK → PRODUCTS | SKU liên quan |
| planned_qty_milli | INTEGER | No | CHECK 1..1,000,000,000 | Quantity × 1000, magnitude trên chứng từ; cap mô phỏng |

### INVENTORY_MOVEMENTS

| Thuộc tính | SQLite type | NULL | Key/constraint | Miền / ý nghĩa |
|---|---|---:|---|---|
| movement_id | INTEGER | No | PK | ID ledger movement |
| document_line_id | INTEGER | No | FK → INVENTORY_DOCUMENT_LINES | Source line |
| movement_leg_no | INTEGER | No | UNIQUE with document_line_id; > 0 | Ordinal ổn định trong document line |
| movement_role | TEXT | No | CHECK | MAIN / SOURCE / DESTINATION; transfer cần đúng SOURCE và DESTINATION |
| source_movement_ref | TEXT | No | UNIQUE | Stable source/leg identity chống duplicate posting; event hợp lệ tương tự có ref khác |
| location_id | INTEGER | No | FK → LOCATIONS | Vị trí nhận/trừ stock |
| qty_delta_milli | INTEGER | No | CHECK <> 0 AND abs(qty_delta_milli) ≤ 1,000,000,000 | Dương tăng tồn; âm giảm tồn; magnitude theo cap mô phỏng |
| moved_at_utc | TEXT | No | ISO-8601 UTC milliseconds | Phải bằng document.posted_at_utc; dùng cho as-of event time |

Mỗi source_movement_ref đại diện một source line/leg duy nhất, không phải fingerprint của giá trị cột. Movement hợp lệ giống nhau về product/location/quantity/time vẫn được giữ nếu source ref/leg khác. Giới hạn mô phỏng: tối đa 100,000 movements/database; với cap 1,000,000,000 milli-unit/movement, aggregate tối đa 10^14 milli-unit, dưới signed 64-bit.

Cross-row validation: movement chỉ thuộc document POSTED; mọi movement time bằng posted_at_utc. Receipt/shipment/adjustment line có tổng absolute movement bằng planned quantity. Mỗi transfer line có đúng hai legs cùng magnitude: SOURCE âm tại from warehouse, DESTINATION dương tại to warehouse; locations/warehouses khác nhau. Hai legs chung document/batch, timestamp và atomic commit. posting_seq duy nhất sắp documents có cùng timestamp.

## 4. Business Rules

> Mọi quy tắc dưới đây là **synthetic simulation assumptions được Benchmark Owner chấp nhận cho logic design ngày 2026-11-09**; không phải chuẩn WMS phổ quát.

| ID | Quy tắc mô phỏng | Cách diễn giải / truy vấn |
|---|---|---|
| WMS-BR-01 | Chỉ POSTED documents ảnh hưởng stock | DRAFT/CANCELLED không có movement hiệu lực. Receipt/shipment không có thêm trạng thái packed, in-transit hoặc quality inspection trong mô hình này. |
| WMS-BR-02 | Signed movement là nguồn quantity | Receipt/return dương; shipment âm; transfer có hai legs đối dấu; adjustment tùy kiểm kê. |
| WMS-BR-03 | On-hand tại T = tổng movement đã post | Filter moved_at_utc < cutoff_utc; timestamp bằng cutoff bị loại toàn bộ. Reconstruct running balance theo (posted_at_utc,posting_seq), mỗi document là atomic posting batch; kết quả có thể bằng 0. No movement và movement net 0 khác nhau. |
| WMS-BR-04 | Không có balance snapshot | Không cache on-hand; warehouse quantity là tổng locations cùng SKU/base unit. |
| WMS-BR-05 | Tồn âm không hợp lệ trong snapshot benchmark | Sau mỗi posting batch theo (posted_at_utc,posting_seq), running balance product/location >= 0. Negative stock chỉ là invalid-fixture check, không phải benchmark state. |
| WMS-BR-06 | Transfer atomic, không đổi tổng tồn network | Mỗi transfer line đúng 2 movement đối dấu cùng quantity/timestamp; location và warehouse khác nhau; cùng atomic transaction. |
| WMS-BR-07 | Quantity cùng base unit của product | Không cộng quantity khác base_unit; không có conversion table; SUM/AVG phải giữ unit hoặc group theo unit. |
| WMS-BR-08 | Inventory valuation nằm ngoài 50 intents | Không có standard/unit cost trong logical schema; không hỏi inventory value, FIFO hoặc average costing. |
| WMS-BR-09 | Business date độc lập với system/event timestamps | business_date được ghi riêng; có thể khác local date của created_at_utc hoặc posted_at_utc. |
| WMS-BR-10 | Timestamp và date range chuẩn hóa | Timestamp YYYY-MM-DDTHH:MM:SS.SSSZ; range [start,end). Biên Asia/Ho_Chi_Minh đổi UTC trước event-time query; business_date filter trực tiếp. |
| WMS-BR-11 | No movement khác movement net 0 | COUNT movement, SUM signed qty và on-hand là câu hỏi khác nhau. |
| WMS-BR-12 | Một document line có thể có nhiều movement legs | Aggregate đúng grain; không SUM planned_qty sau join movements. |
| WMS-BR-13 | Active flags không tự lọc lịch sử | Chỉ filter current active nếu Intent Card yêu cầu. |
| WMS-BR-14 | AVG quantity có kiểu/precision cố định | Với S = SUM(qty_milli), N = COUNT(qty_milli), AVG trả INTEGER milli-unit theo sign(S) × floor((2×abs(S)+N)/(2×N)); tie HALF_UP làm tròn xa zero. SUM giữ INTEGER milli-unit. |
| WMS-BR-15 | Ranking khai báo tie policy | Mỗi Intent Card chọn deterministic tie-break hoặc include ties theo yêu cầu; set EX so membership, không kiểm tra row order. |

### Automated invariant checks required before snapshot freeze

| Check | PASS condition |
|---|---|
| Foreign keys | PRAGMA foreign_keys = 1 on every connection; all FK integrity checks return no violations |
| Document state | DRAFT/CANCELLED have no effective movements; POSTED documents have complete lines and corresponding movement legs |
| Document type/direction | RECEIPT/CUSTOMER_RETURN movements positive; SHIPMENT negative; ADJUSTMENT may be either sign; each non-transfer line's total absolute movement equals planned_qty_milli |
| Transfer integrity | Exactly two movements per transfer line, one SOURCE negative and one DESTINATION positive; equal magnitude; distinct locations and warehouses matching header endpoints; both equal document.posted_at_utc |
| Batch ordering | Every POSTED document has unique posting_seq; movement timestamp equals header post timestamp; at a shared timestamp apply whole documents atomically in ascending posting_seq |
| No negative stock | Reconstruct each product/location balance by ordered atomic posting batches; every prefix balance is >= 0 |
| Movement identity | source_movement_ref unique; (document_line_id,movement_leg_no) unique; similar-valued but distinct source legs remain present |
| Units and bounds | Every product has one fixed base_unit; abs(quantity) <= 1,000,000,000 milli-unit; <=100,000 movements/database; sums remain within signed 64-bit |
| Business/event dates | business_date is valid YYYY-MM-DD but is not forced equal to created/posted local date; all timestamps match YYYY-MM-DDTHH:MM:SS.SSSZ |

Validator must emit run/version, DB hash, each invariant ID, PASS/FAIL, failing document/product/location keys and a summary artifact. This is a required Bước 2B build gate, not evidence that a database already exists.

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
| Tồn hiện tại | Tổng signed movements trước exclusive cutoff | Tính tại product/location và một base unit |
| Tồn theo vị trí | On-hand SKU tại một location | Có thể zero dù có history |
| Tồn theo kho | Tổng on-hand locations của warehouse | Không cộng quantity nhiều base units |
| Supplier/Customer | Đối tác trên receipt/shipment/return | Region/active là thuộc tính mô phỏng |
| Ngày nghiệp vụ | business_date ghi trên document | Không suy từ ngày tạo; có thể khác posted event date |
| Posting batch | Một inventory document commit nguyên tử | posting_seq sắp các document cùng timestamp |
| Đồng hạng | Nhiều entity cùng metric xếp hạng | Intent chọn include-ties hoặc stable tie-break; EX không chấm row order |

## 6. Edge-case Plan — chưa tạo dữ liệu

| Case cần fixture | Biến thể cần phân biệt | Lỗi SQL có thể phát hiện |
|---|---|---|
| Một SKU ở nhiều locations/warehouses | Product vs product-location grain | SUM stock bị nhân khi join category/location |
| Hai movement hợp lệ cùng product/location nhưng khác document | Lặp khóa nghiệp vụ ở nhiều giao dịch | DISTINCT product/location làm mất movement hoặc tổng quantity |
| Lặp movement bất thường với cùng document line/location/amount | Duplicate transaction | SUM không phát hiện duplicate posting; fixture phải kiểm tra source identity và expected movement count |
| Transfer có hai legs cùng line | Source/destination signs | Chỉ lấy một leg hoặc đếm quantity hai lần |
| DRAFT document có planned lines, không movement | Planned vs posted | Tính tồn từ planned quantity |
| Hai movement trái dấu tổng bằng 0 | Zero vs absence | Coi no-movement giống stock zero có history |
| Movement ngay trước/đúng cutoff | As-of semantics | Exclusive cutoff và timestamp equality khác kết quả |
| Hai posting cùng timestamp, posting_seq đổi thứ tự | Batch order and no-negative-stock invariant | Không xác định hoặc bỏ qua batch order khi kiểm tra running balance |
| Posting sequence giảm/tăng không khớp event timestamp | Total order integrity | Running balance có thể phụ thuộc dữ liệu order bất hợp lệ |
| Transfer hai legs cùng timestamp nhưng thiếu một leg | Atomic transfer | As-of balance lệch hoặc transfer tạo/làm mất stock |
| business_date khác created/posted local date | Business vs event time | Dùng created_at/posted_at thay business_date cho daily report |
| UTC/local nửa đêm và milliseconds | Timezone/precision boundary | Truncation hoặc timezone filter làm lệch date/cutoff |
| Hai SKU cùng tên | Identity/grouping | Group theo name thay product_id/SKU |
| NULL category, no movement và zero balance | Unassigned vs absence vs explicit zero | COALESCE/INNER JOIN làm mất phân biệt |
| Nhiều movement trên một document line | Join fan-out | COUNT line hoặc SUM planned qty sau join |
| Hai SKU cùng on-hand | Ranking ties | Top-1 tùy ý; phải deterministic tie-break hoặc include ties theo Intent Card |
| SKU active nhưng chưa movement | Entity absence | INNER JOIN loại SKU khỏi no-movement query |
| Inactive/quarantine location | Location inclusion | Tự loại location khi hỏi total stock |
| Adjustment đưa tồn về zero | Explicit zero | HAVING SUM(qty)>0 làm mất zero stock |
| Transfer giữa locations cùng warehouse | Location vs warehouse grain | Gọi transfer là nhập/xuất ở cấp kho |

Truy vấn về available/sellable/reserved bị chặn tới khi có model/rule bổ sung; inventory valuation bị loại khỏi cả 50 intents. Mỗi Intent Card chốt tie policy. Có đúng 1 empty-result intent trong WMS theo Coverage Matrix. Ghi expected outputs trước SQL execution theo [ANNOTATION_REVIEW_TEMPLATE.md](../ANNOTATION_REVIEW_TEMPLATE.md).

## 7. Source vs simulation register

| Nội dung | Nguồn | Trạng thái |
|---|---|---|
| 25 WMS groups; competency/complexity quota; SQLite/split/metrics | BENCHMARK_SPEC.md §2/§6; Decision Review D2, D4, D11 | Project decision; approved for benchmark scope |
| SQLite affinity/date-time/FK behavior | Official SQLite docs linked in database_design README | External technical fact |
| Document types/statuses, movement signs, on-hand, UOM, posting order, timezone, no-negative-stock policy | Benchmark Owner confirmation recorded in STEP_2A_REVIEW.md on 2026-11-09 | Synthetic simulation; accepted for logic design, not an industry standard |
