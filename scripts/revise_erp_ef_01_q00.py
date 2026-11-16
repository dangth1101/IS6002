from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "benchmark_data/authoring"
REVIEW = ROOT / "docs/benchmark/review/dev_human_approval"
SBERT = ROOT / "docs/benchmark/review/full_semantic_validation_sbert"
QUESTION_ID = "ERP-EF-01-Q00"
NEW_TEXT = "Liệt kê các đơn hàng đã được xác nhận, kèm mã đơn hàng, số đơn hàng, mã khách hàng, ngày đặt hàng và trạng thái đơn hàng."


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), reader.fieldnames


def write_csv(path: Path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


registry_path = AUTH / "dataset.json"
registry = read_json(registry_path)
question = next(q for q in registry["questions"] if q["question_id"] == QUESTION_ID)
if question["question"] == NEW_TEXT:
    raise SystemExit("The requested Q00 wording is already current.")
if "CONFIRMED" not in question["question"]:
    raise SystemExit("Q00 text changed unexpectedly; refusing to overwrite it.")

question["question"] = NEW_TEXT
question["variant_review"] = "NEEDS_HUMAN_REVIEW"
question["review_notes"] = "Wording revised after user feedback about mixed English/Vietnamese phrasing; the revised wording awaits confirmation."
question["semantic_review_basis"] = "User-requested linguistic revision; intent, SQL and expected output are unchanged."
question["wording_revision"] = "dev-v8-erp-ef-01-q00-natural-vietnamese"
question.pop("review_decision_provenance", None)
group = next(g for g in registry["groups"] if g["group_id"] == "ERP-EF-01")
group["human_review_status"] = "NEEDS_HUMAN_REVIEW"
registry["authoring_revision"] = "dev-v8-erp-ef-01-q00-natural-vietnamese"
registry["revision_notes"] = (
    "Revised ERP-EF-01 Q00 to natural Vietnamese after user feedback. Only this question was reopened; "
    "all other Development decisions, SQL, expected outputs and snapshots remain unchanged. The ten recorded "
    "SBERT Q00-to-Qi values for this group are stale pending recomputation."
)
write_json(registry_path, registry)
registry_hash = digest(registry_path)

# Update the validation record while preserving the independent SQL evidence.
records_path = AUTH / "validation_records.json"
records = read_json(records_path)
for record in records:
    if record["group_id"] != "ERP-EF-01":
        continue
    record["human_review"] = "NEEDS_HUMAN_REVIEW"
    for item in record.get("question_reviews", []):
        if item["question_id"] == QUESTION_ID:
            item["question"] = NEW_TEXT
            item["review_status"] = "NEEDS_HUMAN_REVIEW"
            item["owner_decision"] = None
            item["review_decision_provenance"] = None
write_json(records_path, records)

# Preserve Original Q0 as history, update the current wording and reopen only this row.
questions_csv = REVIEW / "ERP_DEVELOPMENT_QUESTIONS_55.csv"
rows, fields = read_csv(questions_csv)
for row in rows:
    row["source_registry_revision"] = registry["authoring_revision"]
    row["source_registry_sha256"] = registry_hash
    if row.get("question_id") == QUESTION_ID:
        row["Nội dung câu hỏi hiện tại"] = NEW_TEXT
        row["decision (ACCEPT/REVISE/REJECT)"] = "REVISE"
        row["nhận xét"] = "Đã sửa theo góp ý để dùng tiếng Việt tự nhiên; Q0 cần được xác nhận lại."
        row["wording sửa đề xuất"] = NEW_TEXT
        row["wording_audit_action"] = "USER_REQUESTED_EDIT_APPLIED_PENDING_REVIEW"
        row["audit_proposal_not_owner_decision"] = "Wording mới chưa được tính là approval."
write_csv(questions_csv, rows, fields)

reconciliation = REVIEW / "DEV_V6_QUESTION_REVISION_RECONCILIATION.csv"
rows, fields = read_csv(reconciliation)
for row in rows:
    if row["question_id"] == QUESTION_ID:
        row["current_registry_text"] = NEW_TEXT
        row["matches_v5"] = "False"
        row["action"] = "USER_REQUESTED_NATURAL_VIETNAMESE_REVISION; REOPEN_REVIEW"
        row["review_status"] = "NEEDS_HUMAN_REVIEW"
write_csv(reconciliation, rows, fields)

# Keep the previous blanket approval as history and record the new current state.
approval_path = REVIEW / "USER_APPROVAL_PROVENANCE_2026-11-16.json"
approval = read_json(approval_path)
approval["current_review_state"] = {
    "development_groups_with_intent_sql_approval": 10,
    "development_questions_still_accepted": 109,
    "development_questions_reopened": 1,
    "reopened_question_id": QUESTION_ID,
    "reason": "User flagged mixed English/Vietnamese and unnatural phrasing; Q00 was rewritten and awaits confirmation.",
    "previous_q00_approval": "Superseded for current wording; historical decision retained above.",
}
approval["registry_sha256_after_wording_revision"] = registry_hash
write_json(approval_path, approval)

# The existing scores use the former Q00. Keep their numeric values for traceability, but mark them stale.
for filename in ("q00_variant_similarity.csv", "similarity_low.csv", "high_similarity_semantic_risk.csv", "jaccard_36_review.csv"):
    path = SBERT / filename
    if not path.exists():
        continue
    rows, fields = read_csv(path)
    for row in rows:
        if row.get("group_id") == "ERP-EF-01":
            if "original_q0" in row:
                row["original_q0"] = NEW_TEXT
            if "review_status" in row:
                row["review_status"] = "STALE_SCORE_RECOMPUTE_REQUIRED; NEEDS_HUMAN_REVIEW"
            if "semantic_slot_flags" in row and "SCORE_STALE_AFTER_Q0_EDIT" not in row["semantic_slot_flags"]:
                row["semantic_slot_flags"] += ";SCORE_STALE_AFTER_Q0_EDIT"
    write_csv(path, rows, fields)

queue_path = SBERT / "human_review_queue.csv"
rows, fields = read_csv(queue_path)
for row in rows:
    if row.get("group_id") == "ERP-EF-01":
        row["human_review_required"] = "YES"
        row["review_status"] = "NEEDS_HUMAN_REVIEW"
write_csv(queue_path, rows, fields)

audit_path = SBERT / "ground_truth_validation_audit.csv"
rows, fields = read_csv(audit_path)
for row in rows:
    if row.get("group_id") == "ERP-EF-01":
        row["human_review_status"] = "NEEDS_HUMAN_REVIEW"
        row["limitation"] = "Intent/SQL approval remains recorded; ERP-EF-01-Q00 wording was revised and reopened. Its ten Q00 SBERT pairs are stale pending recomputation."
write_csv(audit_path, rows, fields)

gaps_path = SBERT / "intent_sql_evidence_gaps.csv"
rows, fields = read_csv(gaps_path)
for row in rows:
    if row.get("group_id") == "ERP-EF-01":
        row["evidence_status"] = "NEEDS_HUMAN_REVIEW_Q00_REVISED"
        row["gap"] = "Q00 wording was revised to natural Vietnamese and reopened. Ten Q00-to-variant SBERT scores still reflect the prior Q00 and require recomputation; SQL/expected output are unchanged."
write_csv(gaps_path, rows, fields)

summary_path = SBERT / "summary.json"
summary = read_json(summary_path)
summary["registry_revision"] = registry["authoring_revision"]
summary["registry_sha256"] = registry_hash
summary["manifest_match"] = True
summary["question_texts_match_sbert_audit"] = False
summary["sbert_status"] = "PARTIALLY_STALE_AFTER_ERP_EF_01_Q00_EDIT"
summary["stale_q00_variant_pairs"] = [f"ERP-EF-01-Q{i:02d}" for i in range(1, 11)]
summary["stale_q00_pair_count"] = 10
summary["stale_score_reason"] = "Q00 wording changed after the recorded SBERT run. sentence_transformers is unavailable in this project environment; no replacement scores were generated."
summary["ground_truth_status_counts"]["('development', 'NEEDS_HUMAN_REVIEW')"] = 1
summary["human_review_queue_groups"] = 41
summary["source_hashes"]["dataset.json"] = registry_hash
summary["source_hashes"]["validation_records.json"] = digest(records_path)
summary["score_distribution_scope"] = "Historical distribution includes ten stale ERP-EF-01 Q00 pairs and must not be treated as current until they are recomputed."
write_json(summary_path, summary)

with (SBERT / "README.md").open("a", encoding="utf-8", newline="") as handle:
    handle.write(
        "\n\n## Q0 wording revision (2026-11-16)\n\n"
        "ERP-EF-01-Q00 was rewritten in the current registry to natural Vietnamese. Its ten recorded Q00-to-Qi cosine values still use the prior wording and are marked stale. The model package is unavailable in the current project environment, so replacement scores were not generated. SBERT status is stale until recomputed; this question is back in Human Review.\n"
    )
with (REVIEW / "README.md").open("a", encoding="utf-8", newline="") as handle:
    handle.write(
        "\n\n## Question reopened\n\n"
        "ERP-EF-01-Q00 wording was revised to natural Vietnamese after user feedback. Its current wording is not yet approved; the previous approval is retained as historical provenance only. The other 109 Development question decisions remain unchanged.\n"
    )

# Refresh registry and report artifact hashes. The score report remains semantically stale by design.
manifest_path = AUTH / "dev_v6_vietnamese_first_manifest.json"
manifest = read_json(manifest_path)
manifest["revision"] = registry["authoring_revision"]
manifest["registry_sha256"] = registry_hash
manifest["scope"] = "Development approval with ERP-EF-01-Q00 wording reopened; Final independent outputs remain linked and unapproved."
manifest["question_review_note"] = "ERP-EF-01-Q00 was revised after user feedback. Its ten Q00-to-variant SBERT scores are stale pending recomputation."
tracked = set(manifest.get("files", {}))
for directory in (REVIEW, SBERT):
    tracked.update(str(path.relative_to(ROOT)).replace("\\", "/") for path in directory.iterdir() if path.is_file())
tracked.update({
    "benchmark_data/authoring/dataset.json",
    "benchmark_data/authoring/validation_records.json",
    "scripts/revise_erp_ef_01_q00.py",
})
manifest["files"] = {
    rel: digest(ROOT / rel)
    for rel in sorted(tracked)
    if (ROOT / rel).is_file() and rel != "benchmark_data/authoring/dev_v6_vietnamese_first_manifest.json"
}
write_json(manifest_path, manifest)

summary = read_json(summary_path)
summary["report_artifact_sha256"] = {
    path.name: digest(path) for path in SBERT.iterdir() if path.is_file() and path.name != "summary.json"
}
write_json(summary_path, summary)
manifest["files"]["docs/benchmark/review/full_semantic_validation_sbert/summary.json"] = digest(summary_path)
write_json(manifest_path, manifest)

print(json.dumps({"question_id": QUESTION_ID, "new_text": NEW_TEXT, "registry_sha256": registry_hash, "stale_sbert_pairs": 10}, ensure_ascii=False))
