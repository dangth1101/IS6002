"""Offline evaluation of saved model outputs; this module never calls an LLM."""

from __future__ import annotations

import json
import hashlib
import platform
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bird_demo.runner import Rows, SqlError, Timeout, run
from bird_demo.llm import Reply
from bird_demo.prompt import extract_sql

from .metrics import INFRA_FAILURE, SUCCESS, Observation, metric_summary, result_equal
from .registry import load_registry, registry_hash, sha256_file


def _db_path(root: Path, db_id: str) -> Path:
    if db_id not in {"erp_sales", "wms_inventory"}:
        raise ValueError(f"Unknown benchmark database {db_id!r}")
    return root / "benchmark_data" / "physical" / f"{db_id}.sqlite"


def _run(path: Path, sql: str | None, timeout_s: float) -> tuple[str, list[list[Any]] | None, str | None]:
    if sql is None or not sql.strip():
        return "no_sql", None, "no SQL supplied"
    try:
        result = run(path, sql, timeout_s=timeout_s)
    except (OSError, sqlite3.Error) as error:
        return INFRA_FAILURE, None, str(error)
    if isinstance(result, Timeout):
        return "timeout", None, f"query exceeded {result.timeout_s:g}s"
    if isinstance(result, SqlError):
        return "sql_error", None, result.message
    if isinstance(result, Rows):
        return SUCCESS, [list(row) for row in result.rows], None
    return INFRA_FAILURE, None, f"unknown runner result {type(result).__name__}"


def evaluate_saved_predictions(
    *,
    repository_root: Path,
    registry_path: Path,
    predictions_path: Path,
    output_path: Path,
    model_id: str = "offline-fixture",
    run_id: str = "offline",
    replicate_id: int = 0,
    timeout_s: float = 30.0,
    allow_draft: bool = False,
) -> dict[str, Any]:
    """Run each prediction read-only, compare to canonical SQL, and save provenance.

    Input predictions JSON is {"predictions": [{"question_id": ..., "sql": ...,
    "status": "infra_error" (optional)}]}. No model client is imported or invoked.
    """
    registry = load_registry(registry_path, allow_draft=allow_draft)
    physical_manifest = repository_root / "benchmark_data" / "physical" / "build_manifest.json"
    if allow_draft and physical_manifest.exists():
        pending_gold = [group["group_id"] for group in registry["groups"]
                        if group.get("intent_card_status") != "APPROVED"
                        or group.get("ground_truth_review") != "VALIDATED"
                        or group.get("expected_output") is None
                        or not group.get("expected_outputs_derived_before_sql_execution")]
        pending_variants = [question["question_id"] for question in registry["questions"]
                            if question.get("variant_review") != "ACCEPT"]
        pending_gold.extend(pending_variants)
        if pending_gold:
            raise ValueError("Refusing to execute draft canonical SQL on frozen snapshots before independent expected outputs and human validation: "
                             + ", ".join(pending_gold[:5]))
    prediction_doc = json.loads(predictions_path.read_text(encoding="utf-8"))
    prediction_map: dict[str, dict[str, Any]] = {}
    for item in prediction_doc.get("predictions", []):
        qid = item["question_id"]
        if qid in prediction_map:
            raise ValueError(f"Duplicate prediction for {qid}")
        normalized = dict(item)
        if "sql" not in normalized and "reply_text" in normalized:
            normalized["sql"] = extract_sql(Reply(normalized["reply_text"], normalized.get("finish_reason", "stop")))
        prediction_map[qid] = normalized
    question_map = {item["question_id"]: item for item in registry["questions"]}
    group_map = {item["group_id"]: item for item in registry["groups"]}
    if set(prediction_map) != set(question_map):
        missing = sorted(set(question_map) - set(prediction_map))
        extra = sorted(set(prediction_map) - set(question_map))
        raise ValueError(f"Prediction coverage mismatch: missing={missing[:5]}, extra={extra[:5]}")

    observations: dict[str, Observation] = {}
    records: list[dict[str, Any]] = []
    database_meta: dict[str, dict[str, str]] = {}
    gold_cache: dict[str, tuple[str, list[list[Any]] | None, str | None, str | None]] = {}
    group_results: dict[str, dict[str, Any]] = {}
    for question in registry["questions"]:
        qid = question["question_id"]
        group_id = question["group_id"]
        path = _db_path(repository_root, question["db_id"])
        if path.is_file():
            if question["db_id"] not in database_meta:
                schema_file = repository_root / "benchmark_data" / "physical" / f"schema_{question['db_id']}.sql"
                manifest_file = repository_root / "benchmark_data" / "physical" / "build_manifest.json"
                manifest = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.exists() else {}
                db_key = question["db_id"]
                db_entry = manifest.get("databases", {}).get(db_key, {})
                schema_entry = manifest.get("schemas", {}).get(db_key, {})
                actual_db_hash = sha256_file(path)
                actual_schema_hash = sha256_file(schema_file) if schema_file.exists() else "missing"
                expected_db_hash = db_entry.get("sha256")
                expected_schema_hash = schema_entry.get("sha256")
                if expected_db_hash and expected_db_hash != actual_db_hash:
                    raise ValueError(f"Database hash mismatch for {db_key}: manifest={expected_db_hash}, actual={actual_db_hash}")
                if expected_schema_hash and expected_schema_hash != actual_schema_hash:
                    raise ValueError(f"Schema hash mismatch for {db_key}: manifest={expected_schema_hash}, actual={actual_schema_hash}")
                database_meta[question["db_id"]] = {
                    "database_sha256": actual_db_hash,
                    "schema_sha256": actual_schema_hash,
                    "schema_version": manifest.get("schema_version"),
                    "build_manifest_sha256": sha256_file(manifest_file) if manifest_file.exists() else "missing",
                }
        if group_id not in gold_cache:
            if not path.is_file():
                gold_cache[group_id] = (INFRA_FAILURE, None, f"missing database: {path.name}", None)
                group_results[group_id] = {"canonical_sql_sha256": question.get("canonical_sql_sha256"),
                                           "status": INFRA_FAILURE, "canonical_rows": None,
                                           "canonical_rows_sha256": None,
                                           "error": f"missing database: {path.name}"}
            else:
                sql_text = question.get("canonical_sql")
                actual_sql_hash = hashlib.sha256((sql_text or "").encode("utf-8")).hexdigest()
                recorded_sql_hash = group_map[group_id].get("canonical_sql_sha256")
                if recorded_sql_hash and recorded_sql_hash != actual_sql_hash:
                    raise ValueError(f"Canonical SQL hash mismatch for {group_id}")
                gold_status, gold_rows, gold_error = _run(path, sql_text, timeout_s)
                if gold_status not in (SUCCESS, INFRA_FAILURE):
                    raise ValueError(f"Canonical SQL for {group_id} failed ({gold_status}): {gold_error}")
                # EX is only meaningful when the reviewed canonical query returns
                # a successful result. Treat a failed gold query as a blocked run,
                # not as infrastructure missingness or a score of zero.
                if gold_status != SUCCESS:
                    raise ValueError(f"Canonical SQL for {group_id} is not executable ({gold_status}): {gold_error}")
                sql_hash = recorded_sql_hash or actual_sql_hash
                if gold_status == SUCCESS and gold_rows is not None:
                    rows_hash = hashlib.sha256(json.dumps(gold_rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
                else:
                    rows_hash = None
                gold_cache[group_id] = (gold_status, gold_rows, gold_error, rows_hash)
                group_results[group_id] = {"canonical_sql_sha256": sql_hash, "status": gold_status,
                                           "canonical_rows": gold_rows, "canonical_rows_sha256": rows_hash,
                                           "error": gold_error}
        gold_status, gold_rows, gold_error, _ = gold_cache[group_id]
        if gold_status != SUCCESS:
            outcome, rows, error = INFRA_FAILURE, None, f"canonical SQL failed ({gold_status}): {gold_error}"
        else:
            supplied = prediction_map[qid]
            if supplied.get("status") == INFRA_FAILURE:
                outcome, rows, error = INFRA_FAILURE, None, supplied.get("error", "mock infrastructure failure")
            else:
                outcome, rows, error = _run(path, supplied.get("sql"), timeout_s)
                if outcome == SUCCESS:
                    correct = result_equal(rows or [], gold_rows or [])
                else:
                    correct = False if outcome != INFRA_FAILURE else None
        if outcome == SUCCESS:
            observations[qid] = Observation(outcome, rows, correct)
        elif outcome == INFRA_FAILURE:
            observations[qid] = Observation(outcome)
        else:
            observations[qid] = Observation(outcome, correct=False)
        records.append({
            "question_id": qid,
            "group_id": question["group_id"],
            "q_index": question["q_index"],
            "db_id": question["db_id"],
            "split": question["split"],
            "status": outcome,
            "correct": observations[qid].is_correct,
            "canonical_status": gold_status,
            "canonical_rows_sha256": gold_cache[group_id][3],
            "predicted_rows": rows,
            "error": error,
            "prediction_sql": prediction_map[qid].get("sql"),
        })

    splits: dict[str, Any] = {}
    for split in ("development", "final"):
        split_groups = [g for g in registry["groups"] if g["split"] == split]
        if not split_groups:
            continue
        group_ids = [g["group_id"] for g in split_groups]
        qids = {g["group_id"]: [q["question_id"] for q in sorted(
            (item for item in registry["questions"] if item["group_id"] == g["group_id"]),
            key=lambda item: item["q_index"],
        )] for g in split_groups}
        selected = {qid: observations[qid] for values in qids.values() for qid in values}
        splits[split] = metric_summary(group_ids, qids, selected)

    artifact = {
        "artifact_version": 1,
        "benchmark_version": registry.get("benchmark_version"),
        "registry_sha256": registry_hash(registry),
        "run_id": run_id,
        "replicate_id": replicate_id,
        "model_id": model_id,
        "execution": {"python": platform.python_version(), "sqlite": sqlite3.sqlite_version, "timeout_s": timeout_s, "read_only": True},
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "database_artifacts": database_meta,
        "question_records": records,
        "group_records": group_results,
        "metrics_by_split": splits,
        "warning": "Offline/mock evaluation only; not an empirical model result." if model_id.startswith("offline") else None,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(artifact, ensure_ascii=False, indent=2)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    temp_path.write_text(payload, encoding="utf-8")
    temp_path.replace(output_path)
    artifact_hash = hashlib.sha256(output_path.read_bytes()).hexdigest()
    output_path.with_suffix(output_path.suffix + ".sha256").write_text(f"{artifact_hash}  {output_path.name}\n", encoding="ascii")
    return artifact
