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

Benchmark Owner đã phê duyệt D1–D7, D10 và D11 ngày 2026-11-09. Các simulation rules chi tiết R-01–R-11 được chấp nhận cho logic design và ghi trong STEP_2A_REVIEW.md ngày 2026-11-09; không được diễn giải là chuẩn ERP/WMS phổ quát. D8, D9, D12, D13 và D14 vẫn PROPOSED. D4 riêng vẫn chỉ phê duyệt định hướng hai SQLite DB.

| ID | Giá trị khuyến nghị | Lý do | Quyết định | Người quyết định | Ngày | Rationale thực tế / deviation |
|---|---|---|---|---|---|---|
| D1 | 10 Dev groups/110 Questions; 40 Final groups/440 Questions; group/near-duplicate cluster split | Tránh rò rỉ wording cùng intent và dành 40 nhóm cho đánh giá Final; split theo group/near-duplicate cluster. | ☒ APPROVE ☐ REVISE ☐ REJECT | Benchmark Owner | 2026-11-09 | Chấp nhận split 10/40; các câu Q0–Q10 cùng group phải ở cùng split, và near-duplicates giữa group phải được kiểm tra trước khi khóa split. |
| D2 | 25 ERP groups + 25 WMS groups; 5/5 Dev và 20/20 Final | Cân bằng domain trong toàn tập và từng split để tránh một domain chi phối kết quả. | ☒ APPROVE ☐ REVISE ☐ REJECT | Benchmark Owner | 2026-11-09 | Chấp nhận phân bổ 25/25; giữ cân bằng 5/5 ở Development và 20/20 ở Final. |
| D3 | Synthetic deterministic, không PII thật; public source chỉ khi license/provenance rõ | Hỗ trợ tái lập và giảm rủi ro riêng tư/nguồn dữ liệu không rõ quyền. | ☒ APPROVE ☐ REVISE ☐ REJECT | Benchmark Owner | 2026-11-09 | Chấp nhận ưu tiên dữ liệu tổng hợp xác định; mọi nguồn công khai bổ sung phải có license và provenance được ghi nhận. |
| D4 | Định hướng hai SQLite DB; tài liệu nghiệp vụ được xác minh trước annotation | Schema phải có nghĩa nghiệp vụ rõ và tái lập. | ☒ APPROVE ☐ REVISE ☐ REJECT | Benchmark Owner | 2026-11-09 | D4 phê duyệt hướng thiết kế. Business Rules/Glossary synthetic được Benchmark Owner chấp nhận cho logic design theo R-01–R-11; không phải chuẩn ngành. |
| D5 | Schema context/Evidence giống nhau cho 11 questions trong cùng group | Cô lập tác động wording; các câu trong group phải nhận cùng thông tin nền. | ☒ APPROVE ☐ REVISE ☐ REJECT | Benchmark Owner | 2026-11-09 | Chấp nhận giữ schema, glossary/context và Evidence giống nhau giữa Q0–Q10 trong cùng group; chỉ wording câu hỏi được thay đổi. |
| D6 | Chính xác 2 empty-result intents: 1 ERP + 1 WMS | Bao gồm empty có chủ đích ở cả hai DB; quota nhỏ giúp kiểm soát false-empty match bằng fixtures. | ☒ APPROVE ☐ REVISE ☐ REJECT | Benchmark Owner | 2026-11-09 | Benchmark Owner chốt quota từ khoảng 2–3 thành đúng 2 intent, một cho mỗi DB; fixture phải kiểm tra false-empty collision. |
| D7 | BIRD-compatible set EX/RSS; EX_bag diagnostic; primary EX không chấm row order; mỗi ranking Intent Card chốt tie policy | Bảo toàn comparator tương thích; ranking semantics phải nêu deterministic tie-break hoặc include ties. | ☒ APPROVE ☐ REVISE ☐ REJECT | Benchmark Owner | 2026-11-09 | Set comparator so result membership, không xác minh output order; mỗi intent ranking ghi quy tắc đồng hạng rõ ràng. |
| D8 | Timeout khởi điểm 30 giây/query; đo trên DB rồi freeze cùng resource limits | Source hiện dùng 30s, workload mới chưa đo. | ☐ APPROVE ☐ REVISE ☐ REJECT | | | |
| D9 | 3 replicates nếu đủ nguồn lực; nếu không single-shot; paired theo replicate và báo từng lần | Kiểm soát sampling variability, không chọn run tốt nhất. | ☐ APPROVE ☐ REVISE ☐ REJECT | | | |
| D10 | Một Benchmark Owner single-human validation; AI/Codex hỗ trợ critique/oracle; công bố không có independent human annotation | Phù hợp nguồn lực đồ án; nêu rõ common-method bias, không đo inter-annotator agreement. | ☒ APPROVE ☐ REVISE ☐ REJECT | Benchmark Owner | 2026-11-09 | Chấp nhận một người thực hiện và chịu trách nhiệm human review/final approval; Codex/LLM chỉ hỗ trợ kỹ thuật, không được tính là annotator độc lập hoặc double-blind review. |
| D11 | Competency quota §6; complexity ERP 8/12/5 và WMS 8/12/5; mỗi group 3 Lexical/3 Syntactic/2 Reordering/2 Mixed | Khóa coverage và complexity mỗi database trước authoring. | ☒ APPROVE ☐ REVISE ☐ REJECT | Benchmark Owner | 2026-11-09 | Chấp nhận tổng 16/24/10 và phân bổ 8/12/5 cho mỗi DB; mapping từng intent theo rubric complexity. |
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

## 6. Trạng thái Bước 2A và bước tiếp theo

Benchmark Owner xác nhận R-01–R-11 và nghiệm thu logic design ngày 2026-11-09; chi tiết, rationale và phạm vi được lưu trong [STEP_2A_REVIEW.md](database_design/STEP_2A_REVIEW.md). Đây là acceptance của design artifacts, không phải nghiệm thu physical database hay kết quả validator.

Physical schema/seed, invariant validator, reproducibility check và edge-case fixtures được theo dõi tại [physical database README](physical_database/README.md), cùng build manifest và validation hashes. Benchmark Owner xác nhận nghiệm thu Bước 2B riêng ngày 2026-11-09. Intent Cards, SQL candidates và Questions hiện là drafts; chưa human-approved. D8/D9/D13 vẫn phải chốt trước official evaluation; D12 trước phát hành/chia sẻ Final; D14 trước báo cáo novelty.
