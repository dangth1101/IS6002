# Development paraphrase quality audit — dev-v2

> **Lịch sử v2–v4, không dùng làm chứng nhận wording hiện hành.** Các tỷ lệ/near-duplicate flags và nhận xét bên dưới thuộc lần audit cũ. Bản hiện hành là [v5 audit](DEV_V5_PARAPHRASE_AUDIT.md), với 82 sửa đổi và hai `TAXONOMY_LIMITATION`; tất cả câu vẫn chờ human review. Không diễn giải tỷ lệ tự kiểm tra cũ thành human semantic equivalence.

Status: draft; all Q0–Q10 still need human review. Heuristic checks do not prove equivalence.

## Q0 audit

All 10 Q0 were clarified to expose projection/output grain and relevant filters/status/time/unit/tie semantics already present in the card and SQL. No SQL projection conflicts found; no Owner decision is required. WMS-CD-02 already stated its key business semantics and was made explicit about the complete output columns.

## Variant audit

| Group | Lexical | Syntactic | Reordering | Mixed | Expected rows | Technical rows | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| ERP-EF-01 | 3 | 3 | 2 | 2 | 48 | 48 | VALIDATED_BY_AUTOMATION |
| ERP-GB-03 | 3 | 3 | 2 | 2 | 6 | 6 | VALIDATED_BY_AUTOMATION |
| ERP-RK-02 | 3 | 3 | 2 | 2 | 9 | 9 | VALIDATED_BY_AUTOMATION |
| ERP-JN-02 | 3 | 3 | 2 | 2 | 156 | 156 | VALIDATED_BY_AUTOMATION |
| ERP-TM-02 | 3 | 3 | 2 | 2 | 27 | 27 | VALIDATED_BY_AUTOMATION |
| WMS-EF-01 | 3 | 3 | 2 | 2 | 44 | 44 | VALIDATED_BY_AUTOMATION |
| WMS-EF-02 | 3 | 3 | 2 | 2 | 6 | 6 | VALIDATED_BY_AUTOMATION |
| WMS-AG-02 | 3 | 3 | 2 | 2 | 4 | 4 | VALIDATED_BY_AUTOMATION |
| WMS-JN-04 | 3 | 3 | 2 | 2 | 24 | 24 | VALIDATED_BY_AUTOMATION |
| WMS-CD-02 | 3 | 3 | 2 | 2 | 80 | 80 | VALIDATED_BY_AUTOMATION |

Totals: **100/100 variants** are authored as content-bearing transformations rather than fixed lead-in/lead-out wrappers; quotas are 30 lexical, 30 syntactic, 20 reordering, 20 mixed. All 100 remain `NEEDS_HUMAN_REVIEW`; this count is an authoring/heuristic audit, not a semantic-equivalence acceptance rate.

## Examples by taxonomy

### Lexical

ERP-AG equivalent terms: ‘tổng lượng xuất giao khách’ / ‘lượng đã xuất cho khách’; filters, unit and aggregation retained.

### Syntactic

ERP-JN-02 changes from a direct request to a question over each order line and its full six-field projection.

### Reordering

ERP-TM-02 states the delivered/local-year filters before grouping by local date, while retaining [start,end) and no zero-day rows.

### Mixed

WMS-CD-02 combines alternative wording for planned/executed quantities with reordered status and transfer rules; secondary tags identify both transformations.

## Q0 wording changes

| Group | Previous Q0 | Revised Q0 |
|---|---|---|
| ERP-EF-01 | Cho xem các đơn hàng đã xác nhận? | Liệt kê từng đơn hàng ở trạng thái CONFIRMED, kèm mã đơn, số đơn, mã khách hàng, ngày đặt và trạng thái. |
| ERP-GB-03 | Đếm confirmed orders theo sales rep, gồm nhóm chưa gán? | Với mỗi sales rep có confirmed orders, kể cả một nhóm riêng cho sales rep chưa gán (NULL), cho biết mã sales rep, tên nếu có và số đơn CONFIRMED trong toàn bộ dữ liệu. |
| ERP-RK-02 | Trong từng đơn vị cơ sở, những SKU nào thuộc top 3 số lượng bán trong các đơn đã xác nhận, kể cả đồng hạng tại vị trí thứ ba? | Trong từng base unit riêng biệt, xếp hạng mỗi SKU theo tổng ordered quantity của các đơn CONFIRMED; trả SKU, tên sản phẩm, base unit, tổng lượng (milli-unit) và hạng, lấy mọi hạng từ 1 đến 3 kể cả đồng hạng ở mốc 3. |
| ERP-JN-02 | Hiển thị từng dòng confirmed order cùng tên sản phẩm? | Liệt kê từng dòng của mọi đơn CONFIRMED, một dòng cho mỗi order line, gồm số đơn, ngày đặt, SKU, tên sản phẩm, ordered quantity theo milli-unit và line net theo VND. |
| ERP-TM-02 | Mỗi ngày trong năm 2025 có bao nhiêu chuyến giao hàng được ghi nhận là đã giao? | Cho mỗi ngày Việt Nam trong năm 2025 có ít nhất một shipment DELIVERED, trả ngày địa phương và số shipment; dùng delivered_at_utc quy đổi sang Asia/Ho_Chi_Minh, khoảng [2025-01-01, 2026-01-01), không tạo dòng cho ngày không có shipment. |
| WMS-EF-01 | Liệt kê chứng từ kho đã posted? | Liệt kê từng inventory document có document_status POSTED, gồm document ID, document number, document type, trạng thái và business date. |
| WMS-EF-02 | Liệt kê SKU có base unit là KG? | Liệt kê từng product có base_unit KG, gồm product ID, SKU, tên sản phẩm, base unit và category ID (giữ NULL nếu chưa phân loại). |
| WMS-AG-02 | Với từng SKU có đơn vị cơ sở là KG, tổng lượng xuất giao khách là bao nhiêu? | Với mỗi product có base_unit KG và phát sinh ít nhất một movement âm thuộc chứng từ SHIPMENT đã POSTED trong toàn bộ lịch sử, trả product ID, SKU, base unit và tổng lượng xuất (milli-KG). |
| WMS-JN-04 | Liệt kê transfer movement legs giữa hai warehouse theo chứng từ? | Liệt kê từng movement leg của mỗi chứng từ TRANSFER POSTED, một dòng mỗi leg; gồm document ID/no, line number, SKU, leg number/role, warehouse nguồn/đích, signed quantity milli-unit và thời điểm movement UTC. |
| WMS-CD-02 | Với mỗi chứng từ và SKU, so sánh số lượng theo kế hoạch với số lượng đã thực hiện; chứng từ chưa post có số lượng thực hiện bằng không? | Với mọi cặp document × SKU, bất kể trạng thái, trả document ID/no/type/status, SKU, base unit, planned quantity và executed quantity theo milli-unit; executed bằng 0 nếu document chưa POSTED, TRANSFER chỉ tính SOURCE leg một lần, loại POSTED khác theo movement rules đã chốt. |

## Semantic risks for reviewers

- ERP-GB-03: confirm ‘mã sales rep, tên nếu có’ maps to the nullable sales_rep_id and LEFT JOIN employee name; NULL stays one group.
- ERP-TM-02: confirm Vietnamese local date, half-open 2025 interval, DELIVERED only, and no generated zero-count dates.
- ERP-RK-02: confirm milli-quantity remains within each base unit; rank <=3 includes ties at third position.
- WMS-AG-02: confirm ‘lượng xuất giao khách’ means negative movement magnitude from POSTED SHIPMENT only, output in milli-KG.
- WMS-JN-04: confirm one row per movement leg and signed movement quantity; both transfer legs remain visible.
- WMS-CD-02: confirm all document statuses, planned/executed milli-units, transfer SOURCE once, and other posted types per rules.
- Every lexical synonym and mixed wording remains subject to Vietnamese domain review; no item has been accepted automatically.

## Provenance

Previous registry SHA-256 (generic-wrapper version) is recorded in `dataset_v1_before_paraphrase_rewrite.json`.

Registry SHA-256: `debbace269fcc19526eb3fa403806715a22a0ccedd4148f65951b68999b30484`  
Validation Records SHA-256: `ba8307e3ec435064f27567f6015d8d3202e150de560042584b910becbfbb254d`  
Expected outputs SHA-256: `65759da39903bb217b509c1704759d67f2ab8c7f688017ada00391cb2231be89`  
Audit JSON: `benchmark_data/authoring/dev_paraphrase_quality_audit.json`  
Question changes are confined to Development Q0–Q10; SQL candidates, expected rows, Python oracles and frozen snapshots are unchanged.

## Projection alignment revision dev-v4 (2026-11-09)

Benchmark Owner chose Option B for `ERP-RK-02`: final SELECT returns exactly SKU, product name, base unit, sold quantity and rank. Partitioning by `base_unit`, top-three cutoff and tie inclusion are unchanged. Expected outputs were re-derived by the Python oracle before candidate SQL execution; main and fixture results now have five columns. Dataset machine `validation_status` matches `ground_truth_validation.json`; `intent_card_status`, `ground_truth_review`, all question review states and Owner approval remain pending. The evaluator gates release using the registry review/freeze fields; machine validation is evidence, not approval.

All questions remain pending human semantic review. See the [v4 review package](dev_human_approval/README.md).

## Near-duplicate audit

The repository token-Jaccard audit reports **19 candidate pairs**: **3 within-group** and **16 between-group**. Among between-group pairs, **0 involve Development** and **0 cross the split**. All between-group flags are in Final; within-group flags are expected comparison candidates, not cross-group leakage. A flag requires human inspection and is not a semantic judgment.

| Scope | Pair | Similarity |
|---|---|---:|
| within_group_variant | ERP-EF-04-Q00 ↔ ERP-EF-04-Q01 | 0.8000 |
| within_group_variant | WMS-AG-03-Q00 ↔ WMS-AG-03-Q01 | 0.8148 |
| within_group_variant | WMS-AG-03-Q00 ↔ WMS-AG-03-Q04 | 0.7857 |
| between_groups | ERP-GB-01-Q01 ↔ WMS-GB-01-Q01 | 0.7500 |
| between_groups | ERP-GB-01-Q02 ↔ WMS-GB-01-Q02 | 0.7857 |
| between_groups | ERP-GB-01-Q03 ↔ WMS-GB-01-Q03 | 0.8333 |
| between_groups | ERP-GB-01-Q04 ↔ WMS-GB-01-Q04 | 0.7857 |
| between_groups | ERP-GB-01-Q05 ↔ WMS-GB-01-Q05 | 0.7857 |
| between_groups | ERP-GB-01-Q06 ↔ WMS-GB-01-Q06 | 0.8125 |
| between_groups | ERP-GB-01-Q07 ↔ WMS-GB-01-Q07 | 0.8421 |
| between_groups | ERP-GB-01-Q08 ↔ WMS-GB-01-Q08 | 0.8000 |
| between_groups | ERP-GB-01-Q09 ↔ WMS-GB-01-Q09 | 0.8571 |
| between_groups | ERP-GB-01-Q10 ↔ WMS-GB-01-Q10 | 0.8696 |
| between_groups | ERP-GB-02-Q10 ↔ ERP-NA-01-Q10 | 0.7333 |
| between_groups | ERP-JN-01-Q09 ↔ ERP-NA-01-Q09 | 0.7200 |
| between_groups | ERP-JN-01-Q10 ↔ ERP-JN-04-Q10 | 0.7241 |
| between_groups | ERP-JN-01-Q10 ↔ ERP-NA-01-Q10 | 0.7407 |
| between_groups | WMS-AG-01-Q09 ↔ WMS-GB-01-Q09 | 0.7391 |
| between_groups | WMS-AG-01-Q10 ↔ WMS-GB-01-Q10 | 0.7600 |
