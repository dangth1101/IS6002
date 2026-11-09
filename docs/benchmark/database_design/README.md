# BIRD-VN-Robust-50 — Database Logic Design

| Thuộc tính | Giá trị |
|---|---|
| Phiên bản | 0.1.0 — Draft, logic-only |
| Ngày | 2026-11-09 |
| Phạm vi | Thiết kế logic ERP Sales, WMS Inventory và coverage; chưa có physical database |
| Trạng thái | D1–D7, D10, D11 được ghi APPROVED; thiết kế chi tiết này chưa được Benchmark Owner phê duyệt |

## Bộ tài liệu

- [ERP Sales logical design](ERP_SALES_DESIGN.md): phạm vi, ERD, data dictionary, business rules, glossary và edge cases.
- [WMS Inventory logical design](WMS_INVENTORY_DESIGN.md): cùng các nội dung trên cho kho.
- [Coverage Matrix](COVERAGE_MATRIX.md): ánh xạ quota competency/complexity đã duyệt vào khả năng schema; không tạo câu hỏi benchmark.

## Căn cứ và ranh giới giữa nguồn với giả định

1. Quy mô và quota benchmark lấy từ [BENCHMARK_SPEC.md](../BENCHMARK_SPEC.md) §2, §6 và Decision Review D1–D7, D10, D11: 50 Semantic Groups; 25 ERP và 25 WMS; competency quota 8/8/8/6/8/4/4/4; complexity 16/24/10. Đây là yêu cầu dự án đã phê duyệt, không phải thông lệ ngành.
2. D4 phê duyệt định hướng hai SQLite DB và yêu cầu xác minh nghiệp vụ trước annotation. D4 không phê duyệt status, quy tắc ghi nhận doanh thu, tồn kho hay glossary trong các tài liệu này. Các quy tắc đó được gắn nhãn **Mô phỏng — đề xuất cần Benchmark Owner xác nhận**.
3. Nguồn ngoài về kỹ thuật SQLite: SQLite không có storage class riêng cho ngày/giờ; tài liệu chính thức nêu các biểu diễn TEXT/REAL/INTEGER, và thiết kế này chọn ISO-8601 TEXT. SQLite cần bật foreign-key enforcement trên từng connection; bước triển khai sau phải bật và xác nhận PRAGMA foreign_keys. [SQLite Datatypes](https://www.sqlite.org/datatype3.html), [SQLite Foreign Key Support](https://www.sqlite.org/foreignkeys.html).
4. Không có nguồn ERP/WMS cụ thể được chỉ định trong tài liệu dự án. Không quy tắc mô phỏng nào ở đây được trình bày như chuẩn ERP/WMS phổ quát. Trước khi freeze, Benchmark Owner cần chọn domain owner hoặc nguồn nghiệp vụ thay thế.

## Quy ước thiết kế dùng chung — đề xuất mô phỏng

- Khóa chính logic là ID số nguyên ổn định; mã nghiệp vụ có UNIQUE và không dùng làm FK.
- SQLite INTEGER lưu tiền VND và số lượng ở độ chính xác cố định; TEXT lưu mã, nhãn và thời điểm ISO-8601. BOOLEAN biểu diễn bằng INTEGER 0/1 vì SQLite không có boolean storage class riêng. [SQLite Datatypes](https://www.sqlite.org/datatype3.html).
- Timestamp là UTC ISO-8601 có hậu tố Z; ngày nghiệp vụ là YYYY-MM-DD. Múi giờ diễn giải đề xuất Asia/Ho_Chi_Minh; khoảng ngày dùng [start, end) sau khi quy đổi biên local sang UTC. Đây là quy tắc mô phỏng, cần xác nhận.
- Tiền là VND nguyên; không có FX/conversion trong scope. Giá trị dòng cho lượng phân số được làm tròn HALF_UP đến 1 VND tại từng dòng. Công thức và giới hạn integer phải được kiểm tra bằng fixture trước khi triển khai.
- Quantity dùng milli-unit nguyên (qty_milli = số lượng × 1000), theo base unit sản phẩm; không tự chuyển đổi EA/KG/L. Quantity chứng từ dương; dấu +/- nằm ở WMS movement.
- NULL chỉ biểu diễn thiếu/chưa biết/không áp dụng theo từng field; không dùng 0 thay NULL. Không lưu chuỗi rỗng; absence của quan hệ biểu diễn bằng không có child row. SUM trên tập rỗng không tự động mang nghĩa 0; Intent Card phải xác định có giữ entity không giao dịch hay không.
- Các FK/CHECK dưới đây là logical constraints dự kiến. SQLite chỉ enforce FK khi bật trên connection; enforcement cần được xác minh ở bước tạo DB. Không có schema.sql trong Bước 2A.

## Quyết định còn cần xác nhận trước physical build

- Người/nguồn kiểm định nghiệp vụ ERP Sales và WMS Inventory.
- Status flow, điều kiện chuyển trạng thái, revenue recognition, payment/refund/return semantics và định nghĩa tồn kho hiện tại/lịch sử.
- VND-only, precision 0.001, rounding HALF_UP, timezone Asia/Ho_Chi_Minh, interval [start,end).
- Có chấp nhận mô hình không hỗ trợ partial delivery/partial return hay cần mở rộng.
- Quota 2–3 empty-result intents từ D6 cần fixture nào; chưa chọn item.
- Chấp nhận hay sửa entity/table/attribute và quan hệ đề xuất trong hai design docs.

## Ranh giới Bước 2A

Đây là thiết kế logic để review. Chưa tạo database vật lý, schema.sql, seed.sql, 50 canonical SQL, 550 câu hỏi hoặc dữ liệu fixture thực tế; chưa sửa source Python và không gọi LLM API. Bước 2B chưa bắt đầu.
