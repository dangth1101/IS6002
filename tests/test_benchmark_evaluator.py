import json
import hashlib
import sqlite3
from copy import deepcopy
from pathlib import Path

from bird_demo.benchmark.evaluator import evaluate_saved_predictions
from bird_demo.benchmark.registry import load_registry
from bird_demo.data import ROOT


def test_offline_evaluator_records_run_hashes_and_metrics(tmp_path):
    root = tmp_path
    physical = root / "benchmark_data" / "physical"
    physical.mkdir(parents=True)
    for db in ("erp_sales", "wms_inventory"):
        path = physical / f"{db}.sqlite"
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE item (id INTEGER PRIMARY KEY, label TEXT)")
        conn.execute("INSERT INTO item VALUES (1, 'x')")
        conn.commit()
        conn.close()
        (physical / f"schema_{db}.sql").write_text("CREATE TABLE item(id INTEGER PRIMARY KEY, label TEXT)", encoding="utf-8")

    project_root = Path(__file__).resolve().parents[1]
    registry_doc = json.loads((project_root / "benchmark_data/authoring/dataset.json").read_text(encoding="utf-8"))
    registry_doc = deepcopy(registry_doc)
    for group in registry_doc["groups"]:
        group["ground_truth_review"] = "NEEDS_HUMAN_REVIEW"
        group["canonical_sql_sha256"] = hashlib.sha256(b"SELECT id FROM item").hexdigest()
    questions = registry_doc["questions"]
    for question in questions:
        question["canonical_sql"] = "SELECT id FROM item"
    predictions = [{"question_id": question["question_id"], "sql": "SELECT id FROM item"} for question in questions]
    registry = root / "registry.json"
    predictions_path = root / "predictions.json"
    output = root / "run.json"
    registry.write_text(json.dumps(registry_doc), encoding="utf-8")
    predictions_path.write_text(json.dumps({"predictions": predictions}), encoding="utf-8")

    artifact = evaluate_saved_predictions(
        repository_root=root,
        registry_path=registry,
        predictions_path=predictions_path,
        output_path=output,
        allow_draft=True,
    )
    assert len(artifact["question_records"]) == 550
    assert artifact["metrics_by_split"]["development"]["ex_overall"]["percent"] == 100.0
    assert artifact["metrics_by_split"]["final"]["robust_ex_all"]["numerator"] == 40
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["database_artifacts"]["erp_sales"]["database_sha256"]
    assert saved["execution"]["read_only"] is True
    assert "not an empirical model result" in saved["warning"]
    assert output.with_suffix(output.suffix + ".sha256").is_file()


def test_frozen_snapshot_blocks_draft_gold_execution_before_loading_predictions():
    registry = ROOT / "benchmark_data/authoring/dataset.json"
    try:
        load_registry(registry)
    except ValueError as error:
        assert "unreviewed" in str(error)
    else:
        raise AssertionError("unreviewed dataset must not pass the release gate")
    try:
        evaluate_saved_predictions(
            repository_root=ROOT,
            registry_path=registry,
            predictions_path=ROOT / "does-not-exist.json",
            output_path=ROOT / "benchmark_data/runs/should-not-exist.json",
            allow_draft=True,
        )
    except ValueError as error:
        assert "Refusing to execute draft canonical SQL" in str(error)
    else:
        raise AssertionError("draft ground-truth execution on frozen snapshots must be blocked")


def test_canonical_sql_error_blocks_evaluation_instead_of_counting_as_model_outcome(tmp_path):
    root = tmp_path
    physical = root / "benchmark_data" / "physical"
    physical.mkdir(parents=True)
    for db in ("erp_sales", "wms_inventory"):
        path = physical / f"{db}.sqlite"
        with sqlite3.connect(path) as connection:
            connection.execute("CREATE TABLE item(id INTEGER PRIMARY KEY)")
        (physical / f"schema_{db}.sql").write_text("CREATE TABLE item(id INTEGER PRIMARY KEY)", encoding="utf-8")
    source = json.loads((ROOT / "benchmark_data/authoring/dataset.json").read_text(encoding="utf-8"))
    source = deepcopy(source)
    for group in source["groups"]:
        group["canonical_sql"] = "SELECT missing_column FROM item"
        group["canonical_sql_draft"] = "SELECT missing_column FROM item"
        group["canonical_sql_sha256"] = hashlib.sha256(b"SELECT missing_column FROM item").hexdigest()
    for question in source["questions"]:
        question["canonical_sql"] = "SELECT missing_column FROM item"
    registry = root / "registry.json"
    registry.write_text(json.dumps(source), encoding="utf-8")
    predictions = root / "predictions.json"
    predictions.write_text(json.dumps({"predictions": [{"question_id": q["question_id"], "sql": "SELECT id FROM item"} for q in source["questions"]]}), encoding="utf-8")
    try:
        evaluate_saved_predictions(repository_root=root, registry_path=registry,
                                  predictions_path=predictions, output_path=root / "run.json",
                                  allow_draft=True)
    except ValueError as error:
        assert "Canonical SQL" in str(error)
    else:
        raise AssertionError("failed canonical SQL must block evaluation")
