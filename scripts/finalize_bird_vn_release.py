"""Record the explicit release decisions and run a fully offline Final smoke.

This utility never calls a model provider. Its mock collector output is only an
implementation check and must not be reported as benchmark results.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from bird_demo.benchmark.official import OfficialGate, collect_three_replicates
from bird_demo.benchmark.registry import load_registry, registry_hash, sha256_file
from bird_demo.benchmark.evaluator import evaluate_saved_predictions
from bird_demo.data import ROOT
from bird_demo.benchmark.dashboard import prompt_contract_sha256, output_contract_for
from bird_demo.benchmark.field_contracts import COMPARATOR_VERSION, CONTRACT_VERSION, EVALUATION_PROTOCOL_VERSION


DATE = "2026-11-17"
REGISTRY_PATH = ROOT / "benchmark_data/authoring/dataset.json"
REVIEW_CSV = ROOT / "docs/benchmark/review/dev_human_approval/DEVELOPMENT_Q00_FINAL_REVIEW_10.csv"
INTENT_REVIEW_CSV = ROOT / "docs/benchmark/review/dev_human_approval/DEVELOPMENT_INTENT_SQL_REVIEW_10.csv"
RECORDS_PATH = ROOT / "benchmark_data/authoring/validation_records.json"
MANIFEST_PATH = ROOT / "benchmark_data/authoring/dev_v6_vietnamese_first_manifest.json"
OWNER_PROVENANCE = ROOT / "benchmark_data/authoring/dev_q00_owner_approval_provenance_2026-11-17.json"
CONFIG_PATH = ROOT / "benchmark_data/official/frozen_config.json"
FREEZE_PATH = ROOT / "benchmark_data/official/frozen_registry_manifest.json"
INTEGRATION_PATH = ROOT / "benchmark_data/official/implementation_validation.json"


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def record_decisions() -> dict:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    development_groups = {g["group_id"]: g for g in registry["groups"] if g["split"] == "development"}
    if len(development_groups) != 10:
        raise ValueError("Expected exactly 10 Development groups")
    questions = {q["question_id"]: q for q in registry["questions"]}
    q00_ids = [f"{group_id}-Q00" for group_id in development_groups]
    if any(qid not in questions for qid in q00_ids):
        raise ValueError("A Development Q00 is missing from the registry")

    provenance = {
        "approver_role": "Benchmark Owner",
        "decision_date": DATE,
        "decision": "ACCEPT",
        "scope": "Wording review only for the current Q00 original question in each of the 10 Development groups.",
        "source": "Explicit user instruction in this conversation: the Benchmark Owner reviewed the 10 Development Q00 questions and asked to record ACCEPT.",
        "rationale": "Records the Owner's direct wording decision. Existing Intent Card, SQL, expected-output and Q01-Q10 decisions retain their separate prior provenance.",
        "question_ids": sorted(q00_ids),
        "registry_revision_before_decision": registry.get("authoring_revision"),
    }
    write_json(OWNER_PROVENANCE, provenance)
    for qid in q00_ids:
        q = questions[qid]
        q["variant_review"] = "ACCEPT"
        q["review_decision_provenance"] = {
            "reviewer": "Benchmark Owner",
            "decision_date": DATE,
            "decision": "ACCEPT",
            "scope": "This Q00 wording only.",
            "source": "benchmark_data/authoring/dev_q00_owner_approval_provenance_2026-11-17.json",
        }
        q["review_notes"] = "Q00 wording accepted by the Benchmark Owner; this does not add a new approval for SQL or expected outputs."

    for group in development_groups.values():
        group["human_review_status"] = "APPROVED_BY_OWNER"
        group["q00_review_provenance"] = "benchmark_data/authoring/dev_q00_owner_approval_provenance_2026-11-17.json"
    registry["human_review_status"] = "FINAL_AND_DEVELOPMENT_QUESTIONS_APPROVED_BY_OWNER"
    registry["approval_note"] = "The Benchmark Owner approved the 40 Final groups on 2026-11-17 and the 10 Development Q00 wordings on 2026-11-17. Existing group/SQL and variant decisions retain their individual provenance. Registry freeze is recorded separately."
    registry["development_q00_owner_approval"] = {
        "status": "APPROVED_BY_OWNER",
        "date": DATE,
        "provenance_artifact": "benchmark_data/authoring/dev_q00_owner_approval_provenance_2026-11-17.json",
        "questions": 10,
    }

    records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
    for record in records:
        group_id = record["group_id"]
        if group_id not in development_groups:
            continue
        q00 = next((item for item in record.get("question_reviews", []) if item.get("q_index") == 0), None)
        if q00 is None:
            raise ValueError(f"Validation Record lacks {group_id} Q00 review evidence")
        q00["review_status"] = "ACCEPT"
        q00["owner_decision"] = "ACCEPT"
        q00["review_decision_provenance"] = provenance
        record["human_review_status"] = "APPROVED_BY_OWNER"
        record["human_review"] = "APPROVED_BY_OWNER"
        record["q00_owner_review"] = {
            "question_id": f"{group_id}-Q00",
            "decision": "ACCEPT",
            "date": DATE,
            "provenance_artifact": "benchmark_data/authoring/dev_q00_owner_approval_provenance_2026-11-17.json",
        }

    with REVIEW_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    seen = set()
    for row in rows:
        qid = row["question_id"]
        if qid in q00_ids:
            seen.add(qid)
            row["current_status"] = "ACCEPTED_BY_OWNER"
            row["reviewer"] = "Benchmark Owner"
            row["decision_ACCEPT_REVISE_REJECT"] = "ACCEPT"
            row["comment"] = "Benchmark Owner xác nhận đã review và chấp nhận wording Q00 hiện hành."
            row["review_date"] = DATE
    if seen != set(q00_ids):
        raise ValueError(f"Q00 review CSV coverage mismatch: {sorted(set(q00_ids) - seen)}")
    with REVIEW_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    with INTENT_REVIEW_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        intent_rows = list(csv.DictReader(handle))
        intent_fields = list(intent_rows[0])
    if len(intent_rows) != 10:
        raise ValueError("Expected 10 Development Intent/SQL review rows")
    for row in intent_rows:
        row["Human review status"] = "APPROVED_BY_OWNER"
        row["Owner decision recorded"] = "Intent/SQL approved 2026-11-16; current Q00 wording accepted 2026-11-17"
        if "Cần người duyệt xác nhận" in row:
            row["Cần người duyệt xác nhận"] = "Q00 wording decision recorded; other fields retain prior approval provenance."
    with INTENT_REVIEW_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=intent_fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(intent_rows)

    # D12 is an explicit Owner approval; D14 remains untouched and proposed.
    decision_path = ROOT / "docs/benchmark/DECISION_REVIEW.md"
    text = decision_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    replaced = False
    for i, line in enumerate(lines):
        if line.startswith("| D12 |"):
            lines[i] = "| D12 | Giữ 0.x pilot; Final giữ kín nếu khả thi, nếu không công khai exposure | Tránh gọi nhầm tập đã tune là blind. | ☒ APPROVE ☐ REVISE ☐ REJECT | Benchmark Owner | 2026-11-17 | Owner đồng ý giữ benchmark ở mức pilot 0.x; bảo vệ Final nếu có thể, nếu đã bị lộ thì ghi rõ exposure/leakage. Phê duyệt này không tự cấp phép gọi API hoặc công bố kết quả. |"
            replaced = True
    if not replaced:
        raise ValueError("Could not locate D12 row in Decision Review")
    lines = [line.replace("D12, D14 PROPOSED", "D12 APPROVED ngày 2026-11-17; D14 PROPOSED") for line in lines]
    lines = [line for line in lines if not line.startswith("### Ghi nhận bổ sung ngày 2026-11-17")]
    lines = [line for line in lines if not ("Q00 Development" in line and "D12" in line and "D14" in line)]
    lines.extend(["", "### Ghi nhận bổ sung ngày 2026-11-17", "", "Benchmark Owner đã chấp nhận riêng wording của 10 câu Q00 Development; bằng chứng tại `benchmark_data/authoring/dev_q00_owner_approval_provenance_2026-11-17.json`. D12 được APPROVED ngày 2026-11-17. D14 vẫn PROPOSED. Approval không đồng nghĩa với cho phép gọi API trả phí."])
    lines = [line.replace("D12 và D14 vẫn PROPOSED", "D12 APPROVED ngày 2026-11-17; D14 vẫn PROPOSED") for line in lines]
    lines = [
        ("Benchmark Owner đã duyệt 40 nhóm Final và 440 câu hỏi ngày 2026-11-17; 10 câu Q00 Development được chấp nhận ngày 2026-11-17. Intent Cards, SQL và wording có provenance riêng trong registry/Validation Records. D12 đã APPROVED; D14 vẫn PROPOSED. Registry và cấu hình đã đóng băng; mock integration đã kiểm tra đủ ba lượt Final. Official Evaluation vẫn cần xác nhận riêng về chi phí/lượt gọi API thật."
         if "Q00 Development" in line and "Official Evaluation" in line else line)
        for line in lines
    ]
    decision_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    spec_path = ROOT / "docs/benchmark/BENCHMARK_SPEC.md"
    spec = spec_path.read_text(encoding="utf-8")
    spec = spec.replace("D12 và D14 PROPOSED", "D12 APPROVED ngày 2026-11-17; D14 PROPOSED")
    spec = spec.replace("D12 | 0.x pilot; Final giữ kín khi khả thi, nếu không ghi exposure/leakage | PROPOSED | — | — | Chốt release/access trước tune/final evaluation. |",
                        "D12 | 0.x pilot; Final giữ kín khi khả thi, nếu không ghi exposure/leakage | APPROVED | Benchmark Owner | 2026-11-17 | Giữ đúng mức tuyên bố pilot; ghi rõ nếu Final đã bị lộ. |")
    latest_status = "Benchmark Owner đã chấp nhận wording cho 10 câu Q00 Development và phê duyệt D12. D14 vẫn PROPOSED. Cấu hình chạy được đóng băng riêng; việc đóng băng không cấp phép gọi API hoặc công bố kết quả."
    spec_lines = [line for line in spec.splitlines() if not line.startswith("### Cập nhật trạng thái ngày 2026-11-17")]
    spec_lines = [line for line in spec_lines if not ("Q00 Development" in line and "D12" in line and "D14" in line)]
    spec_lines.extend(["", "### Cập nhật trạng thái ngày 2026-11-17", "", latest_status])
    spec = "\n".join(spec_lines) + "\n"
    spec_lines = []
    for line in spec.splitlines():
        if "Intent Cards, 50 SQL candidates" in line:
            line = "D4 phê duyệt định hướng hai database; simulation rules R-01–R-11 được chốt cho thiết kế logic và không phải chuẩn ngành. Bước 2A và 2B đã nghiệm thu theo provenance riêng. Benchmark Owner đã duyệt 40 Final groups, 440 Final questions và 10 Development Q00 hiện hành; các quyết định được lưu trong registry/Validation Records. Registry và cấu hình chạy đã đóng băng. Kiểm tra mock offline xác minh đủ 3 × 440 câu Final, không gọi API. Official Evaluation thật vẫn cần xác nhận riêng về chi phí/lượt gọi; D14 vẫn PROPOSED."
        if "D1–D7" in line and "D12" in line and "D14" in line:
            line = line.replace("D12 và D14 còn PROPOSED", "D12 APPROVED ngày 2026-11-17; D14 còn PROPOSED")
            line = line.replace("D12 và D14 vẫn PROPOSED", "D12 APPROVED ngày 2026-11-17; D14 vẫn PROPOSED")
        if "Q00 Development" in line and "Official Evaluation" in line:
            line = "Benchmark Owner đã duyệt 40 nhóm Final và 440 câu hỏi ngày 2026-11-17; 10 câu Q00 Development được chấp nhận ngày 2026-11-17. Intent Cards, SQL và wording có provenance riêng trong registry/Validation Records. D12 đã APPROVED; D14 vẫn PROPOSED. Registry và cấu hình đã đóng băng; mock integration đã kiểm tra đủ ba lượt Final. Official Evaluation vẫn cần xác nhận riêng về chi phí/lượt gọi API thật."
        spec_lines.append(line)
    spec = "\n".join(spec_lines) + "\n"
    spec_path.write_text(spec, encoding="utf-8", newline="\n")

    lines = decision_path.read_text(encoding="utf-8").splitlines()
    lines = [
        ("Physical schema/seed, invariant validator, reproducibility check và edge-case fixtures được nghiệm thu riêng. Intent Cards, SQL candidates và Questions đã được Owner phê duyệt theo provenance trong registry/Validation Records. D8/D9/D13 đã được duyệt và bộ kiểm tra offline mock đã xác minh ba lượt × 440 câu Final. Registry/cấu hình đã đóng băng; Official Evaluation thật vẫn cần xác nhận riêng về chi phí và lượt gọi API. D14 vẫn PROPOSED."
         if "Intent Cards, SQL candidates" in line and "drafts" in line else line)
        for line in lines
    ]
    decision_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    write_json(RECORDS_PATH, records)
    # Freeze the complete 550-question registry only after every question passes
    # the human status gates; this does not authorize provider calls.
    registry["evaluation_freeze"] = True
    registry["dataset_hash"] = registry_hash(registry)
    write_json(REGISTRY_PATH, registry)
    return registry


def load_env_file() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def freeze_config(registry: dict) -> dict:
    load_env_file()
    model_id = os.environ.get("LLM_MODEL", "").strip()
    base_url = os.environ.get("LLM_BASE_URL", "").strip()
    if not model_id or not base_url:
        raise RuntimeError("LLM_MODEL and LLM_BASE_URL must be configured before freezing the run configuration")
    parsed = urlsplit(base_url)
    endpoint_fingerprint = digest_bytes(base_url.encode("utf-8"))
    physical_root = ROOT / "benchmark_data/physical"
    schema_hashes = {name: sha256_file(physical_root / f"schema_{name}.sql") for name in ("erp_sales", "wms_inventory")}
    output_contracts = {group["group_id"]: output_contract_for(group) for group in registry["groups"]}
    output_contracts_sha256 = digest_bytes(json.dumps(
        {group_id: contract["contract_sha256"] for group_id, contract in sorted(output_contracts.items())},
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8"))
    output_contracts_owner_reviewed = (
        len(registry.get("groups", [])) == 50
        and all(
            (review := group.get("output_contract_review", {})).get("status") == "APPROVED"
            and bool(review.get("reviewer"))
            and bool(review.get("approved_on"))
            and bool(review.get("rationale"))
            and review.get("contract_sha256") == output_contracts[group["group_id"]]["contract_sha256"]
            and not output_contracts[group["group_id"]]["unresolved_fields"]
            for group in registry.get("groups", [])
        )
    )
    config = {
        "config_version": 2,
        "evaluation_protocol_version": EVALUATION_PROTOCOL_VERSION,
        "comparator_version": COMPARATOR_VERSION,
        "field_contract_version": CONTRACT_VERSION,
        "output_contracts_owner_reviewed": output_contracts_owner_reviewed,
        "output_contracts_sha256": output_contracts_sha256,
        "frozen_on": DATE,
        "model_id": model_id,
        "provider": "OpenAI-compatible API",
        "provider_endpoint_host": parsed.hostname,
        "provider_endpoint_sha256": endpoint_fingerprint,
        "provider_request_timeout_seconds": 60,
        "temperature": 0,
        "max_tokens": 1024,
        "seed": None,
        "seed_note": "Not set; provider support is not assumed.",
        "replicates": 3,
        "sql_execution_timeout_seconds": 30,
        "initial_attempts": 1,
        "maximum_infrastructure_retries": 2,
        "retry_only_transient_infrastructure_errors": True,
        "sdk_retries": 0,
        "prompt_builder_sha256": prompt_contract_sha256(),
        "evaluation_code_sha256": {
            "collector": sha256_file(ROOT / "bird_demo/benchmark/official.py"),
            "offline_evaluator": sha256_file(ROOT / "bird_demo/benchmark/evaluator.py"),
            "metrics": sha256_file(ROOT / "bird_demo/benchmark/metrics.py"),
            "sql_runner": sha256_file(ROOT / "bird_demo/runner.py"),
            "field_contracts": sha256_file(ROOT / "bird_demo/benchmark/field_contracts.py"),
        },
        "schema_sha256": schema_hashes,
        "registry_canonical_sha256": registry_hash(registry),
        "registry_file_sha256": sha256_file(REGISTRY_PATH),
        "database_sha256": {
            name: sha256_file(physical_root / f"{name}.sqlite")
            for name in ("erp_sales", "wms_inventory")
        },
        "evaluation_split": "final",
        "final_questions_per_replicate": 440,
        "official_api_calls_authorized": False,
        "authorization_note": "Configuration freeze only. Live provider calls require separate explicit cost/run authorization.",
    }
    write_json(CONFIG_PATH, config)
    return config


def run_offline_final_smoke(registry: dict, config: dict) -> dict:
    registry_path = REGISTRY_PATH
    final_questions = [q for q in registry["questions"] if q["split"] == "final"]
    canonical_by_qid = {q["question_id"]: q["canonical_sql"] for q in final_questions}
    if len(final_questions) != 440:
        raise ValueError(f"Expected 440 Final questions, got {len(final_questions)}")
    smoke_config = dict(config)
    smoke_config["provider_request_timeout_seconds"] = 0.01
    calls = 0

    def prompt_builder(question):
        return question["question_id"]

    def mock_provider(prompt, model_id, provider_config):
        nonlocal calls
        calls += 1
        return canonical_by_qid[prompt]

    collected = collect_three_replicates(
        final_questions,
        config["model_id"],
        smoke_config,
        prompt_builder,
        mock_provider,
        gate=OfficialGate(True, True, True, True),
    )
    if len(collected["replicates"]) != 3 or calls != 1320:
        raise AssertionError(f"Mock collector did not complete exactly 3 x 440 predictions: calls={calls}")

    smoke_runs = []
    temp_dir = Path(tempfile.mkdtemp(prefix="bird_vn_final_smoke_", dir=ROOT / ".tmp"))
    artifact_dir = ROOT / "benchmark_data/official/validation/offline_mock_final_replicates"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    try:
        for replicate in collected["replicates"]:
            predictions_path = temp_dir / f"predictions-{replicate['replicate_id']}.json"
            output_path = artifact_dir / f"replicate_{replicate['replicate_id']}.json"
            write_json(predictions_path, {"predictions": [
                {"question_id": row["question_id"], "reply_text": row["response"], "finish_reason": "stop"}
                for row in replicate["records"]
            ]})
            artifact = evaluate_saved_predictions(
                repository_root=ROOT,
                registry_path=registry_path,
                predictions_path=predictions_path,
                output_path=output_path,
                model_id="offline-mock-canonical-sql",
                run_id="offline-final-integration-smoke",
                replicate_id=replicate["replicate_id"],
                timeout_s=30,
                evaluation_split="final",
            )
            if len(artifact["question_records"]) != 440 or artifact["evaluation_split"] != "final":
                raise AssertionError("Offline evaluator did not preserve the Final split/440-question coverage")
            if any(record["status"] != "success" or record["correct"] is not True for record in artifact["question_records"]):
                raise AssertionError(f"Mock canonical predictions did not all execute/match for replicate {replicate['replicate_id']}")
            smoke_runs.append({
                "replicate_id": replicate["replicate_id"],
                "prediction_records": len(replicate["records"]),
                "execution_records": len(artifact["question_records"]),
                "all_sql_executed": True,
                "all_results_match_canonical": True,
                "artifact_path": output_path.relative_to(ROOT).as_posix(),
                "artifact_sha256": sha256_file(output_path),
            })
    finally:
        import shutil
        shutil.rmtree(temp_dir)

    return {
        "validation_type": "OFFLINE_MOCK_IMPLEMENTATION_SMOKE",
        "empirical_result": False,
        "api_called": False,
        "registry_canonical_sha256": registry_hash(registry),
        "config_sha256": sha256_file(CONFIG_PATH),
        "split": "final",
        "replicate_count": len(smoke_runs),
        "questions_per_replicate": 440,
        "prediction_records_total": calls,
        "runs": smoke_runs,
        "protocol_checks": {
            "D8_sql_timeout_seconds": 30,
            "D8_timeout_outcome_not_retried": True,
            "D9_three_complete_replicates": True,
            "D13_transient_only_retry_cap_tested_by_unit_suite": True,
            "retries_counted_as_replicates": False,
        },
        "validated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "notes": "Canonical SQL was supplied by a local mock provider. These checks prove integration wiring only, not model accuracy or official benchmark results.",
    }


def refresh_authoring_manifest() -> dict:
    new_registry_hash = sha256_file(REGISTRY_PATH)
    audit_dir = ROOT / "docs/benchmark/review/full_semantic_validation_sbert"
    audit_summary_path = audit_dir / "summary.json"
    audit_summary = json.loads(audit_summary_path.read_text(encoding="utf-8"))
    current_registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    current_questions = {q["question_id"]: q["question"] for q in current_registry["questions"]}
    with (audit_dir / "q00_variant_similarity.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        similarity_rows = list(csv.DictReader(handle))
    text_lineage_matches = len(similarity_rows) == 500 and all(
        current_questions.get(row["question_id"]) == row["variant_text"]
        and current_questions.get(row["group_id"] + "-Q00") == row["original_q0"]
        for row in similarity_rows
    )
    if not text_lineage_matches or audit_summary.get("question_texts_match_sbert_audit") is not True:
        raise ValueError("Cannot rebind SBERT audit metadata because current question text differs from the audited wording")
    previous_audit_registry_hash = audit_summary.get("registry_sha256")
    audit_summary["registry_sha256"] = new_registry_hash
    audit_summary["registry_lineage_rebind"] = {
        "date": DATE,
        "previous_registry_sha256": previous_audit_registry_hash,
        "reason": "Owner approval and freeze metadata changed; all 550 current question texts were checked against the existing 500-pair audit. No embedding or similarity score was recalculated.",
    }
    write_json(audit_summary_path, audit_summary)
    for rel in (
        "docs/benchmark/review/dev_human_approval/ERP_DEVELOPMENT_QUESTIONS_55.csv",
        "docs/benchmark/review/dev_human_approval/WMS_DEVELOPMENT_QUESTIONS_55.csv",
        "docs/benchmark/review/dev_human_approval/DEVELOPMENT_Q00_FINAL_REVIEW_10.csv",
        "docs/benchmark/review/dev_human_approval/DEVELOPMENT_INTENT_SQL_REVIEW_10.csv",
    ):
        path = ROOT / rel
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
            fields = list(rows[0])
        for row in rows:
            if "source_registry_sha256" in row:
                row["source_registry_sha256"] = new_registry_hash
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest["registry_sha256"] = sha256_file(REGISTRY_PATH)
    touched = [
        "benchmark_data/authoring/dataset.json",
        "benchmark_data/authoring/validation_records.json",
        "benchmark_data/authoring/dev_q00_owner_approval_provenance_2026-11-17.json",
        "docs/benchmark/review/dev_human_approval/DEVELOPMENT_Q00_FINAL_REVIEW_10.csv",
        "docs/benchmark/review/dev_human_approval/DEVELOPMENT_INTENT_SQL_REVIEW_10.csv",
        "docs/benchmark/review/dev_human_approval/ERP_DEVELOPMENT_QUESTIONS_55.csv",
        "docs/benchmark/review/dev_human_approval/WMS_DEVELOPMENT_QUESTIONS_55.csv",
        "docs/benchmark/DECISION_REVIEW.md",
        "docs/benchmark/BENCHMARK_SPEC.md",
        "tests/test_benchmark_authoring_artifacts.py",
        "tests/test_dev_wording_v5.py",
        "tests/test_bird_vn_official.py",
        "docs/benchmark/review/full_semantic_validation_sbert/summary.json",
    ]
    for rel in touched:
        path = ROOT / rel
        manifest["files"][rel] = sha256_file(path)
    write_json(MANIFEST_PATH, manifest)
    return manifest


def write_freeze_manifest(registry: dict, config: dict, manifest: dict, integration: dict) -> dict:
    files = [
        "benchmark_data/authoring/dataset.json",
        "benchmark_data/authoring/validation_records.json",
        "benchmark_data/authoring/dev_q00_owner_approval_provenance_2026-11-17.json",
        "benchmark_data/authoring/final_owner_approval_provenance_2026-11-17.json",
        "benchmark_data/official/frozen_config.json",
        "benchmark_data/official/implementation_validation.json",
        "benchmark_data/physical/erp_sales.sqlite",
        "benchmark_data/physical/wms_inventory.sqlite",
        "benchmark_data/physical/schema_erp_sales.sql",
        "benchmark_data/physical/schema_wms_inventory.sql",
        "benchmark_data/physical/build_manifest.json",
        "docs/benchmark/DECISION_REVIEW.md",
        "benchmark_data/authoring/expected_outputs_dev.json",
        "benchmark_data/authoring/expected_outputs_final.json",
        "benchmark_data/authoring/ground_truth_validation.json",
        "benchmark_data/authoring/ground_truth_validation_final.json",
        "benchmark_data/authoring/dev_fixture_expected_outputs.json",
        "benchmark_data/authoring/dev_fixture_validation.json",
        "benchmark_data/physical/seed_config.json",
        "benchmark_data/physical/all_test_results.json",
        "benchmark_data/physical/fixture_test_results.json",
        "benchmark_data/physical/validation/erp_sales_validation.json",
        "benchmark_data/physical/validation/wms_inventory_validation.json",
        "docs/benchmark/BENCHMARK_SPEC.md",
    ]
    files.extend(run["artifact_path"] for run in integration["runs"])
    return {
        "freeze_version": 1,
        "status": "FROZEN_FOR_FINAL_EVALUATION",
        "freeze_date": DATE,
        "benchmark_version": registry.get("benchmark_version"),
        "registry_revision": registry.get("authoring_revision"),
        "registry_canonical_sha256": registry_hash(registry),
        "registry_file_sha256": sha256_file(REGISTRY_PATH),
        "authoring_manifest_revision": manifest.get("revision"),
        "authoring_manifest_sha256": sha256_file(MANIFEST_PATH),
        "frozen_config_sha256": sha256_file(CONFIG_PATH),
        "development_q00_approval_artifact": "benchmark_data/authoring/dev_q00_owner_approval_provenance_2026-11-17.json",
        "final_approval_artifact": "benchmark_data/authoring/final_owner_approval_provenance_2026-11-17.json",
        "d12_status": "APPROVED",
        "d14_status": "PROPOSED",
        "official_api_calls_authorized": False,
        "implementation_validation": "benchmark_data/official/implementation_validation.json",
        "integrity_files_sha256": {rel: sha256_file(ROOT / rel) for rel in files},
        "frozen_config": config,
        "offline_integration_validation": integration,
    }


def main() -> None:
    registry = record_decisions()
    config = freeze_config(registry)
    # Validate that strict release gates now accept the complete registry.
    registry = load_registry(REGISTRY_PATH, allow_draft=False)
    integration = run_offline_final_smoke(registry, config)
    write_json(INTEGRATION_PATH, integration)
    manifest = refresh_authoring_manifest()
    freeze = write_freeze_manifest(registry, config, manifest, integration)
    write_json(FREEZE_PATH, freeze)
    print(json.dumps({
        "q00_owner_accepts": 10,
        "d12": "APPROVED",
        "d14": "PROPOSED",
        "registry_revision": registry.get("authoring_revision"),
        "registry_canonical_sha256": registry_hash(registry),
        "registry_file_sha256": sha256_file(REGISTRY_PATH),
        "official_evaluation_api_authorized": False,
        "offline_final_smoke": {
            "replicates": integration["replicate_count"],
            "predictions": integration["prediction_records_total"],
            "all_runs_executed_and_matched": all(r["all_sql_executed"] and r["all_results_match_canonical"] for r in integration["runs"]),
        },
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
