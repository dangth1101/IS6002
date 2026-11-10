"""Guard wording-only lineage and pending human gates, not linguistic correctness."""
import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

from bird_demo.benchmark.registry import load_registry
from scripts.dev_wording_slot_checks import editorial_markers, slot_evidence

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "benchmark_data/authoring"
R = ROOT / "docs/benchmark/review/dev_human_approval"


def read(name):
    return json.loads((A / name).read_text(encoding="utf-8"))


def test_wording_lineage_keeps_contracts_evidence_and_exports_in_sync():
    result = subprocess.run([sys.executable, str(ROOT / "scripts/audit_dev_wording_v5.py")],
                            cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["verification"] == "PASS"


def test_draft_wording_does_not_bypass_release_approval():
    with pytest.raises(ValueError, match="unreviewed items; release blocked"):
        load_registry(A / "dataset.json")
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


def test_q00_objects_and_dev_question_sql_equal_original_pinned_source():
    audit = read("dev_wording_v5_audit.json")
    current = {q["question_id"]: q for q in read("dataset.json")["questions"]}
    for q in audit["original_development_questions"]:
        if q["q_index"] == 0:
            assert current[q["question_id"]] == q
        assert current[q["question_id"]]["canonical_sql"] == q["canonical_sql"]
        assert current[q["question_id"]]["variant_review"] == q["variant_review"]
