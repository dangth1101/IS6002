from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "benchmark_data/authoring"
REVIEW = ROOT / "docs/benchmark/review/dev_human_approval"
SBERT = ROOT / "docs/benchmark/review/full_semantic_validation_sbert"

REVISIONS = {
    "ERP-EF-01": "Liệt kê các đơn hàng đã được xác nhận, kèm mã đơn hàng, số đơn hàng, mã khách hàng, ngày đặt hàng và trạng thái đơn hàng.",
    "ERP-EF-02": "Liệt kê các đơn hàng đã xác nhận trong năm 2025 và có nhân viên phụ trách.",
    "ERP-EF-03": "Liệt kê các sản phẩm đã được phân vào danh mục sản phẩm.",
    "ERP-EF-04": "Tìm các đơn hàng đã xác nhận và đã giao trong quý IV năm 2025, có tổng giá trị sau giảm giá trên 100 triệu đồng.",
    "ERP-AG-01": "Đếm số khách hàng trong từng phân khúc.",
    "ERP-AG-02": "Tính tổng giá trị hàng hóa sau giảm giá của các đơn hàng đã xác nhận trong năm 2025.",
    "ERP-AG-03": "Tính giá trị đơn hàng trung bình của các đơn đã xác nhận trong năm 2025.",
    "ERP-AG-04": "Tính số tiền thuần trung bình trên mỗi đơn hàng có phát sinh khoản thu hoặc hoàn tiền đã ghi sổ trong năm 2025.",
    "ERP-GB-01": "Đếm số đơn hàng theo từng trạng thái.",
    "ERP-GB-02": "Tính tổng giá trị các đơn đã xác nhận theo từng khách hàng, kể cả khách hàng chưa có đơn.",
    "ERP-GB-03": "Với mỗi nhân viên phụ trách bán hàng có ít nhất một đơn đã xác nhận, cho biết mã nhân viên, họ tên nếu có và số đơn đã xác nhận. Nếu có đơn chưa được phân công, tính các đơn đó thành một nhóm riêng.",
    "ERP-GB-04": "Tính tổng doanh thu được ghi nhận theo từng tháng giao hàng trong nửa đầu năm 2025.",
    "ERP-RK-01": "Xếp hạng khách hàng theo doanh thu được ghi nhận trong năm 2025; lấy 5 hạng cao nhất và bao gồm mọi khách hàng đồng hạng ở hạng 5.",
    "ERP-RK-02": "Trong từng đơn vị cơ sở, xếp hạng SKU theo tổng lượng đặt trong các đơn đã xác nhận. Cho biết SKU, tên sản phẩm, đơn vị cơ sở, tổng lượng đặt (tính theo phần nghìn đơn vị) và thứ hạng. Liệt kê các thứ hạng từ 1 đến 3, bao gồm mọi SKU đồng hạng ở hạng 3.",
    "ERP-RK-03": "Tìm khách hàng có tổng tiền thuần từ các khoản thu và hoàn tiền đã ghi sổ cao nhất trong năm 2025; bao gồm mọi khách hàng đồng hạng.",
    "ERP-JN-01": "Liệt kê tất cả khách hàng và số đơn hàng đã xác nhận của từng khách hàng; khách hàng chưa có đơn được tính 0.",
    "ERP-JN-02": "Liệt kê từng dòng hàng của các đơn đã xác nhận, mỗi dòng kết quả ứng với một dòng hàng. Cho biết số đơn, ngày đặt, SKU, tên sản phẩm, lượng đặt (tính theo phần nghìn đơn vị) và giá trị ròng của dòng hàng (đồng).",
    "ERP-JN-03": "Tính doanh thu được ghi nhận theo từng khách hàng và danh mục sản phẩm.",
    "ERP-JN-04": "Tổng hợp lượng hàng đã nhận trả theo từng khách hàng và SKU.",
    "ERP-TM-01": "Liệt kê các đơn hàng đã xác nhận được đặt trong quý I năm 2025.",
    "ERP-TM-02": "Với mỗi ngày trong năm 2025 (theo giờ Việt Nam) có ít nhất một lần giao hàng hoàn tất, cho biết ngày giao và số lần giao. Xác định ngày theo thời điểm giao sau khi quy đổi từ UTC sang giờ Việt Nam; chỉ tính từ 00:00 ngày 01/01/2025 đến trước 00:00 ngày 01/01/2026. Không tạo dòng cho ngày không có lần giao.",
    "ERP-NA-01": "Liệt kê những khách hàng chưa có đơn hàng đã xác nhận.",
    "ERP-NA-02": "Liệt kê các đơn hàng đã xác nhận chưa có khoản thu hoặc hoàn tiền nào được ghi sổ; phân biệt riêng các đơn có giao dịch đã ghi sổ nhưng tổng tiền thuần bằng 0.",
    "ERP-CD-01": "Trong năm 2025, tính riêng theo ngày: tổng giá trị đơn hàng đã xác nhận theo ngày đặt và tổng doanh thu được ghi nhận của các đơn đã giao theo ngày giao.",
    "ERP-CD-02": "Tổng hợp số tiền thu và số tiền hoàn đã ghi sổ theo từng phương thức thanh toán.",
    "WMS-EF-01": "Liệt kê từng chứng từ kho đã ghi sổ, gồm mã chứng từ, số chứng từ, loại chứng từ, trạng thái và ngày nghiệp vụ.",
    "WMS-EF-02": "Liệt kê các sản phẩm có đơn vị cơ sở là ki-lô-gam, gồm mã sản phẩm, SKU, tên sản phẩm, đơn vị cơ sở và mã danh mục nếu có.",
    "WMS-EF-03": "Liệt kê các biến động kho đã ghi sổ tại những vị trí lưu trữ.",
    "WMS-EF-04": "Tìm các SKU có lượng tồn dương tại khu cách ly ở thời điểm chốt số liệu.",
    "WMS-AG-01": "Đếm số chứng từ nhập kho đã ghi sổ.",
    "WMS-AG-02": "Với mỗi sản phẩm có đơn vị cơ sở là ki-lô-gam và có ít nhất một lần xuất kho từ chứng từ giao hàng đã ghi sổ, cho biết mã sản phẩm, SKU, đơn vị cơ sở và tổng lượng xuất trong toàn bộ lịch sử (tính theo phần nghìn ki-lô-gam). Chỉ tính lượng xuất từ chứng từ giao hàng.",
    "WMS-AG-03": "Với từng SKU và đơn vị cơ sở, tính lượng tồn trung bình giữa các vị trí đã phát sinh biến động, tại thời điểm chốt số liệu.",
    "WMS-AG-04": "Với từng SKU trong từng kho, đếm số vị trí có lượng tồn thấp hơn mức tồn trung bình của SKU đó trong kho tại thời điểm chốt.",
    "WMS-GB-01": "Đếm số chứng từ theo từng trạng thái, không phân biệt loại chứng từ.",
    "WMS-GB-02": "Tính tổng lượng biến động kho có dấu theo từng loại chứng từ và từng đơn vị cơ sở.",
    "WMS-GB-03": "Với từng nhà cung cấp, đếm số chứng từ nhập kho đã ghi sổ, kể cả nhà cung cấp chưa có chứng từ nhập.",
    "WMS-GB-04": "Báo cáo lượng tồn theo từng kho, SKU và đơn vị cơ sở tại thời điểm chốt; chỉ gồm những cặp kho–SKU có lịch sử biến động.",
    "WMS-RK-01": "Tại kho WH-SG, tìm SKU tính theo đơn vị cái có lượng tồn cao nhất; bao gồm mọi SKU đồng hạng.",
    "WMS-RK-02": "Xếp hạng các nhà cung cấp theo số chứng từ nhập kho đã ghi sổ; lấy 3 hạng đầu, bao gồm mọi nhà cung cấp đồng hạng ở hạng 3.",
    "WMS-RK-03": "Với SKU W-SKU-001, xếp hạng các vị trí lưu trữ theo lượng tồn tại thời điểm chốt và liệt kê 3 hạng đầu, bao gồm mọi vị trí đồng hạng ở hạng 3.",
    "WMS-JN-01": "Liệt kê các chứng từ nhập kho đã ghi sổ cùng tên nhà cung cấp.",
    "WMS-JN-02": "Liệt kê từng dòng hàng của chứng từ nhập kho đã ghi sổ, gồm SKU và lượng theo kế hoạch.",
    "WMS-JN-03": "Tính tổng lượng biến động kho có dấu theo từng kho, loại vị trí và đơn vị cơ sở.",
    "WMS-JN-04": "Liệt kê từng nhánh biến động kho của mỗi chứng từ chuyển kho đã ghi sổ, mỗi dòng ứng với một nhánh. Cho biết mã và số chứng từ, số dòng, SKU, số thứ tự và vai trò nhánh, kho nguồn, kho đích, lượng biến động có dấu (tính theo phần nghìn đơn vị cơ sở) và thời điểm UTC.",
    "WMS-TM-01": "Liệt kê các chứng từ đã ghi sổ có ngày nghiệp vụ trong tháng 1 năm 2025.",
    "WMS-TM-02": "Tính tổng lượng biến động kho đã ghi sổ trước một mốc thời gian UTC, cho từng cặp sản phẩm–vị trí.",
    "WMS-NA-01": "Liệt kê các SKU chưa từng phát sinh biến động kho tại những vị trí lấy hàng đang hoạt động.",
    "WMS-NA-02": "Liệt kê các cặp sản phẩm–vị trí có tồn kho ròng bằng 0 dù đã có biến động; phân biệt riêng những vị trí chưa từng phát sinh biến động.",
    "WMS-CD-01": "Trong khoảng thời gian đã quy định, tính theo từng sản phẩm và đơn vị cơ sở: tổng lượng xuất cho khách hàng và tổng lượng biến động kho có dấu.",
    "WMS-CD-02": "Với mỗi cặp chứng từ kho–SKU có trong chứng từ, bất kể trạng thái, cho biết mã và số chứng từ, loại chứng từ, trạng thái, SKU, đơn vị cơ sở, lượng theo kế hoạch và lượng thực hiện (tính theo phần nghìn đơn vị). Chứng từ chưa ghi sổ có lượng thực hiện bằng 0; với chứng từ chuyển kho chỉ tính nhánh nguồn một lần; các loại chứng từ đã ghi sổ khác tính theo quy tắc biến động kho đã thống nhất.",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
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
registry = load_json(registry_path)
groups = {g["group_id"]: g for g in registry["groups"]}
questions = {q["question_id"]: q for q in registry["questions"]}
if set(REVISIONS) != set(groups):
    raise SystemExit(f"Q00 revision map coverage mismatch: {set(groups) ^ set(REVISIONS)}")

changed = {}
for group_id, wording in REVISIONS.items():
    question = questions[f"{group_id}-Q00"]
    if question["question"] != wording:
        changed[question["question_id"]] = (question["question"], wording)
        question["question"] = wording
        question["variant_review"] = "NEEDS_HUMAN_REVIEW"
        question["review_notes"] = "Q0 wording revised after user feedback to use natural Vietnamese; wording requires human confirmation."
        question["semantic_review_basis"] = "Language editing against the existing Intent Card; SQL, expected outputs and snapshots unchanged."
        question["wording_revision"] = "dev-v9-all-q00-natural-vietnamese"
        question.pop("review_decision_provenance", None)
    groups[group_id]["human_review_status"] = "NEEDS_HUMAN_REVIEW"

if not changed:
    raise SystemExit("No Q00 wording changes were necessary.")

registry["authoring_revision"] = "dev-v9-all-q00-natural-vietnamese"
registry["revision_notes"] = (
    f"Reviewed and revised {len(changed)} Q00 anchors across all 50 intent groups for natural Vietnamese, "
    "preserving recorded filters, grain, measures and time scope. Q01-Q10, SQL, expected outputs, fixtures and snapshots are unchanged. "
    "All 50 Q00 anchors are open for Human Review; previously computed Q00-to-Qi SBERT scores are stale."
)
save_json(registry_path, registry)
registry_hash = sha(registry_path)

# Keep question review records synchronized; only revised Q00 rows are reopened.
records_path = AUTH / "validation_records.json"
records = load_json(records_path)
for record in records:
    gid = record["group_id"]
    if gid in groups:
        record["human_review"] = "NEEDS_HUMAN_REVIEW"
    for item in record.get("question_reviews", []):
        qid = item["question_id"]
        if qid in changed:
            item["question"] = questions[qid]["question"]
            item["review_status"] = "NEEDS_HUMAN_REVIEW"
            item["owner_decision"] = None
            item["review_decision_provenance"] = None
save_json(records_path, records)

# Update Development review exports. Original Q0 fields remain historical snapshots.
for filename in ("ERP_DEVELOPMENT_QUESTIONS_55.csv", "WMS_DEVELOPMENT_QUESTIONS_55.csv"):
    path = REVIEW / filename
    rows, fields = read_csv(path)
    for row in rows:
        row["source_registry_revision"] = registry["authoring_revision"]
        row["source_registry_sha256"] = registry_hash
        qid = row.get("question_id")
        if qid not in changed:
            continue
        new_text = questions[qid]["question"]
        row["Nội dung câu hỏi hiện tại"] = new_text
        row["decision (ACCEPT/REVISE/REJECT)"] = "REVISE"
        row["nhận xét"] = "Đã biên tập lại Q0 bằng tiếng Việt tự nhiên; cần xác nhận wording mới."
        row["wording sửa đề xuất"] = new_text
        row["wording_audit_action"] = "USER_REQUESTED_Q00_LANGUAGE_REVIEW; PENDING_CONFIRMATION"
        row["audit_proposal_not_owner_decision"] = "Không coi wording mới là approval."
    write_csv(path, rows, fields)

reconciliation_path = REVIEW / "DEV_V6_QUESTION_REVISION_RECONCILIATION.csv"
rows, fields = read_csv(reconciliation_path)
for row in rows:
    qid = row["question_id"]
    if qid in changed:
        row["current_registry_text"] = questions[qid]["question"]
        row["matches_v5"] = "False"
        row["action"] = "USER_REQUESTED_NATURAL_VIETNAMESE_Q00_REVISION; REOPEN_REVIEW"
        row["review_status"] = "NEEDS_HUMAN_REVIEW"
write_csv(reconciliation_path, rows, fields)

approval_path = REVIEW / "USER_APPROVAL_PROVENANCE_2026-11-16.json"
approval = load_json(approval_path)
dev_changed = sorted(qid for qid in changed if groups[qid.removesuffix("-Q00")]["split"] == "development")
dev_reopened_ids = sorted(f"{gid}-Q00" for gid, group in groups.items() if group["split"] == "development")
dev_reopened = len(dev_reopened_ids)
approval["current_review_state"] = {
    "development_groups_with_intent_sql_approval": 10,
    "development_questions_still_accepted": 110 - dev_reopened,
    "development_questions_reopened": dev_reopened,
    "reopened_question_ids": dev_reopened_ids,
    "reason": "User requested a natural-Vietnamese review of original questions; revised anchors await confirmation.",
    "previous_q00_approvals": "Historical decisions retained; current wording changes are not treated as approved.",
}
approval["registry_sha256_after_wording_revision"] = registry_hash
save_json(approval_path, approval)

# Preserve the old scored text and numeric values as historical evidence, and label affected scores stale.
summary_path = SBERT / "summary.json"
summary = load_json(summary_path)
stale_groups = set(summary.get("stale_q00_groups", []))
stale_groups.update(item.rsplit("-Q", 1)[0] for item in summary.get("stale_q00_variant_pairs", []))
stale_groups.update(qid.removesuffix("-Q00") for qid in changed)
for filename in ("q00_variant_similarity.csv", "similarity_low.csv", "high_similarity_semantic_risk.csv", "jaccard_36_review.csv"):
    path = SBERT / filename
    if not path.exists():
        continue
    rows, fields = read_csv(path)
    if "current_q0_text" not in fields:
        fields = [*fields, "current_q0_text"]
    for row in rows:
        gid = row.get("group_id")
        if gid not in groups:
            continue
        if gid in stale_groups:
            row["current_q0_text"] = questions[f"{gid}-Q00"]["question"]
            row["review_status"] = "STALE_SCORE_RECOMPUTE_REQUIRED; NEEDS_HUMAN_REVIEW"
            if "semantic_slot_flags" in row and "SCORE_STALE_AFTER_Q00_REVIEW" not in row["semantic_slot_flags"]:
                row["semantic_slot_flags"] += ";SCORE_STALE_AFTER_Q00_REVIEW"
    write_csv(path, rows, fields)

queue_path = SBERT / "human_review_queue.csv"
rows, fields = read_csv(queue_path)
for row in rows:
    if row.get("group_id") in groups:
        row["human_review_required"] = "YES"
        row["review_status"] = "NEEDS_HUMAN_REVIEW"
write_csv(queue_path, rows, fields)

audit_path = SBERT / "ground_truth_validation_audit.csv"
rows, fields = read_csv(audit_path)
for row in rows:
    gid = row.get("group_id")
    if gid in groups:
        row["human_review_status"] = "NEEDS_HUMAN_REVIEW"
        if f"{gid}-Q00" in changed:
            row["limitation"] = "Q00 wording was revised and reopened; SQL and expected-output evidence are unchanged. All Q00 SBERT scores are stale pending recomputation."
write_csv(audit_path, rows, fields)

gaps_path = SBERT / "intent_sql_evidence_gaps.csv"
rows, fields = read_csv(gaps_path)
for row in rows:
    gid = row.get("group_id")
    if gid in groups and f"{gid}-Q00" in changed:
        row["evidence_status"] = "NEEDS_HUMAN_REVIEW_Q00_REVISED"
        row["gap"] = "Q00 wording was revised for natural Vietnamese and awaits Human Review. Its ten recorded Q00-to-Qi scores are stale; SQL and expected outputs are unchanged."
write_csv(gaps_path, rows, fields)

summary = load_json(summary_path)
summary["registry_revision"] = registry["authoring_revision"]
summary["registry_sha256"] = registry_hash
summary["manifest_match"] = True
summary["question_texts_match_sbert_audit"] = False
summary["sbert_status"] = "STALE_AFTER_Q00_LANGUAGE_REVIEW"
summary["stale_q00_groups"] = sorted(stale_groups)
summary["stale_q00_pair_count"] = 10 * len(stale_groups)
summary["stale_score_reason"] = "Q00 wording changed after the recorded SBERT run; scores have not been recomputed, so no current cosine values are claimed."
summary["ground_truth_status_counts"] = {
    "('development', 'NEEDS_HUMAN_REVIEW')": 10,
    "('final', 'NEEDS_HUMAN_REVIEW')": 35,
    "('final', 'BLOCKED')": 5,
}
summary["group_split_status"] = {
    "development_intent_sql_automation_evidence": 10,
    "development_q00_reopened_for_language_review": dev_reopened,
    "final_independent_outputs_derived_human_review_pending": 35,
    "final_blocked_intent_sql_alignment": 5,
}
summary["human_review_queue_groups"] = 50
summary["cosine_values"] = f"STALE; {10 * len(stale_groups)} of 500 Q00-to-variant pairs require recomputation"
summary["score_distribution_scope"] = "Historical distribution only; all revised-anchor pairs are stale and must not be treated as current."
summary["source_hashes"]["dataset.json"] = registry_hash
summary["source_hashes"]["validation_records.json"] = sha(records_path)
summary["source_hashes"]["ground_truth_validation.json"] = sha(AUTH / "ground_truth_validation.json")
save_json(summary_path, summary)

with (REVIEW / "README.md").open("a", encoding="utf-8", newline="") as handle:
    handle.write(
        "\n\n## Q0 language review\n\n"
        f"All 50 Q0 anchors were reviewed; {len(changed)} were rewritten in natural Vietnamese and reopened for Human Review. "
        "The other question variants, SQL, expected outputs, fixtures and snapshots were not changed. SBERT scores for revised Q0 anchors are stale.\n"
    )
with (SBERT / "README.md").open("a", encoding="utf-8", newline="") as handle:
    handle.write(
        "\n\n## Q0 language review (2026-11-16)\n\n"
        f"Reviewed all 50 anchors and revised {len(changed)}. The {10 * len(stale_groups)} Q00-to-variant scores are stale because their source anchors no longer match the current wording. No replacement scores were generated because `sentence_transformers` is unavailable in the current environment. SBERT results are hidden as stale until recomputed.\n"
    )

# Refresh all tracked hashes. Keep the report integrity current while marking score lineage stale.
manifest_path = AUTH / "dev_v6_vietnamese_first_manifest.json"
manifest = load_json(manifest_path)
manifest["revision"] = registry["authoring_revision"]
manifest["registry_sha256"] = registry_hash
manifest["scope"] = "All Q00 anchors reviewed for natural Vietnamese; revised wording is pending Human Review; SQL and expected outputs are unchanged."
manifest["question_review_note"] = f"{len(changed)} Q00 anchors revised; {10 * len(changed)} prior SBERT pairs are stale pending recomputation."
tracked = set(manifest.get("files", {}))
for directory in (REVIEW, SBERT):
    tracked.update(str(path.relative_to(ROOT)).replace("\\", "/") for path in directory.iterdir() if path.is_file())
tracked.update({
    "benchmark_data/authoring/dataset.json",
    "benchmark_data/authoring/validation_records.json",
    "scripts/revise_all_q00_natural_vietnamese.py",
    "pages/1_BIRD_VN_Robust_50.py",
})
manifest["files"] = {
    rel: sha(ROOT / rel)
    for rel in sorted(tracked)
    if (ROOT / rel).is_file() and rel != "benchmark_data/authoring/dev_v6_vietnamese_first_manifest.json"
}
summary["report_artifact_sha256"] = {
    path.name: sha(path) for path in SBERT.iterdir() if path.is_file() and path.name != "summary.json"
}
save_json(summary_path, summary)
manifest["files"]["docs/benchmark/review/full_semantic_validation_sbert/summary.json"] = sha(summary_path)
save_json(manifest_path, manifest)

print(json.dumps({
    "groups_reviewed": 50,
    "q00_reworded": len(changed),
    "q00_unchanged": 50 - len(changed),
    "development_q00_reopened": len(dev_changed),
    "stale_q00_variant_pairs": 10 * len(stale_groups),
    "changed_question_ids": sorted(changed),
    "registry_sha256": registry_hash,
}, ensure_ascii=False))
