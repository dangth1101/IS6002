# BIRD-VN-Robust-50 — Bước 2A Design Review

| Thuộc tính | Giá trị |
|---|---|
| Phiên bản | 0.2.0 |
| Ngày nghiệm thu thiết kế | 2026-11-09 |
| Người phê duyệt | Benchmark Owner |
| Trạng thái | **ACCEPTED — logic design only** |
| Phạm vi | ERD, Data Dictionary, synthetic Business Rules/Glossary, Coverage Matrix, edge-case/invariant design và R-01…R-11 |
| Không thuộc nghiệm thu | Database vật lý, schema.sql, seed data, fixture execution evidence, Questions, canonical SQL, evaluator/source changes |

## 1. Decision Record R-01…R-11

Benchmark Owner xác nhận từng phương án dưới đây ngày **2026-11-09**. Các quy tắc là simulation assumptions cho benchmark demo, không phải chuẩn ERP/WMS phổ quát.

| ID | Quyết định được chấp nhận | Rationale của Benchmark Owner | Trạng thái / người phê duyệt / ngày |
|---|---|---|
| R-01 | Order value = line net của CONFIRMED orders, theo order_date. Recognized revenue = line net của CONFIRMED orders có shipment DELIVERED, theo delivered_at. Posted cash = CAPTURE trừ REFUND, theo occurred_at. | Ba measures mô tả sự kiện/ngày khác nhau; tách chúng tránh dùng order date hoặc cash date thay revenue date. | ACCEPTED — Benchmark Owner — 2026-11-09 |
| R-02 | REFUND bắt buộc gắn return và cùng order; CAPTURE không gắn return. Cumulative POSTED refunds không vượt cumulative POSTED captures theo occurred_at và txn_seq. Payment-state classification bị loại; truy vấn cash movements vẫn thuộc scope. | Giữ liên kết nguồn refund và xác định rõ giới hạn cash; tránh nhãn paid/unpaid thiếu lifecycle. | ACCEPTED — Benchmark Owner — 2026-11-09 |
| R-03 | Có thể trả một phần purchased quantity, kể cả nhiều returns. Khi return line chuyển RECEIVED thì nhận đủ quantity đã khai báo ở line; không có partial receipt nhiều đợt. Tổng received quantity không vượt sold quantity. | Cho phép partial customer return, nhưng giữ receipt workflow đơn giản và có thể kiểm chứng. | ACCEPTED — Benchmark Owner — 2026-11-09 |
| R-04 | Mỗi transfer line tạo đúng hai movement đối dấu, cùng absolute quantity và timestamp, trong một atomic transaction. Hai locations và warehouses khác nhau; không transfer giữa locations cùng warehouse. | Cặp leg bảo toàn tổng quantity; atomic posting tránh nhìn thấy transfer nửa chừng. | ACCEPTED — Benchmark Owner — 2026-11-09 |
| R-05 | On-hand không âm tại từng product/location sau mỗi posting batch. Cùng timestamp được sắp bằng posting_seq; document là batch atomic. | Tạo total order tái lập được cho kiểm tra stock prefix và không phụ thuộc thứ tự vật lý rows. | ACCEPTED — Benchmark Owner — 2026-11-09 |
| R-06 | Timestamp UTC ISO-8601 có milliseconds: YYYY-MM-DDTHH:MM:SS.SSSZ. Ngày nghiệp vụ theo Asia/Ho_Chi_Minh; ranges [start,end). order_date/business_date độc lập created_at và không mặc định bằng ngày tạo; WMS business_date cũng có thể khác posted event date. | Tách ngày nghiệp vụ khỏi thời điểm hệ thống tạo/post; tránh sai biên và backdated records bị diễn giải ngầm. | ACCEPTED — Benchmark Owner — 2026-11-09 |
| R-07 | VND integer; quantity integer milli-unit; HALF_UP bằng integer arithmetic. AVG amount trả INTEGER VND rounded 1 VND; AVG quantity trả INTEGER milli-unit rounded 0.001 base unit. Dùng các caps ghi trong design docs; validator phải kiểm tra mọi aggregate trong signed 64-bit. | Kiểu và precision output là một phần semantics; caps loại overflow khỏi gold result. | ACCEPTED — Benchmark Owner — 2026-11-09 |
| R-08 | Không cộng SUM/AVG quantity giữa các base units khác nhau. | Tổng warehouse-level quantity chỉ có nghĩa khi SKU cùng unit; mọi query phải giữ unit hoặc group theo unit. | ACCEPTED — Benchmark Owner — 2026-11-09 |
| R-09 | Inventory valuation bị loại khỏi toàn bộ 50 intents và logical schema phiên bản này. | Không có cost method được xác nhận; loại hẳn metric tránh ngụ ý FIFO/average/accounting valuation. | ACCEPTED — Benchmark Owner — 2026-11-09 |
| R-10 | Mọi cross-row invariant có automated validation, PASS/FAIL evidence; bật và kiểm tra PRAGMA foreign_keys trên mỗi connection. | FK không tự đảm bảo type-dependent/sequence/aggregate invariants; cần evidence có thể tái lập. Thực thi validator thuộc Bước 2B. | ACCEPTED — Benchmark Owner — 2026-11-09 |
| R-11 | Mỗi WMS source movement/leg có identity ổn định, không trùng; các movement hợp lệ có cùng thuộc tính nhưng source/leg khác vẫn được giữ. | Ngăn duplicate posting mà không dùng DISTINCT làm rơi giao dịch hợp lệ. | ACCEPTED — Benchmark Owner — 2026-11-09 |

## 2. Quyết định bổ sung được xác nhận

| Nội dung | Giá trị chốt | Lý do |
|---|---|---|
| Empty-result quota | Chính xác 2 intent: 1 ERP, 1 WMS; reserved slots ERP-EF-04 và WMS-EF-04 | Đảm bảo có trường hợp empty có chủ đích ở cả hai database, với quota nhỏ có kiểm soát. |
| Complexity by database | ERP 8 Simple / 12 Moderate / 5 Challenging; WMS 8 / 12 / 5 | Cân bằng độ khó tổng trên hai domain; vẫn dùng rubric khi gán từng intent. |
| Ranking/ties | Mỗi Intent Card chọn deterministic tie-break hoặc include all ties theo intent; không coi set-based EX là kiểm tra row order | Comparator primary chấm membership, còn ordering/tie behavior cần semantics riêng trong prompt/gold. |
| Nguồn business rules | Mọi ERP/WMS rule trong design docs là synthetic assumptions | Không có sản phẩm ERP/WMS cụ thể làm authority; không khái quát thành chuẩn ngành. |

Các tổng quota và quyết định trên được ghi nhận; mapping từng intent, từng question chưa được tạo trong Bước 2A.

## 3. Kiểm tra consistency

- Coverage cộng đúng 50 slots: 25 ERP + 25 WMS; competency totals 8/8/8/6/8/4/4/4; complexity tổng 16/24/10 và 8/12/5 mỗi database.
- ERD và Data Dictionary đã đồng bộ field bổ sung: ERP txn_seq; WMS posting_seq, movement_leg_no, movement_role và source_movement_ref. WMS cost fields đã bỏ cùng inventory valuation.
- ERP order_date độc lập created_at; recognized revenue dùng delivery event; cash dùng payment event. Refund gắn return/order; returns không tự làm thay đổi cash/revenue.
- WMS movement thuộc POSTED document; transfer đúng hai leg atomic; total ordering dùng posting_seq; running balance có non-negative invariant.
- Các field, status, currency, quantity, NULL/zero/absence, business date/event time và tie policy có cách diễn giải nhất quán giữa ERD, dictionary, rules, glossary, coverage và edge plan.
- Repeated business values vẫn hợp lệ; duplicate source identity bị validator chặn. Aggregate nhiều child tables phải preaggregate đúng grain để tránh fan-out.

## 4. Automated invariants và evidence cần ở Bước 2B

Các design docs định nghĩa điều kiện cần kiểm tra. Chưa có database nên chưa có kết quả runtime; đây là implementation gate, không phải Major design defect.

### ERP

- Gross/discount/net khớp integer HALF_UP formula; record caps và aggregate sums nằm trong signed 64-bit.
- Payment refs/type/order valid; txn_seq unique theo order, timestamp không giảm; cumulative POSTED refunds <= captures theo từng sequence prefix.
- Return line thuộc line/order tương ứng; received quantity cumulative <= sold; RECEIVED iff received_at có giá trị.
- Delivered shipment có timestamp hợp lệ; order/shipment cardinality đúng; revenue cohort chỉ confirmed + delivered.
- FK enforcement bật; uniqueness/grain checks pass; output validator ghi invariant ID, DB hash, PASS/FAIL và failing keys.

### WMS

- FK enforcement bật; document type/status/partner/warehouse/location combinations hợp lệ; DRAFT/CANCELLED không có effective movement.
- Posted docs có movements đủ theo type; movement timestamp bằng posted_at; transfer đúng hai leg, cùng quantity/time và atomic, đúng endpoints khác warehouse.
- posting_seq tạo thứ tự xác định cho documents cùng timestamp; running product/location balance không âm sau từng batch.
- source_movement_ref và document_line_id + movement_leg_no không trùng; valid same-valued legs còn nguyên.
- Unit và quantity caps hợp lệ; sums trong signed 64-bit; business_date được giữ riêng, không tự đồng nhất với created/posted date.
- Validator ghi DB hash, invariant ID, PASS/FAIL, offending keys và summary artifact.

## 5. Giới hạn demo được chấp nhận

- ERP: một full shipment tối đa mỗi order; không split/partial delivery, thuế, phí vận chuyển, FX, accounting ledger hoặc payment-state classification.
- ERP returns có thể partial so với sold quantity, nhưng một return line RECEIVED được nhận toàn bộ declared quantity; không partial receipt nhiều đợt. Refund phải được ghi riêng.
- WMS: không transfer cùng warehouse; không reservations/available/sellable, lot/serial/expiry, unit conversion, FIFO/average costing, inventory valuation hoặc pick/pack workflow.
- VND-only; quantity precision 0.001 theo base unit; không cộng khác unit.
- Hai schema, 50 intents, synthetic data và một người validation không đại diện ERP/WMS phổ quát; các assumptions được công bố rõ.

## 6. Nghiệm thu Bước 2A

Benchmark Owner nghiệm thu Bước 2A **về mặt thiết kế logic** ngày **2026-11-09**, trong đúng phạm vi nêu ở đầu tài liệu. Không còn Critical hoặc Major design issue nào chưa được xử lý trong R-01…R-11.

Nghiệm thu này không xác nhận physical database, constraints runtime, automated validation results, seed coverage, question/gold quality hoặc toàn benchmark. **Tại thời điểm nghiệm thu Bước 2A**, Bước 2B chưa được bắt đầu; trạng thái triển khai sau đó được ghi riêng trong [physical database README](../physical_database/README.md). Các validator và pass/fail evidence ở mục 4 là gate cho snapshot được dùng tiếp.
