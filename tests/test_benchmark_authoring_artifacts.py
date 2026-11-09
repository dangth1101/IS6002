import json
from pathlib import Path

from bird_demo.data import ROOT
from bird_demo.benchmark.registry import load_registry, sha256_file
from bird_vn_benchmark.intent_oracles import DEV_ORACLES


AUTHORING = ROOT / "benchmark_data/authoring"


def test_draft_registry_has_quota_split_and_no_auto_approvals():
    registry = load_registry(AUTHORING / "dataset.json", allow_draft=True)
    assert len(registry["groups"]) == 50
    assert len(registry["questions"]) == 550
    assert sum(group["split"] == "development" for group in registry["groups"]) == 10
    assert all(group["ground_truth_review"] == "NEEDS_HUMAN_REVIEW" for group in registry["groups"])
    assert all(question["variant_review"] == "NEEDS_HUMAN_REVIEW" for question in registry["questions"])


def test_draft_sql_static_check_never_executes_result_rows():
    evidence = json.loads((AUTHORING / "draft_validation.json").read_text(encoding="utf-8"))
    assert evidence["static_sql_summary"] == {"pass": 50, "fail": 0, "rows_executed": False}


def test_open_fixture_defects_and_dev_oracle_coverage_are_explicit():
    defects = json.loads((AUTHORING / "defect_report.json").read_text(encoding="utf-8"))
    expected = json.loads((AUTHORING / "expected_outputs_dev.json").read_text(encoding="utf-8"))
    validation = json.loads((AUTHORING / "ground_truth_validation.json").read_text(encoding="utf-8"))
    assert defects["open_defect_count"] == 41
    assert len(expected["expected_outputs"]) == len(DEV_ORACLES) == 10
    assert all(record["derived_before_canonical_sql_execution"] for record in expected["expected_outputs"])
    assert validation["summary"] == {"VALIDATED_BY_AUTOMATION": 4, "NEEDS_HUMAN_REVIEW": 6, "BLOCKED": 0}
    assert validation["all_group_status_summary"] == {"VALIDATED_BY_AUTOMATION": 4, "NEEDS_HUMAN_REVIEW": 6, "BLOCKED": 40}


def test_expected_outputs_are_bound_to_the_frozen_snapshot_hashes():
    expected = json.loads((AUTHORING / "expected_outputs_dev.json").read_text(encoding="utf-8"))
    for record in expected["expected_outputs"]:
        db_path = ROOT / "benchmark_data/physical" / f"{record['group_id'].split('-')[0].lower()}_sales.sqlite"
        if record["group_id"].startswith("WMS"):
            db_path = ROOT / "benchmark_data/physical/wms_inventory.sqlite"
        assert sha256_file(db_path) == record["database_sha256"]
