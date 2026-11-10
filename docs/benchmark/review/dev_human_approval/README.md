# BIRD-VN-Robust-50 — Development Human Approval Package

**Trạng thái:** Draft for human review. Không có Intent, SQL, expected output hay question nào được tự động phê duyệt.

## Files

- [Bảng Intent/SQL 10 groups](DEVELOPMENT_INTENT_SQL_REVIEW_10.csv): mỗi dòng chứa candidate SQL, semantic slots, expected/actual hashes, fixture evidence và mục Owner cần xác nhận.
- [ERP Development Questions (55)](ERP_DEVELOPMENT_QUESTIONS_55.csv): Q0–Q10 cho 5 ERP groups.
- [WMS Development Questions (55)](WMS_DEVELOPMENT_QUESTIONS_55.csv): Q0–Q10 cho 5 WMS groups.
- [Paraphrase audit v5 và hàng đợi Owner](DEV_V5_PARAPHRASE_AUDIT.md): 110 câu đã đối chiếu; hai giới hạn taxonomy còn mở.
- [Audit từng câu (110)](DEV_V5_PARAPHRASE_AUDIT.csv) và [before/after (82 sửa đổi)](DEV_V4_TO_V5_CHANGELOG.csv).
- [CSV v4 lưu đối chiếu](archive/dev-v4/) và [audit lịch sử v2–v4](DEV_PARAPHRASE_QUALITY_AUDIT.md).
- [Validation Records](../../../../benchmark_data/authoring/validation_records.json)
- [Dataset registry](../../../../benchmark_data/authoring/dataset.json)
- [Expected outputs](../../../../benchmark_data/authoring/expected_outputs_dev.json)
- [Fixture expected outputs](../../../../benchmark_data/authoring/dev_fixture_expected_outputs.json)
- [Fixture execution evidence](../../../../benchmark_data/authoring/dev_fixture_validation.json)
- [Snapshot build manifest](../../../../benchmark_data/physical/build_manifest.json)

## Scope and integrity

Registry version: `0.3.0-draft-implementation`. Development: 10 groups, 5 ERP + 5 WMS, 110 questions. Automated SQL/oracle: {'VALIDATED_BY_AUTOMATION': 10, 'NEEDS_HUMAN_REVIEW': 0, 'BLOCKED': 0}. Human approval remains pending for all Development groups and questions. Revision: `dev-v5-paraphrase-audit`.

Status meanings: `dataset.json` `validation_status` records machine validation; `intent_card_status` and `ground_truth_review` remain `NEEDS_HUMAN_REVIEW`. Evaluator release eligibility uses those review fields plus expected-output/freeze gates in `bird_demo/benchmark/registry.py` and `evaluator.py`; the machine artifact does not approve gold SQL.

Registry revision: `dev-v5-paraphrase-audit`
Registry SHA-256: `76b591117daf6d6f95fca629c7f23d894b2e8f307cb1ffa6266aaf5876755187`
Review export SHA-256 (CSV rows verified against the pinned registry revision and validation evidence):
- `DEVELOPMENT_INTENT_SQL_REVIEW_10.csv`: `374c038b414d0ef315d0d3de1c76a5656993f638eb30871d96123c94ed87df43`
- `ERP_DEVELOPMENT_QUESTIONS_55.csv`: `98eebaed1c499e1f5884676c1ca6e619615307a436cad7b21fdf8d805f0ebfac`
- `WMS_DEVELOPMENT_QUESTIONS_55.csv`: `c1f0f0abb2a679cae1c774c365478a626f11413e9c7bf1b307072bfdf86189bd`
Validation Records SHA-256: `4031ec453b9cbb3d1ef32b4ba31ba869ac0fef38042ff5a41ef30a52405679db`
Expected outputs SHA-256: `38f1e00c520f1b2c4b95b9234a43fe8fa45464c8ef8fd8c54f1158403d3d377d`
Fixture validation SHA-256: `5b39dda9b2656332583b2ed3e0d9868d89a9a18d8e42a905ed5de4c949ff7b4d`

v5 chỉ sửa 82 variant, giữ nguyên toàn bộ Q00, Intent/SQL, Business Rules, oracle, expected outputs và Final. [Lineage manifest](../../../../benchmark_data/authoring/dev_wording_v5_manifest.json) ghi hash trước/sau và bất biến. Hash registry v4 trong expected-output artifacts là nguồn **lịch sử của lần tạo expected outputs**, không phải hash registry hiện hành. Các contract/SQL/snapshot không đổi nên evidence vẫn áp dụng; không chạy lại SQL và không ghi giả một lần validation mới. Bảng Intent/SQL 10 dòng không đổi byte và được liên kết lại qua manifest v5.

Hai câu `ERP-EF-01-Q08`, `WMS-EF-01-Q07` vẫn giữ wording cũ với `TAXONOMY_LIMITATION`. Nội dung đề xuất nằm ở cột riêng `audit_proposal_not_owner_decision`; chưa áp dụng và chưa duyệt. Các cột reviewer/decision/nhận xét/wording sửa đề xuất của con người được giữ nguyên. Quota nhãn đúng không đồng nghĩa taxonomy đã được nghiệm thu.

| Database | Snapshot | SHA-256 (manifest/current) |
|---|---|---|
| erp_sales | `benchmark_data/physical/erp_sales.sqlite` | `347c0e7b663d74c740c6b1fba4a2b89a6ca21beeb4148bd8bff41ed3a4ca888b` |
| wms_inventory | `benchmark_data/physical/wms_inventory.sqlite` | `c55c41e8755dccd1e0d77aaaf86b0dcf2895b75ae8a8d5b1891774e26cf589d5` |

## Special semantic review

### ERP-RK-02 — Option B recorded; human review pending

Benchmark Owner chose Option B: the final SELECT now returns only `sku`, `product_name`, `base_unit`, `sold_qty_milli`, and `rnk`. `RANK()`, `PARTITION BY base_unit`, rank cutoff and tie inclusion are unchanged. SQL/oracle/outputs passed machine checks; Intent, SQL and Q0–Q10 still need human review.

### ERP-RK-02

- [ ] Final projection is exactly SKU, product name, base unit, sold quantity and rank.
- [ ] Top 3 is ranked independently within each `base_unit` (`PARTITION BY base_unit`).
- [ ] Every tie at rank 3 is included (`RANK() <= 3`); quantities across EA/KG/L are never compared.
- [ ] Fixture retains both tied EA SKUs at rank 3 and returns all present units.
- [ ] Approve/revise/reject Intent, SQL, expected rows/hash and Q0–Q10 wording.

### WMS-CD-02

- [ ] Output grain is document × SKU and includes DRAFT, POSTED and CANCELLED.
- [ ] Non-POSTED documents have executed quantity 0; planned quantity remains visible.
- [ ] TRANSFER executed quantity counts SOURCE exactly once, not both legs.
- [ ] Other POSTED document types follow the approved movement rules; fixture covers receipt, shipment, adjustment and customer return.
- [ ] Approve/revise/reject Intent, SQL, expected rows/hash and Q0–Q10 wording.

## Experimental protocol decisions approved 2026-11-10

| ID | Approved protocol | Implementation implication |
|---|---|---|
| D8 | SQL execution timeout 30 seconds/query | Record status, elapsed time and error category; never retry SQL timeout. Provider/network timeout is separate. |
| D9 | Exactly 3 complete replicates per model/config | 330 Development predictions/model/config; pair Q0–Q10 within each replicate; report each replicate and mean/SD/range, never best run. |
| D13 | Initial attempt + up to 2 bounded-backoff retries only for transient infrastructure errors | Same request/config; retries are not replicates. No retry for SQL error/timeout, valid-response malformed/missing SQL, or incorrect result. Preserve attempts and UNKNOWN/missingness. |

## Decisions still PROPOSED (do not treat as approved)

| ID | Recommended value in Decision Review | Why the group must decide |
|---|---|---|
| D12 | Keep 0.x pilot; decide Final access/exposure before release. | D8/D9/D13 approval does not decide release/access policy. |
| D14 | Describe as a pilot; avoid absolute novelty claims before literature review. | D8/D9/D13 approval does not decide novelty claims. |

## Evaluation implementation audit (offline source review)

- `scripts/benchmark_eval.py` and `bird_demo/benchmark/evaluator.py` evaluate one saved prediction set; they do not collect model predictions or orchestrate three replicates/retries.
- SQL outcome statuses exist, but prediction records do not include SQL elapsed time or a separate error-category field. The CLI defaults to 30 seconds but permits overriding it; D8 is not enforced as an immutable protocol value.
- `evaluate_saved_predictions()` defaults `replicate_id` to 0 and accepts arbitrary IDs. `summarize_replicates()` summarizes the supplied list but does not require IDs 1/2/3, completeness, or one model/config hash.
- The shared `bird_demo.llm.client()` is configured with SDK `max_retries=3`; that path does not implement D13 classification/bounded-backoff semantics. A benchmark collector must control SDK retries and retain per-attempt records.
- Run artifacts lack a frozen provider/model/config hash and raw response/attempt provenance. Do not use the generic app path as an official benchmark collector until these gaps are implemented and tested.

## Gate before Development LLM evaluation

- [ ] Owner resolves all 10 Intent/SQL/expected-output records, including both special semantics above.
- [ ] Review each Q0–Q10 row; revise/reject defective wording, then revalidate changed groups and freeze registry/hash.
- [ ] Implement and verify D8/D9/D13 in a prediction collector and evaluation orchestrator; the current offline evaluator does not provide collection, retry, or three-replicate orchestration.
- [ ] Select model/provider and immutable config (prompt, schema/glossary context, temperature, token limits, code version); authorize paid API if applicable.
- [ ] Confirm only Development is evaluated; no Final results are inspected or used for tuning.

After gates: save predictions and run artifacts via `uv run python scripts/benchmark_eval.py --registry <reviewed-dev-registry> --predictions <saved-predictions.json> --output <run-output.json>`. This command evaluates saved predictions and does not call an LLM. Use the already configured model runner for collection only after owner approval and cost authorization; do not run current draft registry as a release benchmark.

## Reproduce technical checks (offline; no provider calls)

```powershell
.\.venv\Scripts\python.exe scripts\audit_dev_wording_v5.py
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp .pytest-review-check
```

Use a new, disposable `--basetemp` directory when running tests. The audit command is read-only by default; its `--apply` migration accepts only the pinned v4 source and refuses to overwrite v5 review work. Do not rerun historical authoring/export commands during review: they can replace wording, evidence hashes, protocol documentation or blank reviewer fields. Frozen SQLite snapshots must remain unchanged.
