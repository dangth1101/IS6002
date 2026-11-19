"""Read-only verification of the frozen BIRD-VN release gates."""

from __future__ import annotations

import json
import hashlib
import sqlite3
from pathlib import Path
from typing import Any

from .registry import file_matches_sha256, load_registry, registry_hash, sha256_file
from .dashboard import manifest_status, output_contract_for
from .dashboard import prompt_contract_sha256
from .field_contracts import COMPARATOR_VERSION, CONTRACT_VERSION, EVALUATION_PROTOCOL_VERSION


def release_readiness(repository_root: Path) -> dict[str, Any]:
    root = Path(repository_root)
    official = root / "benchmark_data/official"
    registry_path = root / "benchmark_data/authoring/dataset.json"
    authoring_manifest_path = root / "benchmark_data/authoring/dev_v6_vietnamese_first_manifest.json"
    config_path = official / "frozen_config.json"
    freeze_path = official / "frozen_registry_manifest.json"
    integration_path = official / "implementation_validation.json"
    result: dict[str, Any] = {
        "registry_ready": False,
        "config_ready": False,
        "freeze_integrity_ready": False,
        "d8_ready": False,
        "d9_ready": False,
        "d13_ready": False,
        "implementation_current": False,
        "output_contracts_reviewed": False,
        "official_run_authorized": False,
        "registry_sha256": None,
        "config_sha256": None,
        "reason": None,
    }
    try:
        registry = load_registry(registry_path, allow_draft=False)
        canonical_hash = registry_hash(registry)
        registry_file_hash = sha256_file(registry_path)
        config = json.loads(config_path.read_text(encoding="utf-8"))
        freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
        integration = json.loads(integration_path.read_text(encoding="utf-8"))
        authoring_manifest_hash = sha256_file(authoring_manifest_path)
        authoring_manifest_ok, _ = manifest_status()
        config_hash = sha256_file(config_path)
        integrity_files = freeze.get("integrity_files_sha256", {})
        integrity_ok = bool(integrity_files) and all(
            file_matches_sha256(root / relative, digest)
            for relative, digest in integrity_files.items()
        )
        registry_ok = (
            registry.get("evaluation_freeze") is True
            and authoring_manifest_ok
            and freeze.get("status") == "FROZEN_FOR_FINAL_EVALUATION"
            and freeze.get("registry_canonical_sha256") == canonical_hash
            and freeze.get("registry_file_sha256") == registry_file_hash
            and config.get("registry_canonical_sha256") == canonical_hash
            and config.get("registry_file_sha256") == registry_file_hash
        )
        code_hashes = config.get("evaluation_code_sha256", {})
        current_code_hashes = {
            "collector": sha256_file(root / "bird_demo/benchmark/official.py"),
            "offline_evaluator": sha256_file(root / "bird_demo/benchmark/evaluator.py"),
            "metrics": sha256_file(root / "bird_demo/benchmark/metrics.py"),
            "sql_runner": sha256_file(root / "bird_demo/runner.py"),
            "field_contracts": sha256_file(root / "bird_demo/benchmark/field_contracts.py"),
        }
        implementation_current = (
            config.get("prompt_builder_sha256") == prompt_contract_sha256()
            and all(code_hashes.get(name) == digest for name, digest in current_code_hashes.items())
            and config.get("comparator_version") == COMPARATOR_VERSION
            and config.get("field_contract_version") == CONTRACT_VERSION
            and config.get("evaluation_protocol_version") == EVALUATION_PROTOCOL_VERSION
        )
        output_contracts = {
            group["group_id"]: output_contract_for(group)
            for group in registry["groups"]
        }
        contracts_digest = hashlib.sha256(json.dumps(
            {group_id: contract["contract_sha256"] for group_id, contract in sorted(output_contracts.items())},
            sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")).hexdigest()
        implementation_current = implementation_current and config.get("output_contracts_sha256") == contracts_digest
        output_contracts_reviewed = (
            len(registry["groups"]) == 50
            and all(
                (review := group.get("output_contract_review", {})).get("status") == "APPROVED"
                and bool(review.get("reviewer"))
                and bool(review.get("approved_on"))
                and bool(review.get("rationale"))
                and review.get("contract_sha256") == output_contracts[group["group_id"]]["contract_sha256"]
                and not output_contracts[group["group_id"]]["unresolved_fields"]
                for group in registry["groups"]
            )
        )
        config_ok = (
            bool(config.get("model_id"))
            and config.get("evaluation_split") == "final"
            and config.get("replicates") == 3
            and config.get("sql_execution_timeout_seconds") == 30
            and config.get("initial_attempts") == 1
            and config.get("maximum_infrastructure_retries") == 2
            and config.get("retry_only_transient_infrastructure_errors") is True
            and config.get("sdk_retries") == 0
            and freeze.get("frozen_config_sha256") == config_hash
            and freeze.get("authoring_manifest_sha256") == authoring_manifest_hash
            and implementation_current
            and config.get("output_contracts_owner_reviewed") is True
            and output_contracts_reviewed
        )
        integration_ok = (
            integration.get("validation_type") == "OFFLINE_MOCK_IMPLEMENTATION_SMOKE"
            and integration.get("empirical_result") is False
            and integration.get("api_called") is False
            and integration.get("registry_canonical_sha256") == canonical_hash
            and integration.get("config_sha256") == config_hash
            and integration.get("split") == "final"
            and integration.get("replicate_count") == 3
            and integration.get("questions_per_replicate") == 440
            and integration.get("prediction_records_total") == 1320
            and len(integration.get("runs", [])) == 3
            and all(
                run.get("prediction_records") == 440
                and run.get("execution_records") == 440
                and run.get("all_sql_executed") is True
                and run.get("all_results_match_canonical") is True
                and file_matches_sha256(root / run.get("artifact_path", ""), run.get("artifact_sha256"))
                for run in integration.get("runs", [])
            )
        )
        protocol = integration.get("protocol_checks", {})
        result.update({
            "registry_ready": registry_ok,
            "config_ready": config_ok,
            "freeze_integrity_ready": integrity_ok,
            "d8_ready": integration_ok and protocol.get("D8_sql_timeout_seconds") == 30 and protocol.get("D8_timeout_outcome_not_retried") is True,
            "d9_ready": integration_ok and protocol.get("D9_three_complete_replicates") is True,
            "d13_ready": integration_ok and protocol.get("D13_transient_only_retry_cap_tested_by_unit_suite") is True,
            "implementation_current": implementation_current,
            "output_contracts_reviewed": output_contracts_reviewed,
            "official_run_authorized": config.get("official_api_calls_authorized") is True,
            "registry_sha256": canonical_hash,
            "config_sha256": config_hash,
            "reason": None,
        })
        result["ready_for_official_run"] = all(
            result[name] for name in ("registry_ready", "config_ready", "freeze_integrity_ready", "d8_ready", "d9_ready", "d13_ready", "implementation_current", "output_contracts_reviewed", "official_run_authorized")
        )
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error, json.JSONDecodeError) as error:
        result["reason"] = f"{type(error).__name__}: {error}"
        result["ready_for_official_run"] = False
    return result
