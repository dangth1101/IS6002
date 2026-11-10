"""Reproducible wording-only v4 -> v5 migration; default mode only verifies.

No SQL execution, model API, human decisions, or expected-output regeneration.
The versioned plan records Codex editorial judgments, not semantic proof.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import re
import shutil
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bird_demo.benchmark.registry import load_registry
from dev_wording_v5_plan import PLANS
from dev_wording_slot_checks import editorial_markers, slot_evidence

A = ROOT / "benchmark_data/authoring"
R = ROOT / "docs/benchmark/review/dev_human_approval"
REVISION = "dev-v5-paraphrase-audit"
BASE_SHA = "460acf73b291071a9a05fcd3a43fbfc986876cf4db9b5342bf074e5ea34fbd3f"
CSV_NAMES = ["ERP_DEVELOPMENT_QUESTIONS_55.csv", "WMS_DEVELOPMENT_QUESTIONS_55.csv"]
BASE_CSV = dict(zip(CSV_NAMES, [
    "8f97405d0bd0116460c74a67f40112474769a917efacce4f6285a3b5bf09ae0c",
    "68647c4b6ae13a0db4e653b6b177e683529bee012cf5a275289abd072db79925",
]))
MANIFEST = A / "dev_wording_v5_manifest.json"
AUDIT = A / "dev_wording_v5_audit.json"
HUMAN_COLUMNS = ["reviewer", "decision (ACCEPT/REVISE/REJECT)", "nhận xét", "wording sửa đề xuất"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def csv_read(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def csv_write(path, rows):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def protected_files():
    paths = [ROOT / "docs/benchmark/BENCHMARK_SPEC.md", ROOT / "docs/benchmark/DECISION_REVIEW.md",
             A / "expected_outputs_dev.json", A / "dev_fixture_expected_outputs.json",
             A / "dev_fixture_validation.json", A / "ground_truth_candidates.sql",
             R / "DEVELOPMENT_INTENT_SQL_REVIEW_10.csv"]
    for folder in ["benchmark_data/physical", "docs/benchmark/database_design",
                   "docs/benchmark/intent_cards", "bird_vn_benchmark", "bird_demo/benchmark"]:
        paths.extend(p for p in (ROOT / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths)}


def invariant_digest(data, records, validation):
    """Everything except permitted wording/metadata must remain identical."""
    question_fields = {"question", "transformation_note", "review_notes", "secondary_tags",
                       "semantic_review_basis", "wording_revision", "wording_audit_status"}
    questions = []
    for q in data["questions"]:
        questions.append(q if q["split"] == "final" or q["q_index"] == 0 else
                         {k: v for k, v in q.items() if k not in question_fields})
    record_copy = copy.deepcopy(records)
    for record in record_copy:
        if record["group_id"] in PLANS:
            record.pop("wording_revision", None)
            for q in record["question_reviews"]:
                if q["q_index"]:
                    q.pop("question", None)
    evidence = {k: v for k, v in validation.items()
                if k not in {"validation_records_sha256", "question_wording_revision", "wording_lineage"}}
    return {"groups": digest(data["groups"]), "question_contracts_and_approvals": digest(questions),
            "records_except_dev_variant_text": digest(record_copy), "execution_evidence": digest(evidence),
            "final_questions": digest([q for q in data["questions"] if q["split"] == "final"]),
            "original_questions": digest([q for q in data["questions"] if q["q_index"] == 0])}


def normalized(text):
    return " ".join(re.findall(r"\w+", text.casefold()))


def similarity_audit(questions):
    """Read-only lexical screening; never infer semantic equivalence from it."""
    dev = [q for q in questions if q["split"] == "development"]
    final = [q for q in questions if q["split"] == "final"]
    anchors = {q["group_id"]: normalized(q["question"]) for q in dev if q["q_index"] == 0}
    wrappers = [q["question_id"] for q in dev if q["q_index"] and
                anchors[q["group_id"]] in normalized(q["question"])]
    flags, exact = [], []
    # Final is read only for leakage detection, never inspected for model/prompt tuning.
    pairs = list(combinations(dev, 2)) + [(a, b) for a in dev for b in final]
    tokens = {q["question_id"]: set(normalized(q["question"]).split()) for q in questions}
    for a, b in pairs:
        ta, tb = tokens[a["question_id"]], tokens[b["question_id"]]
        similarity = len(ta & tb) / len(ta | tb)
        same_group = a["group_id"] == b["group_id"]
        if normalized(a["question"]) == normalized(b["question"]):
            exact.append([a["question_id"], b["question_id"]])
        if similarity >= (.78 if same_group else .72):
            flags.append(dict(a=a["question_id"], b=b["question_id"], score=round(similarity, 4),
                              scope="WITHIN_GROUP" if same_group else
                              "CROSS_SPLIT" if a["split"] != b["split"] else "BETWEEN_DEV_GROUPS"))
    return dict(method="Token-set Jaccard: within >= .78; between >= .72; no Final-Final audit",
                warning="Shared projections inflate similarity; flags require human linguistic review.",
                q0_wrappers=wrappers, normalized_exact_duplicates=exact, near_duplicate_flags=flags)


def verify():
    manifest = read(MANIFEST)
    data = load_registry(A / "dataset.json", allow_draft=True)
    assert data["authoring_revision"] == REVISION
    assert sha(A / "dataset.json") == manifest["registry_sha256"]
    assert protected_files() == manifest["protected_files_sha256"], "Protected content changed"
    records, validation = read(A / "validation_records.json"), read(A / "ground_truth_validation.json")
    assert invariant_digest(data, records, validation) == manifest["protected_content_sha256"]
    for name, checksum in manifest["outputs_sha256"].items():
        assert sha(ROOT / name) == checksum, f"Stale output: {name}"
    assert validation["validation_records_sha256"] == sha(A / "validation_records.json")
    dev = {q["question_id"]: q for q in data["questions"] if q["split"] == "development"}
    assert len(dev) == 110
    assert Counter(q["variant_type"] for q in dev.values()) == dict(anchor=10, lexical=30, syntactic=30, reordering=20, mixed=20)
    assert all(q["variant_review"] == "NEEDS_HUMAN_REVIEW" for q in dev.values())
    for name in CSV_NAMES:
        rows = csv_read(R / name)
        original = {r["question_id"]: r for r in csv_read(R / "archive/dev-v4" / name)}
        assert len(rows) == 55 and len({r["question_id"] for r in rows}) == 55
        for row in rows:
            q = dev[row["question_id"]]
            assert row["Nội dung câu hỏi hiện tại"] == q["question"]
            assert row["source_registry_sha256"] == manifest["registry_sha256"]
            assert row["Original Q0"] == dev[f"{q['group_id']}-Q00"]["question"]
            for field in HUMAN_COLUMNS:
                assert row[field] == original[q["question_id"]][field], f"Human edit overwritten: {q['question_id']}"
    for record in records:
        if record["group_id"] in PLANS:
            assert all(q["question"] == dev[q["question_id"]]["question"] for q in record["question_reviews"])
    audit = read(AUDIT)
    assert audit["after_similarity"] == similarity_audit(data["questions"])
    assert not audit["after_similarity"]["q0_wrappers"]
    assert not audit["after_similarity"]["normalized_exact_duplicates"]
    print(json.dumps({"verification": "PASS", "revision": REVISION, "sha256": manifest["registry_sha256"],
                      "actions": audit["action_counts"], "human_review": "PENDING",
                      "official_evaluation": "NOT_AUTHORIZED"}, ensure_ascii=False))


def apply():
    if MANIFEST.exists():
        raise SystemExit("Migration already recorded. Run without --apply to verify; never overwrite review work.")
    assert sha(A / "dataset.json") == BASE_SHA, "Not the authorized v4 registry"
    assert all(sha(R / n) == h for n, h in BASE_CSV.items()), "Review export is not pinned v4"
    data = load_registry(A / "dataset.json", allow_draft=True)
    records, validation = read(A / "validation_records.json"), read(A / "ground_truth_validation.json")
    protected = protected_files()
    invariants = invariant_digest(data, records, validation)
    before_similarity = similarity_audit(data["questions"])
    group_map = {g["group_id"]: g for g in data["groups"]}
    audit_rows, old_questions = [], []
    for q in data["questions"]:
        if q["split"] != "development":
            continue
        plan = PLANS[q["group_id"]][q["q_index"]]
        old = q["question"]
        old_questions.append(copy.deepcopy(q))
        if plan["action"] == "REVISE":
            assert q["q_index"] != 0 and plan["proposed_wording"] != old
            q["question"] = plan["proposed_wording"]
            q["transformation_note"] = plan["transformation"]
            q["review_notes"] = "Draft wording revised by Codex; see v5 per-question audit. Human review pending."
            q["wording_revision"] = REVISION
            q["semantic_review_basis"] = "Codex editorial comparison against locked card/SQL; not human validation."
            if q["variant_type"] == "mixed":
                q["secondary_tags"] = [t for t in ("lexical", "syntactic", "reordering")
                                       if t in plan["transformation"].casefold().split(":")[0]]
                assert len(q["secondary_tags"]) >= 2
        audit_rows.append(dict(group_id=q["group_id"], question_id=q["question_id"],
            variant_type=q["variant_type"], original_wording=old, proposed_wording=plan["proposed_wording"] or "",
            current_wording=q["question"], action=plan["action"], issue_type=plan["issue_type"],
            risk=plan["risk"], reason=plan["reason"], transformation=plan["transformation"],
            taxonomy_status="TAXONOMY_LIMITATION" if plan["action"] == "HOLD" else
                            "ANCHOR_UNCHANGED" if q["q_index"] == 0 else "PROVISIONAL_AGENT_ASSESSMENT",
            review_status="NEEDS_HUMAN_REVIEW", semantic_slots=group_map[q["group_id"]]["card_fields"],
            semantic_assessment="Đối chiếu wording với card/SQL đã khóa; xem lý do và slots. Chưa có human semantic equivalence.",
            canonical_sql_sha256=group_map[q["group_id"]]["canonical_sql_sha256"]))
        audit_rows[-1]["slots_before"] = slot_evidence(q["group_id"], old)
        audit_rows[-1]["slots_after"] = slot_evidence(q["group_id"], q["question"])
        assert not editorial_markers(q["question"])
    data["authoring_revision"] = REVISION
    data["paraphrase_revision"] = REVISION
    data["authoring_revision_note"] = "Wording-only Development audit; all groups, Q00, Final, SQL and approvals unchanged."
    data["paraphrase_revision_note"] = "82 variant revisions; 2 Reordering limitations held for Owner. No human approval."
    question_map = {q["question_id"]: q for q in data["questions"]}
    for record in records:
        if record["group_id"] in PLANS:
            record["wording_revision"] = REVISION
            for q in record["question_reviews"]:
                q["question"] = question_map[q["question_id"]]["question"]
    validation["question_wording_revision"] = REVISION
    validation["wording_lineage"] = "dev_wording_v5_manifest.json; execution evidence unchanged, not a new SQL run."
    assert invariant_digest(data, records, validation) == invariants
    after_similarity = similarity_audit(data["questions"])
    assert not after_similarity["q0_wrappers"] and not after_similarity["normalized_exact_duplicates"]
    archive = R / "archive/dev-v4"
    archive.mkdir(parents=True, exist_ok=False)
    for name in CSV_NAMES:
        shutil.copyfile(R / name, archive / name)
    write(A / "dataset.json", data)
    write(A / "validation_records.json", records)
    validation["validation_records_sha256"] = sha(A / "validation_records.json")
    write(A / "ground_truth_validation.json", validation)
    registry_sha = sha(A / "dataset.json")
    row_map = {r["question_id"]: r for r in audit_rows}
    for name in CSV_NAMES:
        rows = csv_read(archive / name)
        for row in rows:
            q = question_map[row["question_id"]]
            audit_row = row_map[q["question_id"]]
            row["Nội dung câu hỏi hiện tại"] = q["question"]
            row["secondary_tags"] = json.dumps(q.get("secondary_tags", []), ensure_ascii=False)
            row["wording_audit_action"] = audit_row["action"]
            row["taxonomy_assessment"] = audit_row["taxonomy_status"]
            row["audit_proposal_not_owner_decision"] = audit_row["proposed_wording"] if audit_row["action"] == "HOLD" else ""
            row["source_registry_revision"] = REVISION
            row["source_registry_sha256"] = registry_sha
        csv_write(R / name, rows)
    csv_rows = [{k: json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v
                 for k, v in row.items()} for row in audit_rows]
    csv_write(R / "DEV_V5_PARAPHRASE_AUDIT.csv", csv_rows)
    csv_write(R / "DEV_V4_TO_V5_CHANGELOG.csv", [row for row in csv_rows if row["action"] == "REVISE"])
    write(AUDIT, dict(revision=REVISION, baseline_registry_sha256=BASE_SHA, registry_sha256=registry_sha,
                     assessor="Codex; AI-assisted editorial audit, not human approval",
                     action_counts=dict(Counter(row["action"] for row in audit_rows)),
                     before_similarity=before_similarity, after_similarity=after_similarity,
                     original_development_questions=old_questions, questions=audit_rows))
    outputs = [A / "dataset.json", A / "validation_records.json", A / "ground_truth_validation.json", AUDIT,
               R / "DEV_V5_PARAPHRASE_AUDIT.csv", R / "DEV_V4_TO_V5_CHANGELOG.csv"]
    outputs += [R / n for n in CSV_NAMES] + [archive / n for n in CSV_NAMES]
    write(MANIFEST, dict(revision=REVISION, source_revision="dev-v4-erp-rk02-projection-b",
        source_registry_sha256=BASE_SHA, registry_sha256=registry_sha, source_review_csv_sha256=BASE_CSV,
        date="2026-11-10", approval="PENDING", evaluation_freeze=False,
        lineage_note="Expected-output source_registry_sha256 remains its historical v4 derivation source. "
                     "Unchanged contracts/SQL/snapshots and preserved execution evidence bind v5 to that evidence. "
                     "Historical v2/v3/v4 audits are not current wording validation.",
        protected_files_sha256=protected, protected_content_sha256=invariants,
        outputs_sha256={p.relative_to(ROOT).as_posix(): sha(p) for p in outputs},
        authoring_sources_sha256={p.relative_to(ROOT).as_posix(): sha(p) for p in
                                  [Path(__file__), ROOT / "scripts/dev_wording_v5_plan.py",
                                   ROOT / "scripts/dev_wording_slot_checks.py"]}))
    verify()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="One-time migration of the exact pinned v4 source")
    args = parser.parse_args()
    apply() if args.apply else verify()
