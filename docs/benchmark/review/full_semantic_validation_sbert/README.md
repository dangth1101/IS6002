# Full Benchmark Semantic Validation Audit

The current registry has 50 groups and 550 questions. Sentence Transformers computed 500 current Q00-to-variant cosine scores and 2,250 within-group variant scores on CPU with the pinned model revision recorded in `summary.json`. The 36 historical Jaccard candidates are also rescored. Scores support review triage only; no similarity threshold accepts or rejects a question.

All 50 Q0 anchors were reviewed and 49 were rewritten in natural Vietnamese. Their Q01?Q10 variants are unchanged. SBERT scores were recomputed from the current registry after the wording edits, so the Q00 score lineage is current. All 10 Development Q0 anchors are back in Human Review; the other 100 Development question decisions remain accepted. Final remains pending, including five groups with recorded Intent/SQL alignment blockers.

See `q00_variant_similarity.csv`, `within_group_variant_similarity.csv`, `summary.json`, `human_review_queue.csv`, `ground_truth_validation_audit.csv`, and `intent_sql_evidence_gaps.csv`. Decision provenance is in `../dev_human_approval/USER_APPROVAL_PROVENANCE_2026-11-16.json`.

Expected outputs for Final were independently derived before candidate SQL comparison. Execution agreement on one snapshot does not establish gold correctness. No paid LLM API or official evaluation was run.
