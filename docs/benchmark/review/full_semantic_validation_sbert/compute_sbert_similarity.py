"""Reproduce the pinned, CPU-only SBERT similarity audit. Does not edit benchmark inputs."""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
import re
import statistics
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import sentence_transformers
import torch
import transformers
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[4]
AUTHORING = ROOT / "benchmark_data" / "authoring"
OUT = ROOT / "docs" / "benchmark" / "review" / "full_semantic_validation_sbert"
MODEL_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
BATCH_SIZE = 32


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict], fields: list[str]):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def quantile(values: list[float], fraction: float) -> float:
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    pos = (len(values) - 1) * fraction
    lo, hi = int(pos), min(int(pos) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def distribution(rows: list[dict]) -> dict:
    values = [float(row["cosine_similarity"]) for row in rows]
    return {
        "count": len(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "stddev_population": statistics.pstdev(values),
        "min": min(values),
        "p05": quantile(values, 0.05),
        "p25": quantile(values, 0.25),
        "p75": quantile(values, 0.75),
        "p95": quantile(values, 0.95),
        "max": max(values),
    }


def cue_flags(original: str, variant: str) -> list[str]:
    """Surface-cue deltas only; these never prove semantic mismatch or equivalence."""
    import re

    checks = {
        "negation_scope": r"không|chưa|ngoại trừ|trừ|chỉ|nếu có|NULL|zero|bằng 0",
        "time": r"20\d{2}|Q[1-4]|UTC|Asia/Ho_Chi_Minh|ngày|tháng|năm|trước|sau",
        "status": r"CONFIRMED|POSTED|DELIVERED|DRAFT|CANCELLED|đã xác nhận|đã ghi sổ|đã giao",
        "unit": r"milli-unit|milli-KG|KG|EA|VND|đơn vị cơ sở|đơn vị",
        "projection": r"mã|SKU|tên|ngày|trạng thái|số lượng|lượng|tổng|hạng|kho|chứng từ|đơn hàng|khách hàng|nhân viên|giá trị",
    }
    flags = []
    for label, pattern in checks.items():
        left = sorted(set(re.findall(pattern, original, flags=re.IGNORECASE)))
        right = sorted(set(re.findall(pattern, variant, flags=re.IGNORECASE)))
        if left != right:
            flags.append(label.upper() + "_SURFACE_CUE_DIFF_REVIEW")
    return flags


def normalized_request_core(text: str) -> str:
    """Strip common politeness/polar wrappers for overlap triage only."""
    text = unicodedata.normalize("NFKD", text).casefold()
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(
        r"^(ban vui long cho biet|ban co the cho toi biet|"
        r"toi can mot bao cao cho noi dung sau ban hay cung cap giup|"
        r"toi can tra cuu noi dung sau|hay giup toi xac dinh dieu nay)\s*:?\s*",
        "", text,
    )
    text = re.sub(r"\s+khong\??$", "", text)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def main():
    registry_path = AUTHORING / "dataset.json"
    registry_bytes = registry_path.read_bytes()
    registry_hash = hashlib.sha256(registry_bytes).hexdigest()
    registry = json.loads(registry_bytes.decode("utf-8"))
    manifest = read_json(AUTHORING / "dev_v6_vietnamese_first_manifest.json")
    if manifest.get("revision") != registry.get("authoring_revision"):
        raise RuntimeError("Manifest revision does not match current registry; refusing to run.")
    if manifest.get("registry_sha256") != registry_hash:
        raise RuntimeError("v6 manifest hash does not match current registry; refusing to run.")

    groups = registry["groups"]
    questions = registry["questions"]
    if len(groups) != 50 or len(questions) != 550:
        raise RuntimeError("Expected exactly 50 groups and 550 questions.")
    grouped = defaultdict(list)
    for question in questions:
        grouped[question["group_id"]].append(question)
    for group in groups:
        grouped[group["group_id"]].sort(key=lambda row: row["q_index"])
        if len(grouped[group["group_id"]]) != 11:
            raise RuntimeError(f"Expected Q00-Q10 for {group['group_id']}.")

    texts = [question["question"] for question in questions]
    q_index = {question["question_id"]: index for index, question in enumerate(questions)}
    model = SentenceTransformer(MODEL_ID, revision=MODEL_REVISION, device="cpu")
    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_tensor=True,
        normalize_embeddings=True,
    )
    if embeddings.device.type != "cpu" or embeddings.shape[0] != 550:
        raise RuntimeError("Unexpected embedding device or row count.")

    anchors, within = [], []
    for group in groups:
        qs = grouped[group["group_id"]]
        anchor = qs[0]
        for variant in qs[1:]:
            score = float(torch.dot(embeddings[q_index[anchor["question_id"]]],
                                    embeddings[q_index[variant["question_id"]]]).item())
            flags = cue_flags(anchor["question"], variant["question"])
            anchors.append({
                "split": group["split"], "domain": group["db_id"], "group_id": group["group_id"],
                "question_id": variant["question_id"], "original_q0": anchor["question"],
                "variant_text": variant["question"], "variant_type": variant["variant_type"],
                "cosine_similarity": f"{score:.8f}",
                "semantic_slot_flags": ";".join(flags + ["SEMANTIC_EQUIVALENCE_REQUIRES_HUMAN_REVIEW"]),
                "duplicate_risk": "HIGH_SIMILARITY_CANDIDATE" if score >= 0.90 else "NO_HIGH_SIMILARITY_FLAG",
                "review_priority": "HIGH" if score >= 0.90 or flags else "STANDARD",
                "review_status": variant.get("variant_review", "NEEDS_HUMAN_REVIEW"),
            })
        for left, right in itertools.combinations(qs[1:], 2):
            score = float(torch.dot(embeddings[q_index[left["question_id"]]],
                                    embeddings[q_index[right["question_id"]]]).item())
            flags = cue_flags(left["question"], right["question"])
            within.append({
                "split": group["split"], "domain": group["db_id"], "group_id": group["group_id"],
                "question_a": left["question_id"], "question_b": right["question_id"],
                "cosine_similarity": f"{score:.8f}",
                "semantic_slot_flags": ";".join(flags + ["SEMANTIC_EQUIVALENCE_REQUIRES_HUMAN_REVIEW"]),
                "risk_type": "HIGH_SIMILARITY_CANDIDATE" if score >= 0.90 else "NO_HIGH_SIMILARITY_FLAG",
                "review_status": "NEEDS_HUMAN_REVIEW",
            })

    anchor_fields = list(anchors[0])
    write_csv(OUT / "q00_variant_similarity.csv", anchors, anchor_fields)
    within_fields = list(within[0])
    write_csv(OUT / "within_group_variant_similarity.csv", within, within_fields)

    low = sorted(anchors, key=lambda row: float(row["cosine_similarity"]))[:100]
    high = sorted((row for row in anchors if float(row["cosine_similarity"]) >= 0.90),
                  key=lambda row: float(row["cosine_similarity"]), reverse=True)
    write_csv(OUT / "similarity_low.csv", low, anchor_fields)
    write_csv(OUT / "high_similarity_semantic_risk.csv", high, anchor_fields)

    # Enrich the prior 36 Jaccard flags with actual SBERT values and cue deltas.
    prior_path = OUT / "within_group_variant_overlap.csv"
    with prior_path.open(encoding="utf-8-sig", newline="") as stream:
        prior = list(csv.DictReader(stream))
    lookup = {(row["group_id"], row["question_a"], row["question_b"]): row for row in within}
    for row in prior:
        scored = lookup[(row["group_id"], row["question_a"], row["question_b"])]
        row["cosine_similarity"] = scored["cosine_similarity"]
        row["semantic_slot_flags"] = scored["semantic_slot_flags"]
        left = grouped[row["group_id"]][int(row["question_a"].rsplit("Q", 1)[1])]
        right = grouped[row["group_id"]][int(row["question_b"].rsplit("Q", 1)[1])]
        if normalized_request_core(left["question"]) == normalized_request_core(right["question"]):
            note = ("Same request remains after stripping polite lead-in/polar framing; likely weak wording "
                    "transformation. Owner should judge taxonomy and standalone naturalness; no auto-reject.")
        elif row["group_id"] == "WMS-JN-04":
            note = ("Projection-heavy pair with ten required fields and same transfer-leg grain; inspect "
                    "naturalness, projection completeness, and whether reordering is substantive.")
        elif row["group_id"] == "WMS-CD-02":
            note = ("Repeated measures/status/source-only rules; check status scope, SOURCE-once rule, "
                    "and whether rearrangement adds a meaningful transformation.")
        elif row["group_id"] == "WMS-AG-02":
            note = ("Shared outbound cohort and projection; inspect whether question structure differs "
                    "meaningfully while retaining shipment-only negative movements.")
        else:
            note = ("Lexical-overlap candidate: manually compare scope, measure, projection, and "
                    "transformation; overlap score alone is inconclusive.")
        row["triage_finding"] = note
    prior_fields = list(prior[0]) if prior else []
    if "semantic_slot_flags" not in prior_fields:
        prior_fields.append("semantic_slot_flags")
    write_csv(OUT / "jaccard_36_review.csv", prior, prior_fields)

    within_ranked = sorted(within, key=lambda row: float(row["cosine_similarity"]))
    write_csv(OUT / "within_group_low_similarity.csv", within_ranked[:100], within_fields)
    write_csv(OUT / "within_group_high_similarity.csv",
              [row for row in reversed(within_ranked) if float(row["cosine_similarity"]) >= 0.90],
              within_fields)

    distributions = {}
    for pair_kind, rows in [("q00_to_variant", anchors), ("within_group_variants", within)]:
        distributions[pair_kind] = {"overall": distribution(rows)}
        for key, value in [("split", "split"), ("domain", "domain")]:
            distributions[pair_kind][key] = {}
            for category in sorted({row[value] for row in rows}):
                distributions[pair_kind][key][category] = distribution(
                    [row for row in rows if row[value] == category]
                )

    import huggingface_hub
    summary_path = OUT / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary.update({
        "sbert_status": "COMPLETED_CPU",
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "sentence_transformers_version": sentence_transformers.__version__,
        "transformers_version": transformers.__version__,
        "torch_version": torch.__version__,
        "huggingface_hub_version": huggingface_hub.__version__,
        "device": "cpu",
        "embedding_dimension": int(embeddings.shape[1]),
        "max_sequence_length": int(model.max_seq_length),
        "batch_size": BATCH_SIZE,
        "normalize_embeddings": True,
        "preprocessing": "Raw question strings passed to SentenceTransformer tokenizer; no external lowercasing, punctuation removal, or truncation. Cosine is dot product of L2-normalized embeddings.",
        "q00_variant_pairs_computed": len(anchors),
        "within_group_variant_pairs_computed": len(within),
        "distribution": distributions,
        "q00_lowest_100": "similarity_low.csv",
        "q00_high_similarity_threshold": 0.90,
        "high_similarity_threshold_note": "Triage-only reporting threshold; no automatic ACCEPT/REJECT/equivalence decision.",
        "high_similarity_candidate_count": len(high),
        "within_group_high_similarity_threshold": 0.90,
        "within_group_high_similarity_candidate_count": sum(
            float(row["cosine_similarity"]) >= 0.90 for row in within
        ),
        "jaccard_36_scored": len(prior),
        "dependency_error": None,
        "registry_revision": registry.get("authoring_revision"),
        "registry_sha256": registry_hash,
        "manifest_match": True,
        "question_texts_match_sbert_audit": True,
        "cosine_values": "COMPUTED; all 500 Q00-to-variant pairs use current registry wording",
        "score_distribution_scope": "Current registry wording; all 500 Q00-to-variant pairs recomputed in this run.",
        "stale_q00_groups": [],
        "stale_q00_pair_count": 0,
        "stale_score_reason": None,
    })
    summary["report_artifact_sha256"] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in OUT.iterdir() if path.is_file() and path.name != "summary.json"
    }
    summary["source_hashes"] = {
        **summary.get("source_hashes", {}),
        "dataset.json": registry_hash,
        "validation_records.json": hashlib.sha256((AUTHORING / "validation_records.json").read_bytes()).hexdigest(),
        "expected_outputs_dev.json": hashlib.sha256((AUTHORING / "expected_outputs_dev.json").read_bytes()).hexdigest(),
        "expected_outputs_final.json": hashlib.sha256((AUTHORING / "expected_outputs_final.json").read_bytes()).hexdigest(),
        "ground_truth_validation.json": hashlib.sha256((AUTHORING / "ground_truth_validation.json").read_bytes()).hexdigest(),
        "ground_truth_validation_final.json": hashlib.sha256((AUTHORING / "ground_truth_validation_final.json").read_bytes()).hexdigest(),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest["files"].update({
        str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in OUT.iterdir() if path.is_file()
    })
    manifest["files"]["docs/benchmark/review/full_semantic_validation_sbert/compute_sbert_similarity.py"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (AUTHORING / "dev_v6_vietnamese_first_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"q00_variant_pairs": len(anchors), "within_group_variant_pairs": len(within),
                      "jaccard_36_scored": len(prior), "high_similarity_candidates": len(high),
                      "model_revision": MODEL_REVISION, "device": "cpu"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
