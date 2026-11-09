"""Human review screen for BIRD-VN-Robust-50 draft Development groups."""

from __future__ import annotations

import json
import hashlib
import platform
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
from openai import OpenAIError

from bird_demo.benchmark.metrics import INFRA_FAILURE, SUCCESS, Observation, metric_summary
from bird_demo.benchmark.registry import load_registry, registry_hash, sha256_file
from bird_demo.data import ROOT
from bird_demo.llm import MAX_TOKENS, complete, default_model
from bird_demo.prompt import extract_sql
from bird_demo.runner import Rows, SqlError, Timeout, run

REGISTRY_PATH = ROOT / "benchmark_data/authoring/dataset.json"
RUNS_DIR = ROOT / "benchmark_data/runs"


def registry_data() -> dict:
    return load_registry(REGISTRY_PATH, allow_draft=True)


def show_result_artifact(group_id: str) -> None:
    artifacts = sorted(RUNS_DIR.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True) if RUNS_DIR.exists() else []
    if not artifacts:
        st.info("Chưa có execution artifact. SQL và wording hiện là bản nháp; expected outputs chưa được suy ra độc lập.")
        return
    selected = st.selectbox("Execution artifact", artifacts, format_func=lambda path: path.name)
    payload = json.loads(selected.read_text(encoding="utf-8"))
    st.caption(f"Run: {payload.get('run_id')} · model: {payload.get('model_id')} · registry SHA-256: {payload.get('registry_sha256')}")
    group_result = payload.get("group_records", {}).get(group_id)
    if group_result:
        st.markdown("**Canonical result recorded for this group**")
        st.json(group_result)
    question_results = [item for item in payload.get("question_records", []) if item.get("group_id") == group_id]
    if question_results:
        st.markdown("**Question-level outcomes**")
        st.dataframe([{key: item.get(key) for key in ("question_id", "status", "correct", "error")} for item in question_results], hide_index=True)
    for split, metrics in payload.get("metrics_by_split", {}).items():
        if split != "development":
            continue
        st.markdown("**Development metrics recorded in this run**")
        cols = st.columns(4)
        for col, key, label in zip(cols, ("ex_original", "ex_variants", "rss", "robust_ex_all"), ("EX Original", "EX Variants", "RSS", "Robust EX All")):
            value = metrics[key]
            col.metric(label, "N/A" if value["percent"] is None else f"{value['percent']:.1f}%", f"{value['numerator']}/{value['denominator']}")
    if payload.get("warning"):
        st.warning(payload["warning"])


def show_ground_truth_validation(group_id: str) -> None:
    expected_path = ROOT / "benchmark_data/authoring/expected_outputs_dev.json"
    validation_path = ROOT / "benchmark_data/authoring/ground_truth_validation.json"
    if not expected_path.is_file() or not validation_path.is_file():
        st.info("Expected output/oracle validation is not available for this group yet.")
        return
    expected_doc = json.loads(expected_path.read_text(encoding="utf-8"))
    validation_doc = json.loads(validation_path.read_text(encoding="utf-8"))
    expected = next((item for item in expected_doc["expected_outputs"] if item["group_id"] == group_id), None)
    observed = next((item for item in validation_doc["results"] if item["group_id"] == group_id), None)
    if not expected or not observed:
        st.info("This Final group has no executed validation artifact. Final data is not opened in the demo.")
        return
    st.subheader("Python oracle and candidate SQL result")
    st.caption(f"Status: {observed['status']} · Oracle: {expected['oracle_id']} · DB SHA-256: {observed['database_sha256']}")
    left, right = st.columns(2)
    headers = [f"column_{index+1}" for index in range(max((len(row) for row in expected["expected_rows"]), default=0))]
    with left:
        st.markdown(f"**Expected rows ({len(expected['expected_rows'])}) — derived before SQL run**")
        st.dataframe([dict(zip(headers, row)) for row in expected["expected_rows"]], hide_index=True, use_container_width=True)
    with right:
        actual_rows = observed.get("actual_rows")
        st.markdown(f"**Candidate SQL rows ({len(actual_rows) if actual_rows is not None else 0})**")
        st.dataframe([dict(zip(headers, row)) for row in (actual_rows or [])], hide_index=True, use_container_width=True)


def run_reviewed_dev_group(registry: dict, group: dict, questions: list[dict]) -> None:
    validation_path = ROOT / "benchmark_data/authoring/ground_truth_validation.json"
    validation_record = None
    if validation_path.is_file():
        validation_doc = json.loads(validation_path.read_text(encoding="utf-8"))
        validation_record = next((item for item in validation_doc.get("results", []) if item["group_id"] == group["group_id"]), None)
    released = (group.get("intent_card_status") == "APPROVED"
                and group.get("ground_truth_review") == "VALIDATED"
                and all(item.get("variant_review") == "ACCEPT" for item in questions)
                and validation_record is not None
                and validation_record.get("status") in {"VALIDATED_BY_AUTOMATION", "NEEDS_HUMAN_REVIEW"}
                and validation_record.get("canonical_sql_sha256") == group.get("canonical_sql_sha256"))
    if not released or registry.get("evaluation_freeze") is not True:
        st.info("Model-run control is locked until the Intent Card, canonical SQL, Q0, and Q1–Q10 have actual human approvals recorded.")
        return
    try:
        model_default = default_model()
    except SystemExit:
        model_default = ""
    model_id = st.text_input("Model ID (Development only)", value=model_default, key=f"model-{group['group_id']}")
    authorize_cost = st.checkbox("I authorize 11 model requests; provider usage may incur cost.", key=f"cost-{group['group_id']}")
    run_clicked = st.button("Run this Development group", type="primary", disabled=not (authorize_cost and model_id.strip()), key=f"run-{group['group_id']}")
    if not run_clicked:
        return

    db_path = ROOT / "benchmark_data/physical" / f"{group['db_id']}.sqlite"
    schema_path = ROOT / "benchmark_data/physical" / f"schema_{group['db_id']}.sql"
    ddl = schema_path.read_text(encoding="utf-8")
    # Check the validated gold first so a stale/broken snapshot costs no model calls.
    gold_result = run(db_path, group["canonical_sql_draft"])
    if not isinstance(gold_result, Rows):
        st.error(f"Canonical SQL no longer executes on the recorded snapshot: {gold_result}. No model calls were made.")
        return

    observations = {}
    records = []
    for question in questions:
        prompt = (f"{ddl}\n\n-- Benchmark business rules (synthetic): {group['card_fields']['business_rules']}\n"
                  f"-- Question (Vietnamese): {question['question']}\n"
                  "-- Use valid SQLite. Return one SELECT or WITH query only.")
        try:
            reply = complete(prompt, model_id.strip())
        except (OpenAIError, SystemExit) as error:
            records.append({"question_id": question["question_id"], "status": INFRA_FAILURE,
                            "error": str(error), "prediction_sql": None, "predicted_rows": None})
            observations[question["question_id"]] = Observation(INFRA_FAILURE)
            for remaining in questions[question["q_index"] + 1:]:
                records.append({"question_id": remaining["question_id"], "status": INFRA_FAILURE,
                                "error": "not attempted after provider failure", "prediction_sql": None, "predicted_rows": None})
                observations[remaining["question_id"]] = Observation(INFRA_FAILURE)
            break
        sql = extract_sql(reply)
        if sql is None:
            status, predicted_rows, error = "no_sql", None, "no SQL extracted from model reply"
            observation = Observation(status, correct=False)
        else:
            try:
                result = run(db_path, sql)
                if isinstance(result, Rows):
                    status, predicted_rows, error = SUCCESS, [list(row) for row in result.rows], None
                    observation = Observation(SUCCESS, result.rows,
                                              correct=set(map(tuple, result.rows)) == set(map(tuple, gold_result.rows)))
                elif isinstance(result, Timeout):
                    status, predicted_rows, error = "timeout", None, f"query exceeded {result.timeout_s:g}s"
                    observation = Observation(status, correct=False)
                elif isinstance(result, SqlError):
                    status, predicted_rows, error = "sql_error", None, result.message
                    observation = Observation(status, correct=False)
                else:
                    status, predicted_rows, error = INFRA_FAILURE, None, "unknown runner result"
                    observation = Observation(INFRA_FAILURE)
            except (OSError, sqlite3.Error) as error_value:
                status, predicted_rows, error = INFRA_FAILURE, None, str(error_value)
                observation = Observation(INFRA_FAILURE)
        observations[question["question_id"]] = observation
        records.append({"question_id": question["question_id"], "status": status,
                        "correct": observation.is_correct, "prediction_sql": sql,
                        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                        "predicted_rows": predicted_rows, "error": error, "reply_text": reply.text,
                        "finish_reason": reply.finish_reason})

    qids = [item["question_id"] for item in questions]
    summary = metric_summary([group["group_id"]], {group["group_id"]: qids}, observations)
    manifest = ROOT / "benchmark_data/physical/build_manifest.json"
    canonical_rows = [list(row) for row in gold_result.rows]
    artifact = {
        "artifact_version": 1, "benchmark_version": registry["benchmark_version"],
        "registry_sha256": registry_hash(registry),
        "run_id": f"dev-{group['group_id']}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "replicate_id": 0, "model_id": model_id.strip(), "split": "development",
        "execution": {"python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
                      "timeout_s": 30, "temperature": 0, "max_tokens": MAX_TOKENS,
                      "read_only": True, "provider_retry_policy": "SDK default; not an official evaluation run"},
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "database_artifacts": {group["db_id"]: {"database_sha256": sha256_file(db_path),
                                                "schema_sha256": sha256_file(schema_path),
                                                "build_manifest_sha256": sha256_file(manifest)}},
        "question_records": records,
        "group_records": {group["group_id"]: {"canonical_sql_sha256": group["canonical_sql_sha256"],
                                               "canonical_rows": canonical_rows,
                                               "canonical_rows_sha256": hashlib.sha256(json.dumps(canonical_rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()}},
        "metrics_by_group": summary,
        "warning": "Single Development group demonstration; not a full benchmark evaluation.",
    }
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    output = RUNS_DIR / f"{artifact['run_id']}.json"
    output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix + ".sha256").write_text(f"{digest}  {output.name}\n", encoding="ascii")
    st.success(f"Saved Development demonstration artifact: {output.name}")
    st.json(summary)


def main() -> None:
    st.set_page_config(page_title="BIRD-VN-Robust-50", layout="wide")
    st.title("BIRD-VN-Robust-50")
    st.caption("Intent review and offline run inspection · SQL/questions remain drafts until reviewed")
    try:
        registry = registry_data()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        st.error(f"Không tải được benchmark registry: {error}")
        return
    groups = [group for group in registry["groups"] if group["split"] == "development"]
    groups_by_id = {group["group_id"]: group for group in groups}
    selected_id = st.selectbox("Development group", list(groups_by_id), format_func=lambda item: f"{item} · {groups_by_id[item]['db_id']} · {groups_by_id[item]['complexity']}")
    group = groups_by_id[selected_id]
    question_rows = sorted((question for question in registry["questions"] if question["group_id"] == selected_id), key=lambda item: item["q_index"])

    st.warning(f"Trạng thái: {group['intent_card_status']} · Ground-truth: {group['ground_truth_review']} · Chưa được Benchmark Owner phê duyệt.")
    card = group["card_fields"]
    left, right = st.columns(2)
    with left:
        st.subheader("Intent Card")
        st.write({"Competency": group["competency"], "Complexity": group["complexity"], "Brief": card["brief"],
                  "Entity/grain": card["entity_grain"], "Filters/group/time": card["filters_group_time"],
                  "NULL/zero/ties": card["null_tie"], "Business rules": card["business_rules"]})
    with right:
        st.subheader("Canonical SQL candidate")
        st.caption(f"Draft SHA-256: {group['canonical_sql_sha256']} · validation: {group['validation_status']}")
        st.code(group["canonical_sql_draft"], language="sql", wrap_lines=True)
        st.caption("Chưa chạy để so với gold: expected output phải được suy ra và lưu trước.")

    st.subheader("Semantic Group · Q0–Q10")
    st.dataframe([{"ID": question["question_id"], "Index": question["q_index"], "Type": question["variant_type"],
                   "Wording": question["question"], "Review": question["variant_review"]} for question in question_rows],
                 hide_index=True, use_container_width=True)
    st.caption("Tất cả Q1–Q10 cần kiểm tra thủ công từng semantic slot; nhãn tự động không phải ACCEPT.")
    show_ground_truth_validation(selected_id)
    run_reviewed_dev_group(registry, group, question_rows)
    show_result_artifact(selected_id)


main()
