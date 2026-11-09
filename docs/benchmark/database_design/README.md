# BIRD-VN-Robust-50 — Database Logic Design

| Thuộc tính | Giá trị |
|---|---|
| Phiên bản | 0.2.0 — Logic design accepted, 2026-11-09 |
| Ngày | 2026-11-09 |
| Phạm vi | Thiết kế logic ERP Sales, WMS Inventory và coverage |
| Trạng thái | Bước 2A được nghiệm thu; Bước 2B đã được Benchmark Owner xác nhận nghiệm thu riêng ngày 2026-11-09; Intent Cards hiện là draft |

## Bộ tài liệu

- [ERP Sales logical design](ERP_SALES_DESIGN.md): phạm vi, ERD, data dictionary, business rules, glossary và edge cases.
- [WMS Inventory logical design](WMS_INVENTORY_DESIGN.md): cùng các nội dung trên cho kho.
- [Coverage Matrix](COVERAGE_MATRIX.md): ánh xạ quota competency/complexity đã duyệt vào khả năng schema; không tạo câu hỏi benchmark.
- [Bước 2A Design Review](STEP_2A_REVIEW.md): decision record R-01–R-11 và phạm vi nghiệm thu logic.
- [Physical Database implementation](../physical_database/README.md): artifacts, build/validation commands và trạng thái Bước 2B.

## Căn cứ và ranh giới giữa nguồn với giả định

1. Quy mô và quota benchmark lấy từ [BENCHMARK_SPEC.md](../BENCHMARK_SPEC.md) §2, §6 và Decision Review D1–D7, D10, D11: 50 Semantic Groups; 25 ERP và 25 WMS; competency quota 8/8/8/6/8/4/4/4; complexity ERP 8/12/5 và WMS 8/12/5. Đây là yêu cầu dự án đã phê duyệt, không phải thông lệ ngành.
2. Benchmark Owner đã xác nhận R-01–R-11 cho thiết kế logic ngày 2026-11-09. D4 ban đầu chỉ phê duyệt định hướng hai SQLite DB; xác nhận riêng R-01–R-11 đóng băng các simulation assumptions cho thiết kế logic. Các quy tắc ERP/WMS là **synthetic business assumptions**, không phải chuẩn ERP/WMS phổ quát.
3. Nguồn ngoài về kỹ thuật SQLite: SQLite không có storage class riêng cho ngày/giờ; tài liệu chính thức nêu các biểu diễn TEXT/REAL/INTEGER, và thiết kế này chọn ISO-8601 TEXT. Builder/validator bật và xác nhận foreign-key enforcement trên connection của chúng; mọi client khác phải tiếp tục bật `PRAGMA foreign_keys` trên từng connection. [SQLite Datatypes](https://www.sqlite.org/datatype3.html), [SQLite Foreign Key Support](https://www.sqlite.org/foreignkeys.html).
4. Không có nguồn ERP/WMS cụ thể được chỉ định trong tài liệu dự án. Các quy tắc mô phỏng được chấp nhận cho benchmark demo, không phải chuẩn ngành.

## Quy ước thiết kế dùng chung — đề xuất mô phỏng

- Khóa chính logic là ID số nguyên ổn định; mã nghiệp vụ có UNIQUE và không dùng làm FK.
- SQLite INTEGER lưu tiền VND và số lượng ở độ chính xác cố định; TEXT lưu mã, nhãn và thời điểm ISO-8601. BOOLEAN biểu diễn bằng INTEGER 0/1 vì SQLite không có boolean storage class riêng. [SQLite Datatypes](https://www.sqlite.org/datatype3.html).
- Timestamp là UTC ISO-8601 chính xác milliseconds theo format YYYY-MM-DDTHH:MM:SS.SSSZ; ngày nghiệp vụ là YYYY-MM-DD. Business date độc lập created_at; range dùng [start,end), biên ngày Asia/Ho_Chi_Minh chuyển UTC cho event-time query.
- Tiền là VND integer; không FX. Quantity lưu milli-unit theo product base unit. HALF_UP dùng integer arithmetic; line amount được snapshot. AVG dùng S = integer sum và N = số giá trị non-NULL (kể cả zero): khi N>0, kết quả integer là sign(S) × floor((2×abs(S)+N)/(2×N)); tie làm tròn xa zero; khi N=0, kết quả là NULL/không xác định. AVG amount trả INTEGER VND; AVG quantity trả INTEGER milli-unit (0.001 base unit). Không dùng floating point cho tiền/quantity.
- Caps mô phỏng giới hạn ERP: quantity tối đa 1,000,000 milli-unit/line; unit price tối đa 1,000,000,000 VND; amount tối đa 1,000,000,000,000 VND/transaction; tối đa 100,000 order lines và 100,000 payment transactions/database. WMS giới hạn movement magnitude 1,000,000,000 milli-unit và tối đa 100,000 movements/database. Validator phải kiểm tra từng phép tính và aggregate trước freeze.
- Quantity dùng milli-unit nguyên (qty_milli = số lượng × 1000), theo base unit sản phẩm; không tự chuyển đổi EA/KG/L. Quantity chứng từ dương; dấu +/- nằm ở WMS movement.
- NULL chỉ biểu diễn thiếu/chưa biết/không áp dụng theo từng field; không dùng 0 thay NULL. Không lưu chuỗi rỗng; absence của quan hệ biểu diễn bằng không có child row. SUM trên tập rỗng không tự động mang nghĩa 0; Intent Card phải xác định có giữ entity không giao dịch hay không.
- Physical DDL dùng FK/CHECK; cross-row constraints được xác nhận bằng validator độc lập. Builder/validator bật PRAGMA foreign_keys trên connection của chúng; clients khác cũng phải làm như vậy.

## Quyết định đã chốt và trạng thái physical implementation

- Empty-result quota đúng 2 intents: 1 ERP và 1 WMS; placeholder được giữ tại ERP-EF-04 và WMS-EF-04 trước khi viết Intent Cards.
- Complexity totals: ERP 8/12/5 và WMS 8/12/5; competency-by-complexity chi tiết trong Coverage Matrix là allocation thiết kế, không thay rubric từng intent.
- ERP không dùng payment-state classification; return được phép trả một phần quantity đã mua nhưng mỗi received line nhận đầy đủ declared quantity.
- WMS transfer chỉ giữa warehouse khác nhau, đúng 2 legs atomic; running balance không âm sau từng posting batch.
- Inventory valuation ngoài benchmark; không cộng khác base unit; mọi ranking Intent Card phải chốt deterministic tie-break hoặc include ties.
- Mọi ranking tie policy là semantics của từng Intent Card; set-based EX chỉ kiểm tra membership, không kiểm tra thứ tự rows.
- Snapshot ban đầu và pass/fail evidence được lưu trong [physical database artifacts](../physical_database/README.md); Benchmark Owner xác nhận nghiệm thu Bước 2B riêng trong yêu cầu Autonomous Benchmark Implementation ngày 2026-11-09.

## Ranh giới Bước 2A

Bước 2A được nghiệm thu về mặt thiết kế logic ngày 2026-11-09, chỉ trong phạm vi ERD/Data Dictionary/Business Rules/Glossary/Coverage/Edge-case và R-01–R-11. Physical implementation được theo dõi riêng tại [Bước 2B](../physical_database/README.md); acceptance design không thay thế nghiệm thu database, seed hoặc validator artifacts. Chưa tạo 50 canonical SQL hay 550 câu hỏi.
