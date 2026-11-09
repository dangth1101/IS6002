# ERP Sales — Logical Schema Design

| Thuộc tính | Giá trị |
|---|---|
| Version / status | 0.2.0 — Logic design accepted; physical schema v1 and snapshots accepted by Benchmark Owner, see [Bước 2B artifacts](../physical_database/README.md) |
| Phạm vi dự kiến | 25 Semantic Groups của ERP Sales |
| Domain authority | Chưa có ERP cụ thể/Domain Owner; Benchmark Owner chấp nhận các simulation rules cho logic design ngày 2026-11-09 |

## 1. Phạm vi nghiệp vụ

Mô phỏng luồng order-to-cash tối giản: khách hàng đặt hàng, dòng hàng chụp giá/discount tại thời điểm đặt, đơn có thể gắn một shipment, có giao dịch thanh toán/refund và yêu cầu trả hàng. Schema hỗ trợ truy vấn customer/product/order, giá trị đơn, giao hàng, thanh toán, return, thời gian, aggregation và ranking.

**Out of scope:** nhiều currency/FX, thuế/phí vận chuyển, nhiều địa chỉ giao hàng, split/partial shipment, backorder, lịch sử trạng thái, phân bổ thanh toán giữa nhiều đơn, sổ cái kế toán, điều chỉnh sau kỳ. Cần mở rộng trước freeze nếu các khái niệm này xuất hiện trong Intent Cards.

## 2. ERD logic

~~~mermaid
erDiagram
    CUSTOMERS ||--o{ SALES_ORDERS : places
    EMPLOYEES o|--o{ SALES_ORDERS : owns
    PRODUCT_CATEGORIES o|--o{ PRODUCTS : classifies
    PRODUCTS ||--o{ SALES_ORDER_LINES : sold_as
    SALES_ORDERS ||--|{ SALES_ORDER_LINES : contains
    SALES_ORDERS ||--o| SALES_SHIPMENTS : fulfills
    SALES_ORDERS ||--o{ PAYMENT_TRANSACTIONS : has
    SALES_ORDERS ||--o{ SALES_RETURNS : may_return
    SALES_RETURNS ||--|{ SALES_RETURN_LINES : includes
    SALES_ORDER_LINES ||--o{ SALES_RETURN_LINES : refers_to
    SALES_RETURNS o|--o{ PAYMENT_TRANSACTIONS : may_refund

    CUSTOMERS {
      INTEGER customer_id PK
      TEXT customer_code UK
      TEXT customer_name
      TEXT segment
      TEXT region
      TEXT created_at_utc
      INTEGER is_active
    }
    EMPLOYEES {
      INTEGER employee_id PK
      TEXT employee_code UK
      TEXT full_name
      TEXT team
      INTEGER is_active
    }
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
      INTEGER list_price_vnd
      INTEGER is_active
    }
    SALES_ORDERS {
      INTEGER order_id PK
      TEXT order_no UK
      INTEGER customer_id FK
      INTEGER sales_rep_id FK
      TEXT order_date
      TEXT order_status
      TEXT currency_code
      TEXT created_at_utc
    }
    SALES_ORDER_LINES {
      INTEGER order_line_id PK
      INTEGER order_id FK
      INTEGER line_no
      INTEGER product_id FK
      INTEGER ordered_qty_milli
      INTEGER unit_price_vnd
      INTEGER discount_bps
      INTEGER gross_vnd
      INTEGER discount_vnd
      INTEGER net_vnd
    }
    SALES_SHIPMENTS {
      INTEGER shipment_id PK
      TEXT shipment_no UK
      INTEGER order_id FK_UK
      TEXT shipment_status
      TEXT shipped_at_utc
      TEXT delivered_at_utc
    }
    PAYMENT_TRANSACTIONS {
      INTEGER payment_txn_id PK
      INTEGER order_id FK
      INTEGER return_id FK
      INTEGER txn_seq
      TEXT transaction_ref UK
      TEXT txn_type
      TEXT txn_status
      INTEGER amount_vnd
      TEXT payment_method
      TEXT occurred_at_utc
    }
    SALES_RETURNS {
      INTEGER return_id PK
      TEXT return_no UK
      INTEGER order_id FK
      TEXT return_status
      TEXT requested_at_utc
      TEXT received_at_utc
    }
    SALES_RETURN_LINES {
      INTEGER return_line_id PK
      INTEGER return_id FK
      INTEGER order_line_id FK
      INTEGER return_qty_milli
    }
~~~

### Cardinality và integrity notes

- Một customer có 0..N order; mỗi order phải có đúng một customer. Employee phụ trách là optional.
- Mỗi order có 1..N order lines; mỗi line trỏ một product; (order_id,line_no) duy nhất.
- Mỗi order tối đa một shipment trong mô hình; shipment đầy đủ toàn bộ order, không partial.
- Một order có 0..N payment transactions. Return có thể gắn 0..N refund transactions; return_id chỉ dùng với txn_type REFUND.
- Một order có 0..N returns; mỗi return line trỏ line thuộc cùng order. Kiểm tra cùng order là cross-row validation.
- Category tự tham chiếu tùy chọn; không cho parent là chính nó và cần ngăn cycle.
- FK ON DELETE RESTRICT theo logic; snapshot benchmark được freeze, không cascade xóa lịch sử.

## 3. Data Dictionary

SQLite có dynamic typing; affinity dưới đây là kiểu lưu dự kiến cùng CHECK/range validation ở physical design. SQLite không có BOOLEAN hoặc DATE storage class riêng; lựa chọn INTEGER 0/1 và ISO text là design choice. [SQLite Datatypes](https://www.sqlite.org/datatype3.html).

### CUSTOMERS

| Thuộc tính | SQLite type | NULL | Key/constraint | Miền / ý nghĩa |
|---|---|---:|---|---|
| customer_id | INTEGER | No | PK | ID nội bộ ổn định |
| customer_code | TEXT | No | UNIQUE | Mã khách hàng, không rỗng |
| customer_name | TEXT | No | — | Tên hiển thị; không rỗng |
| segment | TEXT | Yes | CHECK khi có giá trị | RETAIL / SMB / ENTERPRISE; phân nhóm mô phỏng |
| region | TEXT | Yes | — | Vùng địa lý mô phỏng; không phải địa giới chuẩn |
| created_at_utc | TEXT | No | ISO-8601 UTC | Thời điểm tạo fixture |
| is_active | INTEGER | No | CHECK 0/1 | 1 active, 0 inactive; không đồng nghĩa không có order |

### EMPLOYEES

| Thuộc tính | SQLite type | NULL | Key/constraint | Miền / ý nghĩa |
|---|---|---:|---|---|
| employee_id | INTEGER | No | PK | ID nhân viên |
| employee_code | TEXT | No | UNIQUE | Mã nhân viên mô phỏng |
| full_name | TEXT | No | — | Tên hiển thị synthetic |
| team | TEXT | Yes | — | Nhóm sales; NULL nghĩa là chưa gán |
| is_active | INTEGER | No | CHECK 0/1 | Cờ hoạt động tại snapshot |

### PRODUCT_CATEGORIES

| Thuộc tính | SQLite type | NULL | Key/constraint | Miền / ý nghĩa |
|---|---|---:|---|---|
| category_id | INTEGER | No | PK | ID danh mục |
| category_name | TEXT | No | UNIQUE | Tên danh mục không rỗng |
| parent_category_id | INTEGER | Yes | FK self | NULL nếu root; không self-parent/cycle |

### PRODUCTS

| Thuộc tính | SQLite type | NULL | Key/constraint | Miền / ý nghĩa |
|---|---|---:|---|---|
| product_id | INTEGER | No | PK | ID sản phẩm |
| sku | TEXT | No | UNIQUE | SKU không rỗng |
| product_name | TEXT | No | — | Tên sản phẩm |
| category_id | INTEGER | Yes | FK → PRODUCT_CATEGORIES | NULL nếu chưa phân loại |
| base_unit | TEXT | No | CHECK | EA / KG / L theo whitelist đóng băng |
| list_price_vnd | INTEGER | No | CHECK ≥ 0 | Giá niêm yết tham khảo, VND nguyên |
| is_active | INTEGER | No | CHECK 0/1 | Cờ hiện hành; line giữ giá lịch sử riêng |

### SALES_ORDERS

| Thuộc tính | SQLite type | NULL | Key/constraint | Miền / ý nghĩa |
|---|---|---:|---|---|
| order_id | INTEGER | No | PK | ID nội bộ đơn hàng |
| order_no | TEXT | No | UNIQUE | Số đơn mô phỏng |
| customer_id | INTEGER | No | FK → CUSTOMERS | Chủ thể mua |
| sales_rep_id | INTEGER | Yes | FK → EMPLOYEES | Người phụ trách; NULL chưa gán |
| order_date | TEXT | No | YYYY-MM-DD | Ngày order nghiệp vụ do record ghi; độc lập với created_at_utc và có thể khác ngày tạo |
| order_status | TEXT | No | CHECK | DRAFT / CONFIRMED / CANCELLED |
| currency_code | TEXT | No | CHECK = VND | Một currency duy nhất; FX ngoài scope |
| created_at_utc | TEXT | No | ISO-8601 UTC | Thời điểm hệ thống tạo order |

### SALES_ORDER_LINES

| Thuộc tính | SQLite type | NULL | Key/constraint | Miền / ý nghĩa |
|---|---|---:|---|---|
| order_line_id | INTEGER | No | PK | ID dòng order |
| order_id | INTEGER | No | FK → SALES_ORDERS | Đơn sở hữu dòng |
| line_no | INTEGER | No | UNIQUE with order_id; > 0 | Thứ tự dòng |
| product_id | INTEGER | No | FK → PRODUCTS | Sản phẩm bán |
| ordered_qty_milli | INTEGER | No | CHECK 1..1,000,000 | Quantity × 1000, theo product.base_unit |
| unit_price_vnd | INTEGER | No | CHECK 0..1,000,000,000 | Giá thỏa thuận VND/base unit tại order time |
| discount_bps | INTEGER | No | CHECK 0..10000 | Basis points; 100 bps = 1%; 10000 = 100% |
| gross_vnd | INTEGER | No | CHECK ≥ 0 | Trước discount; rounding HALF_UP ở cấp dòng |
| discount_vnd | INTEGER | No | CHECK 0..gross_vnd | Tiền discount trên dòng |
| net_vnd | INTEGER | No | CHECK ≥ 0 | gross_vnd − discount_vnd; revenue measure cơ sở |

### SALES_SHIPMENTS

| Thuộc tính | SQLite type | NULL | Key/constraint | Miền / ý nghĩa |
|---|---|---:|---|---|
| shipment_id | INTEGER | No | PK | ID shipment |
| shipment_no | TEXT | No | UNIQUE | Mã shipment |
| order_id | INTEGER | No | UNIQUE, FK → SALES_ORDERS | Tối đa một shipment/order |
| shipment_status | TEXT | No | CHECK | PENDING / SHIPPED / DELIVERED / FAILED |
| shipped_at_utc | TEXT | Yes | ISO-8601 UTC | Bắt buộc khi SHIPPED/DELIVERED |
| delivered_at_utc | TEXT | Yes | ISO-8601 UTC | Chỉ khi DELIVERED; >= shipped_at |

### PAYMENT_TRANSACTIONS

| Thuộc tính | SQLite type | NULL | Key/constraint | Miền / ý nghĩa |
|---|---|---:|---|---|
| payment_txn_id | INTEGER | No | PK | ID giao dịch tiền |
| order_id | INTEGER | No | FK → SALES_ORDERS | Order liên quan |
| return_id | INTEGER | Yes | FK → SALES_RETURNS | Chỉ cho refund gắn return |
| transaction_ref | TEXT | No | UNIQUE | Mã giao dịch synthetic |
| txn_type | TEXT | No | CHECK | CAPTURE / REFUND |
| txn_status | TEXT | No | CHECK | PENDING / POSTED / FAILED / VOIDED |
| amount_vnd | INTEGER | No | CHECK 1..1,000,000,000,000 | Số tiền dương; hướng do txn_type quy định |
| payment_method | TEXT | No | CHECK | CASH / BANK_TRANSFER / CARD / E_WALLET (simulation) |
| occurred_at_utc | TEXT | No | ISO-8601 UTC | Thời điểm phát sinh |
| txn_seq | INTEGER | No | UNIQUE with order_id; > 0 | Thứ tự giao dịch trong order; phân xử cùng timestamp và cumulative cash |

### SALES_RETURNS và SALES_RETURN_LINES

| Bảng.thuộc tính | SQLite type | NULL | Key/constraint | Miền / ý nghĩa |
|---|---|---:|---|---|
| SALES_RETURNS.return_id | INTEGER | No | PK | ID return |
| SALES_RETURNS.return_no | TEXT | No | UNIQUE | Mã return |
| SALES_RETURNS.order_id | INTEGER | No | FK → SALES_ORDERS | Order gốc |
| SALES_RETURNS.return_status | TEXT | No | CHECK | REQUESTED / APPROVED / RECEIVED / REJECTED |
| SALES_RETURNS.requested_at_utc | TEXT | No | ISO-8601 UTC | Thời điểm yêu cầu |
| SALES_RETURNS.received_at_utc | TEXT | Yes | ISO-8601 UTC milliseconds | Có iff return_status = RECEIVED; không chứng minh refund đã POSTED |
| SALES_RETURN_LINES.return_line_id | INTEGER | No | PK | ID dòng trả |
| SALES_RETURN_LINES.return_id | INTEGER | No | FK → SALES_RETURNS | Return sở hữu dòng |
| SALES_RETURN_LINES.order_line_id | INTEGER | No | FK → SALES_ORDER_LINES | Dòng bán gốc |
| SALES_RETURN_LINES.return_qty_milli | INTEGER | No | CHECK > 0 | Lượng khai báo cho return; nếu status RECEIVED thì coi toàn bộ lượng dòng đã nhận |

Tất cả timestamp trong các bảng dùng format cố định YYYY-MM-DDTHH:MM:SS.SSSZ. Giới hạn mô phỏng: tối đa 100,000 sales order lines và 100,000 payment transactions/database; các caps từng record bên trên giữ phép nhân và SUM dưới signed 64-bit. Validator kiểm tra cả record caps lẫn aggregate thực tế trước freeze.

Cross-row checks: (return_id,order_line_id) unique trong một return; line gốc phải thuộc order gốc; tổng return_qty_milli trên các return RECEIVED không vượt số lượng bán. Khách có thể trả một phần số lượng đã mua hoặc trả nhiều lần; khi header thành RECEIVED, toàn bộ quantity khai báo ở mỗi return line được coi là nhận. Không mô hình hóa partial receipt nhiều đợt.

## 4. Business Rules

> Mọi quy tắc dưới đây là **synthetic simulation assumptions được Benchmark Owner chấp nhận cho logic design ngày 2026-11-09**; không phải chuẩn ERP phổ quát.

| ID | Quy tắc mô phỏng | Cách diễn giải / truy vấn |
|---|---|---|
| ERP-BR-01 | DRAFT và CANCELLED không phải đơn đã xác nhận | Order counts/sales include only CONFIRMED unless Intent Card says otherwise. |
| ERP-BR-02 | Shipment độc lập với order status | Delivered = shipment_status DELIVERED; không suy ra từ CONFIRMED. |
| ERP-BR-03 | Một shipment đầy đủ tối đa cho một order | Không split shipment; revenue recognized theo delivery date. |
| ERP-BR-04 | Net line value là measure order | net_vnd = gross_vnd − discount_vnd; order value = SUM(net_vnd) trên order CONFIRMED; chưa trừ return/refund, thuế, vận chuyển. |
| ERP-BR-05 | Gross/discount/net được snapshot cấp dòng | Với q=ordered_qty_milli, p=unit_price_vnd, gross=floor((q×p+500)/1000); discount=floor((gross×discount_bps+5000)/10000); net=gross−discount. Integer arithmetic, HALF_UP với giá trị không âm; caps ngăn overflow. |
| ERP-BR-06 | Order value, recognized revenue và cash là ba metric khác nhau | Order value = SUM(net_vnd) của CONFIRMED order, theo order_date. Recognized revenue = cùng line net chỉ cho CONFIRMED order có shipment DELIVERED, theo delivered_at_utc. Cash movement theo occurred_at_utc. |
| ERP-BR-07 | Đã thu là cash movement POSTED | CAPTURE cộng; REFUND trừ; PENDING/FAILED/VOIDED không tham gia cash. Cash khác revenue. |
| ERP-BR-08 | Payment-state classification ngoài benchmark | Không tạo nhãn UNPAID/PARTIALLY_PAID/PAID/OVERPAID; benchmark vẫn có thể truy vấn posted cash movement. |
| ERP-BR-09 | Refund gắn return và order; capture không gắn return | CAPTURE.return_id phải NULL; REFUND.return_id bắt buộc và phải thuộc cùng order_id. Theo thứ tự (occurred_at_utc, txn_seq), cumulative POSTED REFUND không vượt cumulative POSTED CAPTURE; txn_seq duy nhất trong order và timestamp không giảm theo sequence. |
| ERP-BR-10 | Return receipt và refund là sự kiện riêng | Return RECEIVED không tự tạo cash/refund và không tự giảm recognized revenue. Mỗi received line nhận trọn return_qty_milli; tổng received quantity qua returns không vượt số lượng bán. |
| ERP-BR-11 | order_date độc lập với created_at_utc | order_date là ngày nghiệp vụ YYYY-MM-DD; không suy ra hoặc ép bằng ngày local của created_at_utc. Order cohort dùng order_date; creation-time query dùng created_at_utc. |
| ERP-BR-12 | Timestamp và date range có chuẩn cố định | Timestamp UTC dạng YYYY-MM-DDTHH:MM:SS.SSSZ; range [start,end). Biên local Asia/Ho_Chi_Minh chuyển sang UTC trước khi lọc event time; order_date lọc theo ngày nghiệp vụ. |
| ERP-BR-13 | Không có line/payment/return là absence, không phải amount 0 | Đếm child PK; giữ parent không giao dịch theo Intent Card. |
| ERP-BR-14 | Order có nhiều lines, payments và returns | Không join các child sets rồi SUM trực tiếp; preaggregate mỗi nhánh về đúng grain để tránh fan-out. |
| ERP-BR-15 | AVG trả kiểu và precision cố định | Với S = integer SUM và N = COUNT(non-NULL), AVG trả INTEGER theo sign(S) × floor((2×abs(S)+N)/(2×N)); tie HALF_UP làm tròn xa zero. Amount là VND nguyên; quantity là milli-unit (0.001 base unit). Không chấm REAL tiền. |
| ERP-BR-16 | Ranking luôn khai báo tie policy | Intent Card chốt deterministic secondary key hoặc include ties theo nghiệp vụ; set-based EX chỉ so row membership, không kiểm tra thứ tự output. |

### Automated invariant checks required before snapshot freeze

| Check | PASS condition |
|---|---|
| Monetary line arithmetic | q <= 1,000,000 milli-unit, unit_price <= 1,000,000,000 VND, discount_bps 0..10,000; computed gross/discount/net match integer HALF_UP formulas and net = gross - discount |
| Numeric bounds | At most 100,000 order lines/payment transactions per DB; every row amount and aggregate SUM stays within signed 64-bit |
| Payment identity/status | CAPTURE has NULL return_id; REFUND has return_id; return belongs to same order; transaction reference and (order_id,txn_seq) are unique |
| Payment sequence | For each order txn_seq strictly increases; occurred_at_utc does not decrease along txn_seq; cumulative POSTED refunds never exceed cumulative POSTED captures at any sequence prefix |
| Return identity/quantity | Return line points to order line of same order; sum of return_qty_milli where return status RECEIVED <= sold quantity per order line |
| Return timestamps | return_status = RECEIVED iff received_at_utc is present; non-RECEIVED statuses have NULL received_at_utc |
| Shipment/revenue | Delivered shipment has delivered_at_utc >= shipped_at_utc; at most one shipment/order; recognized-revenue cohort is CONFIRMED + DELIVERED only |
| Foreign keys and grain | PRAGMA foreign_keys = 1 on every connection; no orphan rows; no duplicate (order_id,line_no), return line identity or payment transaction reference |

Validator must emit run/version, DB hash, each invariant ID, PASS/FAIL, failing entity keys and a summary artifact. Bước 2A only defines these checks; executing them requires the physical database in Bước 2B.

## 5. Business Glossary — đề xuất mô phỏng

| Thuật ngữ tiếng Việt | Nghĩa đề xuất | Tránh nhập nhằng |
|---|---|---|
| Đơn hàng | SALES_ORDERS record | Khác shipment/payment |
| Dòng hàng | Một product/quantity trong order | COUNT dòng khác COUNT order/SKU/customer |
| Giá trị gộp | Tổng line gross trước discount | Không gồm thuế/phí |
| Tiền giảm | Discount snapshot trên dòng | Không phải tỷ lệ discount |
| Giá trị sau giảm | Tổng net_vnd | Không trừ return/refund nếu không nêu rõ |
| Order value | SUM(net_vnd) trên CONFIRMED order | Theo order_date; không gồm tax/shipping/return |
| Doanh thu ghi nhận | Net line của CONFIRMED order đã DELIVERED | Theo delivered_at_utc; khác order value theo ngày đặt và khác tiền thu |
| Tiền đã thu | Capture posted trừ refund posted | Cash metric, khác revenue |
| Payment state | Không phân loại trong benchmark phiên bản này | Không dùng UNPAID/PAID/PARTIALLY_PAID làm nhãn chuẩn |
| Đã giao | Shipment DELIVERED với delivered time hợp lệ | Không suy từ order CONFIRMED |
| Khách hàng hoạt động | is_active=1 tại snapshot | Không đồng nghĩa có giao dịch |
| Khách không phát sinh đơn | Không có qualifying order trong kỳ | Khác inactive customer |
| Trả hàng | Return request/receipt workflow | Không mặc định refund hoàn tất |
| Đồng hạng | Hai hay nhiều entity cùng metric xếp hạng | Chốt deterministic tie-break hoặc include ties; không giả định EX kiểm tra thứ tự |

## 6. Edge-case Plan — chưa tạo dữ liệu

| Case cần fixture | Biến thể cần phân biệt | Lỗi SQL có thể phát hiện |
|---|---|---|
| Customer có 2 orders, mỗi order nhiều lines | Entity grain vs line grain | Đếm order bằng COUNT(*) sau join lines |
| Cùng product xuất hiện ở hai lines của một order | Repeated business key vs duplicate row | Gộp/đếm product và line sai; không được giả định product unique per order |
| Một order có 3 lines, 2 payment rows | Join fan-out | SUM(net_vnd) bị nhân khi join payments |
| Order gross 0/discount 100% | Zero vs absence | Bỏ nhầm order net=0 hoặc COALESCE sai |
| Payment PENDING/FAILED và POSTED CAPTURE | Status inclusion | Cộng mọi payment rows |
| Một capture và một refund posted | Sign/type semantics | Cộng refund hoặc nhầm cash với revenue |
| Capture/refund cùng timestamp, refund sequence trước capture | Transaction sequence | Chỉ kiểm tra net cuối thay vì cap cumulative tại từng giao dịch |
| CONFIRMED nhưng chưa delivered | Revenue recognition | Lọc order_date thay delivered_at |
| order_date khác ngày created_at_utc | Business date vs creation time | Dùng created_at thay order_date làm sai order cohort |
| Shipment đúng biên ngày local | Timezone and [start,end) | Inclusive end gây đếm lặp hoặc lệch UTC/local |
| Hai reps cùng revenue | Ranking tie | TOP 1 tùy ý; Intent phải chọn stable tie-break hoặc include ties |
| Product không có lines/customer không có order | Empty child set | INNER JOIN làm mất entity; LEFT JOIN + COUNT(*) đếm placeholder |
| Hai partial returns cho một line; received total vừa bằng sold và vượt sold 1 milli-unit | Return quantity cap | Không cộng cumulative received hoặc sai precision |
| Return RECEIVED nhưng không có refund; refund POSTED sau return | Return vs refund | Coi return tự tạo cash hoặc tự giảm revenue |
| Hai product/category cùng tên | ID vs label grouping | Gộp entity theo name thay vì ID |
| Hai line hợp lệ có cùng product và price | Lặp thuộc tính nhưng PK khác | Dùng DISTINCT sai làm rơi line hợp lệ hoặc giảm tổng net |
| NULL rep/category | Unknown vs zero | Gộp NULL thành Unknown hoặc 0 |

**Validation:** Với mỗi Intent Card, chọn case phù hợp và ghi expected output trước khi chạy canonical SQL theo [ANNOTATION_REVIEW_TEMPLATE.md](../ANNOTATION_REVIEW_TEMPLATE.md). Ambiguity làm thay đổi kết quả phải được giải quyết trước annotation.

## 7. Source vs simulation register

| Nội dung | Nguồn | Trạng thái |
|---|---|---|
| 25 ERP groups; competency/complexity quota; SQLite/split/metrics | BENCHMARK_SPEC.md §2/§6; Decision Review D2, D4, D11 | Project decision; approved for benchmark scope |
| SQLite affinity/date-time/FK behavior | Official SQLite docs linked in database_design README | External technical fact |
| Statuses, revenue definition, VND, precision, payment/refund/return flow, timezone | Benchmark Owner confirmation recorded in STEP_2A_REVIEW.md on 2026-11-09 | Synthetic simulation; accepted for logic design, not an industry standard |
