# BIRD-VN-Robust-50: Đặc tả benchmark Text-to-SQL tiếng Việt

| Thuộc tính | Giá trị |
|---|---|
| Phiên bản | **0.3.0** |
| Trạng thái | **Draft – D1–D7, D10, D11 đã APPROVED; D8, D9, D12–D14 còn PROPOSED** |
| Ngày | 2026-11-09 |
| DBMS | SQLite |
| Quy mô đề xuất | 550 Questions; 50 Semantic Groups/Intent; 50 canonical SQL |
| Split đề xuất | Development: 10 groups/110 Questions; Final: 40 groups/440 Questions |
| Phạm vi tài liệu | Bước 1; chưa tạo câu hỏi, database, seed data hay SQL benchmark |

Đây vẫn là đặc tả Draft, chưa phải benchmark đã được triển khai hoặc phát hành. Benchmark Owner đã phê duyệt D1–D7, D10 và D11 ngày 2026-11-09; D8, D9, D12–D14 còn PROPOSED. Các ví dụ nghiệp vụ chỉ minh họa cách làm, không phải item của benchmark.

**Ghi chú phiên bản 0.3.0:** quy mô đề xuất tăng lên 50 Semantic Groups, mỗi group gồm 1 original + 10 variants; cập nhật split, taxonomy, metrics và single-human validation. Các quyết định D1–D7, D10, D11 được ghi nhận APPROVED ngày 2026-11-09; trạng thái Draft vẫn giữ nguyên cho đến khi hoàn tất các quyết định và nghiệm thu benchmark.

## 1. Research Problem và Research Questions

Text-to-SQL thường đánh giá mỗi yêu cầu bằng ít cách diễn đạt. BIRD-VN-Robust-50 khảo sát tính chính xác và result consistency của LLM trên 50 intents tiếng Việt, mỗi intent có một original và 10 semantic variants thuộc bốn loại biến đổi.

| ID | Research Question | Phép đo |
|---|---|---|
| RQ1 | Model đạt EX bao nhiêu trên 50 original, 500 variants và toàn bộ 550 câu? | EX Original, EX Variants, EX Overall; theo DB/competency/complexity, có mẫu số. |
| RQ2 | Kết quả của 10 variants so với original trong cùng intent ổn định đến đâu? | RSS trên Original–Variant pairs; Robust EX (All); Pairwise Robust Accuracy. |
| RQ3 | Loại biến thể Lexical/Syntactic/Reordering/Mixed nào có tỷ lệ đúng hoặc ổn định khác nhau? | Phân tích mô tả theo loại variant, cluster theo Semantic Group; không xem 550 câu là quan sát độc lập. |
| RQ4 (tùy chọn) | Wording effect tách biệt ra sao với sampling/API nondeterminism? | Repeats đã đăng ký trước; paired trong cùng group và replicate. |

## 2. Phạm vi và Dataset Card

| Thuộc tính | Đặc tả |
|---|---|
| Task | Câu hỏi tiếng Việt → một truy vấn SQLite đọc dữ liệu |
| Database | 2 database nghiệp vụ: ERP Sales và WMS Inventory |
| Phân bổ domain | ERP Sales 25 Semantic Groups; WMS Inventory 25 Semantic Groups |
| Intent | 50 yêu cầu truy vấn nghiệp vụ độc lập |
| Semantic Group | 50; mỗi group có 1 original Q0 và 10 semantic variants Q1–Q10 |
| Questions | 550 = 50 original + 500 variants |
| Ground-truth | 50 SQL canonical; một SQL dùng chung cho 11 questions trong group |
| Dữ liệu | Ưu tiên synthetic deterministic, không chứa PII thật |
| Context trong group | Cùng schema, glossary/Evidence, snapshot, prompt và model configuration cho cả 11 Questions |
| Split | 10 Development groups / 40 Final groups; không tách một group |
| DBMS ban đầu | SQLite |

Scope gồm SELECT/WITH, filter, join, aggregation, ranking/top-k, thời gian, NULL/zero/absence và điều kiện nghiệp vụ. Empty result hợp lệ khi đúng intent. Ngoài scope: multi-turn, clarification, ghi dữ liệu, tự chọn database, nhiều dialect, VES/hiệu năng và LLM-as-a-Judge làm nhãn chuẩn.

Đây là pilot nhỏ; không đại diện toàn bộ tiếng Việt, nghiệp vụ ERP/WMS, database hoặc model.

## 3. Kế thừa, tham khảo và đề xuất

| Phân loại | Nội dung | Giới hạn |
|---|---|---|
| Kế thừa trực tiếp từ BIRD | Database-grounded Text-to-SQL; đưa schema/data context và Evidence khi cần; kiểm tra tính hợp lệ SQL và alignment giữa question, knowledge, SQL; EX dựa trên kết quả thực thi. Tham chiếu BIRD 2023, phần task formulation/annotation, §3.3 và §5. | Quy mô, domain, quy trình crowd annotation và evaluator của pilot khác BIRD; không tuyên bố cùng coverage. |
| Tham khảo nghiên cứu khác | Spider-Syn nghiên cứu biến thiên từ vựng có người biên soạn; Dr.Spider khảo sát perturbation ở database/NL/SQL. [Spider-Syn](https://aclanthology.org/2021.acl-long.195/), [Dr.Spider](https://openreview.net/forum?id=Wc5bmZZU9cy). | Không claim paraphrase robustness là ý tưởng mới hoàn toàn. |
| Đề xuất IS6002 | Benchmark 50 intents × 11 wordings trên hai DB nghiệp vụ; taxonomy có quota; Result Stability Score, Correctness Agreement, Robust EX (All), Pairwise Robust Accuracy; single-human validation có AI hỗ trợ và công khai hạn chế. | Cần rà soát literature rộng hơn trước mọi tuyên bố novelty. |

BIRD paper: Li et al., *Can LLM Already Serve as A Database Interface? A BIg Bench for Large-Scale Database Grounded Text-to-SQLs*, NeurIPS 2023 ([Proceedings](https://proceedings.neurips.cc/paper_files/paper/2023/hash/83fc8fab1710363050bbd1d4b8cc0021-Abstract-Datasets_and_Benchmarks.html); PDF lưu trong repository nếu có).

### Thành phần source IS6002 có thể tái sử dụng

| Chức năng | Source và symbol | Có thể tái sử dụng / giới hạn |
|---|---|---|
| Nạp schema và câu hỏi | `bird_demo/data.py`: `load_subset_questions()`, `load_ddl()` | Cách introspect SQLite/schema; chưa có registry hai DB, snapshot hash hoặc group split. |
| Tạo prompt | `bird_demo/prompt.py`: `build_prompt()` | Prompt/schema context; phải version hóa và giữ giống nhau trong cả group. |
| Thực thi SQL | `bird_demo/runner.py`: `run()` | Read-only SQLite, trả Rows/SqlError/Timeout; timeout hiện tại 30 giây. |
| Chấm từng câu | `bird_demo/scoring.py`: `score()` | EX kiểu set trên tuple rows; cần đối chiếu chính thức và chưa hỗ trợ group metrics. |
| Tổng hợp EX | `bird_demo/report.py`: `ex()` | Denominator gồm cả No SQL; chưa có Result Stability/Robust EX. |
| Batch/cache | `scripts/batch_eval.py`: `cached_complete()` | Có thể tái sử dụng ý tưởng cache; benchmark cần metadata và khóa cache theo config/hash. |
| Tạo subset | `scripts/make_subset.py`: `pick_subset()`, `check_ground_truth()` | Tính tái lập lấy mẫu; chọn ngẫu nhiên không chứng minh annotation hợp lệ. |

Đây là phân tích source hiện tại, không hàm ý các chức năng benchmark đã được cài đặt. `score()` xác nhận GT chạy trước, lỗi/timeout/no SQL của prediction là verdict không đúng; `run()` dùng SQLite read-only và deadline; `ex()` tính tỷ lệ Match.

## 4. Cấu trúc Semantic Group

Một Semantic Group biểu diễn một intent nghiệp vụ và chứa 11 Questions (Q0 + Q1–Q10), không phải 11 intents độc lập.

| Trường | Quy tắc |
|---|---|
| group_id / db_id | ID ổn định; một trong ERP Sales hoặc WMS Inventory |
| intent_card | Entity, grain, output, measure, filters, thời gian, grouping, tie policy, NULL/absence, đơn vị |
| question_original / variants | Q0 gốc và 10 variants tiếng Việt tự nhiên; mỗi variant giữ nguyên mọi intent slot |
| variant_type | 3 Lexical, 3 Syntactic, 2 Reordering, 2 Mixed variants trong mỗi group |
| canonical_sql | Một SQL canonical dùng chung cho Q0–Q10 |
| competency / complexity | Nhãn theo rubric cố định |
| split | Development hoặc Final; nguyên group ở cùng split |
| validation_record | Bằng chứng annotation/review/adjudication theo mẫu riêng |

**Ví dụ minh họa, không phải benchmark item:** Intent: tổng tiền sau giảm giá theo khách hàng, chỉ tính đơn delivered trong khoảng [2025-01-01, 2025-04-01), không yêu cầu thứ tự. Original Q0: “Trong quý I năm 2025, mỗi khách hàng có đơn đã giao đã mua tổng cộng bao nhiêu tiền sau giảm giá?” Q1 minh họa: “Tổng hợp giá trị sau chiết khấu theo khách hàng cho các đơn có trạng thái delivered, đặt từ 01/01/2025 đến trước 01/04/2025.” Đây chỉ là một ví dụ variant, không phải toàn bộ 10 variants. Mọi câu trong group phải giữ cùng status, date boundary, measure, grain và tập khách hàng. Chưa thiết kế schema hoặc SQL.

## 5. Database và dữ liệu

1. Hai database có schema phù hợp truy vấn nghiệp vụ và data dictionary/glossary được version hóa.
2. Ưu tiên dữ liệu synthetic có generator/seed/version hoặc dữ liệu public có license rõ; không dùng PII thật.
3. Chốt snapshot database trước annotation cuối; tất cả model/question dùng đúng cùng snapshot.
4. Lưu SHA-256 cho DB, schema, glossary, câu hỏi, SQL canonical, prompt và evaluator.
5. Định nghĩa rõ date/time/timezone, currency/rounding, đơn vị, NULL, empty string, zero và absence.
6. Thiết kế fixtures có boundary date, status, quantity/stock bằng 0, NULL, ties, nhiều child rows gây fan-out, không có giao dịch và giá trị sát ngưỡng.
7. Synthetic data không loại bỏ nhu cầu kiểm thử counterexample: các state phải đủ phân biệt những cách hiểu SQL sai phổ biến.
8. Có thể chọn một số intent trả empty result hợp lệ, nhưng số lượng và test false-empty collision cần quyết định nhóm.
9. Trong group chỉ wording đổi; schema, docs, glossary, Evidence, DB snapshot, prompt template, model config, execution environment và timeout giữ nguyên cho Q0–Q10.

## 6. Ma trận phân bố 50 intent

| Competency chính | Tổng | ERP | WMS | Phạm vi |
|---|---:|---:|---:|---|
| Entity filtering/điều kiện | 8 | 4 | 4 | AND/OR, range, status/attribute |
| COUNT/SUM/AVG | 8 | 4 | 4 | Measure/unit; entity count vs row count |
| GROUP BY | 8 | 4 | 4 | Customer/product/warehouse/status |
| Ranking/top-k/min-max/ties | 6 | 3 | 3 | Tie policy và top-k |
| Join nhiều bảng | 8 | 4 | 4 | Quan hệ, fan-out, duplicate aggregate |
| Time boundaries | 4 | 2 | 2 | Inclusive/exclusive, timezone |
| NULL/zero/absence | 4 | 2 | 2 | NULL vs 0, thiếu quan hệ/giao dịch |
| Conditional/derived metric | 4 | 2 | 2 | CASE và metric nghiệp vụ |
| **Tổng** | **50** | **25** | **25** | 1 intent/group, 11 questions/group, 1 SQL/group |

Đề xuất complexity 16 Simple, 24 Moderate, 10 Challenging (tăng gấp đôi quota Draft trước). Gán theo joins, subquery/CTE, tầng aggregation, conditional/time logic và schema linking; không dựa vào độ dài câu. Quota phải được khóa trước khi viết 550 Questions.

## 7. Quy trình tạo và kiểm duyệt Question

1. Chốt database, schema, data dictionary và glossary.
2. Tạo intent card, ghi rõ output grain, projection, filters, time boundaries, grouping, ordering/ties, NULL/empty, units và giả định.
3. Soạn original bằng tiếng Việt tự nhiên, không dịch ngược từ SQL.
4. Tạo đúng 10 variants cho intent: 3 Lexical, 3 Syntactic, 2 Reordering, 2 Mixed. Mỗi câu phải là cách diễn đạt có ý nghĩa, tự nhiên và giữ tất cả slots; không tạo paraphrase bằng cách chỉ thay vài từ máy móc.
5. Kiểm tra trùng/near-duplicate giữa intent; cùng một yêu cầu không được tách group hoặc chia chéo split.
6. Người phụ trách review từng variant theo semantic slots và trạng thái ACCEPT/REVISE/REJECT; lưu lý do revise/reject. Chỉ ACCEPT variants được đưa vào release.
7. Kiểm tra duplicate/near-duplicate trong toàn bộ 50 groups, không chỉ giữa Q0 và variants cùng group. Nếu các intent gần nhau về template hoặc business meaning, ghi cluster và giữ cùng split.
8. AI/Codex có thể gợi ý diễn đạt hoặc ambiguity; không tự accept. Lưu provenance và cách xử lý gợi ý.
9. Khóa toàn bộ 11 wordings của group; mọi sửa đổi cần re-review và version/changelog.

### Quota Semantic Variation Taxonomy

| Loại | Mỗi group | Toàn bộ 50 groups | Development 10 groups | Final 40 groups | Quy tắc chính |
|---|---:|---:|---:|---:|---|
| Lexical | 3 | 150 | 30 | 120 | Thay cách dùng từ/cụm từ bằng diễn đạt nghiệp vụ tương đương; không chỉ thay token máy móc. |
| Syntactic | 3 | 150 | 30 | 120 | Thay cấu trúc câu/mệnh đề nhưng giữ quan hệ và ý nghĩa. |
| Reordering | 2 | 100 | 20 | 80 | Đổi thứ tự thông tin/điều kiện mà không thay quan hệ logic. |
| Mixed | 2 | 100 | 20 | 80 | Kết hợp ít nhất hai thao tác có nhãn; ghi secondary tags. |
| **Tổng variants** | **10** | **500** | **100** | **400** | Cộng thêm 50 originals → 550 Questions. |

Mọi variant phải giữ nguyên entity, output grain, projection, filters, grouping, aggregation, time boundaries, units, NULL/absence và business assumptions. Các loại biến đổi mô tả intervention chủ đạo; chúng không hoàn toàn trực giao. Phân tích loại biến thể là exploratory và được cluster theo Semantic Group.

## 8. Ground-truth Validation: single-human with AI-assisted verification

Benchmark được thực hiện bởi một người phụ trách. Quy trình này thay yêu cầu hai human SQL authors bằng **single-human validation with AI-assisted verification** để phù hợp quy mô đồ án demo. Đây là phương án giảm nguồn lực, không phải independent human annotation và không được mô tả là tương đương double-blind hoặc bất kỳ quy trình independent human annotation nào.

### Quy trình cho mỗi Semantic Group

1. **Xác nhận và khóa Intent Card trước SQL.** Ghi output grain, projection, filters, boundaries, grouping/order/ties, NULL/zero/absence, units và nguồn căn cứ nghiệp vụ. Domain Owner có thể xác nhận; nếu người thực hiện tự xác nhận do không có owner khác, ghi rõ điều đó và các giả định chưa được xác minh.
2. **Thiết kế fixtures và xác định expected outputs độc lập với SQL.** Trước khi viết hoặc chạy canonical SQL, định nghĩa main/boundary/counterexample cases và tính expected results bằng cách áp dụng trực tiếp business rules lên fixture records. Lưu phép tính tay, bảng dẫn xuất hoặc Python reference oracle cùng timestamp. “Độc lập” ở đây là độc lập về cách suy ra expected result, không phải một human annotator khác.
3. **Viết canonical SQL.** Người phụ trách tự viết hoặc dùng Codex hỗ trợ; lưu SQL cuối, hash, thời điểm, tool/model/version và mức hỗ trợ. AI output là draft/advice, không phải annotation hay reviewer độc lập.
4. **Tự kiểm tra logic SQL thủ công.** Dùng checklist: grain, columns, join keys/fan-out, filter/status, date boundary, aggregation, DISTINCT/count semantics, NULL, empty set, ties/order, units. Ghi lý do cho lựa chọn có ảnh hưởng kết quả.
5. **AI-assisted challenge pass.** Có thể yêu cầu công cụ AI tìm lỗi join/filter/boundary hoặc đề xuất thêm phản ví dụ. Người phụ trách tự tính expected output cho fixture mới trước khi chạy SQL, kiểm tra từng gợi ý với Intent Card và ghi accepted/rejected/unresolved. Không biểu quyết theo đa số AI và không coi lần gọi khác nhau là reviewer độc lập.
6. **Đối chiếu bằng alternative implementation khi khả thi.** Viết SQL thay thế sau khi đã khóa canonical SQL, hoặc dùng Python reference oracle tính từ fixture rows; ghi nguồn input/phép tính và hash. Nếu không khả thi, ghi lý do và mức rủi ro.
7. **Thực thi và lưu evidence.** Chạy canonical SQL và oracle/alternative trên snapshot/fixtures, lưu trạng thái, expected rows so với actual rows, column metadata, runtime, DB hash, environment và artifact hashes. SQL chỉ chạy thành công không đủ chứng minh logic đúng.
8. **Benchmark Owner phê duyệt cuối hoặc sửa.** Canonical SQL chỉ được chấp nhận khi intent, expected outputs được suy ra độc lập với SQL, manual logic review và execution evidence nhất quán. Người phụ trách ghi kết luận và ngày vào Validation Record. Bất đồng unresolved, expected output chưa xác định hoặc GT error/timeout là blocker; sửa, hỏi domain owner nếu có thể, hoặc loại item theo version policy.

AI không thay thế independent human annotation. Việc dùng một người, kể cả có AI critique và một SQL/Python oracle, vẫn có nguy cơ common-method bias, lỗi cùng nguồn và thiếu phép đo inter-annotator agreement. Ghi hạn chế này trong report/paper.

Mẫu Validation Record gọn cho một người phụ trách có tại [ANNOTATION_REVIEW_TEMPLATE.md](ANNOTATION_REVIEW_TEMPLATE.md). Record cần giữ được Intent Card/hash, expected outputs được lập trước khi SQL execution, SQL provenance, manual checklist, oracle/fixture evidence, AI assistance log, quyết định cuối và hash các artifact.

## 9. Kiểm chứng Semantic Equivalence

Mỗi một trong 10 variants tương đương với Q0 nếu với mọi state hợp lệ theo schema, constraints và quy tắc nghiệp vụ, câu đó yêu cầu cùng entity/grain, output columns/measure, filters, joins, thời gian, grouping, ordering/tie, NULL/absence và units.

- Người phụ trách ghi slot interpretation cho mỗi Q1–Q10 và đối chiếu từng slot với Intent Card/glossary. Lưu 10 quyết định ACCEPT/REVISE/REJECT cùng rationale. Đây là review của cùng một người, không phải 10 reviewers độc lập.
- Kiểm tra ambiguity nghiệp vụ: gross/net, on-hand/available, end-date, status, ties, entity count và NULL.
- Dùng counterfactual fixtures và AI-generated challenge suggestions để tìm phản ví dụ; người phụ trách phải tự xác minh mỗi phản ví dụ.
- Cùng output trên một snapshot hoặc đồng thuận giữa AI outputs không chứng minh equivalence trên mọi state.
- Nếu có Domain Owner khác, xin xác nhận những slot nghiệp vụ rủi ro cao và ghi bằng chứng; nếu không có, công khai rằng equivalence do một người đánh giá.
- LLM-as-a-Judge chỉ hỗ trợ triage/gợi ý, không phải oracle, không tự động accept/reject và không thay người duyệt.
- Nếu còn mơ hồ sau kiểm tra, sửa wording hoặc loại pair; không tăng độ chắc chắn chỉ vì AI đồng ý.
- Chỉ release group khi Q0 và cả 10 variants đều được chấp nhận hoặc đã được thay bằng variant mới có record review; không tính variant REVISE/REJECT vào 550.

## 10. EX, Result Stability, Correctness Agreement và Robust EX

Có G=50 Semantic Groups; mỗi group có Q0 và Q1–Q10. y[g,i]=1 khi SQL prediction thực thi thành công và set(predicted_rows)=set(canonical_rows); SQL error, timeout hoặc no SQL có y[g,i]=0. Infrastructure failure chưa khôi phục là unknown, không phải y=0. P[g,i] là tuple rows trả về nếu SQL chạy thành công.

### Execution Accuracy

K_o = số Q0 có outcome xác định; K_v = số variants có outcome xác định; K_a = tổng số Questions có outcome xác định. Nếu không có unrecoverable infrastructure failures thì K_o=50, K_v=500, K_a=550.

~~~text
EX_Original = 100 * sum_g(y[g,0]) / K_o
EX_Variants = 100 * sum_g sum_i=1..10(y[g,i]) / K_v
EX_Overall  = 100 * sum_g sum_i=0..10(y[g,i]) / K_a
~~~

Báo tử số/mẫu số; mặc định 50, 500, 550. Infrastructure questions không khôi phục được bị loại khỏi denominator phù hợp và phải báo missing count. SQL error, timeout và no SQL là model outcomes, vẫn ở mẫu số với y=0. Nếu một denominator bằng 0 thì metric tương ứng là N/A, không gán 0%. EX so executed result với gold theo comparator BIRD-compatible.

### Result Stability Score (RSS) — metric mở rộng IS6002

Với mỗi Original–Variant pair Q0–Qi (i=1..10), pair đủ điều kiện nếu cả hai có model outcome xác định. C là set-based result comparator ở §11.

~~~text
s[g,i] = 1 nếu hai SQL chạy thành công và C(P[g,0], P[g,i]) = equal; ngược lại s[g,i] = 0
M_RSS  = số pair có hai outcome xác định (tối đa 500)
RSS    = 100 * sum_g sum_i=1..10(s[g,i]) / M_RSS
~~~

SQL error, timeout hoặc no SQL là outcome xác định và cho s=0. Nếu có unrecoverable infrastructure failure, pair là unknown và bị loại sau fixed retries. Hai SQL cùng trả về kết quả sai vẫn có thể cho s=1. RSS đo consistency output, không đo correctness hay semantic equivalence. Nếu M_RSS=0 thì RSS là N/A.

Per-group descriptive score: M_g = số variants trong group có pair outcome xác định; RSS_g = 100 × sum_i s[g,i] / M_g nếu M_g>0, ngược lại N/A. Overall RSS là micro-average trên mọi eligible pair như công thức trên; báo phân phối RSS_g để thấy khác biệt giữa groups.

### Correctness Agreement (CA) — metric phụ

~~~text
M_CA = số Original–Variant pairs có cả hai correctness outcomes xác định (cùng eligibility với RSS)
CA   = 100 * sum_g sum_i=1..10(I(y[g,0] = y[g,i])) / M_CA
~~~

Cả hai sai cho CA pair=1; SQL error/timeout/no SQL có y=0 và vẫn tham gia CA. CA không đo result consistency. Nếu M_CA=0 thì CA là N/A.

### Robust EX (All) — metric mở rộng IS6002

~~~text
K_G = số group có đủ 11 outcomes xác định (mặc định 50)
RobustEX_All = 100 * count(groups where all y[g,0..10] = 1) / K_G
~~~

Group đạt nếu cả 11 Questions đều đúng. Một error/timeout/no SQL làm y=0 và group fail; unrecoverable infrastructure failure làm group incomplete, loại khỏi K_G và được báo riêng. Nếu K_G=0 thì RobustEX_All là N/A.

### Pairwise Robust Accuracy (PRA) — metric mở rộng IS6002

~~~text
M_PRA = số Original–Variant pairs có hai outcomes xác định (tối đa 500)
PRA   = 100 * sum_g sum_i=1..10(I(y[g,0]=1 AND y[g,i]=1)) / M_PRA
~~~

PRA là tỷ lệ đúng trên các Q0–Qi pairs, không phải trên 550 Questions. Một Q0 xuất hiện trong 10 pairs nên các pair phụ thuộc nhau. Nếu M_PRA=0 thì PRA là N/A.

### Truth table

| Q0 vs gold | Qi vs gold | Prediction results bằng nhau? | EX Q0/Qi | RSS pair | CA pair | PRA pair | Robust EX (All) |
|---|---|---:|---:|---:|---:|---:|---:|
| Đúng | Đúng | Có | 1 / 1 | 1 | 1 | 1 | Có thể đạt nếu Q1–Q10 đều đúng |
| Sai | Sai | Có | 0 / 0 | 1 | 1 | 0 | 0 |
| Sai | Sai | Không | 0 / 0 | 0 | 1 | 0 | 0 |
| Đúng | Sai | Không | 1 / 0 | 0 | 0 | 0 | 0 |
| Đúng | Qi SQL error/timeout/no SQL | Không xét | 1 / 0 | 0 | 0 | 0 | 0 |
| Q0 error/timeout/no SQL | Qi error/timeout/no SQL | Không xét | 0 / 0 | 0 | 1 | 0 | 0 |
| Q0 error/timeout/no SQL | Qi đúng/sai | Không xét | 0 / y_i | 0 | so y=0 với y_i | 0 | 0 |
| Có infrastructure failure chưa khôi phục | Bất kỳ | Không xác định | Không tính pair | Không xác định | Không xác định | Không xác định | Group incomplete |

Ví dụ: Q0 và Qi đều chạy, cùng trả empty result nhưng gold không rỗng → EX của cả hai là 0; RSS=1, CA=1, PRA=0 và Robust EX (All)=0. Vì EX và RSS dùng cùng comparator với gold, nếu một prediction đúng và prediction kia sai thì result sets không thể bằng nhau.

### Repeated runs và suy luận thống kê

Nếu dùng R>1 repeats, chạy đủ 550 questions mỗi replicate với cùng config; so Q0/Qi trong cùng group và cùng replicate index. Tính metric riêng theo replicate, báo mean, range/SD và raw counts; không gộp SQL outputs giữa repeats và không chọn repeat có điểm cao nhất. Retry policy và seed phải được cố định trước run.

Đơn vị cluster cho bootstrap/CI là Semantic Group (50 clusters), không phải 550 Questions hay 500 pairs độc lập. Các variants trong group và pairs dùng chung Q0 nên tương quan. Báo eligible groups/pairs và infrastructure missingness; suy luận vẫn exploratory.
## 11. SQL Comparator, giới hạn EX và test cases

### Comparator tương thích BIRD và IS6002

Đã đối chiếu evaluator chính thức BIRD Mini-Dev hiện hành: `evaluation/evaluation_ex.py:calculate_ex()` dùng `set(predicted_res) == set(ground_truth_res)`; `execute_model()` chuyển exception và timeout thành điểm 0, timeout mặc định 30 giây; `evaluation_utils.py:execute_sql()` lấy rows bằng `fetchall()` và evaluator không so column names. Source IS6002 `bird_demo/scoring.py:score()` cũng dùng set trên rows; `bird_demo/runner.py:run()` thực thi read-only với deadline và phân loại SQL error/timeout; `bird_demo/report.py:ex()` giữ No SQL trong denominator. Vì vậy set comparison dưới đây tương thích với evaluator BIRD đã xem ở [evaluation_ex.py](https://github.com/bird-bench/mini_dev/blob/main/evaluation/evaluation_ex.py) và [evaluation_utils.py](https://github.com/bird-bench/mini_dev/blob/main/evaluation/evaluation_utils.py). Khi công bố benchmark, nhóm vẫn cần pin commit hash của evaluator để bảo đảm tái lập.

Comparator đề xuất cho EX: `set(predicted_rows) == set(gold_rows)`, với row là tuple có thứ tự cột. Comparator đề xuất cho RSS cũng dùng set equality giữa hai prediction thành công. Không normalize, cast hay round values ngoài quy tắc đã freeze.

| Trường hợp | Hành vi của set comparator | Test case nghiệm thu |
|---|---|---|
| Row order | Bỏ qua thứ tự dòng | `[(1,), (2,)]` và `[(2,), (1,)]` → equal |
| Duplicate rows | Bỏ multiplicity | `[(1,), (1,)]` và `[(1,)]` → equal; bag diagnostic phải mismatch |
| Column names/aliases | Không so tên cột; chỉ so tuple values | Cùng rows, tên cột `id` và `customer_id` → EX match |
| Column order/arity | So tuple position/value; tên cột không giúp nhận diện semantic column | `[(1, 'A')]` và `[('A', 1)]` → mismatch; test khác tên nhưng cùng values vẫn match |
| Data types | Không có normalization; Python value equality | `('1',)` vs `(1,)` → mismatch; `(1,)` vs `(1.0,)` có thể equal trong Python, cần ghi caveat/test |
| NULL | SQLite NULL thành Python `None`; so theo value | `(None,)` vs `(None,)` → equal; `None` vs `0` → mismatch |
| Empty result | Hai tập rỗng equal, bất kể column metadata | `[]` vs `[]` → match; kiểm tra false-empty collision |
| ORDER BY/ranking | Row order không được chấm; top-k membership vẫn chấm nếu tập rows khác | Cùng top-k rows theo thứ tự khác → match; thay một member top-k → mismatch |
| SQL error/timeout/no SQL | Không có result để match; correctness=0; RSS=0 | Mỗi trạng thái prediction riêng phải ra 0, vẫn trong denominator |
| Ground-truth error/timeout | Benchmark item không hợp lệ | Không chấm model; dừng release/evaluation cho item và ghi defect |

Set comparator có thể nhận nhầm câu trả lời thiếu duplicate; cũng không chấm thứ tự output, tên cột, hoặc metadata khi result rỗng. Ranking chỉ có ý nghĩa về membership nếu protocol không yêu cầu vị trí xếp hạng; nếu thứ tự nghiệp vụ là một phần intent thì pilot phải định nghĩa output order và metric ordered riêng trước freeze, không diễn giải set EX như đã chấm thứ tự.

Đề xuất báo set-based EX để tương thích với pipeline/BIRD-style; có thể báo thêm EX_bag dùng multiset/Counter làm diagnostic. EX_bag, RSS, CA và Robust EX là các mở rộng/diagnostic IS6002, không được gộp tên với EX BIRD. Không sửa evaluator tại bước đặc tả này.

## 12. SQL error, timeout, kết quả rỗng và trạng thái không xác định

| Tình huống | EX | RSS | Xử lý protocol |
|---|---:|---:|---|
| Prediction parse/runtime error | 0 | 0 cho mọi pair liên quan | Ghi error type/message đã làm sạch; giữ question trong EX denominator và pair/group có outcome xác định. |
| Model trả lời thành công nhưng không có SQL | 0 | 0 cho mọi pair liên quan | Ghi no_sql; giữ denominator. |
| Prediction timeout | 0 | 0 cho mọi pair liên quan | Dùng timeout cố định; giữ denominator. |
| GT lỗi/timeout | Không tính question/group | Chưa xác định | Benchmark defect; sửa/loại theo version và chạy lại mọi đánh giá liên quan. |
| GT hợp lệ trả 0 rows | Theo so sánh | Theo output pair | Item hợp lệ; empty/empty match; đánh giá collision bằng fixture. |
| Provider/network/infra failure | Unknown | Unknown cho pair/group liên quan | Đề xuất retry initial + tối đa 2 retries cùng request/config. Sau đó giữ status infra_error; loại question khỏi EX denominator, pair khỏi RSS/CA/PRA denominators và group khỏi RobustEX_All nếu thiếu một trong 11 outcomes. Báo attempts/missingness; chốt retry cap trước run. |
| Prediction API thành công nhưng content rỗng/từ chối/no SQL | 0 | 0 cho mọi pair liên quan | Đây là outcome model, không phải infra failure. |

Timeout hiện tại trong `bird_demo/runner.py:TIMEOUT_S` là 30 giây; chỉ là điểm xuất phát cần kiểm tra trên snapshot benchmark, rồi freeze cùng resource limits, SQLite/Python và execution environment. Mọi nhóm model dùng cùng giới hạn. Infra retry cap là đề xuất, cần chốt cùng retry/repeat policy trước evaluation.

## 13. Experimental Protocol và Development/Final

### Chia split không leakage

1. Lập danh sách 50 intent độc lập và audit near-duplicate trước khi tạo 500 variants; cluster các intent gần nhau theo nghiệp vụ/template.
2. Gán toàn bộ semantic/near-duplicate cluster vào cùng split. Mọi Q0–Q10 thuộc một group, và mọi group liên quan gần nhau phải ở cùng split.
3. Chọn 10 Development groups/110 Questions và 40 Final groups/440 Questions. Đề xuất stratification 5 ERP + 5 WMS ở Dev, 20 ERP + 20 WMS ở Final; giữ nguyên quota transformation của từng group. Ghi seed, thuật toán và manifest phân bổ.
4. Nếu có thể, giữ kín Final questions, SQL và labels trước khi model/prompt freeze; nếu không, báo đây là fixed held-out split với leakage risk, không gọi là blind test.
5. Development dùng để debug pipeline. Không đổi protocol vì quan sát Final mà vẫn giữ cùng version/score; thay đổi semantic tạo version mới.

### Freeze và giữ điều kiện tương đương

- Pin benchmark, DB snapshot, schema, glossary/Evidence, prompt, evaluator, runtime, timeout và hashes.
- Pin model snapshot/provider, decoding parameters, system/user prompt, tool settings, retries, seed nếu hỗ trợ.
- Giữ mọi đầu vào trên giống nhau cho 11 Questions trong group, chỉ thay wording. Ghi thứ tự chạy; randomize/cân bằng thứ tự 550 Questions bằng seed cố định trước run.
- Nếu có repeats, chạy đủ 550 Questions mỗi replicate; pair Q0–Qi cùng group và replicate. Số lần, aggregation, seed và retry policy đăng ký trước.
- Không thay schema, glossary hoặc prompt giữa các 11 wordings; nếu điều chỉnh thì chạy lại group và tạo run/version mới.

### Lưu kết quả

**Per-question record** tối thiểu: benchmark/version, split, group_id, question_id, role (Q0/Q1–Q10), transformation label, DB/hash, question, model snapshot/provider, config/prompt hash, replicate/attempt/timestamp, raw response, extracted SQL, status (success/sql_error/timeout/no_sql/infra_error), executed rows/column metadata, gold verdict, duration, error details đã làm sạch, retry/cache metadata.

**Per-group record** tối thiểu: 11 question run IDs, correctness Q0–Q10, per-variant RSS/CA/PRA pair outcomes, group RSS mean, RobustEX_All, 2x2 correctness counts, status ACCEPT/revise/reject của variants, missing/infra status và replicate IDs. Giữ raw results theo quyền truy cập; aggregate phải truy nguyên được.

### Quy tắc kết quả chưa xác định

SQL error, timeout, no SQL là outcomes đã định nghĩa, không phải missing data. Đề xuất hạ tầng: một initial attempt + tối đa 2 infra retries với cùng request/config; giữ mọi attempts. Không retry lỗi SQL/model output. Nếu infra failure chưa khôi phục, question/pairs/group được xử lý unknown theo §10; không gán 0 hoặc 1, và báo mọi denominator/missing count. Không loại mẫu sau khi xem model correctness. Tại đủ dữ liệu, mặc định denominators là 50/500/550 questions, 500 anchor pairs, 50 groups.

### Giới hạn thiết kế

Chỉ hai database không đủ đo generalization sang domain/schema khác. Mỗi intent có 10 variants được thiết kế theo quota nhưng không bao phủ hết biến thiên tự nhiên tiếng Việt; các category có thể chồng lấn, và 50 group là số cluster độc lập tối đa. 550 Questions và 500 Q0–Qi pairs không phải quan sát độc lập; CI/inference phải cluster theo group. Phân tích theo loại/competency nhỏ vẫn exploratory. Không kết luận phổ quát về “robustness tiếng Việt”.

## 14. Versioning và chống leakage

- 0.x là pilot Draft; 1.0.0 chỉ sau acceptance/release review.
- Patch chỉ sửa metadata/typo không đổi semantics, SQL, DB hay metric.
- Minor thêm dữ liệu/quota/split hoặc thay đổi material trong quy trình annotation/validation; báo score từng version riêng và ghi rõ protocol change.
- Major thay intent, question semantics, schema/data, gold SQL, comparator hoặc metric; không so trực tiếp như cùng benchmark.
- Manifest lưu version, commit, SHA-256 DB/schema/questions/SQL/glossary/prompt/evaluator, runtime, model snapshot và config.
- Final không xuất hiện trong demo/tuning/cache trước freeze nếu cần blind evaluation; cache key gắn tất cả hash/config và response lưu immutable.
- Synthetic/public data vẫn có thể leakage qua code hoặc prompt exposure; ghi rõ exposure.

## 15. Decision Record — D1–D14

D1–D7, D10 và D11 đã được Benchmark Owner phê duyệt ngày 2026-11-09. D8, D9, D12, D13 và D14 vẫn PROPOSED. Mỗi status và rationale được ghi tại Decision Review; không tự phê duyệt quyết định nào khác.

| Decision ID | Recommended value | Status | Decision owner / approver | Date | Rationale (confirm or replace at decision) |
|---|---|---|---|---|---|
| D1 | 10 Development groups/110 Questions; 40 Final groups/440 Questions; chia ở cấp group/near-duplicate cluster | APPROVED | Benchmark Owner | 2026-11-09 | Tránh rò rỉ wording cùng intent; mọi Q0–Q10 trong group ở cùng split và near-duplicate clusters phải được kiểm tra trước khi khóa split. |
| D2 | 25 ERP groups + 25 WMS groups; mỗi split cân bằng 5/5 Dev và 20/20 Final | APPROVED | Benchmark Owner | 2026-11-09 | Cân bằng hai domain trong toàn tập và trong từng split để giảm nguy cơ kết quả bị chi phối bởi một database. |
| D3 | Synthetic deterministic, không PII thật; public data nếu license/provenance rõ | APPROVED | Benchmark Owner | 2026-11-09 | Ưu tiên dữ liệu tổng hợp xác định để tái lập; chỉ dùng nguồn công khai bổ sung khi license và provenance được ghi lại. |
| D4 | Định hướng: hai SQLite DB; glossary/data dictionary/business rules phải được kiểm tra và chốt trước annotation | APPROVED (định hướng) | Benchmark Owner | 2026-11-09 | Phê duyệt phạm vi hai DB và nguyên tắc xác minh tài liệu nghiệp vụ trước annotation. Business Rules và Glossary chi tiết chưa được phê duyệt; cần được kiểm tra trong Bước 2A. |
| D5 | Schema context/Evidence giống nhau cho mọi 11 Questions trong group | APPROVED | Benchmark Owner | 2026-11-09 | Giữ dữ liệu và thông tin nền giống nhau giữa Q0–Q10 trong cùng group để cô lập wording variation. |
| D6 | Empty-result intents có chủ đích; quota 2–3 trên 50 | APPROVED | Benchmark Owner | 2026-11-09 | Cho phép kiểm tra trường hợp kết quả rỗng nhưng giới hạn số lượng; từng intent cần fixture/counterexample kiểm tra false match. |
| D7 | BIRD-compatible set EX và set-based RSS; EX_bag diagnostic; primary EX không chấm row order | APPROVED | Benchmark Owner | 2026-11-09 | Chấp nhận set-based comparator chính và EX_bag diagnostic; row order không tính vào EX chính. Ranking/ties vẫn phải có quy tắc và test cases trong protocol. |
| D8 | Timeout khởi điểm 30 giây/query, đo trên snapshot rồi freeze; cùng resource limits cho mọi câu | PROPOSED | — | — | Source hiện dùng 30s; workload mới cần đo. |
| D9 | Ưu tiên 3 replicates nếu đủ nguồn lực; nếu không single-shot. Paired theo replicate, báo từng run và mean/range/SD | PROPOSED | — | — | Không gộp SQL outputs hoặc chọn replicate cao nhất. |
| D10 | Một Benchmark Owner thực hiện single-human validation; AI/Codex hỗ trợ critique/oracle; công khai không có independent human annotation | APPROVED | Benchmark Owner | 2026-11-09 | Chấp nhận quy trình một người; AI/Codex chỉ hỗ trợ kiểm tra kỹ thuật, không được tính là annotator độc lập hay double-blind review; công bố common-method bias. |
| D11 | Competency quota §6 (8/8/8/6/8/4/4/4), complexity 16/24/10; mỗi group 3 Lexical, 3 Syntactic, 2 Reordering, 2 Mixed | APPROVED | Benchmark Owner | 2026-11-09 | Khóa coverage competency, complexity và taxonomy biến thể trước authoring; mọi biến thể vẫn phải qua semantic-slot review. |
| D12 | 0.x pilot; Final giữ kín khi khả thi, nếu không ghi exposure/leakage | PROPOSED | — | — | Chốt release/access trước tune/final evaluation. |
| D13 | Bootstrap/statistics cluster theo 50 groups; infra retry tối đa 2 sau initial; missingness/denominators công bố | PROPOSED | — | — | 550 câu và 500 pairs lồng trong groups; suy luận exploratory. |
| D14 | Gọi là pilot, không tuyên bố “first” hoặc novelty tuyệt đối | PROPOSED | — | — | Cần literature review trước novelty claim. |

## 16. Checklist nghiệm thu

### Dataset và split
- [ ] Đúng 50 Semantic Groups/intents, 550 Questions (50 Q0 + 500 variants) và 50 canonical SQL.
- [ ] Mỗi group có đúng một Q0 và mười variants ACCEPT; một canonical SQL dùng chung cho 11 Questions.
- [ ] Hai DB SQLite; 25 ERP groups + 25 WMS groups; competency/complexity/taxonomy khớp các quyết định.
- [ ] Split 10/40 groups = 110/440 Questions; ghi seed, near-duplicate clusters và phân bổ.
- [ ] Mỗi group có 3 Lexical, 3 Syntactic, 2 Reordering, 2 Mixed variants; tổng 150/150/100/100.
- [ ] Snapshot, generator/provenance/license và hashes đã lưu; không có PII.

### Annotation và semantic equivalence
- [ ] Intent Card được xác nhận/freeze trước khi viết hoặc chạy SQL; nguồn và giả định được lưu.
- [ ] Expected outputs được suy ra từ intent/fixture trước khi chạy canonical SQL, có timestamp/artifact.
- [ ] SQL do người viết hoặc Codex hỗ trợ; tool/model provenance và final human ownership được ghi.
- [ ] Manual logic checklist hoàn tất; boundary/counterexample fixtures có expected results.
- [ ] Alternative SQL/Python reference oracle được đối chiếu khi khả thi; nếu không, ghi lý do.
- [ ] AI challenge pass được lưu như hỗ trợ kỹ thuật, không ghi là annotator/reviewer độc lập.
- [ ] Có 50 Validation Records; mỗi record có canonical SQL evidence và status/reason cho đủ 10 variants.
- [ ] Execution evidence, artifacts/hashes, kết luận equivalence và limitation được lưu.
- [ ] Benchmark Owner ghi human final approval/ngày cho từng canonical SQL và group.
- [ ] Công bố single-human validation; không gọi là independent double annotation/double-blind annotation.
- [ ] GT errors, unresolved ambiguity hoặc expected-output mismatch chặn release cho đến khi sửa/loại theo version policy.

### Evaluation và tái lập
- [ ] BIRD evaluator source/commit được pin và audit; comparator tests đã chạy khi triển khai.
- [ ] Test duplicate/order/column/type/NULL/empty/ranking/error/timeout/no-SQL đạt.
- [ ] Metric formulas và truth table được nhóm duyệt.
- [ ] Prompt/schema/glossary/model/runtime/timeout giữ giống nhau cho cả 11 Questions trong group.
- [ ] Lưu kết quả question-level và group-level, attempts, errors, hashes, config.
- [ ] Infra failure được phân biệt với model failure; không âm thầm drop mẫu.
- [ ] Báo raw counts, denominators, metric, limitations và missingness.

## 17. Hạn chế và threats to validity

| Nguy cơ | Tác động | Giảm thiểu |
|---|---|---|
| 50 intents, 2 DB | Coverage vẫn thấp so với domain/schema đa dạng; CI rộng | Gọi pilot; công bố n và raw counts. |
| 10 variants/intent | Quota không bao quát mọi diễn đạt; variants trong cùng group tương quan | Nêu rõ taxonomy; bootstrap group-level; không coi 550 câu độc lập. |
| Nhiều variants/group | Một sai lệch ngôn ngữ nhỏ có thể lặp/lan ra 10 paraphrases | Slot review và ACCEPT/REVISE/REJECT cho đủ 500 variants; log rationale. |
| 550 Questions / 500 pairs bị coi là độc lập | Sai số chuẩn thấp giả tạo, kết luận quá mạnh | Cluster bootstrap theo 50 Semantic Groups; báo group-level counts. |
| Pair không tương đương/ambiguous | Đo lỗi annotation như lỗi model | Intent slots, tài liệu nghiệp vụ, counterexample; Domain Owner review nếu có; công khai self-validation khi không có. |
| Gold sai hoặc snapshot-specific | EX sai lệch | Expected outputs ghi trước SQL execution, manual review, alternative oracle/fixtures, hashes; nêu single-human bias. |
| Set comparator bỏ duplicate/order/metadata | Một số lỗi không bị bắt | Báo caveat; EX_bag diagnostic; kiểm tra ranking policy. |
| Empty outputs quá nhiều | Collision giả giữa query sai | Empty quota có chủ đích và fixtures đối kháng. |
| Model/provider drift hoặc stochasticity | Khó tái lập và quy nguyên nhân | Pin snapshot/config; repeats theo protocol. |
| Leakage từ Final/schema/template | Điểm không phản ánh generalization | Group/cluster split, giữ kín khi khả thi, ghi exposure. |
| Single-human/common-method bias | Cùng người xác định intent, expected outputs, SQL và kết luận; không đo inter-annotator agreement | Công khai hạn chế; tách expected-output derivation khỏi SQL run; fixtures/oracle và Domain Owner check khi có; AI không tính là reviewer độc lập. |
| RSS cao nhưng cả hai sai | Dễ nhầm consistency với correctness | Luôn báo EX, CA và Robust EX cùng RSS. |
| LLM judge bias | Tự củng cố lỗi model | Judge chỉ triage; quyết định cuối do người. |
| Infra failures bị tính sai | Denominator thiên lệch | Phân loại infra_error; retry cố định, báo missingness. |

## 18. Điều kiện để bắt đầu Bước 2A

D1–D7, D10 và D11 đã được Benchmark Owner phê duyệt ngày 2026-11-09; D8, D9, D12, D13 và D14 vẫn PROPOSED và không cản trở việc bắt đầu Bước 2A. Có thể bắt đầu Bước 2A để kiểm tra Business Rules/Glossary chi tiết, xác định Domain Owner hoặc nguồn nghiệp vụ thay thế, rà soát date/time/currency/NULL rules, và phát triển thiết kế schema theo định hướng hai SQLite DB đã duyệt.

D4 chỉ duyệt định hướng thiết kế; không xem bất kỳ Business Rules hoặc Glossary chi tiết nào là đã xác nhận. Bước 2A cần ghi nguồn, giả định, bất đồng và kết quả rà soát trước khi freeze schema/data. D8/D9/D13 phải được chốt trước evaluation; D12 trước phát hành/chia sẻ Final; D14 trước báo cáo novelty. Lần cập nhật này không tạo Questions, database, seed hay SQL benchmark.
## Phụ lục A. Phân loại phương pháp

- **Kế thừa BIRD:** database-grounded task, schema/data context, Evidence khi cần, kiểm tra SQL validity và text/knowledge/SQL alignment, execution-based EX.
- **Tham khảo:** Spider-Syn cho biến thiên từ vựng; Dr.Spider cho perturbation benchmark.
- **Đề xuất IS6002:** pilot tiếng Việt, ERP/WMS, 50 Semantic Groups × 11 Questions, RSS/CA/Robust EX/PRA và single-human validation có AI hỗ trợ. Cách làm này không tương đương independent/double-blind annotation; công bố rõ common-method bias và không đo inter-annotator agreement. Các metric mở rộng cần được trình bày là đề xuất của nhóm và không tuyên bố độc quyền nếu chưa rà soát literature.

**Bước 1 dừng tại đặc tả này.** Chưa tạo Questions, database, seed data hoặc SQL benchmark; không sửa Python source và không gọi LLM API.
