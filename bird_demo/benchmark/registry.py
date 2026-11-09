"""Versioned question/group registry validation and deterministic hashing."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

EXPECTED_QUESTION_COUNT = 550
QUESTIONS_PER_GROUP = 11


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_registry(path: Path, *, allow_draft: bool = False) -> dict[str, Any]:
    registry = json.loads(path.read_text(encoding="utf-8"))
    if registry.get("format_version") != 1:
        raise ValueError("Unsupported benchmark registry format_version")
    groups = registry.get("groups", [])
    questions = registry.get("questions", [])
    if len(groups) != 50 or len(questions) != EXPECTED_QUESTION_COUNT:
        raise ValueError(f"Expected 50 groups/550 questions; got {len(groups)}/{len(questions)}")
    ids = [q.get("question_id") for q in questions]
    if len(ids) != len(set(ids)) or any(not item for item in ids):
        raise ValueError("question_id values must be present and unique")
    groups_by_id = {item.get("group_id"): item for item in groups}
    if len(groups_by_id) != 50 or None in groups_by_id:
        raise ValueError("group_id values must be present and unique")
    domain_counts = Counter(group.get("db_id") for group in groups)
    if domain_counts != Counter({"erp_sales": 25, "wms_inventory": 25}):
        raise ValueError(f"Domain quota mismatch: {dict(domain_counts)}")
    split_counts = Counter(group.get("split") for group in groups)
    if split_counts != Counter({"development": 10, "final": 40}):
        raise ValueError(f"Split quota mismatch: {dict(split_counts)}")
    dev_domain_counts = Counter(group.get("db_id") for group in groups if group.get("split") == "development")
    if dev_domain_counts != Counter({"erp_sales": 5, "wms_inventory": 5}):
        raise ValueError(f"Development domain quota mismatch: {dict(dev_domain_counts)}")
    expected_complexity = {("erp_sales", "Simple"): 8, ("erp_sales", "Moderate"): 12,
                           ("erp_sales", "Challenging"): 5, ("wms_inventory", "Simple"): 8,
                           ("wms_inventory", "Moderate"): 12, ("wms_inventory", "Challenging"): 5}
    complexity_counts = Counter((group.get("db_id"), group.get("complexity")) for group in groups)
    if complexity_counts != Counter(expected_complexity):
        raise ValueError(f"Complexity quota mismatch: {dict(complexity_counts)}")
    expected_competency = {"Filter": 8, "Aggregate": 8, "Group": 8, "Ranking": 6,
                           "Join": 8, "Time": 4, "NULL": 4, "Conditional": 4}
    competency_counts = Counter(group.get("competency") for group in groups)
    if competency_counts != Counter(expected_competency):
        raise ValueError(f"Competency quota mismatch: {dict(competency_counts)}")
    questions_by_group: dict[str, list[dict[str, Any]]] = {group_id: [] for group_id in groups_by_id}
    for question in questions:
        group_id = question.get("group_id")
        if group_id not in questions_by_group:
            raise ValueError(f"Question references unknown group {group_id!r}")
        questions_by_group[group_id].append(question)
    for group_id, items in questions_by_group.items():
        if len(items) != QUESTIONS_PER_GROUP:
            raise ValueError(f"{group_id}: expected 11 questions, got {len(items)}")
        indexes = sorted(item.get("q_index") for item in items)
        if indexes != list(range(11)):
            raise ValueError(f"{group_id}: q_index must be 0..10")
        for item in items:
            index = item["q_index"]
            if item.get("question_id") != f"{group_id}-Q{index:02d}":
                raise ValueError(f"{group_id}: question_id does not match q_index {index}")
            expected_role = "original" if index == 0 else "variant"
            if item.get("role") is not None and item.get("role") != expected_role:
                raise ValueError(f"{group_id}: wrong role for q_index {index}")
            if not isinstance(item.get("question"), str) or not item["question"].strip():
                raise ValueError(f"{group_id}: question wording must be non-empty")
        if len({item.get("canonical_sql") for item in items}) != 1:
            raise ValueError(f"{group_id}: all questions must share one canonical SQL")
        if len({item.get("db_id") for item in items}) != 1:
            raise ValueError(f"{group_id}: questions in a group must use one database")
        if len({item.get("split") for item in items}) != 1 or items[0].get("split") != groups_by_id[group_id].get("split"):
            raise ValueError(f"{group_id}: group/questions split mismatch")
        variants = Counter(item.get("variant_type") for item in items[1:])
        if variants != Counter({"lexical": 3, "syntactic": 3, "reordering": 2, "mixed": 2}):
            raise ValueError(f"{group_id}: variant taxonomy quota mismatch: {dict(variants)}")
    cluster_splits: dict[str, set[str]] = {}
    for group in groups:
        for cluster in group.get("near_duplicate_clusters", []):
            cluster_splits.setdefault(cluster, set()).add(group["split"])
    leaked = sorted(cluster for cluster, values in cluster_splits.items() if len(values) > 1)
    if leaked:
        raise ValueError(f"Near-duplicate clusters cross splits: {leaked}")
    empty_ids = {group["group_id"] for group in groups if group.get("designed_empty_result")}
    if empty_ids != {"ERP-EF-04", "WMS-EF-04"}:
        raise ValueError(f"Designed empty-result quota mismatch: {sorted(empty_ids)}")
    if not allow_draft:
        unreviewed = [q["question_id"] for q in questions if q.get("variant_review") != "ACCEPT"]
        unreviewed += [g["group_id"] for g in groups
                       if g.get("intent_card_status") != "APPROVED"
                       or g.get("ground_truth_review") != "VALIDATED"
                       or g.get("expected_output") is None
                       or not g.get("expected_outputs_derived_before_sql_execution")]
        if unreviewed:
            raise ValueError(f"Registry has unreviewed items; release blocked ({len(unreviewed)} pending)")
        if registry.get("evaluation_freeze") is not True:
            raise ValueError("Official evaluation requires an explicitly frozen registry")
        if registry.get("dataset_hash") != registry_hash(registry):
            raise ValueError("Frozen registry dataset_hash mismatch")
    return registry


def registry_hash(registry: dict[str, Any]) -> str:
    payload = json.dumps(registry, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
