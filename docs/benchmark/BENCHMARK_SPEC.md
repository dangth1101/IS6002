# BIRD-VN-Robust-50: Đặc tả benchmark Text-to-SQL tiếng Việt

| Thuộc tính | Giá trị |
|---|---|
| Phiên bản | **0.4.0** |
| Trạng thái | **Draft — D1–D7, D10, D11, D12, D8, D9, D13 APPROVED; D14 PROPOSED** |
| Ngày | 2026-11-18 |
| DBMS | SQLite |
| Quy mô đề xuất | 550 Questions; 50 Semantic Groups/Intent; 50 canonical SQL |
| Split đề xuất | Development: 10 groups/110 Questions; Final: 40 groups/440 Questions |
| Phạm vi tài liệu | Đặc tả benchmark v0.4.0 Draft cho 50 Intent/550 Questions; bộ dữ liệu và SQL hiện có có trạng thái review riêng trong registry/Validation Records |

Đây vẫn là đặc tả Draft, chưa phải benchmark đã phát hành. D1–D7, D10, D11, D12, D8, D9, D13 đã được phê duyệt theo Decision Review; riêng comparator D7 được sửa đổi ngày 2026-11-18. D14 còn PROPOSED. Việc duyệt comparator không tự duyệt các hợp đồng trường của 50 group.

**Ghi chú phiên bản 0.4.0:** bổ sung comparator contract-aware: căn kết quả theo tên trường, bỏ qua thứ tự cột, yêu cầu đúng projection và mô tả trường trong prompt. D7 được Benchmark Owner xác nhận lại ngày 2026-11-18; thay đổi này tạo protocol version mới. Official Evaluation cần cấu hình đóng băng mới và duyệt đủ 50 hợp đồng trường.

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
| Tạo prompt | BIRD Original: `bird_demo/prompt.py::build_prompt()`; BIRD-VN: `bird_demo/benchmark/official.py::make_bird_vn_prompt_builder()` gọi `dashboard.py::prompt_for()` | Prompt BIRD-VN gồm schema, business rules, glossary, phân biệt các cặp ID/code/no dễ nhầm, output field contract và câu hỏi. Hash prompt từng câu; giữ cùng contract và cấu hình trong Q00–Q10. |
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

Complexity được phân bổ đều theo database: ERP Sales 8 Simple / 12 Moderate / 5 Challenging; WMS Inventory 8 / 12 / 5 (tổng 16/24/10). Gán theo joins, subquery/CTE, tầng aggregation, conditional/time logic và schema linking; không dựa vào độ dài câu. Mỗi intent vẫn cần rubric-level justification trước khi viết Questions.

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

### Output Field Contract trong prompt

Mỗi prompt BIRD-VN gồm: lược đồ SQLite, quy tắc nghiệp vụ, glossary, giải thích các cặp trường dễ nhầm và hợp đồng trường đầu ra của Intent. Hợp đồng nêu đúng tên cột SQL cần trả về và ý nghĩa; ví dụ `customer_id` là ID nội bộ còn `customer_code` là mã nghiệp vụ, `product_id` khác `sku`, `order_id` khác `order_no`, `sales_rep_id` tham chiếu `employee_id` chứ không phải `employee_code`. Model được yêu cầu trả đúng các trường trong contract, không thiếu hoặc thêm trường. Cùng một contract được gửi cho cả Q00–Q10.

Hợp đồng hiện được tạo từ projection SQL chuẩn và từ điển mô tả trường, nên chỉ là hướng dẫn dự thảo cho tới khi người phụ trách đối chiếu với Intent Card và duyệt. Không gửi expected rows, đáp án SQL hoặc fixture values trong prompt. Prompt hash bao gồm template, từ điển thuật ngữ, logic tạo contract và mã mô tả trường. Mọi thay đổi tạo run/version mới.

## 10. EX, Result Stability, Correctness Agreement và Robust EX

Bản 0.4.0 bổ sung **hợp đồng trường đầu ra** cho từng Semantic Group. Hợp đồng gồm tên từng cột cần trả về, ý nghĩa nghiệp vụ và các bí danh được cho phép riêng. Cùng một hợp đồng được gửi cho Q00–Q10. Hợp đồng hiện được suy ra từ projection của SQL chuẩn và từ điển trường; trạng thái mặc định là dự thảo, chưa được Benchmark Owner duyệt.

Quy tắc căn chỉnh kết quả:

1. Tên cột được so sau khi bỏ khoảng trắng đầu/cuối và không phân biệt chữ hoa/thường.
2. Thứ tự cột không bắt buộc. Kết quả được sắp lại theo thứ tự chuẩn của hợp đồng trước khi so giá trị.
3. Bí danh chỉ được chấp nhận nếu được khai báo rõ cho đúng Intent. Không tự suy đoán rằng hai tên bất kỳ có cùng nghĩa.
4. Thiếu cột, cột thừa, tên cột trùng, tên không nhận diện được, thiếu metadata tên cột hoặc số giá trị trong dòng không khớp số cột đều làm projection không hợp lệ.
5. Khi projection hợp lệ, so các dòng theo set semantics: bỏ qua thứ tự dòng và số lần lặp của dòng. Không tự ép kiểu, làm tròn hay đổi NULL.

Gọi C_g là hợp đồng đầu ra của group g. y[g,i]=1 khi SQL chạy thành công, projection hợp lệ theo C_g và tập dòng sau khi căn cột bằng kết quả SQL chuẩn; các trường hợp còn lại có y[g,i]=0. Lỗi hạ tầng không khôi phục được là UNKNOWN, không phải 0.

### Execution Accuracy (EX)

K_o là số Q00 có outcome xác định; K_v là số biến thể có outcome xác định; K_a là tổng số câu có outcome xác định.

~~~text
EX_Original = 100 × số Q00 có y=1 / K_o
EX_Variants = 100 × số Q01–Q10 có y=1 / K_v
EX_Overall  = 100 × số câu Q00–Q10 có y=1 / K_a
~~~

Mẫu số tối đa lần lượt là 50, 500 và 550. Lỗi SQL, timeout, không sinh SQL, projection không hợp lệ vẫn là outcome của mô hình và có điểm 0. Lỗi hạ tầng còn UNKNOWN sau retries được loại khỏi mẫu số phù hợp và phải báo số lượng bị thiếu. Mẫu số bằng 0 thì hiển thị N/A.

EX phiên bản này dùng phép so sánh kết quả dạng tập của BIRD sau bước kiểm tra/căn chỉnh hợp đồng trường đầu ra do IS6002 bổ sung. Vì bước hợp đồng làm thay đổi tiêu chí đúng, EX 0.4.0 không được so trực tiếp với EX của comparator cũ.

### Result Stability Score (RSS)

Với từng cặp Q00–Q_i (i=1..10), kết quả ổn định chỉ khi cả hai SQL chạy thành công, cả hai projection đều hợp lệ theo cùng C_g, và hai tập dòng sau khi căn cột bằng nhau.

~~~text
s[g,i] = 1 khi hai điều kiện trên cùng đúng; nếu không thì s[g,i] = 0
M_RSS = số cặp có hai outcome xác định (tối đa 500)
RSS = 100 × tổng s[g,i] / M_RSS
~~~

Hai SQL cùng trả một kết quả sai vẫn có thể có RSS=1 nếu projection hợp lệ. Nếu một SQL thành công nhưng thiếu/thừa/trùng cột thì cặp có RSS=0. Lỗi SQL, timeout hoặc không sinh SQL là outcome xác định và cho RSS=0. Pair có lỗi hạ tầng chưa khôi phục được là UNKNOWN và bị loại khỏi mẫu số. Nếu M_RSS=0 thì RSS là N/A.

### Correctness Agreement (CA)

CA là metric phụ đo hai câu trong cặp cùng đúng hoặc cùng sai; không đo kết quả SQL có nhất quán hay không.

~~~text
M_CA = số cặp Q00–Q_i có hai correctness outcome xác định
CA = 100 × số cặp có cùng trạng thái đúng/sai / M_CA
~~~

Hai câu cùng sai, kể cả cùng lỗi SQL, có thể làm CA=1. Không dùng CA thay cho RSS hoặc EX.

### Robust EX (All) và Pairwise Robust Accuracy

~~~text
K_G = số group có đủ 11 outcome xác định (tối đa 50)
RobustEX_All = 100 × số group mà cả Q00–Q10 đều có y=1 / K_G

M_PRA = số cặp Q00–Q_i có hai outcome xác định (tối đa 500)
PRA = 100 × số cặp mà cả Q00 và Q_i đều có y=1 / M_PRA
~~~

Lỗi SQL, timeout, không sinh SQL hoặc projection sai làm câu đó sai; group không đạt Robust EX nếu có ít nhất một câu sai. Lỗi hạ tầng chưa khôi phục khiến group chưa đầy đủ và bị loại khỏi K_G, đồng thời phải báo riêng. Q00 xuất hiện trong 10 cặp nên các cặp có phụ thuộc; không xem 500 cặp là quan sát độc lập.

### Bảng phân biệt metric

| Tình huống | EX của từng câu | RSS cặp | CA cặp | Robust EX |
|---|---:|---:|---:|---:|
| Q00 và Q_i đúng, cùng projection và cùng kết quả | 1, 1 | 1 | 1 | Có thể đạt nếu 11 câu đều đúng |
| Hai SQL trả cùng dữ liệu sai, projection đều hợp lệ | 0, 0 | 1 | 1 | Không đạt |
| Dữ liệu bằng nhau nhưng một SQL trả thêm cột | 0 cho câu sai projection | 0 | Tùy correctness của cặp | Không đạt |
| Cột giống nhau nhưng thứ tự cột khác | Theo dữ liệu sau khi căn cột | Có thể là 1 | Theo correctness | Không bị trượt chỉ vì thứ tự |
| Một SQL lỗi/timeout/không sinh SQL | 0 | 0 cho cặp liên quan | So trạng thái đúng/sai nếu outcome xác định | Không đạt |
| Lỗi hạ tầng chưa khôi phục | Không xác định | Không tính cặp liên quan | Không tính cặp liên quan | Group incomplete |

## 11. SQL Comparator và các trường hợp biên

Comparator phiên bản **named-fields-order-insensitive-v1** có hai bước. Bước đầu xác minh projection theo hợp đồng của Intent; bước sau căn cột hợp lệ vào thứ tự chuẩn rồi dùng so sánh tập dòng. Phần so tập dòng giữ semantics BIRD: không xét thứ tự dòng và bỏ qua số dòng trùng. Kiểm tra projection theo tên và ý nghĩa trường là phần mở rộng riêng của IS6002, vì vậy không gọi toàn bộ comparator mới là evaluator EX nguyên bản của BIRD.

| Trường hợp | Quy tắc | Kết quả mong đợi |
|---|---|---|
| Thứ tự dòng khác | Bỏ qua thứ tự dòng | Cùng tập dòng thì bằng |
| Dòng trùng lặp | Set semantics bỏ số lần lặp, tương thích comparator BIRD | `[(1,), (1,)]` và `[(1,)]` bằng; đây là giới hạn đã biết |
| Thứ tự cột khác | Căn cột theo tên trường chuẩn trước khi so | Cùng giá trị theo tên trường thì bằng |
| Tên cột khác nhưng bí danh đã khai báo cho Intent | Ánh xạ bí danh sang trường chuẩn | Có thể bằng; artifact phải ghi bí danh đã dùng |
| Tên cột khác, không có bí danh | Không đoán ý nghĩa theo giá trị | Projection sai, EX=0 |
| Thiếu cột | Projection sai | EX=0, RSS của cặp liên quan bằng 0 |
| Có cột thừa | Projection sai | EX=0, RSS của cặp liên quan bằng 0 |
| Tên cột trùng hoặc nhiều tên cùng ánh xạ vào một trường | Projection mơ hồ/sai | EX=0 |
| Sai số cột trong dòng hoặc thiếu metadata tên cột | Không thể căn chỉnh đáng tin cậy | Projection sai; ghi lỗi comparator |
| Kiểu dữ liệu | Không tự ép kiểu hay làm tròn | Chuỗi `'1'` khác số `1`; hành vi tương đương số nguyên/số thực theo kiểu giá trị Python/SQLite được ghi nhận |
| NULL | Giữ nguyên `None` sau khi đọc SQLite | NULL bằng NULL; NULL khác 0 |
| Kết quả rỗng | Vẫn kiểm tra tên và số cột dù không có dòng | Hai kết quả rỗng chỉ bằng khi cả projection đều hợp lệ |
| Ranking/top-k | Không xét thứ tự dòng; kiểm tra tập thành viên và cột hạng nếu Intent yêu cầu | Thiếu cột hạng hoặc sai thành viên là sai; thứ tự hiển thị không được chấm |
| SQL error/timeout/no SQL | Outcome xác định, không có kết quả hợp lệ | EX=0; RSS=0 cho cặp liên quan |
| Lỗi hạ tầng | UNKNOWN sau retries theo D13 | Loại khỏi denominator tương ứng, báo missingness |
| SQL chuẩn lỗi/timeout | Lỗi benchmark | Chặn đánh giá item; sửa theo version policy trước khi chạy |

Các ví dụ cần giữ trong kiểm tra comparator: (1) cùng dữ liệu nhưng đổi thứ tự cột phải đạt sau căn chỉnh; (2) cùng giá trị nhưng tên trường sai phải trượt; (3) thêm cột phải trượt; (4) bỏ một cột phải trượt; (5) tên bí danh được khai báo phải được ghi nhận và căn chỉnh; (6) kết quả rỗng phải kiểm tra cả metadata cột; (7) duplicate rows vẫn được bỏ qua theo set semantics; (8) NULL, chuỗi/số, ranking ties và SQL error phải có kết quả xác định như bảng trên.

Hợp đồng trường được sinh từ projection của SQL chuẩn và FIELD_MEANINGS. Mọi hợp đồng có hash riêng. Tên trường không có mô tả, mô tả sai, hay bất đồng với Intent phải chuyển thành NEEDS_FIELD_REVIEW; không được xem hash hoặc việc SQL chuẩn chạy thành công là bằng chứng Owner đã duyệt hợp đồng. Đánh giá chính thức cần lưu trạng thái, người duyệt, ngày, lý do và hash hợp đồng được duyệt cho đủ 50 group.

Thay đổi comparator này là thay đổi protocol và mã chấm điểm. Kết quả theo comparator cũ và mới phải báo riêng; không tính lại hoặc diễn giải lại kết quả cũ như thể dùng comparator mới. Frozen config, prompt hash, code hash, comparator version và output-contract hashes phải khớp trước khi mở Official Evaluation.

## 12. SQL error, timeout, kết quả rỗng và trạng thái không xác định

| Tình huống | EX | RSS | Xử lý protocol |
|---|---:|---:|---|
| Prediction parse/runtime error | 0 | 0 cho mọi pair liên quan | Ghi error type/message đã làm sạch; giữ question trong EX denominator và pair/group có outcome xác định. |
| Model trả lời thành công nhưng không có SQL | 0 | 0 cho mọi pair liên quan | Ghi no_sql; giữ denominator. |
| Prediction timeout | 0 | 0 cho mọi pair liên quan | Dùng timeout cố định; giữ denominator. |
| GT lỗi/timeout | Không tính question/group | Chưa xác định | Benchmark defect; sửa/loại theo version và chạy lại mọi đánh giá liên quan. |
| GT hợp lệ trả 0 rows | Theo so sánh | Theo output pair | Item hợp lệ; empty/empty match; đánh giá collision bằng fixture. |
| Lỗi provider/network/hạ tầng tạm thời | Unknown | Unknown cho pair/group bị ảnh hưởng | D13: một initial attempt + tối đa hai retries bounded-backoff với cùng request/config; lưu lịch sử từng attempt. Nếu chưa khôi phục, ghi infra_error/UNKNOWN, loại khỏi denominator liên quan và báo missingness. |
| Prediction API thành công nhưng content rỗng/từ chối/no SQL | 0 | 0 cho mọi pair liên quan | Đây là outcome model, không phải infra failure. |

D8 chốt SQL execution timeout là 30 giây/query cho mọi model/question. Ghi SQL status, elapsed time và error category. Không retry SQL timeout. Provider/network timeout thuộc prediction collector và chỉ được retry khi phân loại là lỗi hạ tầng tạm thời theo D13; phải tách hai loại timeout này.

## 13. Experimental Protocol và Development/Final

### Chia split không leakage

1. Lập danh sách 50 intent độc lập và audit near-duplicate trước khi tạo 500 variants; cluster các intent gần nhau theo nghiệp vụ/template.
2. Gán toàn bộ semantic/near-duplicate cluster vào cùng split. Mọi Q0–Q10 thuộc một group, và mọi group liên quan gần nhau phải ở cùng split.
3. Chọn 10 Development groups/110 Questions và 40 Final groups/440 Questions. Đề xuất stratification 5 ERP + 5 WMS ở Dev, 20 ERP + 20 WMS ở Final; giữ nguyên quota transformation của từng group. Ghi seed, thuật toán và manifest phân bổ.
4. Nếu có thể, giữ kín Final questions, SQL và labels trước khi model/prompt freeze; nếu không, báo đây là fixed held-out split với leakage risk, không gọi là blind test.
5. Development dùng để debug pipeline. Không đổi protocol vì quan sát Final mà vẫn giữ cùng version/score; thay đổi semantic tạo version mới.

### Freeze và giữ điều kiện tương đương

- Pin benchmark, DB snapshot, schema, glossary/Evidence, prompt, evaluator, runtime, timeout và hashes.
- Pin model snapshot/provider, decoding parameters, system/user prompt, tool settings, D13 retry policy, seed nếu được hỗ trợ và model/config hash. Theo dõi provider/network timeout riêng với SQL execution timeout D8.
- Giữ mọi đầu vào trên giống nhau cho 11 Questions trong group, chỉ thay wording. Ghi thứ tự chạy; randomize/cân bằng thứ tự 550 Questions bằng seed cố định trước run.
- Chạy đúng 3 replicates đầy đủ cho mỗi model/config. Mỗi Development replicate gồm đủ 110 Questions; lưu replicate_id=1/2/3, question_id, group_id, model/config hash và attempt records. Chỉ ghép Q0–Qi trong cùng group và replicate. Báo từng replicate cùng mean/SD/range; không chọn best run.
- Tạo toàn bộ prompt từ registry, schema, glossary, business rules và field contracts trước replicate đầu tiên; dùng nguyên văn cùng prompt cho cả ba replicates và retries. Lưu SHA-256 prompt trong từng prediction record để phát hiện prompt thay đổi.
- Không thay schema, glossary hoặc prompt giữa các 11 wordings; nếu điều chỉnh thì chạy lại group và tạo run/version mới.

### Lưu kết quả

**Per-question record** tối thiểu: benchmark/version, split, group_id, question_id, role (Q0/Q1–Q10), transformation label, DB/hash, question, model snapshot/provider, config/prompt hash, prompt SHA-256, replicate/attempt/timestamp, raw response, extracted SQL, status (success/sql_error/timeout/no_sql/infra_error), executed rows/column metadata, gold verdict, duration, error details đã làm sạch, retry/cache metadata.

**Per-group record** tối thiểu: 11 question run IDs, correctness Q0–Q10, per-variant RSS/CA/PRA pair outcomes, group RSS mean, RobustEX_All, 2x2 correctness counts, status ACCEPT/revise/reject của variants, missing/infra status và replicate IDs. Giữ raw results theo quyền truy cập; aggregate phải truy nguyên được.

### Quy tắc kết quả chưa xác định

SQL error, SQL timeout và no/malformed SQL trong phản hồi model hợp lệ là outcome đã định nghĩa và không được retry. Theo D13, chỉ lỗi hạ tầng tạm thời mới được retry: một initial attempt và tối đa hai bounded-backoff retries với cùng request/config; retries không phải replicates. Nếu vẫn lỗi, ghi UNKNOWN/infra_error, lưu attempts, báo missingness và từng denominator; không chấm 0/1 hoặc loại mẫu dựa trên correctness. D9 yêu cầu ba replicates đầy đủ mỗi model/config. Phân tích cluster theo 50 Semantic Groups; Questions và pairs không phải quan sát độc lập.

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

D1–D7, D10 và D11 được Benchmark Owner phê duyệt ngày 2026-11-09; D8, D9 và D13 được phê duyệt ngày 2026-11-10. D12 APPROVED ngày 2026-11-17; D14 vẫn PROPOSED. Status và rationale được ghi tại Decision Review; phê duyệt này không bao gồm các quyết định khác.

| Decision ID | Recommended value | Status | Decision owner / approver | Date | Rationale (confirm or replace at decision) |
|---|---|---|---|---|---|
| D1 | 10 Development groups/110 Questions; 40 Final groups/440 Questions; chia ở cấp group/near-duplicate cluster | APPROVED | Benchmark Owner | 2026-11-09 | Tránh rò rỉ wording cùng intent; mọi Q0–Q10 trong group ở cùng split và near-duplicate clusters phải được kiểm tra trước khi khóa split. |
| D2 | 25 ERP groups + 25 WMS groups; mỗi split cân bằng 5/5 Dev và 20/20 Final | APPROVED | Benchmark Owner | 2026-11-09 | Cân bằng hai domain trong toàn tập và trong từng split để giảm nguy cơ kết quả bị chi phối bởi một database. |
| D3 | Synthetic deterministic, không PII thật; public data nếu license/provenance rõ | APPROVED | Benchmark Owner | 2026-11-09 | Ưu tiên dữ liệu tổng hợp xác định để tái lập; chỉ dùng nguồn công khai bổ sung khi license và provenance được ghi lại. |
| D4 | Định hướng hai SQLite DB; Business Rules/Glossary được kiểm tra trong Bước 2A | APPROVED (định hướng) | Benchmark Owner | 2026-11-09 | Sau đó, các synthetic rules R-01…R-11 được xác nhận riêng cho logic design ngày 2026-11-09; không phải chuẩn ngành. |
| D5 | Schema context/Evidence giống nhau cho mọi 11 Questions trong group | APPROVED | Benchmark Owner | 2026-11-09 | Giữ dữ liệu và thông tin nền giống nhau giữa Q0–Q10 trong cùng group để cô lập wording variation. |
| D6 | Chính xác 2 empty-result intents: 1 ERP và 1 WMS | APPROVED | Benchmark Owner | 2026-11-09 | Giữ một trường hợp empty có chủ đích cho mỗi database; mỗi intent cần fixture/counterexample kiểm tra false match. |
| D7 | EX contract-aware: kiểm tra đúng tập trường theo Intent; căn cột theo tên và bỏ qua thứ tự cột; chỉ chấp nhận alias khai báo riêng; sau đó dùng set comparison cho các dòng, bỏ qua thứ tự dòng và duplicate rows | Giữ ý nghĩa projection rõ ràng mà không đánh lỗi chỉ vì thứ tự cột; duy trì set semantics cho kết quả | APPROVED (sửa đổi) | Benchmark Owner | 2026-11-18 | Thay comparator D7 ngày 2026-11-09. EX mới là mở rộng IS6002 từ phép so set rows của BIRD; không so trực tiếp kết quả cũ. Cần hash và human review cho từng field contract. |
| D8 | SQL execution timeout cố định 30 giây/query; ghi status, elapsed time, error category; không retry SQL timeout | APPROVED | Benchmark Owner | 2026-11-10 | Cùng giới hạn cho mọi câu; SQL timeout là model outcome, không phải lỗi hạ tầng được retry. |
| D9 | Đúng 3 replicates đầy đủ/model/config; ghép theo replicate_id 1/2/3; báo từng replicate và mean/SD/range | APPROVED | Benchmark Owner | 2026-11-10 | Development có 330 predictions/model/config; không gộp run hoặc chọn best run. |
| D10 | Một Benchmark Owner thực hiện single-human validation; AI/Codex hỗ trợ critique/oracle; công khai không có independent human annotation | APPROVED | Benchmark Owner | 2026-11-09 | Chấp nhận quy trình một người; AI/Codex chỉ hỗ trợ kiểm tra kỹ thuật, không được tính là annotator độc lập hay double-blind review; công bố common-method bias. |
| D11 | Competency quota §6 (8/8/8/6/8/4/4/4); complexity ERP 8/12/5, WMS 8/12/5; mỗi group 3 Lexical, 3 Syntactic, 2 Reordering, 2 Mixed | APPROVED | Benchmark Owner | 2026-11-09 | Khóa coverage theo database, competency và taxonomy trước authoring; mọi biến thể vẫn phải qua semantic-slot review. |
| D12 | 0.x pilot; Final giữ kín khi khả thi, nếu không ghi exposure/leakage | APPROVED | Benchmark Owner | 2026-11-17 | Giữ đúng mức tuyên bố pilot; ghi rõ nếu Final đã bị lộ. |
| D13 | Một initial attempt + tối đa 2 bounded-backoff retries chỉ cho lỗi hạ tầng tạm thời; giữ request/config; cluster theo Semantic Group | APPROVED | Benchmark Owner | 2026-11-10 | Không retry SQL error/timeout, malformed/missing SQL trong phản hồi hợp lệ hoặc kết quả sai. Retry không phải replicate; lưu attempts, error categories, UNKNOWN và denominators. |
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
| Set semantics bỏ duplicate và bỏ qua thứ tự dòng; hợp đồng đầu ra có thể được mô tả sai | Có thể bỏ sót lỗi multiplicity hoặc chấm sai nếu field contract không khớp Intent | Công khai giới hạn set comparison; review và hash riêng từng contract; kiểm tra ranking policy. Không tuyên bố EX_bag đã được tính nếu chưa triển khai metric đó. |
| Empty outputs quá nhiều | Collision giả giữa query sai | Empty quota có chủ đích và fixtures đối kháng. |
| Model/provider drift hoặc stochasticity | Khó tái lập và quy nguyên nhân | Pin snapshot/config; repeats theo protocol. |
| Leakage từ Final/schema/template | Điểm không phản ánh generalization | Group/cluster split, giữ kín khi khả thi, ghi exposure. |
| Single-human/common-method bias | Cùng người xác định intent, expected outputs, SQL và kết luận; không đo inter-annotator agreement | Công khai hạn chế; tách expected-output derivation khỏi SQL run; fixtures/oracle và Domain Owner check khi có; AI không tính là reviewer độc lập. |
| RSS cao nhưng cả hai sai | Dễ nhầm consistency với correctness | Luôn báo EX, CA và Robust EX cùng RSS. |
| LLM judge bias | Tự củng cố lỗi model | Judge chỉ triage; quyết định cuối do người. |
| Infra failures bị tính sai | Denominator thiên lệch | Phân loại infra_error; retry cố định, báo missingness. |

## 18. Trạng thái Bước 2A và điều kiện cho các bước tiếp theo

D1–D7, D10 và D11 được phê duyệt ngày 2026-11-09; D8, D9 và D13 ngày 2026-11-10. D12 APPROVED ngày 2026-11-17; D14 vẫn PROPOSED. Các phê duyệt không vượt ra ngoài quyết định đã nêu.

D4 phê duyệt định hướng hai database; simulation rules R-01–R-11 được chốt cho thiết kế logic và không phải chuẩn ngành. Bước 2A và 2B đã nghiệm thu theo provenance riêng. Benchmark Owner đã duyệt 40 Final groups, 440 Final questions và 10 Development Q00 hiện hành; các quyết định được lưu trong registry/Validation Records. Registry và cấu hình chạy đã đóng băng. Kiểm tra mock offline xác minh đủ 3 × 440 câu Final, không gọi API. Official Evaluation thật vẫn cần xác nhận riêng về chi phí/lượt gọi; D14 vẫn PROPOSED.
## Phụ lục A. Phân loại phương pháp

- **Kế thừa BIRD:** database-grounded task, schema/data context, Evidence khi cần, kiểm tra SQL validity và text/knowledge/SQL alignment, execution-based EX.
- **Tham khảo:** Spider-Syn cho biến thiên từ vựng; Dr.Spider cho perturbation benchmark.
- **Đề xuất IS6002:** pilot tiếng Việt, ERP/WMS, 50 Semantic Groups × 11 Questions, RSS/CA/Robust EX/PRA và single-human validation có AI hỗ trợ. Cách làm này không tương đương independent/double-blind annotation; công bố rõ common-method bias và không đo inter-annotator agreement. Các metric mở rộng cần được trình bày là đề xuất của nhóm và không tuyên bố độc quyền nếu chưa rà soát literature.

**Bước 1 dừng tại đặc tả này.** Chưa tạo Questions, database, seed data hoặc SQL benchmark; không sửa Python source và không gọi LLM API.


## Trạng thái triển khai và kiểm duyệt hiện tại — 2026-11-17






















### Cập nhật trạng thái ngày 2026-11-17

Benchmark Owner đã chấp nhận wording cho 10 câu Q00 Development và phê duyệt D12. D14 vẫn PROPOSED. Cấu hình chạy được đóng băng riêng; việc đóng băng không cấp phép gọi API hoặc công bố kết quả.
