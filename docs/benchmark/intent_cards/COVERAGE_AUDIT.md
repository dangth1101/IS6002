# BIRD-VN-Robust-50 — Intent Coverage Audit (Draft)

| Thuộc tính | Giá trị |
|---|---|
| Phiên bản | 0.1.0 — Draft, 2026-11-09 |
| Trạng thái | Chưa phê duyệt; rà soát snapshot chỉ đọc |
| Snapshot | `benchmark_data/physical/erp_sales.sqlite`, `wms_inventory.sqlite` |
| Bằng chứng kiểm soát | `build_manifest.json`, `validation/*_validation.json`, `fixture_test_results.json`, `all_test_results.json` |

## Kết luận audit

- Hai file snapshot có trong workspace. Hash manifest được đối chiếu với hash validation evidence: ERP `347c0e7b663d74c740c6b1fba4a2b89a6ca21beeb4148bd8bff41ed3a4ca888b`; WMS `c55c41e8755dccd1e0d77aaaf86b0dcf2895b75ae8a8d5b1891774e26cf589d5`. Các invariant hiện có trong evidence báo PASS. Đây là kiểm tra tính toàn vẹn của snapshot đã tạo, không phải phê duyệt Intent Cards.
- `SUPPORTED`: bảng/cột và dữ liệu snapshot hiện có đủ tạo kết quả khác rỗng/đúng dạng và có ít nhất một đối chứng tự nhiên quan trọng. Vẫn cần validation SQL sau này.
- `NEEDS FIXTURE`: schema có đường dữ liệu, nhưng snapshot không chứa một biên/counterexample quan trọng hoặc hiện tại chỉ một nhánh kết quả; phải chuẩn bị fixture kiểm chứng trước canonical SQL. Không sửa database tại bước này.
- `BLOCKED`: schema/seed không thể biểu diễn semantics cốt lõi. Không có card nào bị kết luận BLOCKED trong audit tĩnh; các fixture bắt buộc chưa được tạo nên nhiều card vẫn NEEDS FIXTURE.

## Audit từng Intent

| Intent | Snapshot evidence / schema path | Phân biệt đúng–sai hiện có | Thiếu fixture / rủi ro cụ thể | Audit |
|---|---|---|---|---|
| ERP-EF-01 | `sales_orders`: 48 confirmed, 12 draft, 12 cancelled | Status cohorts khác nhau | — | SUPPORTED |
| ERP-EF-02 | `sales_orders.order_date`, `sales_rep_id`; toàn bộ 72 `created_at` khác `order_date`; 6 confirmed thiếu rep | Sai cột ngày và NULL filter có thể lộ | Fixture đúng boundary 01/01 và exclusive end | NEEDS FIXTURE |
| ERP-EF-03 | 12 products; 1 NULL category; categories hiện hữu | NULL category phân biệt với category hợp lệ | Fixture empty category filter nếu dùng ID không tồn tại | SUPPORTED |
| ERP-EF-04 | 27 delivered shipment chỉ tới 2025-06; không có cohort delivery Q4/2025 | Status có cohort nhưng empty kết quả do delivery date | Positive Q4 delivered order >100m, below-threshold Q4 order, and delivery-time boundaries | NEEDS FIXTURE |
| ERP-AG-01 | 24 customers, 3 segment × 8 | Các segment có số lượng khác nhau | Duplicate join fixture để phân biệt COUNT(*) và COUNT DISTINCT | NEEDS FIXTURE |
| ERP-AG-02 | confirmed order lines; 33 zero-net lines; total order value 592,736,375 VND | Zero line và status loại trừ hiện diện | Boundary line/date fixture; xác nhận discount/null behavior từ schema | NEEDS FIXTURE |
| ERP-AG-03 | 72 orders, 33 zero-net lines | Có nhiều dòng/order; order-level denominator cần thiết | Fixture chứng minh AVG(line) khác AVG(order total), và empty cohort | NEEDS FIXTURE |
| ERP-AG-04 | 44 tx: 36 posted captures, 6 pending captures, 2 posted refunds | Posted/pending/refund hiện diện | Nhiều payment/order + zero-net + local time boundary để bắt fan-out | NEEDS FIXTURE |
| ERP-GB-01 | Status counts 48/12/12 | Mỗi status cohort hiện diện | — | SUPPORTED |
| ERP-GB-02 | 4 customer không có confirmed order; order lines 216 | LEFT JOIN/absence có đối chứng | Multi-line orders chống fan-out khi tổng hợp amount | NEEDS FIXTURE |
| ERP-GB-03 | rep NULL=6; rep1=9 và rep3=9 | NULL bucket và tie hiện diện | — | SUPPORTED |
| ERP-GB-04 | Delivered events Apr–Jun 2025; local month conversion | Revenue theo thời gian có dữ liệu | UTC instant đổi tháng local và month-with-no-rows | NEEDS FIXTURE |
| ERP-RK-01 | Delivered orders/revenue hiện diện | Có cohort ranking | Tie đúng cutoff top-5 chưa chứng minh bởi evidence hiện tại | NEEDS FIXTURE |
| ERP-RK-02 | Snapshot có 12 sản phẩm thuộc EA/KG/L; separate-unit output trên snapshot | Temporary copy tạo tie đúng rank 3 trong EA và giữ cohort KG/L riêng | `dev_fixture_validation.json`: unit partition + rank-3 tie PASS; zero-sold excluded per intent | SUPPORTED |
| ERP-RK-03 | Posted captures/refunds, payment/customer links | Net cash cohort có refunds | Equal maxima, pending decoy, no-cash customer fixture | NEEDS FIXTURE |
| ERP-JN-01 | Customers + orders, 4 customer không confirmed order | Absence và parent retention hiện diện | — | SUPPORTED |
| ERP-JN-02 | 216 lines; order-line-product FK path; snapshot có confirmed/draft/cancelled parents | Temp-copy control chứng minh non-confirmed lines không lọt; PK-corrupt duplicate là ngoài miền dữ liệu hợp lệ | `dev_fixture_validation.json`: candidate/oracle exact-set PASS; invalid duplicate-line case remains optional | SUPPORTED |
| ERP-JN-03 | 27 delivered; lines/customer/product path | Revenue cohort có dữ liệu | Multi-payment/order case để phát hiện fan-out; expected group checks | NEEDS FIXTURE |
| ERP-JN-04 | 4 returns, 2 received + 2 rejected; return-line/order links | Partial return/rejected contrast present | Same SKU multiple lines, full RECEIVED quantity, quantity upper bound | NEEDS FIXTURE |
| ERP-TM-01 | `order_date` from 2024-12-16 to 2026-02-28 | Nhiều ngày trong/ngoài quý | Exact `[start,end)` boundary | NEEDS FIXTURE |
| ERP-TM-02 | 27 delivered timestamps Apr–Jun | Temp copy có instant trước/tại start, trước/tại exclusive end; local date bins kiểm tra | `dev_fixture_validation.json`: four boundary assertions + SQL/oracle PASS; NULL event excluded | SUPPORTED |
| ERP-NA-01 | 4 customers without confirmed order | Anti-join has true and false cases | Ensure draft/cancelled-only customer not mistaken for confirmed | NEEDS FIXTURE |
| ERP-NA-02 | 12 orders without posted cash; pending capture records exist | No-posted vs pending-only distinction possible | Posted capture/refund net-zero order fixture | NEEDS FIXTURE |
| ERP-CD-01 | Validation totals: order value 592,736,375 vs recognized revenue 352,856,000 VND | Different measures/cohorts differ materially | Fixture crossing order date and delivery date periods to expose common-date filter | NEEDS FIXTURE |
| ERP-CD-02 | Posted capture/refund and pending transactions; method columns present | Types/status present | One method with both capture/refund + pending decoy; confirm no synthetic missing-method rows | NEEDS FIXTURE |
| WMS-EF-01 | 46 docs include posted, draft, cancelled | Document statuses differ | — | SUPPORTED |
| WMS-EF-02 | 18 products; six each EA/KG/L; NULL category exists | Unit filter and NULL category | — | SUPPORTED |
| WMS-EF-03 | 90 movements, 8 locations, posted events | Movement/location relation populated | Same SKU/location opposite legs and cutoff | NEEDS FIXTURE |
| WMS-EF-04 | 2 QUARANTINE locations; no quarantine movements | Intended result currently empty | Positive quarantine collision + zero-balance and inactive-location controls; required before use | NEEDS FIXTURE |
| WMS-AG-01 | 6 posted receipts and 1 draft receipt | Status/type contrast | Multi-line receipt to detect inflated COUNT | NEEDS FIXTURE |
| WMS-AG-02 | 20 posted shipments; signed movements; KG cohort exists | Temp copy thêm negative adjustment và transfer trên KG SKU để kiểm tra type filter | `dev_fixture_validation.json`: decoys excluded, candidate/oracle exact-set PASS | SUPPORTED |
| WMS-AG-03 | On-hand validator reports 36 positive product-location balances; no zero-with-history | Positive balance cohort present | Zero-with-history and no-history location; confirm AVG inclusion denominator | NEEDS FIXTURE |
| WMS-AG-04 | Schema supports balances by product-location; current positive balances | Grain exists | Fractional rational mean fixture; zero/history vs no-history | NEEDS FIXTURE |
| WMS-GB-01 | 46 documents with multiple statuses | Status grouping supported | Ensure count document PK vs rows | NEEDS FIXTURE |
| WMS-GB-02 | 57 positive and 33 negative movement rows; types and units varied | Sign/type/unit present | Net-zero same group, avoid adding different units | NEEDS FIXTURE |
| WMS-GB-03 | Supplier receipt counts 5,1,0,0 | Parent no-child groups present | Multi-line docs to catch line-counting | NEEDS FIXTURE |
| WMS-GB-04 | 2 warehouses, movements with transfers | Cross-warehouse aggregation possible | Same timestamp `posted_seq`, transfer legs, multi-location rollup and unit split | NEEDS FIXTURE |
| WMS-RK-01 | WH-SG EA max tie: product 13 and 16 at 500000 milli-units | Actual tie at max | Ranking comparator must include both; non-EA competitor fixture if scope changes | SUPPORTED |
| WMS-RK-02 | Supplier posted receipt counts 5,1,0,0 | Supplier cohort and zero counts | Tie at top-3 boundary | NEEDS FIXTURE |
| WMS-RK-03 | 8 locations; current picking/quarantine have no movement | Location dimension present | Third-place tie, zero-with-history; clarify eligibility of STORAGE only | NEEDS FIXTURE |
| WMS-JN-01 | Six posted receipts have supplier relationship | FK path and status present | Ensure no line join duplicates | SUPPORTED |
| WMS-JN-02 | 80 document lines and product FK path | Line/product path populated | Fixture planned quantity deliberately differs from posted movement | NEEDS FIXTURE |
| WMS-JN-03 | 90 movements with location and warehouse links | Path is populated | Transfer paired legs and aggregation without unit/fanout issues | NEEDS FIXTURE |
| WMS-JN-04 | 12 posted transfers / 24 legs; pair invariants pass | Temp copy thêm transfer có cùng SKU/quantity/timestamp nhưng distinct identity; cả legs phải giữ nguyên | `dev_fixture_validation.json`: candidate/oracle exact-set PASS; corrupted-pair case thuộc validator optional suite | SUPPORTED |
| WMS-TM-01 | business_date range 2024-11-02..2025-01-31 | January cohort exists | business_date differs from posted_at at boundary | NEEDS FIXTURE |
| WMS-TM-02 | UTC event timestamps Jan–Mar 2025; 4 documents share timestamp with posted_seq | Same-time sequence is represented | Exact cutoff and atomic transfer batch evidence | NEEDS FIXTURE |
| WMS-NA-01 | Products exist; no movement at PICKING locations | Anti-join at location scope yields many rows, unlike global no-movement | Add a picking movement collision to prove location scope; confirm active-location filter | NEEDS FIXTURE |
| WMS-NA-02 | No zero-with-history balances; all 36 recorded balances positive | Schema can represent aggregates but snapshot lacks zero case | Add zero-with-history and no-history pair; otherwise cannot validate distinction | NEEDS FIXTURE |
| WMS-CD-01 | 20 posted shipments + other movement types | Conditional type measures can differ | Same product/unit with shipment and non-shipment; pending/cancelled decoy | NEEDS FIXTURE |
| WMS-CD-02 | 80 lines/90 movements; 2 non-posted docs retain planned rows; transfer source/destination legs | Temp copy covers DRAFT/CANCELLED zero execution and POSTED RECEIPT/SHIPMENT/ADJUSTMENT/CUSTOMER_RETURN/TRANSFER invariants | `dev_fixture_validation.json`: statuses, planned/executed and source-only transfer assertions PASS | SUPPORTED |

## Near-duplicate review and split leakage

Clusters are based on same business entity, measure, cohort and output grain, not merely reuse of tables or competency. Proposed split keeps each cluster on one side:

| Cluster | Related intents | Proposed split | Assessment |
|---|---|---|---|
| ERP customer revenue | ERP-GB-02, ERP-RK-01, ERP-JN-03 | Final | Same broad measure family; grain differs (per customer total, top customers, customer-category breakdown), keep together conservatively |
| ERP delivered time/revenue | ERP-GB-04, ERP-RK-01, ERP-JN-03, ERP-CD-01 | Final | Shared delivered cohort/revenue semantics; keep together to prevent template leakage |
| ERP cash/refund | ERP-AG-04, ERP-RK-03, ERP-NA-02, ERP-CD-02, ERP-JN-04 | Final | Shared payment/refund relations; outputs differ but conservative cluster split |
| ERP order-date cohort | ERP-EF-02, ERP-AG-02, ERP-AG-03, ERP-TM-01 | Final | Same order-date cohort family; all are kept in Final to avoid train/test template leakage |
| WMS receipt/supplier | WMS-AG-01, WMS-GB-03, WMS-RK-02, WMS-JN-01, WMS-JN-02 | Final | Receipt/supplier family kept wholly Final; GB03 is no longer in proposed Development set. |
| WMS stock/on-hand | WMS-EF-04, WMS-AG-03, WMS-AG-04, WMS-GB-04, WMS-RK-01, WMS-RK-03, WMS-NA-02, WMS-CD-01 | Final | Same balance reconstruction family, deliberately kept together |
| WMS posted event time | WMS-TM-02, WMS-GB-04, WMS-CD-01, WMS-JN-03 | Final | Same posted-event/cutoff family; all are kept in Final |

**Leakage finding:** no exact duplicate intent is apparent. The proposed Development set avoids the identified conservative near-duplicate clusters: ERP order-date/revenue/cash families and WMS receipt/on-hand/posted-event-time families all remain wholly Final. Dev contains unrelated query shapes even where tables overlap (e.g. WMS document listing vs unit filter vs transfer-leg integrity). The cluster definitions and split IDs still require Owner review before freeze.

## Quota check

| Domain | Entity filter | Count/Sum/Avg | Group | Ranking | Join | Time | NULL/absence | Conditional | Simple/Moderate/Challenging |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ERP | 4 | 4 | 4 | 3 | 4 | 2 | 2 | 2 | 8/12/5 |
| WMS | 4 | 4 | 4 | 3 | 4 | 2 | 2 | 2 | 8/12/5 |
| Total | 8 | 8 | 8 | 6 | 8 | 4 | 4 | 4 | 16/24/10 |

Competency counts and per-domain complexity totals agree with `COVERAGE_MATRIX.md`. Assignment of complexity *within* a competency is a card-level proposal and may differ from the matrix's illustrative cross-tab; every card still needs rubric review after exact semantics and expected SQL shape are frozen.

## Open issues before card approval

1. **Development split:** review/approve the proposed Dev IDs and the conservative cluster boundaries before freeze.
2. **“Exactly two empty intents” interpretation:** ERP-EF-04 and WMS-EF-04 are the only *designed* empty-result intents. Snapshot may incidentally make other filters empty. WMS-NA-01 is designed to be nonempty (PICKING-scoped anti-join), but must be confirmed against exact active location rows.
3. **Fixture capability:** many intents need boundary/tie/fan-out/zero-history fixtures. The user forbids snapshot modification here; fixtures are a later approved data work item and coverage must remain `NEEDS FIXTURE` until evidence exists.
4. **Snapshot governance:** Benchmark Owner separately confirmed B2B acceptance; hashes remain frozen. Keep fixture proposals isolated and do not rebuild/alter either accepted snapshot.
5. No intent is `BLOCKED` at schema level based on the supplied design and physical paths. No card is approved; Development IDs and cluster boundaries remain proposed until Owner review.
