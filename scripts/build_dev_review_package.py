"""Export a compact, traceable human-review package for Development groups."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTHORING = ROOT / "benchmark_data/authoring"
OUT = ROOT / "docs/benchmark/review/dev_human_approval"
DEV_IDS = {
    "ERP-EF-01", "ERP-GB-03", "ERP-JN-02", "ERP-TM-02", "ERP-RK-02",
    "WMS-EF-01", "WMS-EF-02", "WMS-AG-02", "WMS-CD-02", "WMS-JN-04",
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_write(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    registry_path = AUTHORING / "dataset.json"
    validation_path = AUTHORING / "ground_truth_validation.json"
    records_path = AUTHORING / "validation_records.json"
    expected_path = AUTHORING / "expected_outputs_dev.json"
    fixture_path = AUTHORING / "dev_fixture_validation.json"
    manifest_path = ROOT / "benchmark_data/physical/build_manifest.json"
    registry = read_json(registry_path)
    validation = read_json(validation_path)
    records = {x["group_id"]: x for x in read_json(records_path)}
    expected = {x["group_id"]: x for x in read_json(expected_path)["expected_outputs"]}
    validation_results = {x["group_id"]: x for x in validation["results"]}
    fixtures = {x["group_id"]: x for x in read_json(fixture_path)["results"]}
    manifest = read_json(manifest_path)
    groups = [g for g in registry["groups"] if g["group_id"] in DEV_IDS]
    if len(groups) != 10:
        raise RuntimeError(f"Expected 10 Development groups, found {len(groups)}")

    review_rows = []
    question_rows = {"erp": [], "wms": []}
    questions = registry["questions"]
    for group in groups:
        gid = group["group_id"]
        if group.get("split") != "development":
            raise RuntimeError(f"Unexpected split for {gid}: {group.get('split')}")
        card = group["card_fields"]
        gt = validation_results[gid]
        record = records[gid]
        exp = expected[gid]
        fixture = fixtures.get(gid)
        if gt["status"] != "VALIDATED_BY_AUTOMATION":
            raise RuntimeError(f"{gid} is not automation validated")
        if record.get("ground_truth_status") != "NEEDS_HUMAN_REVIEW":
            raise RuntimeError(f"{gid} has unexpected human-review status")

        review_rows.append({
            "Intent ID": gid,
            "Mô tả nghiệp vụ": card.get("brief", ""),
            "Competency": card.get("competency", ""),
            "Complexity": card.get("complexity", ""),
            "Lý do phân loại": card.get("classification", ""),
            "Business Rules": card.get("business_rules", ""),
            "Output grain / projection / measure": card.get("entity_grain", ""),
            "Filters / status / grouping / time": card.get("filters_group_time", ""),
            "NULL / zero / empty / tie / units": card.get("null_tie", ""),
            "Fixture cần/bằng chứng card": card.get("fixture_evidence", ""),
            "Canonical SQL candidate": group.get("canonical_sql_draft", ""),
            "SQL SHA-256": group.get("canonical_sql_sha256", ""),
            "Expected rows": record.get("expected_outputs", {}).get("row_count", gt.get("actual_row_count_before_set_comparison")),
            "Expected rows SHA-256": exp.get("expected_rows_sha256", ""),
            "Actual rows": gt.get("actual_row_count_before_set_comparison"),
            "Actual rows SHA-256": gt.get("actual_rows_sha256", ""),
            "Python oracle": exp.get("oracle_id", ""),
            "Oracle derivation": exp.get("oracle_method", ""),
            "Expected derived before SQL": exp.get("derived_before_canonical_sql_execution"),
            "Snapshot SHA-256": gt.get("database_sha256", ""),
            "Fixture status": fixture.get("status", "NOT_REQUIRED") if fixture else "NOT_REQUIRED",
            "Fixture rows": len(fixture.get("actual_rows", [])) if fixture else "",
            "Fixture expected SHA-256": fixture.get("expected_rows_sha256", "") if fixture else "",
            "Fixture actual SHA-256": fixture.get("actual_rows_sha256", "") if fixture else "",
            "Fixture checks": json.dumps(fixture.get("checks", {}) if fixture else {}, ensure_ascii=False),
            "Technical status": gt.get("status", ""),
            "Human review status": record.get("ground_truth_status", ""),
            "Projection alignment gate": (group.get("projection_alignment_decision", {}).get("status")
                if group.get("projection_alignment_decision") else ("NEEDS_OWNER_DECISION" if group.get("human_review_issues") else "NO_IDENTIFIED_CONFLICT")),
            "Owner issue / options": json.dumps(group.get("projection_alignment_decision", group.get("human_review_issues", [])), ensure_ascii=False),
            "Cần người duyệt xác nhận": (
                "Intent/slots; measure và status; SQL logic/projection/grain; expected rows/hash; "
                "business-rule interpretation; Q0–Q10 wording/semantic equivalence."
            ),
            "Owner decision recorded": ("Option B (2026-11-09); human review still pending"
                if group.get("projection_alignment_decision", {}).get("status") == "RESOLVED_BY_BENCHMARK_OWNER" else "—"),
            "Validation Record": "../../../../benchmark_data/authoring/validation_records.json#" + gid,
        })

        group_questions = sorted(
            (q for q in questions if q["group_id"] == gid), key=lambda q: q["q_index"]
        )
        original = next(q["question"] for q in group_questions if q["q_index"] == 0)
        target = question_rows["erp" if gid.startswith("ERP") else "wms"]
        for q in group_questions:
            target.append({
                "group_id": gid,
                "question_id": q["question_id"],
                "variant_type": q["variant_type"],
                "secondary_tags": json.dumps(q.get("secondary_tags", []), ensure_ascii=False),
                "owner_attention": "Option B recorded: five-column projection aligned; Intent/SQL still need human review." if gid == "ERP-RK-02" else "",
                "Original Q0": original,
                "Nội dung câu hỏi hiện tại": q["question"],
                "Semantic slots bắt buộc giữ nguyên": json.dumps(group.get("card_fields", {}), ensure_ascii=False),
                "reviewer": "",
                "decision (ACCEPT/REVISE/REJECT)": "",
                "nhận xét": "",
                "wording sửa đề xuất": "",
            })

    review_fields = list(review_rows[0])
    csv_write(OUT / "ERP_DEVELOPMENT_QUESTIONS_55.csv", question_rows["erp"], list(question_rows["erp"][0]))
    csv_write(OUT / "WMS_DEVELOPMENT_QUESTIONS_55.csv", question_rows["wms"], list(question_rows["wms"][0]))
    csv_write(OUT / "DEVELOPMENT_INTENT_SQL_REVIEW_10.csv", review_rows, review_fields)

    erp_ids = {g["group_id"] for g in groups if g["group_id"].startswith("ERP")}
    wms_ids = {g["group_id"] for g in groups if g["group_id"].startswith("WMS")}
    if len(erp_ids) != 5 or len(wms_ids) != 5 or len(question_rows["erp"]) != 55 or len(question_rows["wms"]) != 55:
        raise RuntimeError("Domain/group/question counts do not match required review package")

    report = [
        "# BIRD-VN-Robust-50 — Development Human Approval Package",
        "",
        "**Trạng thái:** Draft for human review. Không có Intent, SQL, expected output hay question nào được tự động phê duyệt.",
        "",
        "## Files",
        "",
        "- [Bảng Intent/SQL 10 groups](DEVELOPMENT_INTENT_SQL_REVIEW_10.csv): mỗi dòng chứa candidate SQL, semantic slots, expected/actual hashes, fixture evidence và mục Owner cần xác nhận.",
        "- [ERP Development Questions (55)](ERP_DEVELOPMENT_QUESTIONS_55.csv): Q0–Q10 cho 5 ERP groups.",
        "- [WMS Development Questions (55)](WMS_DEVELOPMENT_QUESTIONS_55.csv): Q0–Q10 cho 5 WMS groups.",
        "- [Paraphrase quality audit](DEV_PARAPHRASE_QUALITY_AUDIT.md): Q0 review, taxonomy quota, near-duplicate flags và semantic risks.",
        "- [Validation Records](../../../../benchmark_data/authoring/validation_records.json)",
        "- [Dataset registry](../../../../benchmark_data/authoring/dataset.json)",
        "- [Expected outputs](../../../../benchmark_data/authoring/expected_outputs_dev.json)",
        "- [Fixture expected outputs](../../../../benchmark_data/authoring/dev_fixture_expected_outputs.json)",
        "- [Fixture execution evidence](../../../../benchmark_data/authoring/dev_fixture_validation.json)",
        "- [Snapshot build manifest](../../../../benchmark_data/physical/build_manifest.json)",
        "",
        "## Scope and integrity",
        "",
        f"Registry version: `{registry['benchmark_version']}`. Development: 10 groups, 5 ERP + 5 WMS, 110 questions. Automated SQL/oracle: {validation['summary']}. Human approval remains pending for all Development groups and questions.",
        "",
        "Status meanings: `dataset.json` `validation_status` records machine validation; `intent_card_status` and `ground_truth_review` remain `NEEDS_HUMAN_REVIEW`. Evaluator release eligibility uses those review fields plus expected-output/freeze gates in `bird_demo/benchmark/registry.py` and `evaluator.py`; the machine artifact does not approve gold SQL.",
        "",
        f"Registry SHA-256: `{sha256(registry_path)}`  ",
        f"Validation Records SHA-256: `{sha256(records_path)}`  ",
        f"Expected outputs SHA-256: `{sha256(expected_path)}`  ",
        f"Fixture validation SHA-256: `{sha256(fixture_path)}`",
        "",
        "| Database | Snapshot | SHA-256 (manifest/current) |",
        "|---|---|---|",
    ]
    for db_id, info in manifest["databases"].items():
        report.append(f"| {db_id} | `benchmark_data/physical/{info['database_file']}` | `{info['sha256']}` |")

    report += [
        "",
        "## Special semantic review",
        "",
        "### ERP-RK-02 — Option B recorded; human review pending",
        "",
        "Benchmark Owner chose Option B: the final SELECT now returns only `sku`, `product_name`, `base_unit`, `sold_qty_milli`, and `rnk`. `RANK()`, `PARTITION BY base_unit`, rank cutoff and tie inclusion are unchanged. SQL/oracle/outputs passed machine checks; Intent, SQL and Q0–Q10 still need human review.",
        "",
        "### ERP-RK-02",
        "",
        "- [ ] Final projection is exactly SKU, product name, base unit, sold quantity and rank.",
        "- [ ] Top 3 is ranked independently within each `base_unit` (`PARTITION BY base_unit`).",
        "- [ ] Every tie at rank 3 is included (`RANK() <= 3`); quantities across EA/KG/L are never compared.",
        "- [ ] Fixture retains both tied EA SKUs at rank 3 and returns all present units.",
        "- [ ] Approve/revise/reject Intent, SQL, expected rows/hash and Q0–Q10 wording.",
        "",
        "### WMS-CD-02",
        "",
        "- [ ] Output grain is document × SKU and includes DRAFT, POSTED and CANCELLED.",
        "- [ ] Non-POSTED documents have executed quantity 0; planned quantity remains visible.",
        "- [ ] TRANSFER executed quantity counts SOURCE exactly once, not both legs.",
        "- [ ] Other POSTED document types follow the approved movement rules; fixture covers receipt, shipment, adjustment and customer return.",
        "- [ ] Approve/revise/reject Intent, SQL, expected rows/hash and Q0–Q10 wording.",
        "",
        "## Decisions still PROPOSED (do not treat as approved)",
        "",
        "| ID | Recommended value in Decision Review | Why the group must decide |",
        "|---|---|---|",
        "| D8 | 30-second/query initial timeout; measure on the benchmark DB and freeze identical resource limits for all questions. | Prevents query hangs and unequal execution budgets; source default is a starting value, not yet benchmark-approved. |",
        "| D9 | Prefer 3 paired replicates if resources allow; otherwise predeclare single-shot; report every run and mean/range/SD. | Makes stochastic model variability visible and prevents selecting the best run. |",
        "| D13 | Exploratory inference clustered by 50 groups; initial attempt + at most 2 infrastructure retries; report missingness and denominators. | Defines repeatable retry and analysis rules for nested questions/pairs. |",
        "",
        "## Gate before Development LLM evaluation",
        "",
        "- [ ] Owner resolves all 10 Intent/SQL/expected-output records, including both special semantics above.",
        "- [ ] Review each Q0–Q10 row; revise/reject defective wording, then revalidate changed groups and freeze registry/hash.",
        "- [ ] Decide D8, D9 and D13 in `docs/benchmark/DECISION_REVIEW.md`; keep status PROPOSED until explicitly decided.",
        "- [ ] Select model/provider and immutable config (prompt, schema/glossary context, temperature, token limits, code version); authorize paid API if applicable.",
        "- [ ] Confirm only Development is evaluated; no Final results are inspected or used for tuning.",
        "",
        "After gates: save predictions and run artifacts via `uv run python scripts/benchmark_eval.py --registry <reviewed-dev-registry> --predictions <saved-predictions.json> --output <run-output.json>`. This command evaluates saved predictions and does not call an LLM. Use the already configured model runner for collection only after owner approval and cost authorization; do not run current draft registry as a release benchmark.",
        "",
        "## Reproduce technical checks (offline; no provider calls)",
        "",
        "```powershell",
        ".\\.venv\\Scripts\\python.exe scripts\\validate_bird_vn_drafts.py",
        ".\\.venv\\Scripts\\python.exe scripts\\prepare_bird_vn_expectations.py",
        ".\\.venv\\Scripts\\python.exe scripts\\validate_bird_vn_dev_fixtures.py",
        ".\\.venv\\Scripts\\python.exe scripts\\run_bird_vn_ground_truth_validation.py",
        ".\\.venv\\Scripts\\python.exe scripts\\benchmark_offline_smoke.py",
        ".\\.venv\\Scripts\\python.exe -m pytest -q",
        "```",
        "",
        "Do not rerun authoring commands during human review unless a defect is confirmed: they regenerate artifacts/hashes. Frozen SQLite snapshots must remain unchanged.",
        "",
    ]
    (OUT / "README.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps({"output": str(OUT), "groups": len(groups), "erp_questions": len(question_rows["erp"]),
                      "wms_questions": len(question_rows["wms"]), "registry_sha256": sha256(registry_path)}, indent=2))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    main()
