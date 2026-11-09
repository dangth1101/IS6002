# BIRD-VN-Robust-50 — Development Human Approval Package

**Trạng thái:** Draft for human review. Không có Intent, SQL, expected output hay question nào được tự động phê duyệt.

## Files

- [Bảng Intent/SQL 10 groups](DEVELOPMENT_INTENT_SQL_REVIEW_10.csv): mỗi dòng chứa candidate SQL, semantic slots, expected/actual hashes, fixture evidence và mục Owner cần xác nhận.
- [ERP Development Questions (55)](ERP_DEVELOPMENT_QUESTIONS_55.csv): Q0–Q10 cho 5 ERP groups.
- [WMS Development Questions (55)](WMS_DEVELOPMENT_QUESTIONS_55.csv): Q0–Q10 cho 5 WMS groups.
- [Paraphrase quality audit](DEV_PARAPHRASE_QUALITY_AUDIT.md): Q0 review, taxonomy quota, near-duplicate flags và semantic risks.
- [Validation Records](../../../../benchmark_data/authoring/validation_records.json)
- [Dataset registry](../../../../benchmark_data/authoring/dataset.json)
- [Expected outputs](../../../../benchmark_data/authoring/expected_outputs_dev.json)
- [Fixture expected outputs](../../../../benchmark_data/authoring/dev_fixture_expected_outputs.json)
- [Fixture execution evidence](../../../../benchmark_data/authoring/dev_fixture_validation.json)
- [Snapshot build manifest](../../../../benchmark_data/physical/build_manifest.json)

## Scope and integrity

Registry version: `0.3.0-draft-implementation`. Development: 10 groups, 5 ERP + 5 WMS, 110 questions. Automated SQL/oracle: {'VALIDATED_BY_AUTOMATION': 10, 'NEEDS_HUMAN_REVIEW': 0, 'BLOCKED': 0}. Human approval remains pending for all Development groups and questions.

Status meanings: `dataset.json` `validation_status` records machine validation; `intent_card_status` and `ground_truth_review` remain `NEEDS_HUMAN_REVIEW`. Evaluator release eligibility uses those review fields plus expected-output/freeze gates in `bird_demo/benchmark/registry.py` and `evaluator.py`; the machine artifact does not approve gold SQL.

Registry SHA-256: `460acf73b291071a9a05fcd3a43fbfc986876cf4db9b5342bf074e5ea34fbd3f`  
Validation Records SHA-256: `fd53bdca50e1b38bfdea073a66e9d78bdf4b19e0cb3a9a1460e5582e0dd21e29`  
Expected outputs SHA-256: `38f1e00c520f1b2c4b95b9234a43fe8fa45464c8ef8fd8c54f1158403d3d377d`  
Fixture validation SHA-256: `5b39dda9b2656332583b2ed3e0d9868d89a9a18d8e42a905ed5de4c949ff7b4d`

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

## Decisions still PROPOSED (do not treat as approved)

| ID | Recommended value in Decision Review | Why the group must decide |
|---|---|---|
| D8 | 30-second/query initial timeout; measure on the benchmark DB and freeze identical resource limits for all questions. | Prevents query hangs and unequal execution budgets; source default is a starting value, not yet benchmark-approved. |
| D9 | Prefer 3 paired replicates if resources allow; otherwise predeclare single-shot; report every run and mean/range/SD. | Makes stochastic model variability visible and prevents selecting the best run. |
| D13 | Exploratory inference clustered by 50 groups; initial attempt + at most 2 infrastructure retries; report missingness and denominators. | Defines repeatable retry and analysis rules for nested questions/pairs. |

## Gate before Development LLM evaluation

- [ ] Owner resolves all 10 Intent/SQL/expected-output records, including both special semantics above.
- [ ] Review each Q0–Q10 row; revise/reject defective wording, then revalidate changed groups and freeze registry/hash.
- [ ] Decide D8, D9 and D13 in `docs/benchmark/DECISION_REVIEW.md`; keep status PROPOSED until explicitly decided.
- [ ] Select model/provider and immutable config (prompt, schema/glossary context, temperature, token limits, code version); authorize paid API if applicable.
- [ ] Confirm only Development is evaluated; no Final results are inspected or used for tuning.

After gates: save predictions and run artifacts via `uv run python scripts/benchmark_eval.py --registry <reviewed-dev-registry> --predictions <saved-predictions.json> --output <run-output.json>`. This command evaluates saved predictions and does not call an LLM. Use the already configured model runner for collection only after owner approval and cost authorization; do not run current draft registry as a release benchmark.

## Reproduce technical checks (offline; no provider calls)

```powershell
.\.venv\Scripts\python.exe scripts\validate_bird_vn_drafts.py
.\.venv\Scripts\python.exe scripts\prepare_bird_vn_expectations.py
.\.venv\Scripts\python.exe scripts\validate_bird_vn_dev_fixtures.py
.\.venv\Scripts\python.exe scripts\run_bird_vn_ground_truth_validation.py
.\.venv\Scripts\python.exe scripts\benchmark_offline_smoke.py
.\.venv\Scripts\python.exe -m pytest -q
```

Do not rerun authoring commands during human review unless a defect is confirmed: they regenerate artifacts/hashes. Frozen SQLite snapshots must remain unchanged.
