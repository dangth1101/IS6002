"""Run the full registry/evaluator path on temporary SQLite fixtures and mock SQL outputs."""

from __future__ import annotations

import json
import hashlib
import sqlite3
import tempfile
from copy import deepcopy
from contextlib import closing
from pathlib import Path

from bird_demo.benchmark.evaluator import evaluate_saved_predictions
from bird_demo.data import ROOT


def main() -> None:
    source = json.loads((ROOT / "benchmark_data/authoring/dataset.json").read_text(encoding="utf-8"))
    registry = deepcopy(source)
    for group in registry["groups"]:
        group["canonical_sql"] = "SELECT value FROM smoke_item"
        group["canonical_sql_draft"] = "SELECT value FROM smoke_item"
        group["canonical_sql_sha256"] = hashlib.sha256(b"SELECT value FROM smoke_item").hexdigest()
    for question in registry["questions"]:
        question["canonical_sql"] = "SELECT value FROM smoke_item"
    predictions = {"predictions": [{"question_id": question["question_id"], "reply_text": "```sql\nSELECT value FROM smoke_item\n```", "finish_reason": "stop"} for question in registry["questions"]]}
    output = ROOT / "benchmark_data/runs/offline_smoke.json"
    temp_parent = ROOT / "benchmark_data" / "pytest_tmp"
    temp_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bird-vn-smoke-", dir=temp_parent) as tmp:
        fixture_root = Path(tmp)
        physical = fixture_root / "benchmark_data" / "physical"
        physical.mkdir(parents=True)
        for db_id in ("erp_sales", "wms_inventory"):
            db_path = physical / f"{db_id}.sqlite"
            with closing(sqlite3.connect(db_path)) as connection:
                connection.execute("CREATE TABLE smoke_item (value INTEGER NOT NULL)")
                connection.execute("INSERT INTO smoke_item VALUES (1)")
                connection.commit()
            (physical / f"schema_{db_id}.sql").write_text("CREATE TABLE smoke_item(value INTEGER NOT NULL);", encoding="utf-8")
        registry_path = fixture_root / "dataset.json"
        predictions_path = fixture_root / "predictions.json"
        registry_path.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
        predictions_path.write_text(json.dumps(predictions, ensure_ascii=False), encoding="utf-8")
        artifact = evaluate_saved_predictions(repository_root=fixture_root, registry_path=registry_path,
                                              predictions_path=predictions_path, output_path=output,
                                              model_id="offline-fixture-identical-sql", run_id="synthetic-smoke",
                                              allow_draft=True)
    print(f"Synthetic offline smoke complete: {len(artifact['question_records'])} mock predictions.")
    print(f"Development EX: {artifact['metrics_by_split']['development']['ex_overall']['numerator']}/"
          f"{artifact['metrics_by_split']['development']['ex_overall']['denominator']}; artifact: {output.relative_to(ROOT)}")
    print("This 100% mock result is a pipeline check, not empirical model performance.")


if __name__ == "__main__":
    main()
