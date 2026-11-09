# BIRD-VN-Robust-50 — Decision Review

| Thuộc tính | Giá trị |
|---|---|
| Đặc tả | BENCHMARK_SPEC.md v0.3.0 — Draft |
| Mẫu annotation | ANNOTATION_REVIEW_TEMPLATE.md v0.3.0 — Draft |
| Review | 0.3.0 — ghi nhận phê duyệt một phần ngày 2026-11-09 |
| Ngày | 2026-11-09 |
| Trạng thái quyết định | D1–D7, D10, D11 APPROVED ngày 2026-11-09; D8, D9, D12–D14 PROPOSED |

## 1. Quy mô và tính nhất quán cần duyệt

- 50 intents = 50 Semantic Groups = 50 canonical Ground-truth SQL.
- Mỗi group có Q0 original + 10 accepted variants = 11 Questions dùng chung một canonical SQL.
- Tổng: 50 Q0 + 500 variants = **550 Questions**; không phải 550 intents hoặc SQL.
- Hai SQLite DB: 25 ERP Sales groups và 25 WMS Inventory groups.
- Split đã duyệt: Development 10 groups/110 Questions (5 ERP + 5 WMS); Final 40 groups/440 Questions (20 ERP + 20 WMS).
- Mỗi group có 3 Lexical, 3 Syntactic, 2 Reordering, 2 Mixed variants.
- EX, RSS, CA, Robust EX (All) và Pairwise Robust Accuracy được báo riêng; mẫu số và infra missingness phải kèm mỗi metric.

### Semantic Variation Taxonomy đề xuất

| Loại | Mỗi group | 50 groups | Development (10) | Final (40) |
|---|---:|---:|---:|---:|
| Lexical | 3 | 150 | 30 | 120 |
| Syntactic | 3 | 150 | 30 | 120 |
| Reordering | 2 | 100 | 20 | 80 |
| Mixed | 2 | 100 | 20 | 80 |
| **Tổng variants** | **10** | **500** | **100** | **400** |

Mixed variants cần secondary tags để ghi các phép biến đổi cấu thành. Ba taxonomy loại hình có thể chồng lấn; gán một primary label theo thao tác chủ đạo và không diễn giải phân tầng này như các treatment hoàn toàn độc lập. Không chấp nhận thay token máy móc nếu không tạo cách diễn đạt tự nhiên có ý nghĩa.

## 2. Metric review và trường hợp biên

Với G=50, Q0 là original, Qi là variant, i=1..10. y[g,i]=1 nếu prediction chạy và result set bằng canonical; SQL error, timeout hoặc no SQL là y=0. Unrecoverable infrastructure failure là unknown sau retry, không phải model failure.

| Metric | Công thức / denominator khi không thiếu infra | Ghi chú |
|---|---|---|
| EX Original | 100 × correct Q0 / K_o (50 nếu đủ) | 50 questions |
| EX Variants | 100 × correct variants / K_v (500 nếu đủ) | 500 questions |
| EX Overall | 100 × correct questions / K_a (550 nếu đủ) | 550 questions |
| RSS | 100 × stable eligible Q0–Qi pairs / M_RSS (≤500) | Chỉ khi cả hai SQL chạy và result sets bằng nhau; same wrong result can yield 1 |
| CA | 100 × pairs có cùng y / M_CA (≤500) | Cả hai sai cũng được tính agreement |
| Robust EX (All) | 100 × groups có đủ 11 outcomes và cả 11 đúng / K_G (≤50) | Model failure làm group fail |
| Pairwise Robust Accuracy | 100 × pairs có Q0 và Qi đều đúng / M_PRA (≤500) | 500 Q0–Qi pairs; shared Q0 làm cặp phụ thuộc nhau |

Unrecoverable infrastructure questions/pairs/groups bị loại khỏi denominator liên quan sau retry cap đã định trước; luôn báo mẫu số thực tế và số missing. Nếu denominator bằng 0, metric là N/A. Đề xuất retry policy: initial + tối đa 2 retries cùng request/config, cần D13 approval.

Repeated runs: so Q0 với Qi trong cùng group và cùng replicate; tính metric mỗi replicate, sau đó báo mean/range/SD và raw counts. Không gộp outputs giữa replicate, không chọn replicate có điểm cao nhất. Bootstrap/CI cluster theo 50 groups; không coi 550 questions hoặc 500 pairs là độc lập.

## 3. Kiểm tra quy trình annotation một người

Đặc tả v0.3.0 dùng single-human validation có AI hỗ trợ:

1. Khóa Intent Card và source/business assumptions trước SQL.
2. Tạo fixtures và derive expected outputs độc lập với canonical SQL trước khi SQL chạy.
3. Người phụ trách viết hoặc nhận SQL draft có Codex hỗ trợ; tự kiểm tra logic SQL thủ công.
4. Kiểm tra boundary/counterexamples; đối chiếu alternative SQL hoặc Python oracle khi khả thi.
5. Lưu execution artifacts/hashes, tool/model provenance, AI suggestions và quyết định human cho đủ 10 variants.
6. Trạng thái mỗi variant là ACCEPT/REVISE/REJECT; chỉ 10 variants ACCEPT tạo thành group release.

Đây không phải independent human annotation, không đo inter-annotator agreement và không được mô tả là tương đương double-blind annotation. AI/Codex và oracle là kiểm tra kỹ thuật, không phải annotator/reviewer độc lập. Common-method bias và giới hạn kiểm chứng bằng một người phải được công bố.

## 4. Decision Record D1–D14

Benchmark Owner đã phê duyệt D1–D7, D10 và D11 ngày 2026-11-09 theo các giá trị khuyến nghị bên dưới. D8, D9, D12, D13 và D14 vẫn PROPOSED. Cột approver ghi vai trò do người dùng xác nhận; rationale ghi căn cứ cụ thể. D4 chỉ phê duyệt định hướng hai SQLite DB và yêu cầu tài liệu nghiệp vụ được chốt trước annotation; Business Rules và Glossary chi tiết chưa được phê duyệt, cần kiểm tra trong Bước 2A.

| ID | Giá trị khuyến nghị | Lý do | Quyết định | Người quyết định | Ngày | Rationale thực tế / deviation |
|---|---|---|---|---|---|---|
| D1 | 10 Dev groups/110 Questions; 40 Final groups/440 Questions; group/near-duplicate cluster split | Tránh rò rỉ wording cùng intent và dành 40 nhóm cho đánh giá Final; split theo group/near-duplicate cluster. | ☒ APPROVE ☐ REVISE ☐ REJECT | Benchmark Owner | 2026-11-09 | Chấp nhận split 10/40; các câu Q0–Q10 cùng group phải ở cùng split, và near-duplicates giữa group phải được kiểm tra trước khi khóa split. |
| D2 | 25 ERP groups + 25 WMS groups; 5/5 Dev và 20/20 Final | Cân bằng domain trong toàn tập và từng split để tránh một domain chi phối kết quả. | ☒ APPROVE ☐ REVISE ☐ REJECT | Benchmark Owner | 2026-11-09 | Chấp nhận phân bổ 25/25; giữ cân bằng 5/5 ở Development và 20/20 ở Final. |
| D3 | Synthetic deterministic, không PII thật; public source chỉ khi license/provenance rõ | Hỗ trợ tái lập và giảm rủi ro riêng tư/nguồn dữ liệu không rõ quyền. | ☒ APPROVE ☐ REVISE ☐ REJECT | Benchmark Owner | 2026-11-09 | Chấp nhận ưu tiên dữ liệu tổng hợp xác định; mọi nguồn công khai bổ sung phải có license và provenance được ghi nhận. |
| D4 | Định hướng: hai SQLite DB; glossary/data dictionary/business rules phải được kiểm tra và chốt trước annotation | Schema cần phản ánh định nghĩa nghiệp vụ thống nhất; chi tiết nghiệp vụ cần xác minh với nguồn phù hợp. | ☒ APPROVE ☐ REVISE ☐ REJECT | Benchmark Owner | 2026-11-09 | Chỉ phê duyệt định hướng thiết kế hai DB và nguyên tắc phải chốt tài liệu nghiệp vụ trước annotation. Không phê duyệt nội dung Business Rules/Glossary cụ thể; các nội dung này phải được kiểm tra trong Bước 2A. |
| D5 | Schema context/Evidence giống nhau cho 11 questions trong cùng group | Cô lập tác động wording; các câu trong group phải nhận cùng thông tin nền. | ☒ APPROVE ☐ REVISE ☐ REJECT | Benchmark Owner | 2026-11-09 | Chấp nhận giữ schema, glossary/context và Evidence giống nhau giữa Q0–Q10 trong cùng group; chỉ wording câu hỏi được thay đổi. |
| D6 | Cho phép empty-result intents có chủ đích; quota đề xuất 2–3/50 | Bao gồm kết quả rỗng có chủ đích nhưng hạn chế empty/empty false match bằng fixtures đối kháng. | ☒ APPROVE ☐ REVISE ☐ REJECT | Benchmark Owner | 2026-11-09 | Chấp nhận quota đề xuất 2–3 intent empty-result; mỗi trường hợp cần fixture chứng minh intent và kiểm tra collision với truy vấn sai. |
| D7 | BIRD-compatible set EX và set RSS; EX_bag diagnostic; primary metric không chấm row order | Bảo toàn comparator set-based tương thích; công bố giới hạn với duplicate/order và xử lý ranking/ties bằng quy tắc đã chốt. | ☒ APPROVE ☐ REVISE ☐ REJECT | Benchmark Owner | 2026-11-09 | Chấp nhận set-based EX/RSS làm comparator chính và EX_bag làm diagnostic; thứ tự hàng không tính vào EX chính. Ranking/ties phải được làm rõ trong protocol và test cases. |
| D8 | Timeout khởi điểm 30 giây/query; đo trên DB rồi freeze cùng resource limits | Source hiện dùng 30s, workload mới chưa đo. | ☐ APPROVE ☐ REVISE ☐ REJECT | | | |
| D9 | 3 replicates nếu đủ nguồn lực; nếu không single-shot; paired theo replicate và báo từng lần | Kiểm soát sampling variability, không chọn run tốt nhất. | ☐ APPROVE ☐ REVISE ☐ REJECT | | | |
| D10 | Một Benchmark Owner single-human validation; AI/Codex hỗ trợ critique/oracle; công bố không có independent human annotation | Phù hợp nguồn lực đồ án; nêu rõ common-method bias, không đo inter-annotator agreement. | ☒ APPROVE ☐ REVISE ☐ REJECT | Benchmark Owner | 2026-11-09 | Chấp nhận một người thực hiện và chịu trách nhiệm human review/final approval; Codex/LLM chỉ hỗ trợ kỹ thuật, không được tính là annotator độc lập hoặc double-blind review. |
| D11 | Competency quota §6 (8/8/8/6/8/4/4/4), complexity 16 Simple/24 Moderate/10 Challenging; mỗi group 3 Lexical/3 Syntactic/2 Reordering/2 Mixed | Khóa coverage và taxonomy trước authoring để kiểm soát phạm vi benchmark. | ☒ APPROVE ☐ REVISE ☐ REJECT | Benchmark Owner | 2026-11-09 | Chấp nhận quota competency, complexity và 10 biến thể/group như đặc tả; giữ tổng 50 intents và không tạo câu hỏi ngoài quota nếu chưa version/review. |
| D12 | Giữ 0.x pilot; Final giữ kín nếu khả thi, nếu không công khai exposure | Tránh gọi nhầm tập đã tune là blind. | ☐ APPROVE ☐ REVISE ☐ REJECT | | | |
| D13 | Inference exploratory, cluster 50 groups; initial + tối đa 2 infra retries; missingness/denominators công bố | 550 câu/pairs lồng trong group; retry policy phải tái lập. | ☐ APPROVE ☐ REVISE ☐ REJECT | | | |
| D14 | Gọi là pilot, không tuyên bố “first”/novelty tuyệt đối trước literature review | Không vượt quá bằng chứng hiện tại. | ☐ APPROVE ☐ REVISE ☐ REJECT | | | |

## 5. Vai trò — mô hình một người

| Vai trò | Trách nhiệm | Người được giao / xác nhận |
|---|---|---|
| Benchmark Owner / người thực hiện | Có thể đảm nhiệm annotation, review, final approval và maintenance; ghi self-validation, ngày và evidence | Vai trò được xác nhận trong yêu cầu phê duyệt ngày 2026-11-09 |
| Domain Owner (nếu có) | Cung cấp/xác nhận business rules và ambiguity; nếu vắng mặt ghi nguồn thay thế và limitation | Chờ xác nhận |
| Codex/LLM support | Gợi ý, critique, code/oracle; lưu provenance, không có quyền approve hoặc tính là annotator | Công cụ; không phải người |
| Maintainer | Quản lý version, hashes, 50 Validation Records, split, decision log và freeze | Có thể kiêm Benchmark Owner; chờ xác nhận |

## 6. Cổng bắt đầu Bước 2A

Các quyết định bắt buộc để mở cổng thiết kế database đã được phê duyệt:

- **D1–D2 — APPROVED:** split 10/40 và domain balance 25/25.
- **D3–D4 — APPROVED có phạm vi:** nguyên tắc data source/privacy và định hướng hai SQLite DB; Business Rules/Glossary chi tiết vẫn cần kiểm tra trong Bước 2A.
- **D5–D7 — APPROVED:** context/Evidence, quota empty-result, comparator set-based và các caveat ranking/order.
- **D10–D11 — APPROVED:** single-human validation có công bố limitation; quota biến thể/competency/complexity.

Benchmark Owner đã xác nhận quyền quyết định trong yêu cầu này. Có thể bắt đầu Bước 2A để rà soát Business Rules/Glossary và phát triển thiết kế schema theo định hướng đã duyệt. Bước 2A phải xác minh Domain Owner hoặc nguồn nghiệp vụ thay thế cho ERP/WMS, date/time/currency/NULL rules, fixtures và audit/version policy; không được xem những chi tiết này là đã phê duyệt bởi D4. D8/D9/D13 phải được quyết định trước evaluation; D12 trước khi phát hành/chia sẻ Final; D14 trước báo cáo novelty.
