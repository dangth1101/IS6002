# Development Human Review Record

Current revision: `dev-v9-all-q00-natural-vietnamese`.

The user previously approved the Development Intent/SQL records and 110 question rows. After the user requested a natural-language review of all Q0 anchors, every Development Q0 is now back in `NEEDS_HUMAN_REVIEW`; the other 100 Development questions retain their prior `ACCEPT` decisions. The prior decisions are retained in the approval provenance log, while revised wording is not treated as approved.

Across all 50 groups, 49 Q0 anchors were reworded in natural Vietnamese. SQL, expected outputs, fixtures and SQLite snapshots were not changed by this wording review. ERP-EF-01 SQL and expected output continue to use `CUSTOMERS.customer_code`.

The 40 Final groups have independent expected-output artifacts and read-only SQL comparison evidence, but remain under Human Review. Five Final groups have recorded Intent/SQL alignment blockers. Official evaluation remains disabled.

Key records: `DEVELOPMENT_INTENT_SQL_REVIEW_10.csv`, `ERP_DEVELOPMENT_QUESTIONS_55.csv`, `WMS_DEVELOPMENT_QUESTIONS_55.csv`, `USER_APPROVAL_PROVENANCE_2026-11-16.json`, `../../../../benchmark_data/authoring/dataset.json`, `../../../../benchmark_data/authoring/expected_outputs_dev.json`, `../../../../benchmark_data/authoring/expected_outputs_final.json`, and `../../../../benchmark_data/authoring/ground_truth_validation_final.json`.
