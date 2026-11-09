# BIRD-VN-Robust-50 — Database Coverage Matrix

| Thuộc tính | Giá trị |
|---|---|
| Version / status | 0.2.0 — Logic design accepted, 2026-11-09; intent mapping drafted in `../intent_cards/`, pending owner approval |
| Quota basis | BENCHMARK_SPEC.md §6; Decision Review D2, D4, D11 |
| Scope | Chứng minh schema dự kiến có đường dữ liệu cho quota; không phải Questions hoặc gold SQL |

## 1. Phân bổ quota đã duyệt

Mỗi đơn vị là intent slot dự kiến, không chứa wording câu hỏi hay truy vấn chuẩn.

| Competency | ERP | WMS | Tổng | Simple | Moderate | Challenging | Đường dữ liệu logic tiêu biểu |
|---|---:|---:|---:|---:|---:|---:|---|
| Entity filtering / điều kiện | 4 | 4 | 8 | 4 | 3 | 1 | ERP: order/customer/product/status/date; WMS: document/product/location/status/date |
| COUNT / SUM / AVG | 4 | 4 | 8 | 2 | 4 | 2 | ERP: lines/orders/payments; WMS: document lines/movements/quantity |
| GROUP BY | 4 | 4 | 8 | 2 | 4 | 2 | ERP: customer/product/category/rep; WMS: product/location/warehouse/type |
| Ranking / top-k / min-max / ties | 3 | 3 | 6 | 1 | 2 | 3 | ERP: customer/product/rep net sales; WMS: SKU/location stock metric |
| Join nhiều bảng | 4 | 4 | 8 | 2 | 5 | 1 | ERP: customer→orders→lines; WMS: document→lines→movements→location |
| Time boundaries | 2 | 2 | 4 | 2 | 2 | 0 | ERP: order/delivery/payment dates; WMS: business_date/movement cutoff |
| NULL / zero / absence | 2 | 2 | 4 | 2 | 1 | 1 | ERP: missing rep/payment/return; WMS: NULL category, no movement vs zero balance |
| Conditional / derived metric | 2 | 2 | 4 | 1 | 3 | 0 | ERP: order value vs recognized revenue; WMS: signed quantity/posted-only balance |
| **Tổng** | **25** | **25** | **50** | **16** | **24** | **10** | 50 intent slots / 50 groups |

## 2. Cross-tab competency × domain × complexity

Đây là cross-tab đề xuất thiết kế; D11 phê duyệt tổng quota chứ không tự phê duyệt từng slot. Độ khó cần áp rubric khi authoring, không suy ra chỉ từ số bảng.

| Competency | ERP S/M/C | WMS S/M/C | Gộp S/M/C |
|---|---:|---:|---:|
| Entity filtering | 2 / 2 / 0 | 2 / 1 / 1 | 4 / 3 / 1 |
| COUNT / SUM / AVG | 1 / 2 / 1 | 1 / 2 / 1 | 2 / 4 / 2 |
| GROUP BY | 1 / 2 / 1 | 1 / 2 / 1 | 2 / 4 / 2 |
| Ranking / top-k | 0 / 1 / 2 | 1 / 1 / 1 | 1 / 2 / 3 |
| Join nhiều bảng | 1 / 3 / 0 | 1 / 2 / 1 | 2 / 5 / 1 |
| Time boundaries | 1 / 1 / 0 | 1 / 1 / 0 | 2 / 2 / 0 |
| NULL / zero / absence | 1 / 0 / 1 | 1 / 1 / 0 | 2 / 1 / 1 |
| Conditional / derived metric | 1 / 1 / 0 | 0 / 2 / 0 | 1 / 3 / 0 |
| **Tổng** | **8 / 12 / 5** | **8 / 12 / 5** | **16 / 24 / 10** |

S/M/C = Simple/Moderate/Challenging. Benchmark Owner chốt complexity totals ERP 8/12/5 và WMS 8/12/5. Cross-tab phân bổ complexity bên trong từng competency là kế hoạch mapping; mỗi slot vẫn phải được gán và kiểm tra theo rubric trước authoring.

## 3. Intent-slot map — không phải Questions

Các ID là placeholder quản lý coverage. Mô tả chỉ là query capability ở mức khái quát, không phải câu hỏi tự nhiên và không chốt semantics đủ tạo gold SQL. Chuyển slot thành Intent Card chỉ sau khi Business Rules/Glossary được xác minh.

| Domain / slot range | Số slot | Đường truy vấn logic được schema hỗ trợ |
|---|---:|---|
| ERP-EF-01..04 | 4 | Filter customer/order/product theo status, segment, date, threshold; giữ ERP-EF-04 làm empty-result slot |
| ERP-AG-01..04 | 4 | Count entity khác nhau; sum/avg line net với grain rõ |
| ERP-GB-01..04 | 4 | Group theo customer/product/category/rep, kể cả parent không có child nếu cần |
| ERP-RK-01..03 | 3 | Top/min/max theo sales measure với tie policy tường minh |
| ERP-JN-01..04 | 4 | Customer/order/line/product; payment/return cần preaggregate chống fan-out |
| ERP-TM-01..02 | 2 | Lọc order date và delivery/payment event time theo [start,end) |
| ERP-NA-01..02 | 2 | No order/no payment/NULL assignment vs amount zero |
| ERP-CD-01..02 | 2 | Phân biệt order value theo order_date với recognized revenue theo delivered_at; không có payment-state classification |
| WMS-EF-01..04 | 4 | Filter SKU/document/location/warehouse/status/time/quantity; giữ WMS-EF-04 làm empty-result slot |
| WMS-AG-01..04 | 4 | Count documents/lines/movements; sum/avg signed quantity theo grain |
| WMS-GB-01..04 | 4 | Group theo SKU/location/warehouse/document type |
| WMS-RK-01..03 | 3 | Rank SKU/location theo on-hand/movement metric, xử lý ties |
| WMS-JN-01..04 | 4 | Document/line/movement/product/location/warehouse; transfer fan-out |
| WMS-TM-01..02 | 2 | Filter business date và UTC/local movement cutoff |
| WMS-NA-01..02 | 2 | No movement vs net zero; NULL category vs unclassified; entity không movement |
| WMS-CD-01..02 | 2 | Posted-only on-hand hoặc signed movement metric |

## 4. Schema adequacy và nguy cơ

| Năng lực | ERP đường dữ liệu / grain | WMS đường dữ liệu / grain | Kiểm tra cần có |
|---|---|---|---|
| Filter / time | SALES_ORDERS, SALES_SHIPMENTS, PAYMENT_TRANSACTIONS | INVENTORY_DOCUMENTS, INVENTORY_MOVEMENTS | Status, [start,end), timezone |
| Aggregate / group | SALES_ORDER_LINES, preaggregate theo order/customer/product | INVENTORY_MOVEMENTS, sum theo location trước warehouse roll-up | Duplicate/fan-out, entity count vs row count |
| Multi-table join | customer→order→line; payment/return là child path riêng | document→line→movement→location→warehouse | Không nhân amount hoặc planned quantity |
| Ranking / ties | Group theo business key; explicit deterministic tie policy | Product/location metric tại cutoff xác định | Equal values, top-k boundary |
| NULL / zero / absence | Nullable employee/category/return; zero net/payment vs no row | Optional category; no movement vs movement sum 0 | LEFT JOIN, COUNT(child PK), COALESCE |
| Conditional metric | CASE theo order/shipment/payment status | CASE theo document type/status/sign | Chỉ tính cohort ghi trong Intent Card |

Đúng 2 empty-result intent được phân bổ: một ERP (ERP-EF-04) và một WMS (WMS-EF-04). Đây là slot reserve, chưa phải Intent Card hoặc Question. Empty result phải là kết quả đúng theo Intent Card và cần collision fixture để phát hiện false-empty SQL.

Mọi ranking Intent Card phải ghi tie policy: deterministic secondary key (metric + stable ID/SKU) hoặc include all ties khi đó là yêu cầu nghiệp vụ. Set-based EX chỉ so membership, không kiểm tra row order.

## 5. Freeze gates

- Mỗi entity, grain, metric, status/time rule và NULL semantics phải giữ căn cứ simulation rules đã được Owner chấp nhận; không tuyên bố là chuẩn ngành.
- Complexity totals ERP/WMS 8/12/5 và empty-result quota 1/1 đã chốt; gán từng slot theo rubric và lưu tie policy trong Intent Card.
- Chuyển edge cases vào fixture plan ở bước dữ liệu sau; file này chưa chứa fixture records.
- Mỗi intent sau này cần Validation Record, expected outputs suy ra độc lập, alternative check/oracle khi khả thi, execution evidence và final human approval.

## Nguồn

- Quota dự án: [BENCHMARK_SPEC.md](../BENCHMARK_SPEC.md) §6; [DECISION_REVIEW.md](../DECISION_REVIEW.md) D1–D7, D10, D11.
- Kỹ thuật SQLite: [SQLite Datatypes](https://www.sqlite.org/datatype3.html); [SQLite Foreign Key Support](https://www.sqlite.org/foreignkeys.html).
- Schema/business rules: design logic IS6002 được nghiệm thu 2026-11-09; synthetic assumptions, không phải chuẩn ngành.
