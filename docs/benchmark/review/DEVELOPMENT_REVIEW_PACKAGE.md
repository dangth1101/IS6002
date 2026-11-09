# BIRD-VN-Robust-50 — Development Review Package

**Ngày chuẩn bị:** 2026-11-09  
**Trạng thái:** Dự thảo cho Benchmark Owner; không có quyết định nào được tự phê duyệt.  
**Phạm vi:** 10 Development groups (110 Questions). Không mở hoặc dùng 40 Final groups để tuning.

> **Cập nhật sau quyết định Benchmark Owner 2026-11-09:** nội dung lịch sử ở §2 về lựa chọn semantics cho ERP-RK-02 và WMS-CD-02 đã được thay thế. ERP-RK-02 dùng ranking riêng theo `base_unit` và giữ mọi tie tại hạng 3. WMS-CD-02 gồm mọi document status; non-POSTED có executed=0; TRANSFER dùng SOURCE một lần; document type khác dùng tổng trị tuyệt đối movement theo các synthetic rules đã chốt. Xem Validation Records/evidence mới ở §1; không có human approval nào được tự ghi.

## Latest validation run after the Owner decisions

| Group | Main snapshot rows | Temporary fixture result |
|---|---:|---|
| ERP-EF-01 | 48 | Not required |
| ERP-GB-03 | 6 | Not required |
| ERP-JN-02 | 156 | 156 / PASS: confirmed-only line control |
| ERP-TM-02 | 27 | 29 / PASS: before/start/last-day/exclusive-end boundaries |
| ERP-RK-02 | 9 | 10 / PASS: EA/KG/L partitioned; EA tie at rank 3 retained |
| WMS-EF-01 | 44 | Not required |
| WMS-EF-02 | 6 | Not required |
| WMS-AG-02 | 4 | 4 / PASS: negative adjustment/transfer decoys excluded |
| WMS-CD-02 | 80 | 87 / PASS: DRAFT/CANCELLED zero; POSTED type invariants; transfer counted once |
| WMS-JN-04 | 24 | 26 / PASS: duplicate-looking valid transfer identity retained |

The six temporary expected outputs were written to `dev_fixture_expected_outputs.json` before candidate execution. All six candidate/oracle fixture comparisons pass. Main snapshot outputs were derived before executing candidates; all 10 main comparisons match. The run reports 10 `VALIDATED_BY_AUTOMATION`, while all 10 Validation Records and all 550 Questions remain pending human review. The 40 Final groups remain blocked.

The updated text audit flags 25 token-Jaccard pairs: 9 within the same groups and 16 between Final groups; none cross splits or pair distinct Development groups. Similarity flags remain wording review hints, not semantic approvals. The six Development fixture proposals are closed by temporary evidence; 35 non-Dev fixture proposals remain open in `defect_report.json`.

Latest artifacts: [`ground_truth_validation.json`](../../benchmark_data/authoring/ground_truth_validation.json), [`dev_fixture_expected_outputs.json`](../../benchmark_data/authoring/dev_fixture_expected_outputs.json), [`dev_fixture_validation.json`](../../benchmark_data/authoring/dev_fixture_validation.json), and [`validation_records.json`](../../benchmark_data/authoring/validation_records.json).

## 1. Tóm tắt trạng thái

Artifacts được tạo từ registry và snapshot đã đóng băng. Expected outputs của 10 Dev groups được tạo bằng Python oracle trước khi chạy canonical SQL. Candidate SQL được thực thi read-only trên snapshot; kết quả đối chiếu dùng set-based EX.

| Trạng thái automation | Số nhóm | Ý nghĩa |
|---|---:|---|
| `VALIDATED_BY_AUTOMATION` | 4 | Khớp Python oracle và coverage audit hiện ghi `SUPPORTED`; vẫn cần Owner duyệt intent, SQL, output và wording. |
| `NEEDS_HUMAN_REVIEW` | 6 | Candidate khớp output đã ghi, nhưng còn fixture/định nghĩa measure cần giải quyết trước khi coi canonical SQL là gold. |
| `BLOCKED` | 0 Dev / 40 Final | 40 Final chưa có expected outputs, chưa thực thi canonical SQL. |

### Evidence files

- Registry, Intent Cards và variants: [`benchmark_data/authoring/dataset.json`](../../benchmark_data/authoring/dataset.json)
- SQL candidates: [`benchmark_data/authoring/ground_truth_candidates.sql`](../../benchmark_data/authoring/ground_truth_candidates.sql)
- Expected rows được tạo trước khi candidate SQL chạy: [`benchmark_data/authoring/expected_outputs_dev.json`](../../benchmark_data/authoring/expected_outputs_dev.json)
- SQL execution và row hashes: [`benchmark_data/authoring/ground_truth_validation.json`](../../benchmark_data/authoring/ground_truth_validation.json)
- Per-group Validation Records: [`benchmark_data/authoring/validation_records.json`](../../benchmark_data/authoring/validation_records.json)
- Coverage/fixture proposals: [`benchmark_data/authoring/defect_report.json`](../../benchmark_data/authoring/defect_report.json)
- Static SQL, quota, near-duplicate audit: [`benchmark_data/authoring/draft_validation.json`](../../benchmark_data/authoring/draft_validation.json)
- Frozen database manifest: [`benchmark_data/physical/build_manifest.json`](../../benchmark_data/physical/build_manifest.json)

DB SHA-256 hiện khớp manifest: ERP `347c0e7b663d74c740c6b1fba4a2b89a6ca21beeb4148bd8bff41ed3a4ca888b`; WMS `c55c41e8755dccd1e0d77aaaf86b0dcf2895b75ae8a8d5b1891774e26cf589d5`.

## 2. Initial findings before Owner decisions (historical; see update above)

Mọi SQL dưới đây là candidate, không phải canonical SQL được phê duyệt. Sample output được rút gọn; toàn bộ rows và hash nằm trong `expected_outputs_dev.json` và `ground_truth_validation.json`.

### ERP-JN-02 — Chi tiết dòng đơn hàng

- **Intent:** Hiển thị từng dòng confirmed order kèm sản phẩm, số lượng và giá trị dòng.
- **SQL candidate:** `SELECT o.order_no,o.order_date,p.sku,p.product_name,l.ordered_qty_milli,l.net_vnd FROM SALES_ORDERS o JOIN SALES_ORDER_LINES l ON l.order_id=o.order_id JOIN PRODUCTS p ON p.product_id=l.product_id WHERE o.order_status='CONFIRMED' ORDER BY o.order_id,l.line_no`
- **Kết quả:** 156 rows; actual SHA `a12707b29c8207015244f97dd5f2d81ce4cfd9f33f312463aac9c57de61e7518`, bằng expected SHA. Ví dụ: `SO-00001 / SKU-005 / 3200 milli / 2,450,000 VND`.
- **Bằng chứng:** Python table-scan oracle `erp_jn_02`; 216 order lines trong snapshot, tối đa 4 dòng/đơn; candidate dùng FK trực tiếp order→line→product.
- **Chưa đạt:** Chưa có fixture xác nhận loại trừ draft/cancelled và phát hiện duplicate/corrupt line. Wording hiện chỉ rõ confirmed.
- **Owner xác nhận:** Grain là một hàng cho mỗi order line; chỉ `CONFIRMED`; cột `net_vnd` là giá trị dòng; có chấp nhận row order là không được EX bảo đảm hay cần ghi tie/order policy riêng.

### ERP-TM-02 — Số chuyến giao theo ngày địa phương

- **Intent:** Đếm shipment đã giao theo ngày tại Việt Nam trong năm 2025.
- **SQL candidate:** `SELECT date(delivered_at_utc,'+7 hours') AS delivered_local_date,COUNT(shipment_id) AS delivered_shipment_count FROM SALES_SHIPMENTS WHERE shipment_status='DELIVERED' AND delivered_at_utc >= '2024-12-31T17:00:00.000Z' AND delivered_at_utc < '2025-12-31T17:00:00.000Z' GROUP BY delivered_local_date ORDER BY delivered_local_date`
- **Kết quả:** 27 ngày có shipment; expected và actual row hashes trùng. Ví dụ: `2025-04-14 → 1`, `2025-04-15 → 1`.
- **Bằng chứng:** Python oracle chuyển UTC instant sang UTC+7; filter half-open tương ứng năm 2025 theo `Asia/Ho_Chi_Minh`; chỉ trạng thái `DELIVERED`.
- **Chưa đạt:** Chưa có fixture ngay trước/tại local midnight và hai biên năm; NULL delivery timestamp chưa có đối chứng.
- **Owner xác nhận:** Dùng `delivered_at_utc` (không dùng order date); local year 2025 với `[2025-01-01, 2026-01-01)`; NULL event bị loại; chỉ những ngày có shipment xuất hiện (không scaffold ngày 0).

### ERP-RK-02 — Top SKU theo lượng bán

- **Intent:** Xếp top 3 SKU theo số lượng trong confirmed orders.
- **SQL candidate:** `WITH sku_qty AS (SELECT p.product_id,p.sku,p.product_name,p.base_unit,SUM(l.ordered_qty_milli) AS sold_qty_milli FROM PRODUCTS p JOIN SALES_ORDER_LINES l ON l.product_id=p.product_id JOIN SALES_ORDERS o ON o.order_id=l.order_id WHERE o.order_status='CONFIRMED' GROUP BY p.product_id,p.sku,p.product_name,p.base_unit), ranked AS (SELECT *,RANK() OVER(ORDER BY sold_qty_milli DESC) AS rnk FROM sku_qty) SELECT product_id,sku,product_name,base_unit,sold_qty_milli,rnk FROM ranked WHERE rnk<=3 ORDER BY rnk,product_id`
- **Kết quả:** 3 rows; current leaders include SKU-012 `111600 L`, SKU-003 and SKU-009 each `108600 L`; hashes trùng oracle.
- **Bằng chứng:** 12 product/unit rows; SQL and Python oracle aggregate quantities by product, then rank with ties.
- **Chưa đạt — BLOCKER nghiệp vụ:** Snapshot có base units khác nhau. Đặc tả đã chốt không cộng quantity giữa các base unit; top-3 toàn bộ SKU đang so sánh milli-EA, milli-KG và milli-L như thể cùng đơn vị. Fixture tie không giải quyết được vấn đề này.
- **Owner xác nhận:** Chọn một định nghĩa: (a) top-3 trong một base unit được nêu trong câu hỏi, (b) nhóm/rank riêng theo base unit, hoặc (c) đổi measure/intent. Sau khi chốt phải sửa Intent Card, wording Q0, candidate SQL và oracle; không được coi output hiện tại là gold.

### WMS-AG-02 — Tổng lượng giao theo SKU KG

- **Intent:** Tổng hợp lượng xuất giao khách của SKU có base unit KG.
- **SQL candidate:** `SELECT p.product_id,p.sku,p.base_unit,SUM(-m.qty_delta_milli) AS shipped_qty_milli FROM INVENTORY_MOVEMENTS m JOIN INVENTORY_DOCUMENT_LINES dl ON dl.document_line_id=m.document_line_id JOIN INVENTORY_DOCUMENTS d ON d.document_id=dl.document_id JOIN PRODUCTS p ON p.product_id=dl.product_id WHERE d.document_status='POSTED' AND d.document_type='SHIPMENT' AND p.base_unit='KG' AND m.qty_delta_milli<0 GROUP BY p.product_id,p.sku,p.base_unit ORDER BY p.product_id`
- **Kết quả:** 4 SKU; ví dụ SKU-011 `15149 milli-KG`, SKU-002 `33121 milli-KG`; actual/expected hashes trùng.
- **Bằng chứng:** Python table-scan oracle lọc posted shipment, negative movement và KG; snapshot có 20 posted shipments.
- **Chưa đạt:** Cần decoy adjustment/transfer âm trên cùng SKU để chứng minh lọc `SHIPMENT`; cần xác nhận unit/measure wording hiển thị milli-unit hay quy đổi.
- **Owner xác nhận:** “Lượng xuất giao khách” chỉ là movement của `POSTED SHIPMENT`; dùng độ lớn movement âm; chỉ SKU base unit KG; unit output milli-KG. Fixture là blocker cho bằng chứng phân biệt shipment với movement âm khác.

### WMS-CD-02 — Planned và posted quantity

- **Intent:** So sánh planned quantity với posted movement quantity theo chứng từ và SKU.
- **SQL candidate:** `WITH planned AS (SELECT document_id,product_id,SUM(planned_qty_milli) AS planned_qty_milli FROM INVENTORY_DOCUMENT_LINES GROUP BY document_id,product_id), moved AS (SELECT dl.document_id,dl.product_id,SUM(ABS(m.qty_delta_milli)) AS posted_movement_qty_milli FROM INVENTORY_MOVEMENTS m JOIN INVENTORY_DOCUMENT_LINES dl ON dl.document_line_id=m.document_line_id JOIN INVENTORY_DOCUMENTS d ON d.document_id=dl.document_id WHERE d.document_status='POSTED' GROUP BY dl.document_id,dl.product_id) SELECT d.document_id,d.document_no,d.document_type,p.sku,p.base_unit,pl.planned_qty_milli,COALESCE(mv.posted_movement_qty_milli,0) AS posted_movement_qty_milli FROM INVENTORY_DOCUMENTS d JOIN planned pl ON pl.document_id=d.document_id JOIN PRODUCTS p ON p.product_id=pl.product_id LEFT JOIN moved mv ON mv.document_id=pl.document_id AND mv.product_id=pl.product_id WHERE d.document_status='POSTED' ORDER BY d.document_id,p.product_id`
- **Kết quả hiện tại:** 78 rows, hashes trùng Python oracle. **12 transfer rows đều cho posted movement gấp 2 planned:** ví dụ WD-00007 planned `21000`, posted `42000`; WD-00008 `22000`→`44000`.
- **Bằng chứng:** Snapshot có transfer đúng hai legs đối dấu cùng quantity; oracle `wms_cd_02` cũng cộng `ABS()` trên cả hai legs. Vì vậy phép đối chiếu hiện tại lặp lại cùng giả định với SQL, không phải independent check cho transfer measure.
- **Chưa đạt — BLOCKER gold:** Tổng `ABS()` hai leg cho ra 2× lượng chuyển logic. Câu hỏi chưa định nghĩa “posted movement quantity” là tổng physical legs hay lượng nghiệp vụ đã chuyển một lần. Nếu benchmark intended executed quantity, SQL và oracle hiện sai measure.
- **Owner xác nhận:** Chốt transfer tính một lần (ví dụ source leg hoặc quy ước canonical) hay cộng cả hai physical legs; quy tắc với receipt/shipment/adjustment; `COALESCE` không movement thành zero có đúng không; output grain là document×SKU. Sau quyết định cần sửa cả SQL và Python oracle, thêm fixture riêng có planned≠posted và transfer legs.

### WMS-JN-04 — Hai legs của transfer

- **Intent:** Liệt kê source/destination movement legs cho posted transfer giữa hai warehouse.
- **SQL candidate:** `SELECT d.document_id,d.document_no,dl.line_no,p.sku,m.movement_leg_no,m.movement_role,src.warehouse_code AS source_warehouse,dst.warehouse_code AS destination_warehouse,m.qty_delta_milli,m.moved_at_utc FROM INVENTORY_DOCUMENTS d JOIN INVENTORY_DOCUMENT_LINES dl ON dl.document_id=d.document_id JOIN PRODUCTS p ON p.product_id=dl.product_id JOIN INVENTORY_MOVEMENTS m ON m.document_line_id=dl.document_line_id JOIN LOCATIONS loc ON loc.location_id=m.location_id JOIN WAREHOUSES src ON src.warehouse_id=d.from_warehouse_id JOIN WAREHOUSES dst ON dst.warehouse_id=d.to_warehouse_id WHERE d.document_type='TRANSFER' AND d.document_status='POSTED' ORDER BY d.document_id,dl.line_no,m.movement_leg_no`
- **Kết quả:** 24 rows = 12 transfer × 2 legs; hashes trùng. Ví dụ WD-00010 có `SOURCE -24000` và `DESTINATION +24000` cùng timestamp.
- **Bằng chứng:** Oracle quét document/line/movement; validator physical database đã kiểm tra cấu trúc transfer pairs.
- **Chưa đạt:** Cần test duplicate-looking valid leg vs corrupted missing/duplicate leg trên temporary fixture. Snapshot có 12 pair đúng, không có trường hợp lỗi.
- **Owner xác nhận:** Ý định là trả cả hai physical legs, không deduplicate theo SKU/quantity/timestamp; source/destination warehouse lấy từ document; chỉ posted transfer liên warehouse. Fixture là important validation, không phải snapshot defect.

## 3. Bốn nhóm đã khớp automation — human approval checklist

| Group | Candidate result / evidence | Owner checklist (không tự đánh dấu) |
|---|---|---|
| ERP-EF-01 | 48 rows; hashes khớp; snapshot 48 confirmed, 12 draft, 12 cancelled. SQL lọc `order_status='CONFIRMED'`. | [ ] Đúng mục tiêu/danh sách cột; [ ] confirmed là status duy nhất; [ ] grain order; [ ] Q0 và cả 10 variants cùng nghĩa. |
| ERP-GB-03 | 6 buckets: NULL rep=6; reps 1..5 = 9,10,9,7,7. Hashes khớp. | [ ] NULL assignment là bucket riêng; [ ] LEFT JOIN và count order đúng; [ ] không cần hiển thị employee NULL thành nhãn thay thế; [ ] variants giữ cùng grouping. |
| WMS-EF-01 | 44 posted documents; hashes khớp; SQL lọc document status POSTED. | [ ] grain document; [ ] chỉ posted; [ ] business_date là cột đúng; [ ] Q0–Q10 giữ loại/status/date projection. |
| WMS-EF-02 | 6 sản phẩm base unit KG; hashes khớp. | [ ] `base_unit='KG'`; [ ] category NULL vẫn được giữ; [ ] grain product; [ ] variants không diễn đạt nhầm “đang tồn kho” hoặc “đã nhập”. |

Cho mỗi group, người duyệt ghi ngày, tên/role, rationale, quyết định cho Intent Card, canonical SQL, expected output hash và Q0–Q10 trong Validation Record. `VALIDATED_BY_AUTOMATION` không đồng nghĩa `APPROVED`.

## 4. Phân loại 41 fixture proposals

`BLOCKING` = trước khi group dùng làm gold/evaluation vì hiện thiếu bằng chứng để xác định/kiểm tra đúng semantics hoặc tồn tại mâu thuẫn measure. `IMPORTANT` = semantics đọc được và candidate có thể review, fixture giúp bắt SQL sai có khả năng. `OPTIONAL` = tăng độ phủ nhưng không đổi kết luận gold cơ bản. Mọi fixture nếu cần chạy phải nằm trong temporary copy; không sửa frozen snapshot.

| Intent | Mức | Lý do ngắn |
|---|---|---|
| ERP-EF-02 | IMPORTANT | Kiểm thử inclusive start và exclusive end cho ngày nghiệp vụ. |
| ERP-EF-04 | BLOCKING | Empty intent cần positive collision, ngưỡng dưới/qua và delivery-time boundary để loại false-empty. |
| ERP-AG-01 | OPTIONAL | Duplicate-join negative case tăng độ phủ; candidate đếm trực tiếp CUSTOMERS nên không cần join. |
| ERP-AG-02 | IMPORTANT | Boundary date và xác nhận line net/discount/NULL. |
| ERP-AG-03 | IMPORTANT | Phân biệt AVG ở order grain với line grain và empty cohort. |
| ERP-AG-04 | IMPORTANT | Nhiều payment/order, posted zero-net và fan-out. |
| ERP-GB-02 | IMPORTANT | Multi-line order phát hiện tổng tiền bị nhân bởi joins. |
| ERP-GB-04 | IMPORTANT | UTC event qua local month boundary và month không có dữ liệu. |
| ERP-RK-01 | IMPORTANT | Tie tại vị trí cutoff top-5 theo tie policy đã ghi. |
| ERP-RK-02 | BLOCKING | Đơn vị sản phẩm khác nhau làm ranking hiện tại so sánh quantity không cùng unit; tie fixture chưa đủ. |
| ERP-RK-03 | IMPORTANT | Đồng hạng, pending decoy, customer không có posted cash. |
| ERP-JN-02 | OPTIONAL | Negative test với duplicate line không hợp lệ theo PK; snapshot đã có confirmed và non-confirmed để review status filter. |
| ERP-JN-03 | IMPORTANT | Nhiều payment/order để bắt revenue fan-out. |
| ERP-JN-04 | IMPORTANT | Nhiều line cùng SKU, received quantity và upper bound. |
| ERP-TM-01 | IMPORTANT | Kiểm tra chính xác `[start,end)` của order_date. |
| ERP-TM-02 | BLOCKING | Biên local midnight/năm và NULL event xác định date bucket/filter. |
| ERP-NA-01 | IMPORTANT | Draft/cancelled-only không được xem như confirmed order. |
| ERP-NA-02 | IMPORTANT | Net-zero posted cash khác absence/pending-only. |
| ERP-CD-01 | BLOCKING | Cần đối chứng order_date vs delivery date để xác định measure/cohort revenue. |
| ERP-CD-02 | IMPORTANT | Capture/refund cùng method, pending decoy; xác nhận không tự tạo bucket method vắng mặt. |
| WMS-EF-03 | BLOCKING | Balance-as-of cần cutoff, đối dấu và posted movements; sai thứ tự/batch có thể đổi tồn. |
| WMS-EF-04 | BLOCKING | Empty intent bắt buộc positive collision, zero balance và inactive location controls. |
| WMS-AG-01 | IMPORTANT | Multi-line receipt bắt lỗi đếm dòng thay vì đếm chứng từ. |
| WMS-AG-02 | BLOCKING | Negative transfer/adjustment cùng SKU phải phân biệt với posted shipment; unit KG đã nêu. |
| WMS-AG-03 | BLOCKING | Zero-with-history vs no-history quyết định denominator của average tồn theo location. |
| WMS-AG-04 | BLOCKING | Phân số mean, rounding và tập location zero/history quyết định output metric. |
| WMS-GB-01 | IMPORTANT | Đếm document PK thay vì join rows. |
| WMS-GB-02 | BLOCKING | Net-zero và không cộng quantity giữa base units khác nhau. |
| WMS-GB-03 | IMPORTANT | Multi-line document để bắt line-counting. |
| WMS-GB-04 | BLOCKING | Cùng timestamp cần posted_seq/atomic transfer và unit-separated rollup cho tồn theo thời gian. |
| WMS-RK-02 | IMPORTANT | Tie tại top-3 boundary theo tie policy. |
| WMS-RK-03 | BLOCKING | Tie/zero-with-history và eligibility STORAGE hiện chưa đủ rõ để xác lập cohort ranking. |
| WMS-JN-02 | IMPORTANT | Planned khác posted movement phát hiện join/measure sai. |
| WMS-JN-03 | IMPORTANT | Transfer pair trong aggregation để bắt double count và mixed-unit. |
| WMS-JN-04 | IMPORTANT | Snapshot có 12 cặp/24 legs; temporary case duplicate-looking nhưng hợp lệ kiểm tra không deduplicate nhầm; corrupted-pair case bổ sung cho validator. |
| WMS-TM-01 | BLOCKING | Business date và posted timestamp tách rời; cần case lệch qua boundary để xác định time filter. |
| WMS-TM-02 | BLOCKING | Exact cutoff, same-timestamp sequence và transfer batch có thể đổi trạng thái balance. |
| WMS-NA-01 | BLOCKING | Picking scope, active-location filter và collision quyết định điều kiện anti-join. |
| WMS-NA-02 | BLOCKING | Phân biệt balance zero có history với cặp product-location chưa từng có movement. |
| WMS-CD-01 | BLOCKING | Cùng SKU shipment/non-shipment và pending/cancelled decoys quyết định conditional cohort. |
| WMS-CD-02 | BLOCKING | Transfer hai legs hiện bị cộng `ABS()` thành 2×; cần Owner chốt measure trước khi có gold. |

Tổng phân loại: **18 BLOCKING, 21 IMPORTANT, 2 OPTIONAL**. Không có đề xuất nào đã được triển khai vào snapshot. Priority này là review triage cho Bước Development, không thay đổi benchmark quota hay metric protocol.

## 5. Near-duplicate audit — initial run, 19 pairs (superseded)

Các score là token Jaccard triage, không phải phán định semantic equivalence. Có **3 cặp trong cùng group** và **16 cặp giữa groups**. Tất cả cặp giữa groups hiện thuộc Final; **không có cặp high-score cắt qua Dev/Final và không có cặp giữa hai Development groups**. Vì vậy hiện chưa thấy split leakage từ danh sách này. Các cặp generic wrapper vẫn cho thấy generator tạo wording quá khuôn mẫu, nên chưa được xem là paraphrases đạt chất lượng.

| Phạm vi | Cặp | Similarity | Nhận định |
|---|---|---:|---|
| Cùng group | ERP-EF-04 Q00–Q01 | 0.8000 | Cùng intent; wording gần, cần viết/review khác biệt diễn đạt. |
| Cùng group | WMS-AG-03 Q00–Q01 | 0.8148 | Cùng intent; kiểm tra đây có chỉ là wrapper thêm vào hay không. |
| Cùng group | WMS-AG-03 Q00–Q04 | 0.7857 | Cùng intent; yêu cầu semantic review riêng. |
| Khác groups, Final | ERP-GB-01-Q01 × WMS-GB-01-Q01 | 0.7500 | Cùng wrapper đếm theo trạng thái; entity khác. |
| Khác groups, Final | ERP-GB-01-Q02 × WMS-GB-01-Q02 | 0.7857 | Cùng wrapper đếm theo trạng thái; entity khác. |
| Khác groups, Final | ERP-GB-01-Q03 × WMS-GB-01-Q03 | 0.8333 | Cùng wrapper đếm theo trạng thái; entity khác. |
| Khác groups, Final | ERP-GB-01-Q04 × WMS-GB-01-Q04 | 0.7857 | Cùng wrapper đếm theo trạng thái; entity khác. |
| Khác groups, Final | ERP-GB-01-Q05 × WMS-GB-01-Q05 | 0.7857 | Cùng wrapper đếm theo trạng thái; entity khác. |
| Khác groups, Final | ERP-GB-01-Q06 × WMS-GB-01-Q06 | 0.8125 | Cùng wrapper đếm theo trạng thái; entity khác. |
| Khác groups, Final | ERP-GB-01-Q07 × WMS-GB-01-Q07 | 0.8421 | Cùng wrapper đếm theo trạng thái; entity khác. |
| Khác groups, Final | ERP-GB-01-Q08 × WMS-GB-01-Q08 | 0.8000 | Cùng wrapper đếm theo trạng thái; entity khác. |
| Khác groups, Final | ERP-GB-01-Q09 × WMS-GB-01-Q09 | 0.8571 | Cùng wrapper đếm theo trạng thái; entity khác. |
| Khác groups, Final | ERP-GB-01-Q10 × WMS-GB-01-Q10 | 0.8696 | Cùng wrapper đếm theo trạng thái; entity khác. |
| Khác groups, Final | ERP-GB-02-Q10 × ERP-NA-01-Q10 | 0.7333 | Customer/group vs absence intent; wrapper gây giống câu. |
| Khác groups, Final | ERP-JN-01-Q09 × ERP-NA-01-Q09 | 0.7200 | Customer order-count vs absence; semantic khác, wording cần chỉnh. |
| Khác groups, Final | ERP-JN-01-Q10 × ERP-JN-04-Q10 | 0.7241 | Customer-order vs return aggregation; không cắt split. |
| Khác groups, Final | ERP-JN-01-Q10 × ERP-NA-01-Q10 | 0.7407 | Hai intent customer nhưng cohort khác nhau; review leakage/wording. |
| Khác groups, Final | WMS-AG-01-Q09 × WMS-GB-01-Q09 | 0.7391 | Receipt count vs document status count. |
| Khác groups, Final | WMS-AG-01-Q10 × WMS-GB-01-Q10 | 0.7600 | Hai grouped document counts; kiểm tra template leakage. |

**Quyết định review:** Dev không có near-duplicate cặp bị flag bởi ngưỡng hiện tại. Final chỉ được ghi nhận để giữ nguyên audit; không chỉnh câu, prompt hay cấu hình model dựa trên nội dung/đáp án Final. Mọi 500 variants đều còn `NEEDS_HUMAN_REVIEW`.

## 6. Owner review tối thiểu trước real Development run

1. Duyệt từng trong 10 Intent Card: business intent, grain, filters/status, projection, unit, NULL/zero/absence, time boundary và tie policy.
2. Kiểm tra execution evidence cho 6 nhóm trước đây NEEDS_HUMAN_REVIEW, đặc biệt fixture partitions/ties của **ERP-RK-02** và source-only transfer/non-posted-zero của **WMS-CD-02**.
3. Duyệt 10 canonical SQL candidates và expected-output hashes mới. ERP-RK-02 và WMS-CD-02 đã được chỉnh theo quyết định Owner ngày 2026-11-09; không có nội dung nào tự đánh dấu APPROVED.
4. Duyệt Q0 và từng Q1–Q10 của mỗi Dev group: accept/revise/reject theo semantic slots; không dùng generator status làm approval.
5. Ghi tên người, ngày, rationale và status thật vào Validation Records; đánh dấu registry freeze/hash sau khi nội dung đã khóa.
6. Trước official Development run, ghi quyết định cho D8 (timeout; đề xuất khởi điểm 30s/query), D9 (3 replicates nếu đủ nguồn lực, nếu không single-shot) và D13 (initial call + tối đa 2 infrastructure retries; không retry model errors), hiện còn PROPOSED. Chốt provider/model ID, prompt/schema/business-rule text, temperature/token và xác nhận chi phí. Lưu predictions trước khi tính score; không gọi provider trong bước chuẩn bị này. D12/D14 có thể chốt trước Final/public report, không cần chặn riêng Dev pilot.

Chỉ sau các gate trên mới có thể chạy Dev LLM evaluation thật. Chạy riêng 11 câu cho từng approved Development group, lưu prompt/model/config hashes và result artifacts. Không dùng mock artifact làm kết quả model. Không mở Final để điều chỉnh bất cứ cấu hình nào.

## 7. Thay đổi kỹ thuật và verification

Trong lần review này chưa sửa snapshot hoặc candidate SQL. Đã phát hiện hai điểm cần kỹ thuật hóa trước khi tin vào validation:

- `WMS-CD-02` Python oracle hiện cộng `abs()` trên cả hai transfer legs như SQL candidate; hiện nó không độc lập với giả định measure của SQL. Phải cập nhật sau khi Owner chọn semantics.
- Near-duplicate heuristic chỉ đo Jaccard token; không đánh giá semantic slots. Tài liệu phân loại rõ đây là triage, không phải leakage verdict.

Kết quả bộ kiểm thử sau implementation: `74 passed`; static prepare: `50 PASS / 0 FAIL`; 10 Dev SQL/oracle output hashes khớp ở lần chạy hiện tại. Smoke artifact 550/550 dùng mock SQL trên fixture tạm, không phải thực nghiệm. Không gọi LLM API và hai snapshot vẫn khớp manifest.

Lệnh tái lập kiểm tra kỹ thuật:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=benchmark_data/pytest_tmp -p no:cacheprovider
.\.venv\Scripts\python.exe scripts\validate_bird_vn_drafts.py
.\.venv\Scripts\python.exe scripts\prepare_bird_vn_expectations.py
.\.venv\Scripts\python.exe scripts\validate_bird_vn_dev_fixtures.py
.\.venv\Scripts\python.exe scripts\run_bird_vn_ground_truth_validation.py
.\.venv\Scripts\python.exe scripts\benchmark_offline_smoke.py
git diff --check
```
