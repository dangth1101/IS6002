"""Attach latest near-duplicate audit and reconcile historical review summary."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "benchmark_data/authoring"
PKG = ROOT / "docs/benchmark/review/dev_human_approval"
HISTORY = ROOT / "docs/benchmark/review/DEVELOPMENT_REVIEW_PACKAGE.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    audit_path = AUTH / "dev_paraphrase_quality_audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    draft = json.loads((AUTH / "draft_validation.json").read_text(encoding="utf-8"))
    pairs = draft["near_duplicate_candidates"]
    audit["near_duplicate_audit"] = {
        "candidate_pair_count": len(pairs),
        "within_group": sum(x["scope"] == "within_group_variant" for x in pairs),
        "between_groups": sum(x["scope"] == "between_groups" for x in pairs),
        "development_involved": sum(
            x.get("left_split") == "development" or x.get("right_split") == "development"
            for x in pairs if x["scope"] == "between_groups"
        ),
        "cross_split": sum(
            x.get("left_split") != x.get("right_split")
            for x in pairs if x["scope"] == "between_groups"
        ),
        "pairs": pairs,
        "method_limit": "Token Jaccard flags wording similarity only; it neither proves paraphrase equivalence nor decides leakage by itself.",
    }
    audit["source_hashes"] = {
        "previous_registry": sha(PKG / "dataset_v1_before_paraphrase_rewrite.json"),
        "registry": sha(AUTH / "dataset.json"),
        "validation_records": sha(AUTH / "validation_records.json"),
        "expected_outputs": sha(AUTH / "expected_outputs_dev.json"),
        "draft_validation": sha(AUTH / "draft_validation.json"),
        "erp_snapshot": json.loads((ROOT / "benchmark_data/physical/build_manifest.json").read_text(encoding="utf-8"))["databases"]["erp_sales"]["sha256"],
        "wms_snapshot": json.loads((ROOT / "benchmark_data/physical/build_manifest.json").read_text(encoding="utf-8"))["databases"]["wms_inventory"]["sha256"],
    }
    change_log = PKG / "DEV_V2_TO_V3_CHANGELOG.csv"
    audit["revision"] = "dev-v4-erp-rk02-projection-b"
    audit["wording_change_log"] = {"path": "docs/benchmark/review/dev_human_approval/DEV_V2_TO_V3_CHANGELOG.csv", "sha256": sha(change_log)}
    audit["owner_decisions_required"] = []
    audit["owner_decisions_recorded"] = ["ERP-RK-02 Option B: removed product_id from final projection; five requested fields retained."]
    audit["editorial_annotation_occurrences_remaining"] = 0
    audit["semantic_equivalence_status"] = "ALL_110_QUESTIONS_NEED_HUMAN_REVIEW"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    audit_md = PKG / "DEV_PARAPHRASE_QUALITY_AUDIT.md"
    md = audit_md.read_text(encoding="utf-8")
    add = [
        "## Near-duplicate audit",
        "",
        f"The repository token-Jaccard audit reports **{len(pairs)} candidate pairs**: **{audit['near_duplicate_audit']['within_group']} within-group** and **{audit['near_duplicate_audit']['between_groups']} between-group**. Among between-group pairs, **{audit['near_duplicate_audit']['development_involved']} involve Development** and **{audit['near_duplicate_audit']['cross_split']} cross the split**. All between-group flags are in Final; within-group flags are expected comparison candidates, not cross-group leakage. A flag requires human inspection and is not a semantic judgment.",
        "",
        "| Scope | Pair | Similarity |",
        "|---|---|---:|",
    ]
    for pair in pairs:
        add.append(f"| {pair['scope']} | {pair['left']} ↔ {pair['right']} | {pair['jaccard']:.4f} |")
    # Replace the historical v3 note before rebuilding the near-duplicate section.
    v3_header = "## Targeted wording review dev-v3"
    if v3_header in md:
        before, tail = md.split(v3_header, 1)
        after = tail.split("## Near-duplicate audit", 1)[1] if "## Near-duplicate audit" in tail else ""
        md = before + (
            "## Projection alignment revision dev-v4 (2026-11-09)\n\n"
            "Benchmark Owner chose Option B for `ERP-RK-02`: final SELECT returns exactly SKU, product name, base unit, sold quantity and rank. Partitioning by `base_unit`, top-three cutoff and tie inclusion are unchanged. Expected outputs were re-derived by the Python oracle before candidate SQL execution; main and fixture results now have five columns. Dataset machine `validation_status` matches `ground_truth_validation.json`; `intent_card_status`, `ground_truth_review`, all question review states and Owner approval remain pending. The evaluator gates release using the registry review/freeze fields; machine validation is evidence, not approval.\n\n"
            "All questions remain pending human semantic review. See the [v4 review package](dev_human_approval/README.md).\n\n"
            "## Near-duplicate audit" + after
        )
    elif "## Projection alignment revision dev-v4" not in md:
        md += (
            "\n\n## Projection alignment revision dev-v4 (2026-11-09)\n\n"
            "Benchmark Owner chose Option B for `ERP-RK-02`: final SELECT returns exactly SKU, product name, base unit, sold quantity and rank. Partitioning by `base_unit`, top-three cutoff and tie inclusion are unchanged. Expected outputs were re-derived by the Python oracle before candidate SQL execution; main and fixture results now have five columns. Dataset machine `validation_status` matches `ground_truth_validation.json`; human review and Owner approval remain pending.\n"
        )
    # Discard any prior copy and append exactly one refreshed audit section.
    md = md.split("## Near-duplicate audit", 1)[0].rstrip()
    md = md + "\n\n" + "\n".join(add) + "\n"
    audit_md.write_text(md, encoding="utf-8")

    history = HISTORY.read_text(encoding="utf-8")
    marker = "## 1. Tóm tắt trạng thái"
    current = (
        "## Current alignment revision dev-v4 (2026-11-09)\n\n"
        "The earlier 4/6 automation split is **historical only**. Current Development status is 10/10 `VALIDATED_BY_AUTOMATION`; all 10 groups and all 110 questions remain pending human review. Benchmark Owner chose Option B for ERP-RK-02: remove `product_id` from final SELECT, retaining exactly SKU, product name, base unit, sold quantity and rank; per-unit ranking and tie policy are unchanged. Expected and actual row hashes match on the main snapshot and fixtures. Dataset machine statuses match the validation artifact, while Intent/Gold/question review and Owner approval remain pending. The 100 variants retain quota 30/30/20/20. Near-duplicate audit: 19 candidates, none involving Development or crossing splits. See [v4 review package](dev_human_approval/README.md), [wording change log](dev_human_approval/DEV_V2_TO_V3_CHANGELOG.csv), and [quality audit](dev_human_approval/DEV_PARAPHRASE_QUALITY_AUDIT.md).\n\n"
    )
    if "## Current alignment revision dev-v4" in history:
        before, tail = history.split("## Current alignment revision dev-v4", 1)
        rest = tail.split(marker, 1)[1]
        history = before + current + marker + rest
    elif "## Current wording revision dev-v3" in history:
        before, tail = history.split("## Current wording revision dev-v3", 1)
        rest = tail.split(marker, 1)[1]
        history = before + current + marker + rest
    elif "## Current wording revision dev-v2" in history:
        before, tail = history.split("## Current wording revision dev-v2", 1)
        rest = tail.split(marker, 1)[1]
        history = before + current + marker + rest
    else:
        history = history.replace(marker, current + marker, 1)
    history = history.replace("| `VALIDATED_BY_AUTOMATION` | 4 |", "| `VALIDATED_BY_AUTOMATION` | 4 (historical) |", 1)
    history = history.replace("| `NEEDS_HUMAN_REVIEW` | 6 |", "| `NEEDS_HUMAN_REVIEW` | 6 (historical) |", 1)
    HISTORY.write_text(history, encoding="utf-8")
    print(json.dumps({"near_duplicate_candidates":len(pairs),"within_group":audit['near_duplicate_audit']['within_group'],
                      "between_groups":audit['near_duplicate_audit']['between_groups'],
                      "development_involved":audit['near_duplicate_audit']['development_involved'],
                      "cross_split":audit['near_duplicate_audit']['cross_split'],
                      "registry_sha256":audit['source_hashes']['registry']}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
