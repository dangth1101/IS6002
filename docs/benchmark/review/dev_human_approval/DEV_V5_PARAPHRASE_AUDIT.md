# Audit Development wording — v5

Ngày: **2026-11-10**. Trạng thái: **Draft / NEEDS_HUMAN_REVIEW**. Người hỗ trợ: Codex; đây không phải independent human annotation. Revision: `dev-v5-paraphrase-audit`.

## Nguồn và kết quả

Đã xác minh v4 đúng SHA-256 `460acf73b291071a9a05fcd3a43fbfc986876cf4db9b5342bf074e5ea34fbd3f` và ba review CSV đồng bộ trước khi sửa. Ví dụ thêm lời dẫn rồi chép Q00 trong yêu cầu không còn xuất hiện ở nguồn v4 này: wrapper detector ghi **0 trước / 0 sau**. Các lỗi thực tế gồm câu ghép thiếu tự nhiên, taxonomy yếu, thuật ngữ khó đọc, thiếu/làm mơ hồ projection, cohort, trạng thái và cutoff.

| Group | Giữ nguyên | Sửa draft | Giữ lại chờ Owner | Nhãn L/S/R/M |
|---|---:|---:|---:|---|
| ERP-EF-01 | 4 | 6 | 1 | 3/3/2/2 |
| ERP-GB-03 | 6 | 5 | 0 | 3/3/2/2 |
| ERP-RK-02 | 2 | 9 | 0 | 3/3/2/2 |
| ERP-JN-02 | 3 | 8 | 0 | 3/3/2/2 |
| ERP-TM-02 | 3 | 8 | 0 | 3/3/2/2 |
| WMS-EF-01 | 2 | 8 | 1 | 3/3/2/2 |
| WMS-EF-02 | 3 | 8 | 0 | 3/3/2/2 |
| WMS-AG-02 | 1 | 10 | 0 | 3/3/2/2 |
| WMS-JN-04 | 1 | 10 | 0 | 3/3/2/2 |
| WMS-CD-02 | 1 | 10 | 0 | 3/3/2/2 |
| **Tổng** | **26** | **82** | **2** | **30/30/20/20** |

Giữ nguyên gồm **10 Q00 + 16 variants**. Không có đề xuất đổi Q00 hoặc đổi nghiệp vụ/SQL trong lần này. 82 câu đã sửa vẫn là draft. **98/100 variants có mô tả thao tác biến đổi đề xuất; 2/100 chưa giải quyết taxonomy**. Đây là đánh giá của agent, không phải tỷ lệ human-validated. Cả 110 câu cần con người kiểm tra độ tự nhiên và semantic equivalence.

- [Audit 110 câu](DEV_V5_PARAPHRASE_AUDIT.csv): wording v4, đề xuất, wording hiện hành, loại lỗi, rủi ro, lý do, biến đổi, slots và dấu hiệu trước/sau.
- [Changelog 82 câu](DEV_V4_TO_V5_CHANGELOG.csv): chỉ những câu thực sự được sửa.
- Review: [ERP 55 câu](ERP_DEVELOPMENT_QUESTIONS_55.csv), [WMS 55 câu](WMS_DEVELOPMENT_QUESTIONS_55.csv). Cột quyết định của người duyệt để nguyên; đề xuất của agent nằm riêng.
- [Evidence máy đọc được](../../../../benchmark_data/authoring/dev_wording_v5_audit.json), [manifest và toàn bộ hash](../../../../benchmark_data/authoring/dev_wording_v5_manifest.json). CSV v4 giữ tại [archive/dev-v4](archive/dev-v4/).

## Semantic slots và taxonomy

Đối chiếu mỗi câu với `dataset.json` → `groups[].card_fields`, `canonical_sql` và `validation_records.json` → `semantic_slots`. Các card/rules không thay đổi. Những sửa đổi đáng chú ý:

- ERP-EF-01-Q09: “đã được chốt” → “đã được xác nhận”, giữ mã khách hàng và đủ năm cột.
- ERP-GB-03: cohort chỉ rep có đơn CONFIRMED; nhóm NULL chỉ từ các đơn CONFIRMED chưa gán, không thêm rep có 0 đơn.
- ERP-RK-02: làm rõ cutoff hạng 1–3, lượng **đặt**, partition từng base unit, đồng hạng và năm cột Option B. Không thêm `product_id`, không đổi RANK thành DENSE_RANK.
- ERP-TM-02: xác định ngày từ thời điểm giao UTC sang Asia/Ho_Chi_Minh; năm địa phương 2025 tương ứng `[2025-01-01,2026-01-01)`. Không thêm ngày không có shipment.
- WMS-AG-02-Q01: “biến động giảm tồn kho” thuộc SHIPMENT POSTED; tổng lượng xuất dương milli-KG, không gộp adjustment/transfer âm.
- WMS-JN-04: giữ document ID **và** number, line number, leg number/role, hai kho, lượng có dấu milli-unit và timestamp UTC ở grain từng leg.
- WMS-CD-02-Q09: đủ tám cột, planned/executed riêng; chỉ executed của non-POSTED bằng 0; TRANSFER tính SOURCE một lần.

Ví dụ biến đổi: ERP-JN-02-Q02 thay *order line / line net* bằng *dòng chi tiết / giá trị ròng* (Lexical); ERP-EF-01-Q04 chuyển sang câu hỏi “Những đơn hàng nào…” và yêu cầu thuộc tính (Syntactic); WMS-EF-02-Q07 đưa NULL trước filter KG và projection (Reordering); WMS-CD-02-Q09 dùng “dự kiến / đã thực hiện” đồng thời hỏi hai measure (Mixed lexical + syntactic). Secondary tags nằm trong metadata, không chèn chú thích taxonomy vào câu hỏi.

`scripts/dev_wording_slot_checks.py::slot_evidence()` chỉ tìm **dấu hiệu từ ngữ** cho projection/measure/status/unit/time/NULL đã định nghĩa theo từng group. 54 câu v4 có ít nhất một dấu hiệu không khớp bộ pattern, v5 là 0. Con số 54 **không phải 54 lỗi semantic được chứng minh**: từ đồng nghĩa và tên trường viết tắt có thể tạo false positives. Cũng không suy ra 110/110 tương đương từ kết quả 0; keyword có thể đúng nhưng scope, phủ định, thứ tự rank hoặc quan hệ vẫn sai. Test negative control xác nhận bộ lint không tự trả ACCEPT/equivalent.

## Hàng đợi human review

| Ưu tiên | Question / phạm vi | Việc Owner cần quyết định |
|---|---|---|
| 1 | ERP-EF-01-Q08 | `TAXONOMY_LIMITATION`: filter→projection giống Q00; projection→filter đã có Q07. Giữ nguyên câu, lưu một đề xuất ngắn hơn chưa áp dụng. Owner đề xuất một đảo thông tin thực chất hoặc quyết định ngoại lệ taxonomy qua thay đổi protocol riêng; chưa tự đổi quota. |
| 1 | WMS-EF-01-Q07 | `TAXONOMY_LIMITATION`: thêm “trước/sau” chỉ mô tả thao tác; Q08 đã đảo projection→filter. Xử lý như trên, không thêm time/sort/column để tạo biến thể. |
| 2 | ERP-RK-02 Q00–Q10 | Xác nhận cách hiểu hạng cạnh tranh có thể nhảy số (RANK), cutoff ≤3, cùng unit và lượng đặt; chưa xem cách gọi “ba hạng đầu” là human-approved. |
| 2 | WMS-JN-04 Q00–Q10 | Xác nhận “vế biến động kho” diễn đạt đúng leg; 10 thuộc tính làm câu dài nhưng không được bỏ cột để rút ngắn. |
| 2 | ERP-TM-02 Q01/Q02/Q03/Q09/Q10 | Xác nhận lượt/lần/lô giao hàng có định danh `(shipment)` vẫn đếm shipment, không đổi sang đơn bán, chuyến xe hoặc kiện hàng. |
| 2 | WMS-CD-02 Q00–Q10 | Xác nhận tám cột, không diễn giải mọi cặp document×SKU thành tích Descartes; “quy tắc movement” cần glossary/schema context đã khóa. |
| 3 | Toàn bộ 110 câu | Reviewer, ACCEPT/REVISE/REJECT, nhận xét khi cần và review lại sửa đổi. Sau đó review riêng Intent/SQL/expected outputs/fixture evidence. |

Không có xung đột buộc sửa SQL/Intent được xác định trong lần audit này. Hai giới hạn taxonomy là **vấn đề mở**, không được tuyên bố dataset đã đạt chất lượng cuối cùng. Cách gọi tiếng Việt/English trộn vẫn cần Owner đánh giá; chỉ giữ tên enum/trường cần phân biệt và không sửa hàng loạt các câu đã ổn định.

## Duplicate screening

`scripts/audit_dev_wording_v5.py::similarity_audit()` dùng token-set Jaccard ≥0.78 trong group, ≥0.72 giữa groups. Kiểm tra Dev–Final chỉ để phát hiện leakage, không chạy SQL/model Final; không audit các cặp Final–Final. Cùng phương pháp: **12 cặp trước / 6 cặp sau**, đều trong cùng group; **0 exact duplicate, 0 cặp giữa Development groups, 0 cặp qua split**. Không có flag không chứng minh hoàn toàn không leakage.

| Cặp hiện hành | Jaccard | Đánh giá sơ bộ cần human review |
|---|---:|---|
| WMS-AG-02-Q04 / Q05 | 0.8108 | Hỏi số lượng của cohort đã nêu / hỏi chọn cohort và số lượng; cùng projection. Kiểm tra mức khác biệt có đủ hay chỉ tách câu. |
| WMS-JN-04-Q01 / Q10 | 0.8571 | Lexical entity-first / Mixed projection-first; nhiều từ trùng do đủ 10 cột. |
| WMS-JN-04-Q04 / Q06 | 0.8286 | Hỏi quan hệ chứng từ rồi thuộc tính leg / toàn bộ projection làm chủ thể nghi vấn. |
| WMS-JN-04-Q05 / Q06 | 0.8056 | Yêu cầu một bảng / câu hỏi thuộc tính; cần đánh giá độ tự nhiên. |
| WMS-JN-04-Q05 / Q08 | 0.8611 | Grain/filter trước projection / projection trước grain/filter. |
| WMS-JN-04-Q06 / Q08 | 0.8286 | Nghi vấn projection / mô tả kết quả rồi grain/filter. |

Các cặp cùng group không phải leakage giữa intents; vẫn có thể là variants yếu. Không xóa hoặc gắn ACCEPT chỉ dựa trên Jaccard.

## Verification và provenance

- Registry loader: 50 groups/550 câu, Development 10/110 (5 ERP + 5 WMS), ID duy nhất, Q00–Q10, quota/split: **PASS**.
- Bất biến: toàn bộ groups/cards/SQL, 50 Q00, 440 Final questions, Final Validation Records, oracle, expected outputs, fixture evidence, snapshots, schema/manifest, business rules, metric code và D8/D9/D13: **không đổi so với đầu phiên audit**. Các phê duyệt protocol có sẵn trong working tree được giữ nguyên.
- Validation Records chỉ đồng bộ text Dev và revision; `ground_truth_validation.json` chỉ cập nhật hash record/wording lineage. Evidence thực thi và status 10/10 giữ nguyên. Không chạy lại SQL trong lần sửa wording.
- Hai CSV UTF-8 BOM: `Workbook.fromCSV` đọc đúng 55 dòng dữ liệu mỗi file, text Unicode khớp registry và reviewer/decision còn trống. Bảng Intent/SQL 10 dòng giữ nguyên, Expected/Actual rows/hashes đã có.
- `python scripts/audit_dev_wording_v5.py`: **PASS**; 80 repository tests: **PASS, 0 FAIL**. Các test mới bảo vệ lineage, Q00/SQL, CSV, HOLD chưa áp dụng, gate release và giới hạn của keyword checks.
- Không gọi LLM API, không official evaluation, không model tuning; **Human approval PENDING**.

Registry SHA-256: `76b591117daf6d6f95fca629c7f23d894b2e8f307cb1ffa6266aaf5876755187`. Hash files mới/thay đổi và files được bảo vệ nằm trong manifest. Expected-output artifacts giữ hash registry v4 **như provenance lịch sử**; manifest v5 chứng minh contract/snapshot/SQL không đổi, không thay hash trong evidence cũ để giả lập lần tạo mới.

Lệnh tái kiểm tra chỉ đọc và tests nằm trong [README](README.md#reproduce-technical-checks-offline-no-provider-calls). Bước tiếp theo là xử lý hai giới hạn taxonomy, human review các câu và Intent/SQL, rồi freeze/release theo các gates đã ghi; audit này không cấp phép evaluation.
