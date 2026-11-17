"""Guard wording-only lineage and pending human gates, not linguistic correctness."""
import csv
import hashlib
import json
from pathlib import Path

import pytest

from bird_demo.benchmark.registry import load_registry
from scripts.dev_wording_slot_checks import editorial_markers, slot_evidence

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "benchmark_data/authoring"
R = ROOT / "docs/benchmark/review/dev_human_approval"


def read(name):
    return json.loads((A / name).read_text(encoding="utf-8"))


def test_current_registry_lineage_and_development_review_exports_are_in_sync():
    registry_path = A / "dataset.json"
    manifest = json.loads((A / "dev_v6_vietnamese_first_manifest.json").read_text(encoding="utf-8"))
    data = read("dataset.json")
    assert data["authoring_revision"] == manifest["revision"]
    assert hashlib.sha256(registry_path.read_bytes()).hexdigest() == manifest["registry_sha256"]
    assert len(data["groups"]) == 50 and len(data["questions"]) == 550
    development = {q["question_id"]: q for q in data["questions"] if q["split"] == "development"}
    assert len(development) == 110
    for name in ("ERP_DEVELOPMENT_QUESTIONS_55.csv", "WMS_DEVELOPMENT_QUESTIONS_55.csv"):
        with (R / name).open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == 55
        for row in rows:
            assert row["Nội dung câu hỏi hiện tại"] == development[row["question_id"]]["question"]
            assert row["source_registry_revision"] == manifest["revision"]
            assert row["source_registry_sha256"] == manifest["registry_sha256"]
            assert row["source_registry_sha256"] == manifest["registry_sha256"]


def test_v6_semantic_glossary_has_valid_unicode_and_verified_mappings():
    data = read("dataset.json")
    glossary = data["semantic_glossary"]
    assert len(glossary) == 10
    assert all("?" not in item["vi"] and "?" not in item["basis"] for item in glossary)
    mappings = {item["vi"]: item["technical"] for item in glossary}
    assert mappings["Đã xác nhận (đơn hàng)"] == "SALES_ORDERS.order_status = CONFIRMED"
    assert mappings["Đã ghi sổ (chứng từ kho)"] == "INVENTORY_DOCUMENTS.document_status = POSTED"
    assert mappings["Đã giao hàng"] == "SALES_SHIPMENTS.shipment_status = DELIVERED"
    assert mappings["Chưa được phân công nhân viên phụ trách"] == "SALES_ORDERS.sales_rep_id IS NULL"


def test_development_intent_briefs_match_registry_and_owner_review_is_recorded():
    data = read("dataset.json")
    development = {g["group_id"]: g for g in data["groups"] if g["split"] == "development"}
    with (R / "DEVELOPMENT_INTENT_SQL_REVIEW_10.csv").open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
    assert len(rows) == 10
    brief_col = reader.fieldnames[1]
    for row in rows:
        brief = development[row["Intent ID"]]["card_fields"]["brief"]
        assert row[brief_col] == brief
        assert "?" not in brief
        assert row["Human review status"] == "APPROVED_BY_OWNER"


def test_current_owner_decisions_satisfy_registry_review_gates():
    registry = load_registry(A / "dataset.json")
    assert len(registry["questions"]) == 550
    audit = read("dev_wording_v5_audit.json")
    assert all(row["review_status"] == "NEEDS_HUMAN_REVIEW" for row in audit["questions"])
    held = [r for r in audit["questions"] if r["action"] == "HOLD"]
    assert {r["question_id"] for r in held} == {"ERP-EF-01-Q08", "WMS-EF-01-Q07"}
    assert all(r["current_wording"] == r["original_wording"] != r["proposed_wording"] for r in held)


def test_every_changed_wording_has_before_after_evidence_without_changes_to_q00():
    audit = read("dev_wording_v5_audit.json")
    changed = [r for r in audit["questions"] if r["original_wording"] != r["current_wording"]]
    assert len(changed) == audit["action_counts"]["REVISE"] == 82
    assert all(not r["question_id"].endswith("Q00") for r in changed)
    assert all(r["reason"] and r["transformation"] and r["semantic_slots"] for r in changed)
    with (R / "DEV_V4_TO_V5_CHANGELOG.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert {r["question_id"] for r in rows} == {r["question_id"] for r in changed}
    for r in audit["questions"]:
        assert slot_evidence(r["group_id"], r["current_wording"]) == r["slots_after"]
        assert not editorial_markers(r["current_wording"])


def test_slot_cue_lint_detects_removed_projection_but_does_not_claim_equivalence():
    data = read("dataset.json")
    text = next(q["question"] for q in data["questions"] if q["question_id"] == "WMS-CD-02-Q09")
    good = slot_evidence("WMS-CD-02", text)
    assert good["missing_cues"] == []
    bad = slot_evidence("WMS-CD-02", text.replace("đơn vị cơ sở, ", ""))
    assert "base_unit" in bad["missing_cues"]
    # Same words under a negation are not equivalent; lexical lints must not return PASS/ACCEPT.
    negated = slot_evidence("WMS-CD-02", "Không thực hiện yêu cầu sau: " + text)
    assert negated["missing_cues"] == []
    assert "human must check" in negated["interpretation"]
    assert "approved" not in negated and "equivalent" not in negated


def test_q00_review_status_and_question_sql_match_current_group_candidates():
    audit = read("dev_wording_v5_audit.json")
    registry = read("dataset.json")
    current = {q["question_id"]: q for q in registry["questions"]}
    groups = {group["group_id"]: group for group in registry["groups"]}
    with (R / "DEVELOPMENT_Q00_FINAL_REVIEW_10.csv").open(encoding="utf-8-sig", newline="") as stream:
        q00_review = {row["question_id"]: row for row in csv.DictReader(stream)}
    for q in audit["original_development_questions"]:
        if q["q_index"] == 0:
            # Q00 wording has its own explicit Owner acceptance provenance.
            assert current[q["question_id"]]["question"] == q00_review[q["question_id"]]["Q00_text"]
            assert current[q["question_id"]]["variant_review"] == "ACCEPT"
        else:
            assert current[q["question_id"]]["variant_review"] == "ACCEPT"
        assert current[q["question_id"]]["canonical_sql"] == groups[q["group_id"]]["canonical_sql"]


def test_current_development_question_text_matches_review_exports():
    current = {q["question_id"]: q for q in read("dataset.json")["questions"]}
    for filename in ("ERP_DEVELOPMENT_QUESTIONS_55.csv", "WMS_DEVELOPMENT_QUESTIONS_55.csv"):
        with (R / filename).open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                assert current[row["question_id"]]["question"] == row["Nội dung câu hỏi hiện tại"]
