# Full Benchmark Semantic Validation Audit

This audit is generated from the current BIRD-VN-Robust-50 registry. The pinned multilingual SBERT model ran on CPU and computed 500 Q00-to-variant cosine scores and 2,250 within-group variant scores for the 50 groups and 550 questions.

The registry hash and question text lineage are recorded in `summary.json` and the current `q00_variant_similarity.csv`. Similarity scores are review-triage signals only. They do not prove semantic equivalence and do not accept or reject a question.

The Benchmark Owner approved all 40 Final groups and 440 Final questions on 2026-11-17. The approval provenance is recorded in `benchmark_data/authoring/final_owner_approval_provenance_2026-11-17.json`. Ten Development Q00 anchors remain pending review; their previously accepted variants are not changed by this Final decision.

Known limitation: Q01/Q02 share a common request core after framing language is removed. This limitation was disclosed and accepted by the Benchmark Owner; SBERT similarity does not establish that the paraphrases are sufficiently diverse. Fixture statuses remain as individually recorded and approval does not promote missing fixture evidence to PASS.

Use `q00_variant_similarity.csv`, `within_group_variant_similarity.csv`, `summary.json`, `human_review_queue.csv`, `ground_truth_validation_audit.csv`, and `intent_sql_evidence_gaps.csv` for current review evidence. The pinned model revision and dependency versions are in `summary.json`.

Owner approval does not freeze the registry or authorize Official Evaluation. No paid LLM API or official evaluation was used.
