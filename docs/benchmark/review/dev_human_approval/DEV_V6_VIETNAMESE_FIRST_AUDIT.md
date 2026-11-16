# Development Vietnamese-first integrity audit

Current revision: `dev-v6-erp-ef-01-customer-code-clarification`. Registry SHA-256: `f2052fcb6423f37124b98ada98f534c22be4309e845ee3d06294a5523c04a154`.

## ERP-EF-01 customer identifier clarification

The Intent Card now explicitly describes the business-facing customer identifier as `CUSTOMERS.customer_code`, not internal `customer_id`. The canonical SQL still projects `customer_id`; no SQL, expected rows, Oracle, fixture, snapshot, or question text was changed. This creates a projection-alignment issue that remains pending Owner resolution and revalidation. The review status remains `NEEDS_HUMAN_REVIEW`; this wording clarification is not approval. See [change log](ERP_EF_01_CUSTOMER_CODE_INTENT_CLARIFICATION.csv).

## Verified repairs

- Restored all 10 Vietnamese `semantic_glossary` entries from the approved Business Rules and locked Intent Cards. The exact before/after record is [DEV_V6_GLOSSARY_UNICODE_CHANGELOG.csv](DEV_V6_GLOSSARY_UNICODE_CHANGELOG.csv).
- The 10 Development business briefs remain Vietnamese-first and UTF-8. SQL, semantic slots and question text were not changed in this integrity repair.
- Regression tests check the glossary has no replacement `?` characters and protects four core mappings.

## Development question wording reconciliation

Compared all 110 current Development question texts with `DEV_V5_PARAPHRASE_AUDIT.csv`: **110/110 exactly match the verified v5 current wording**. The only durable v6 changelog available records the 10 Intent brief changes; no trusted, slot-verified per-question v6 wording artifact is present. A previous intermediate registry hash was recorded before restoring question text from the v5 UTF-8 audit, but its question wording was character-corrupted and is not a safe restoration source. Therefore zero question texts were reconstructed. The per-question comparison is in [DEV_V6_QUESTION_REVISION_RECONCILIATION.csv](DEV_V6_QUESTION_REVISION_RECONCILIATION.csv). All 110 remain `NEEDS_HUMAN_REVIEW`.

## Ground-truth status

- Development: 10 groups have recorded `VALIDATED_BY_AUTOMATION` SQL/oracle evidence; 6 fixture validations are recorded as PASS. All 10 still need Owner review; automation is not approval.
- Final: 0/40 independently validated. All 40 remain `BLOCKED_EXPECTED_OUTPUT_NOT_DERIVED`; expected outputs, independent Python oracles and execution evidence are absent. The available Python oracle only covers the 10 Development intents. Canonical SQL was not run to manufacture expected outputs.
- No SQL, Oracle, expected-output, fixture, SQLite, metric or protocol changes were made.

## SBERT audit

Question texts did not change in this repair. The previous SBERT pair scores remain valid: 500 Q00-to-variant pairs and 2,250 within-group variant pairs match the current question text snapshot. Zero pairs were recomputed. The report summary was rebound to the new registry hash and records the question-text hash and exact text match. No cosine score was used to approve/reject a question.

Human review remains pending for all Intent Cards, questions and Ground-truth SQL. No release, Final evaluation or LLM evaluation was authorized.
