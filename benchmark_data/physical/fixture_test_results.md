# Physical database fixture tests

- Suite: **BIRD-VN physical database fixtures**
- Status: **PASS**
- Passed: 16
- Failed: 0
- Skipped: 0
- Python: 3.12.6
- Finished UTC: 2026-11-09T08:44:17+00:00

| Test | Status | Duration (s) |
|---|---|---:|
| tests.test_benchmark_physical.test_valid_seed_passes_all_invariants[erp_sales] | PASS | 0.160 |
| tests.test_benchmark_physical.test_valid_seed_passes_all_invariants[wms_inventory] | PASS | 0.058 |
| tests.test_benchmark_physical.test_same_seed_produces_identical_database_bytes | PASS | 0.085 |
| tests.test_benchmark_physical.test_repeated_valid_business_movements_keep_distinct_identity | PASS | 0.052 |
| tests.test_benchmark_physical.test_refund_above_captured_prefix_fails | PASS | 0.055 |
| tests.test_benchmark_physical.test_return_quantity_over_sold_fails | PASS | 0.073 |
| tests.test_benchmark_physical.test_transfer_missing_leg_fails | PASS | 0.049 |
| tests.test_benchmark_physical.test_duplicate_source_leg_identity_is_rejected_by_schema | PASS | 0.044 |
| tests.test_benchmark_physical.test_negative_stock_prefix_fails | PASS | 0.048 |
| tests.test_benchmark_physical.test_bad_timezone_format_fails | PASS | 0.051 |
| tests.test_benchmark_physical.test_aggregate_overflow_fails | PASS | 0.057 |
| tests.test_benchmark_physical.test_foreign_key_violation_is_detected_and_connections_enable_fk | PASS | 0.058 |
| tests.test_benchmark_physical.test_incorrect_status_fails | PASS | 0.049 |
| tests.test_benchmark_physical.test_category_parent_cycle_fails[erp_sales] | PASS | 0.059 |
| tests.test_benchmark_physical.test_category_parent_cycle_fails[wms_inventory] | PASS | 0.052 |
| tests.test_benchmark_physical.test_database_check_rejects_amount_over_cap | PASS | 0.048 |

Generated from pytest JUnit XML. Invalid fixtures are isolated temporary database copies; the benchmark snapshots remain unchanged.
