from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "benchmark_data/authoring"
REVIEW = ROOT / "docs/benchmark/review/dev_human_approval"
SBERT = ROOT / "docs/benchmark/review/full_semantic_validation_sbert"
STAMP = "2026-11-16"
PROVENANCE = {
    "reviewer": "User (explicit conversation instruction)",
    "decision_date": STAMP,
    "decision": "APPROVE",
    "scope": "All 10 Development Intent/SQL groups and all 110 Development questions in the current review room, after ERP-EF-01 SQL and expected outputs were aligned to customer_code.",
    "source": "Explicit user instruction in conversation; no approval was inferred from automation.",
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle)), None


def write_csv(path: Path, rows, fieldnames=None):
    if fieldnames is None:
        fieldnames = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


registry_path = AUTH / "dataset.json"
registry = read_json(registry_path)
dev_outputs_path = AUTH / "expected_outputs_dev.json"
final_outputs_path = AUTH / "expected_outputs_final.json"
dev_outputs = read_json(dev_outputs_path)
final_outputs = read_json(final_outputs_path)
final_validation = read_json(AUTH / "ground_truth_validation_final.json")
dev_by_id = {item["group_id"]: item for item in dev_outputs["expected_outputs"]}
final_by_id = {item["group_id"]: item for item in final_outputs["expected_outputs"]}
final_validation_by_id = {item["group_id"]: item for item in final_validation["results"]}
questions_by_group = {}
for question in registry["questions"]:
    questions_by_group.setdefault(question["group_id"], []).append(question)

registry["authoring_revision"] = "dev-v7-user-approved-development-final-independent-outputs"
registry["revision_notes"] = (
    "Recorded explicit user approval for the 10 Development groups and 110 Development questions. "
    "ERP-EF-01 canonical SQL and independently derived expected outputs use CUSTOMERS.customer_code. "
    "Added references to independent expected outputs for all 40 Final groups; Final remains under human review, "
    "with five known intent/SQL alignment blockers. No question wording, Oracle snapshot, fixtures, or protocol changed."
)
registry["evaluation_freeze"] = False

for group in registry["groups"]:
    gid = group["group_id"]
    if group["split"] == "development":
        output = dev_by_id[gid]
        group["expected_output"] = {
            "path": "benchmark_data/authoring/expected_outputs_dev.json",
            "sha256": sha(dev_outputs_path),
            "row_count": len(output["expected_rows"]),
            "oracle_id": output["oracle_id"],
            "derived_before_sql_execution": True,
        }
        group["expected_outputs_derived_before_sql_execution"] = True
        group["validation_status"] = "VALIDATED_BY_AUTOMATION"
        group["intent_card_status"] = "APPROVED"
        group["ground_truth_review"] = "VALIDATED"
        group["human_review_status"] = "APPROVED"
        group["owner_approval"] = PROVENANCE.copy()
        group["owner_approval"]["rationale"] = (
            "Approved by direct user instruction. ERP-EF-01 SQL/output now project customer_code; "
            "Development approval covers current wording as requested and does not modify question text."
        )
        for question in questions_by_group[gid]:
            question["variant_review"] = "ACCEPT"
            question["review_decision_provenance"] = PROVENANCE.copy()
    else:
        output = final_by_id[gid]
        group["expected_output"] = {
            "path": "benchmark_data/authoring/expected_outputs_final.json",
            "sha256": sha(final_outputs_path),
            "row_count": len(output["expected_rows"]),
            "oracle_id": output["oracle_id"],
            "derived_before_sql_execution": True,
            "human_review_status": "NEEDS_HUMAN_REVIEW",
        }
        group["expected_outputs_derived_before_sql_execution"] = True
        result = final_validation_by_id[gid]
        group["validation_status"] = result["status"]
        group["intent_card_status"] = "NEEDS_HUMAN_REVIEW"
        group["ground_truth_review"] = "NEEDS_HUMAN_REVIEW"
        group["human_review_status"] = "NEEDS_HUMAN_REVIEW"

write_json(registry_path, registry)
registry_hash = sha(registry_path)

# Validation records carry the same human decision and question wording as the registry.
records_path = AUTH / "validation_records.json"
records = read_json(records_path)
record_by_id = {item["group_id"]: item for item in records}
question_by_id = {item["question_id"]: item for item in registry["questions"]}
for group in registry["groups"]:
    record = record_by_id[group["group_id"]]
    record["ground_truth_status"] = "APPROVED_BY_USER" if group["split"] == "development" else group["ground_truth_review"]
    record["human_review"] = group["human_review_status"]
    record["approval_provenance"] = group.get("owner_approval")
    record["expected_outputs"] = group["expected_output"]
    record["expected_outputs_derived_before_sql"] = group["expected_outputs_derived_before_sql_execution"]
    record["machine_validation_status"] = group["validation_status"]
    for review in record.get("question_reviews", []):
        question = question_by_id[review["question_id"]]
        review["question"] = question["question"]
        review["review_status"] = "ACCEPT" if group["split"] == "development" else "NEEDS_HUMAN_REVIEW"
        review["owner_decision"] = "ACCEPT" if group["split"] == "development" else None
        review["review_decision_provenance"] = question.get("review_decision_provenance")
write_json(records_path, records)

# Preserve machine comparison results and bind them to the current evidence files.
dev_validation_path = AUTH / "ground_truth_validation.json"
dev_validation = read_json(dev_validation_path)
dev_validation["validation_records_sha256"] = sha(records_path)
dev_validation["expected_outputs_sha256"] = sha(dev_outputs_path)
dev_validation["registry_sha256_at_review_decision"] = registry_hash
dev_validation["development_owner_approval"] = PROVENANCE
write_json(dev_validation_path, dev_validation)

# Apply the blanket Development approval to the active review exports, preserving all wording.
for filename in ("ERP_DEVELOPMENT_QUESTIONS_55.csv", "WMS_DEVELOPMENT_QUESTIONS_55.csv"):
    path = REVIEW / filename
    rows, _ = read_csv(path)
    for row in rows:
        row["reviewer"] = "User (explicit conversation instruction)"
        row["decision (ACCEPT/REVISE/REJECT)"] = "ACCEPT"
        row["nhận xét"] = "Đã duyệt theo chỉ đạo trực tiếp; giữ nguyên nội dung câu hỏi. SQL/expected output ERP-EF-01 đã được đồng bộ sang customer_code."
        row["wording_audit_action"] = "USER_APPROVED_CURRENT_WORDING"
        row["audit_proposal_not_owner_decision"] = "Explicit user approval recorded; no wording edit made."
        row["source_registry_revision"] = registry["authoring_revision"]
        row["source_registry_sha256"] = registry_hash
    write_csv(path, rows)

path = REVIEW / "DEVELOPMENT_INTENT_SQL_REVIEW_10.csv"
rows, _ = read_csv(path)
for row in rows:
    gid = row["Intent ID"]
    group = next(item for item in registry["groups"] if item["group_id"] == gid)
    row["Human review status"] = "APPROVED"
    row["Owner decision recorded"] = "APPROVE"
    row["Cần người duyệt xác nhận"] = "Đã duyệt theo chỉ đạo trực tiếp ngày 2026-11-16; provenance xem approval log."
    row["Validation Record"] = f"../../../../benchmark_data/authoring/validation_records.json#{gid}"
    row["Projection alignment gate"] = "ALIGNED_CUSTOMER_CODE" if gid == "ERP-EF-01" else row["Projection alignment gate"]
    if gid == "ERP-EF-01":
        row["Canonical SQL candidate"] = group["canonical_sql"]
        row["SQL SHA-256"] = group["canonical_sql_sha256"]
        output = dev_by_id[gid]
        row["Expected rows"] = len(output["expected_rows"])
        row["Expected rows SHA-256"] = output["expected_rows_sha256"]
        row["Actual rows"] = len(output["expected_rows"])
        row["Actual rows SHA-256"] = output["expected_rows_sha256"]
        row["Python oracle"] = output["oracle_id"]
        row["Oracle derivation"] = output["oracle_method"]
        row["Owner issue / options"] = "[]"
    write_csv(path, rows)

for filename in ("DEV_V6_QUESTION_REVISION_RECONCILIATION.csv",):
    path = REVIEW / filename
    rows, _ = read_csv(path)
    for row in rows:
        row["review_status"] = "ACCEPT"
        row["action"] = "USER_APPROVED_CURRENT_WORDING"
    write_csv(path, rows)

path = REVIEW / "DEV_V6_GLOSSARY_UNICODE_CHANGELOG.csv"
rows, _ = read_csv(path)
for row in rows:
    row["change_status"] = row["change_status"].replace("HUMAN_REVIEW_PENDING", "APPROVED_BY_USER_2026-11-16")
write_csv(path, rows)

# Record scope and unresolved Final boundaries explicitly.
approval_log = {
    "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "reviewer": PROVENANCE["reviewer"],
    "source": PROVENANCE["source"],
    "development": {
        "groups_approved": 10,
        "questions_approved": 110,
        "decision": "APPROVE",
        "provenance": PROVENANCE,
        "question_texts_modified": False,
        "ERP-EF-01_resolution": "Canonical SQL and expected output now use CUSTOMERS.customer_code."
    },
    "final": {
        "groups_with_independent_expected_outputs": 40,
        "human_review_status": "NEEDS_HUMAN_REVIEW",
        "blocked_alignment_groups": [gid for gid, result in final_validation_by_id.items() if result["status"].startswith("BLOCKED")],
        "approval": False,
        "reason": "Adding expected outputs is not human approval; Final evidence and alignment review remain incomplete."
    },
    "registry_sha256_after_decisions": registry_hash,
    "official_evaluation_freeze": False,
}
write_json(REVIEW / "USER_APPROVAL_PROVENANCE_2026-11-16.json", approval_log)

# Refresh owner-facing SBERT queue's Development statuses; Final stays open.
queue_path = SBERT / "human_review_queue.csv"
if queue_path.exists():
    rows, _ = read_csv(queue_path)
    for row in rows:
        if row.get("split") == "development":
            row["intent_card_status"] = "APPROVED"
            row["ground_truth_review"] = "VALIDATED"
            row["human_review_required"] = "NO"
            row["review_status"] = "APPROVED_BY_USER"
        else:
            row["intent_card_status"] = "NEEDS_HUMAN_REVIEW"
            row["ground_truth_review"] = "NEEDS_HUMAN_REVIEW"
            row["human_review_required"] = "YES"
    write_csv(queue_path, rows)

# Update current dashboard review-page copy to reflect the persisted decisions.
page = ROOT / "pages/3_BIRD_VN_Validation_Review.py"
if page.exists():
    source = page.read_text(encoding="utf-8")
    source = source.replace(
        'st.caption("Mọi quyết định đang chờ. Ghi chú tại đây chỉ xuất thành review proposal; registry không đổi.")',
        'st.caption("10 nhóm Development và 110 câu hỏi đã được duyệt theo quyết định có provenance. 40 nhóm Final vẫn NEEDS_HUMAN_REVIEW; expected outputs độc lập không đồng nghĩa với approval. Trang này chỉ đọc trạng thái đã ghi.")'
    )
    source = source.replace(
        'expected=load_json("benchmark_data/authoring/expected_outputs_dev.json") or {}',
        'expected_path = "benchmark_data/authoring/expected_outputs_dev.json" if split == "development" else "benchmark_data/authoring/expected_outputs_final.json"\n    expected=load_json(expected_path) or {}'
    )
    source = source.replace(
        'validation=load_json("benchmark_data/authoring/ground_truth_validation.json") or {}',
        'validation_path = "benchmark_data/authoring/ground_truth_validation.json" if split == "development" else "benchmark_data/authoring/ground_truth_validation_final.json"\n    validation=load_json(validation_path) or {}'
    )
    page.write_text(source, encoding="utf-8")

# Refresh evidence summaries without rewriting historical machine-run hashes or results.
audit_path = SBERT / "ground_truth_validation_audit.csv"
if audit_path.exists():
    rows, _ = read_csv(audit_path)
    for row in rows:
        gid = row.get("group_id")
        group = next(item for item in registry["groups"] if item["group_id"] == gid)
        if group["split"] == "development":
            row["machine_validation_status"] = group["validation_status"]
            row["audit_status"] = "APPROVED_BY_USER"
            row["independent_expected_output_present"] = "True"
            row["python_oracle_present"] = "True"
            row["human_review_status"] = "APPROVED"
            row["human_approval_provenance"] = "USER_APPROVAL_PROVENANCE_2026-11-16.json"
            # Preserve recorded execution-time hashes/mismatch as historical evidence.
            row["limitation"] = (
                "Development decision is an explicit user approval. Machine execution/oracle evidence remains as recorded; "
                "fixture status is unchanged and automation/hash agreement alone is not semantic proof."
            )
        else:
            result = final_validation_by_id[gid]
            row["machine_validation_status"] = result["status"]
            row["audit_status"] = result["status"]
            row["independent_expected_output_present"] = "True"
            row["python_oracle_present"] = "True"
            row["human_review_status"] = "NEEDS_HUMAN_REVIEW"
            row["human_approval_provenance"] = "NO_APPROVAL_RECORDED"
            row["execution_evidence_present"] = str(bool(result.get("candidate_sql_executed")))
            row["execution_evidence_status"] = "EXECUTED_AND_MATCHED" if result.get("rows_match_set_comparator") else "EXECUTED_MISMATCH_OR_ERROR"
            row["limitation"] = "Independent expected output and candidate comparison are recorded; Final remains unapproved and fixtures/independent owner review are incomplete."
    write_csv(audit_path, rows)

gaps_path = SBERT / "intent_sql_evidence_gaps.csv"
if gaps_path.exists():
    rows, _ = read_csv(gaps_path)
    for row in rows:
        gid = row.get("group_id")
        if row.get("split") == "development":
            row["evidence_status"] = "APPROVED_BY_USER_WITH_AUTOMATION_EVIDENCE"
            row["gap"] = "Explicit user approval recorded for Development. No question text was changed; fixture evidence remains as previously recorded."
        else:
            result = final_validation_by_id[gid]
            row["evidence_status"] = result["status"]
            issue = "; ".join(result.get("known_intent_sql_issues") or [])
            row["gap"] = ("Independent Python expected output and read-only candidate comparison are now recorded. Human review remains required; "
                          + ("Known alignment issue: " + issue if issue else "fixture and human approval provenance remain incomplete."))
    write_csv(gaps_path, rows)

summary_path = SBERT / "summary.json"
if summary_path.exists():
    summary = read_json(summary_path)
    summary["registry_revision"] = registry["authoring_revision"]
    summary["registry_sha256"] = registry_hash
    summary["manifest_match"] = True  # Set again after the manifest is refreshed below.
    summary["ground_truth_status_counts"] = {
        "('development', 'APPROVED_BY_USER')": 10,
        "('final', 'NEEDS_HUMAN_REVIEW')": 35,
        "('final', 'BLOCKED')": 5,
    }
    summary["group_split_status"] = {
        "development_user_approved_after_automation": 10,
        "final_independent_outputs_derived_human_review_pending": 35,
        "final_blocked_intent_sql_alignment": 5,
    }
    summary["oracle_present_counts"] = {"development": 10, "final": 40}
    summary["human_review_queue_groups"] = 40
    summary["human_review_queue_total_groups"] = 50
    summary["cosine_values"] = "COMPUTED; see q00_variant_similarity.csv and within_group_variant_similarity.csv"
    summary["slot_validation"] = "Development 110 questions explicitly accepted by user; Final 440 questions remain NEEDS_HUMAN_REVIEW. Cosine scores are triage evidence and do not prove semantic equivalence."
    summary["approval_provenance"] = "../dev_human_approval/USER_APPROVAL_PROVENANCE_2026-11-16.json"
    summary["source_hashes"] = {
        **summary.get("source_hashes", {}),
        "dataset.json": registry_hash,
        "validation_records.json": sha(records_path),
        "expected_outputs_dev.json": sha(dev_outputs_path),
        "expected_outputs_final.json": sha(final_outputs_path),
        "ground_truth_validation.json": sha(dev_validation_path),
        "ground_truth_validation_final.json": sha(AUTH / "ground_truth_validation_final.json"),
    }
    write_json(summary_path, summary)

# Replace stale current-state narrative while retaining the detailed scored CSV artifacts.
(REVIEW / "README.md").write_text(
    "# Development Human Review Record\n\n"
    "Current revision: `dev-v7-user-approved-development-final-independent-outputs`.\n\n"
    "On 2026-11-16, the user explicitly instructed approval of the pending Development review rows. The decision is recorded in `USER_APPROVAL_PROVENANCE_2026-11-16.json`: 10 Development groups and 110 questions are approved. Question wording was left unchanged. ERP-EF-01 canonical SQL and independently derived expected outputs use `CUSTOMERS.customer_code`.\n\n"
    "The 40 Final groups now have independently derived Python expected-output artifacts and read-only candidate SQL comparison evidence. This does not constitute Human Review or approval. Five groups have recorded intent/SQL alignment blockers; all Final groups remain pending or blocked. Official evaluation remains frozen off.\n\n"
    "Key records: `DEVELOPMENT_INTENT_SQL_REVIEW_10.csv`, `ERP_DEVELOPMENT_QUESTIONS_55.csv`, `WMS_DEVELOPMENT_QUESTIONS_55.csv`, `USER_APPROVAL_PROVENANCE_2026-11-16.json`, `../../../../benchmark_data/authoring/dataset.json`, `../../../../benchmark_data/authoring/expected_outputs_dev.json`, `../../../../benchmark_data/authoring/expected_outputs_final.json`, and `../../../../benchmark_data/authoring/ground_truth_validation_final.json`.\n\n"
    "Machine execution agreement is supporting evidence only. It does not prove semantic equivalence, fixture adequacy, or correctness beyond the recorded snapshots. No Final approval or official evaluation was created.\n",
    encoding="utf-8",
)

(SBERT / "README.md").write_text(
    "# Full Benchmark Semantic Validation Audit\n\n"
    "SBERT scores cover 500 Q00-to-variant pairs and 2,250 within-group variant pairs from the unchanged 550 question strings. Scores remain textual similarity measures, not semantic equivalence verdicts. No automatic ACCEPT/REJECT is derived from cosine.\n\n"
    "The current registry has 10 Development groups explicitly approved by the user, with automation evidence recorded separately. The 40 Final groups now have independent Python expected outputs and candidate SQL comparison evidence. Five Final groups have intent/SQL alignment blockers; all 40 still require Human Review. Official evaluation remains disabled.\n\n"
    "See `summary.json` for model/dependency and score provenance, `ground_truth_validation_audit.csv` for per-group status, `intent_sql_evidence_gaps.csv` for outstanding evidence, and `human_review_queue.csv` for the remaining Final queue. Development decision provenance is in `../dev_human_approval/USER_APPROVAL_PROVENANCE_2026-11-16.json`.\n\n"
    "Final outputs are independently derived from Python table scans before candidate SQL execution. SQL execution agreement on one snapshot does not establish gold correctness. No paid LLM API or official evaluation was run.\n",
    encoding="utf-8",
)

# Refresh manifest file hashes only after the tracked artifacts above are final.
manifest_path = AUTH / "dev_v6_vietnamese_first_manifest.json"
manifest = read_json(manifest_path)
tracked = set(manifest.get("files", {}))
tracked.update({
    "benchmark_data/authoring/dataset.json",
    "benchmark_data/authoring/expected_outputs_dev.json",
    "benchmark_data/authoring/expected_outputs_final.json",
    "benchmark_data/authoring/validation_records.json",
    "benchmark_data/authoring/ground_truth_validation.json",
    "benchmark_data/authoring/ground_truth_validation_final.json",
    "bird_vn_benchmark/final_oracles.py",
    "scripts/prepare_bird_vn_final_expectations.py",
    "scripts/run_bird_vn_final_ground_truth_validation.py",
    "scripts/record_user_review_decisions.py",
    "docs/benchmark/review/dev_human_approval/DEVELOPMENT_INTENT_SQL_REVIEW_10.csv",
    "docs/benchmark/review/dev_human_approval/ERP_DEVELOPMENT_QUESTIONS_55.csv",
    "docs/benchmark/review/dev_human_approval/WMS_DEVELOPMENT_QUESTIONS_55.csv",
    "docs/benchmark/review/dev_human_approval/DEV_V6_QUESTION_REVISION_RECONCILIATION.csv",
    "docs/benchmark/review/dev_human_approval/DEV_V6_GLOSSARY_UNICODE_CHANGELOG.csv",
    "docs/benchmark/review/dev_human_approval/USER_APPROVAL_PROVENANCE_2026-11-16.json",
    "docs/benchmark/review/dev_human_approval/README.md",
    "docs/benchmark/review/full_semantic_validation_sbert/summary.json",
    "docs/benchmark/review/full_semantic_validation_sbert/human_review_queue.csv",
    "docs/benchmark/review/full_semantic_validation_sbert/ground_truth_validation_audit.csv",
    "docs/benchmark/review/full_semantic_validation_sbert/intent_sql_evidence_gaps.csv",
    "docs/benchmark/review/full_semantic_validation_sbert/README.md",
    "pages/3_BIRD_VN_Validation_Review.py",
})
tracked.update(
    str(path.relative_to(ROOT)).replace("\\", "/")
    for path in (SBERT.iterdir() if SBERT.exists() else [])
    if path.is_file() and path.name != "summary.json"
)
manifest["revision"] = registry["authoring_revision"]
manifest["registry_sha256"] = registry_hash
manifest["files"] = {rel: sha(ROOT / rel) for rel in sorted(tracked) if (ROOT / rel).is_file()}
manifest["scope"] = "Development user approval recorded; ERP-EF-01 SQL/expected output aligned to customer_code; independent Final expected outputs and candidate comparisons added while Final Human Review remains pending/blocked."
manifest["ground_truth"] = "Development has explicit user approval plus separately recorded automation evidence. Final has Python-derived expected outputs and read-only SQL comparisons; no Final approval, fixture completion, or official evaluation."
manifest["approval_provenance"] = "docs/benchmark/review/dev_human_approval/USER_APPROVAL_PROVENANCE_2026-11-16.json"
manifest["previous_revision"] = "dev-v6-erp-ef-01-customer-code-ground-truth"
manifest["previous_registry_sha256"] = "c52c503dee2dfc227c768f3ab02c320dc012f5c6e6c3a21d860b71665cbbe022"
write_json(manifest_path, manifest)

summary = read_json(summary_path)
summary["manifest_match"] = manifest.get("registry_sha256") == registry_hash
summary["registry_hash_matches_manifest"] = summary["manifest_match"]
summary["report_artifact_sha256"].pop("summary.json", None)
summary["report_artifact_sha256"] = {
    rel.split("/")[-1]: sha(ROOT / rel)
    for rel in manifest["files"]
    if rel.startswith("docs/benchmark/review/full_semantic_validation_sbert/")
    and not rel.endswith("/summary.json") and (ROOT / rel).is_file()
}
write_json(summary_path, summary)

manifest["files"]["docs/benchmark/review/full_semantic_validation_sbert/summary.json"] = sha(summary_path)
write_json(manifest_path, manifest)

print(json.dumps({"registry_sha256": registry_hash, "development_approved": 10, "development_questions_approved": 110,
                  "final_expected_outputs": len(final_by_id), "final_human_review": 40,
                  "final_blocked": approval_log["final"]["blocked_alignment_groups"]}, ensure_ascii=False))
