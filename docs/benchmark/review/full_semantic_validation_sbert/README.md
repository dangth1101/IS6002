# Full benchmark semantic validation audit

Audit is read-only and tied to the registry SHA-256 in `summary.json`.

## SBERT execution status

The requested model `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` ran on CPU, pinned to Hugging Face snapshot `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`. Versions: sentence-transformers 6.3.0, transformers 5.23.0, torch 2.15.0+cpu, huggingface-hub 2.4.0. Embeddings are 384-dimensional, max sequence length 128, batch size 32, L2-normalized; cosine is their dot product. Raw question strings were passed to the model tokenizer without external text normalization.

Computed all 500 Q00-to-Qi scores and all 2,250 within-group variant pairs. The 36 previously Jaccard-flagged pairs were rescored and given individual triage notes. The threshold 0.90 only selects a review list and never accepts/rejects a question.

### Q00-to-variant score summary

| Cohort | N | Mean | Median | P05 | P95 | Min | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| All | 500 | 0.8601 | 0.8919 | 0.5939 | 0.9685 | 0.2104 | 0.9815 |
| Development | 100 | 0.8026 | 0.8214 | 0.5936 | 0.9216 | 0.5113 | 0.9365 |
| Final | 400 | 0.8745 | 0.9120 | 0.6126 | 0.9709 | 0.2104 | 0.9815 |
| ERP | 250 | 0.8817 | 0.9140 | 0.7466 | 0.9744 | 0.2104 | 0.9815 |
| WMS | 250 | 0.8386 | 0.8750 | 0.5789 | 0.9626 | 0.4338 | 0.9804 |

Within-variant pairs: mean 0.8740, median 0.8932, P05 0.7192, P95 0.9680, range 0.3418–0.9886. The 0.90 triage threshold marks 235 Q00 pairs and 1,024 within-group pairs. High cosine is not evidence of slot equivalence; low cosine can reflect surface-question framing, as illustrated by a Jaccard-flagged WMS-NA-01 pair scored 0.4746 despite nearly identical request content.

The 36 Jaccard candidates split into 13 Development and 23 Final pairs, with SBERT scores from 0.4746 to 0.9877. A simple politeness/framing normalization found 19 pairs whose request core appears unchanged; this is a triage clue, not a semantic judgment. The CSV records a per-pair finding and keeps all cases for human review.

## Source and scope checks

- Registry revision and v6 manifest: verified; manifest registry hash matches.
- Source coverage: 50 groups, 550 questions, 50 Q00 anchors and 500 variants.
- Development/Final: 10/40 groups and 110/440 questions.
- ERP/WMS: 25/25 groups and 275/275 questions.
- Registry split status: Development 10 `VALIDATED_BY_AUTOMATION`; Final 40 `BLOCKED_EXPECTED_OUTPUT_NOT_DERIVED`.
- Human review: all 50 groups remain `NEEDS_HUMAN_REVIEW`; no approval was inferred.
- The 10 Vietnamese `semantic_glossary` entries were restored from approved Business Rules. Before/after evidence is in `registry_integrity_resolution.csv`; the registry now has zero question-mark corruption in glossary text. Human approval remains pending.

## Artifacts

- `q00_variant_similarity.csv`: exactly 500 pairs with actual cosine values and surface-cue review flags.
- `within_group_variant_similarity.csv`: all 2,250 pairwise variant scores; low and high ranked subsets are in `within_group_low_similarity.csv` and `within_group_high_similarity.csv`.
- `within_group_variant_overlap.csv`: lexical token-Jaccard candidates; this is a separate heuristic, not a semantic verdict.
- `similarity_low.csv` and `high_similarity_semantic_risk.csv`: Q00 low-score and >=0.90 review candidates.
- `jaccard_36_review.csv`: all 36 historical lexical-overlap candidates with SBERT score and per-pair review notes.
- `semantic_slot_flags.csv`: all 550 questions remain pending manual comparison against entity/grain, projection, filters/status, aggregation/grouping, time, NULL/zero/empty, units/ties and negation.
- `ground_truth_validation_audit.csv`: per-group SQL/evidence state, separated from human approval.
- `intent_sql_evidence_gaps.csv`: Development owner-review needs and Final validation blockers.
- `registry_integrity_issues.csv` preserves the pre-repair finding; `registry_integrity_resolution.csv` records verified repairs.
- Development question reconciliation is in `../dev_human_approval/DEV_V6_QUESTION_REVISION_RECONCILIATION.csv`: all 110 current texts match the verified v5 audit; no trustworthy V6 question-text artifact was available for safe restoration.
- `human_review_queue.csv`: all 50 groups, with no auto-approval.
- `summary.json`: registry/source hashes, model/dependency status and counts.

## Validation interpretation

For Development, registry and validation records show automated SQL/oracle execution evidence for 10 groups, and six fixture validations are recorded as PASS. However, all 10 `intent_card_hash` values in those records predate the revised Vietnamese briefs and do not match the current card fields. The original execution/oracle evidence is preserved, but it must not be treated as revalidated against the current brief; Owner review and revalidation are required. For Final, expected outputs and execution evidence have not been derived in the current validation records; all 40 are `BLOCKED_EXPECTED_OUTPUT_NOT_DERIVED`. SQL presence or syntax alone is not reported as ground-truth validation. Human review remains pending for all 50 groups.

## Regression tests and provenance

The full test suite passes: **83 passed, 0 failed**. Two assertions pinned to the v5 verifier/object were updated to verify current v6 lineage and the unchanged Q00 wording/SQL. New regression checks protect glossary Unicode/mappings, Development brief-to-CSV consistency, and the V5 question-text reconciliation. No tests were skipped.

Registry revision is `dev-v6-vietnamese-first-integrity-repair`; current SHA-256 is `d1c18b53933f5510d965dd6c6e3438d35c49aee315bfe44073caf181d3e1d0df`, matching the updated manifest. This repair changed glossary Unicode/basis text, restored a review-export field corrupted in the earlier edit, and updated revision metadata only. Question texts did not change, so the SBERT scores remain tied to the same 550 strings; the exact text snapshot is recorded in `summary.json`. The earlier `dd671…` hash was the registry before the verified glossary repair; `f032…` was an earlier intermediate content state, not a serialization-only difference. No canonical SQL or SQL hash changed.

No LLM evaluation, Final tuning, API call, or source-data modification was performed.
