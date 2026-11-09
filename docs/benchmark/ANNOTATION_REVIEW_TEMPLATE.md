# BIRD-VN-Robust-50 — Group Validation Record

**Mẫu v0.3.0 Draft.** Tạo đúng một Validation Record cho mỗi Semantic Group/ground-truth (50 records). Một group có Q0 + Q1–Q10; tất cả dùng chung một canonical SQL. Đây là single-human validation; AI/oracle không phải annotator độc lập.

## 1. Định danh và Intent Card

| Trường | Giá trị |
|---|---|
| Benchmark/version, group_id, db_id, split | |
| Competency / complexity | |
| DB/schema/glossary hashes | |
| Người phụ trách / ngày | |
| Intent Card ID/version/hash và nguồn nghiệp vụ | |
| Validation status | DRAFT / NEEDS DOMAIN INPUT / VALIDATED / BLOCKED |
| Assumptions / unresolved issue | |

| Intent slot | Định nghĩa đã khóa |
|---|---|
| Entity, output grain, projection/measures/units | |
| Filters/status, grouping/aggregation | |
| Time boundaries/timezone, order/ties | |
| NULL/zero/absence/empty, business assumptions | |

Domain Owner confirmation (nếu có); nếu không có, ghi self-validation và nguồn business rules:

## 2. Ground-truth SQL validation

Canonical SQL source: HUMAN / CODEX-ASSISTED / OTHER  
SQL artifact/hash/date:  
Tool/model/version, prompt/log reference và mức hỗ trợ:  
Người phụ trách đã đọc, tự kiểm tra và chịu trách nhiệm cho SQL cuối: YES / NO

Expected outputs được suy ra từ rules/fixture records độc lập với canonical SQL và ghi trước khi chạy SQL. “Độc lập” là cách suy ra khác với query execution, không phải annotator khác.

| Fixture/case | Input records/values | Expected result/derivation hoặc artifact hash | Expected output freeze time | SQL status/actual result | Match? |
|---|---|---|---|---|---|
| Main snapshot | | | | | |
| Boundary date/status | | | | | |
| NULL/zero/absence/empty | | | | | |
| Duplicate/fan-out | | | | | |
| Tie/top-k (nếu áp dụng) | | | | | |
| Counterexample | | | | | |

Manual logic checklist (PASS / FAIL / N/A; giải thích mọi FAIL/N/A):  
Grain/projection:  
Joins/fan-out:  
Filters/time boundaries:  
Aggregation/count/DISTINCT:  
NULL/empty/ties/order/units:

Alternative check: ALTERNATIVE SQL / PYTHON ORACLE / MANUAL DERIVATION / NONE  
Artifact/hash, nguồn và cách độc lập triển khai; nếu NONE, ghi lý do:

SQLite/Python/runner version, timeout/resources, DB hash, execution date:  
Execution artifact paths/hashes và open defect:

## 3. Semantic review của 10 variants

Q0 ID/text:  
Mỗi Q1–Q10 cần được kiểm tra rõ các slots: entity, output grain, projection, filters, grouping, aggregation, time boundaries, units, NULL/absence và business assumptions. Ghi PASS/FAIL và ACCEPT/REVISE/REJECT riêng; chỉ ACCEPT variants sau review mới được tính vào release.

| Q ID | Primary type | Secondary tags | Question text/reference | Slot checklist PASS/FAIL + differences | Status | Rationale hoặc revision |
|---|---|---|---|---|---|---|
| Q1 | Lexical | | | | | |
| Q2 | Lexical | | | | | |
| Q3 | Lexical | | | | | |
| Q4 | Syntactic | | | | | |
| Q5 | Syntactic | | | | | |
| Q6 | Syntactic | | | | | |
| Q7 | Reordering | | | | | |
| Q8 | Reordering | | | | | |
| Q9 | Mixed | | | | | |
| Q10 | Mixed | | | | | |

Status: **ACCEPT / REVISE / REJECT**. Mọi REVISE phải có revised text/version và được review lại. Không phát hành nếu còn trạng thái ngoài ACCEPT.

## 4. AI-assisted challenge log

Tool/model/version/date và prompt/log reference:  

| AI suggestion/counterexample | Human cross-check bằng Intent Card/fixture/oracle | Accepted / rejected / unresolved và lý do |
|---|---|---|
| | | |

AI output, multiple calls và alternative oracle không tạo independent human annotation, reviewer consensus hoặc inter-annotator agreement.

## 5. Kết luận, provenance và release gate

Ground-truth status: **VALIDATED / BLOCKED**  
Q0–Q10 semantic review: **10/10 ACCEPT? YES / NO**  
Expected outputs, manual review và execution/oracle evidence nhất quán: **YES / NO / UNKNOWN**  
Lý do, limitation, blocker:  
Người phụ trách xác nhận / ngày:

| Version/date | Thay đổi | Lý do/evidence |
|---|---|---|
| | | |

**Giới hạn bắt buộc công bố:** validation do một người thực hiện; không phải double-blind/independent double annotation, không đo inter-annotator agreement và có common-method bias.
