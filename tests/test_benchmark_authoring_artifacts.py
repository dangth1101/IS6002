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
    validation_records = json.loads((AUTHORING / "validation_records.json").read_text(encoding="utf-8"))
    registry = json.loads((AUTHORING / "dataset.json").read_text(encoding="utf-8"))
    assert defects["open_defect_count"] == 35
    assert len(expected["expected_outputs"]) == len(DEV_ORACLES) == 10
    assert all(record["derived_before_canonical_sql_execution"] for record in expected["expected_outputs"])
    assert validation["summary"] == {"VALIDATED_BY_AUTOMATION": 10, "NEEDS_HUMAN_REVIEW": 0, "BLOCKED": 0}
    assert validation["all_group_status_summary"] == {"VALIDATED_BY_AUTOMATION": 10, "NEEDS_HUMAN_REVIEW": 0, "BLOCKED": 40}
    main_results = {record["group_id"]: record for record in validation["results"]}
    registry_groups = {group["group_id"]: group for group in registry["groups"]}
    for group_id, machine in main_results.items():
        assert registry_groups[group_id]["validation_status"] == machine["status"]
        assert registry_groups[group_id]["ground_truth_review"] == "NEEDS_HUMAN_REVIEW"
        assert registry_groups[group_id]["intent_card_status"] == "NEEDS_HUMAN_REVIEW"
    assert all(main_results["ERP-RK-02"]["business_rule_checks"].values())
    assert all(len(row) == 5 for row in main_results["ERP-RK-02"]["actual_rows"])
    assert all(len(row) == 5 for row in next(x for x in expected["expected_outputs"] if x["group_id"] == "ERP-RK-02")["expected_rows"])
    assert "SELECT sku,product_name,base_unit,sold_qty_milli,rnk" in registry_groups["ERP-RK-02"]["canonical_sql_draft"]
    assert registry_groups["ERP-RK-02"]["projection_alignment_decision"]["option"] == "B"
    assert registry_groups["ERP-RK-02"]["projection_alignment_decision"]["status"] == "RESOLVED_BY_BENCHMARK_OWNER"
    assert all(main_results["WMS-CD-02"]["business_rule_checks"].values())
    assert all(record["human_review_status"] == "NEEDS_HUMAN_REVIEW"
               and record["owner_approval"]["status"] == "PENDING"
               for record in validation_records if record["group_id"] in DEV_ORACLES)


def test_dev_fixture_expected_outputs_precede_sql_and_all_six_fixtures_pass():
    expected = json.loads((AUTHORING / "dev_fixture_expected_outputs.json").read_text(encoding="utf-8"))
    validation = json.loads((AUTHORING / "dev_fixture_validation.json").read_text(encoding="utf-8"))
    assert expected["stage"] == "EXPECTED_OUTPUTS_FROZEN_BEFORE_CANDIDATE_SQL_EXECUTION"
    assert all(item["derived_before_candidate_sql_execution"] for item in expected["expected_outputs"])
    assert validation["summary"] == {"PASS": 6, "FAIL": 0}
    by_id = {item["group_id"]: item for item in validation["results"]}
    assert by_id["ERP-RK-02"]["checks"]["unit_partition_and_rank3_tie_pass"]
    assert by_id["ERP-RK-02"]["checks"]["five_column_projection"]
    assert by_id["WMS-CD-02"]["checks"]["transfer_not_double_counted"]
    assert by_id["WMS-CD-02"]["checks"]["nonposted_zero_pass"]
    assert by_id["WMS-CD-02"]["checks"]["posted_invariant_pass"]
    assert validation["snapshot_immutable"] is True


def test_expected_outputs_are_bound_to_the_frozen_snapshot_hashes():
    expected = json.loads((AUTHORING / "expected_outputs_dev.json").read_text(encoding="utf-8"))
    for record in expected["expected_outputs"]:
        db_path = ROOT / "benchmark_data/physical" / f"{record['group_id'].split('-')[0].lower()}_sales.sqlite"
        if record["group_id"].startswith("WMS"):
            db_path = ROOT / "benchmark_data/physical/wms_inventory.sqlite"
        assert sha256_file(db_path) == record["database_sha256"]
