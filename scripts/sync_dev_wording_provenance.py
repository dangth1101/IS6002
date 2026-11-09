"""Refresh source-artifact pointers after Development wording-only revision."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "benchmark_data/authoring"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str):
    path = AUTH / name
    return path, json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    registry_path = AUTH / "dataset.json"
    registry_hash = sha(registry_path)
    expected_path, expected = load("expected_outputs_dev.json")
    expected["source_registry_sha256"] = registry_hash
    save(expected_path, expected)

    fixture_expected_path, fixture_expected = load("dev_fixture_expected_outputs.json")
    fixture_expected["source_registry_sha256"] = registry_hash
    save(fixture_expected_path, fixture_expected)

    fixture_path, fixture = load("dev_fixture_validation.json")
    fixture["expected_outputs_sha256"] = sha(fixture_expected_path)
    save(fixture_path, fixture)

    records_path = AUTH / "validation_records.json"
    ground_path, ground = load("ground_truth_validation.json")
    ground["expected_outputs_sha256"] = sha(expected_path)
    ground["validation_records_sha256"] = sha(records_path)
    ground["question_wording_revision"] = "dev-v2; wording changes only; expected row values and SQL execution evidence unchanged"
    save(ground_path, ground)
    print(json.dumps({
        "registry_sha256": registry_hash,
        "expected_outputs_dev_sha256": sha(expected_path),
        "fixture_expected_sha256": sha(fixture_expected_path),
        "fixture_validation_sha256": sha(fixture_path),
        "validation_records_sha256": sha(records_path),
        "ground_truth_validation_sha256": sha(ground_path),
    }, indent=2))


if __name__ == "__main__":
    main()
