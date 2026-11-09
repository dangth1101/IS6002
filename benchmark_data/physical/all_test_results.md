# Physical database fixture tests

- Suite: **all repository tests**
- Status: **PASS**
- Passed: 57
- Failed: 0
- Skipped: 0
- Python: 3.12.6
- Finished UTC: 2026-11-09T08:44:21+00:00

| Test | Status | Duration (s) |
|---|---|---:|
| tests.test_benchmark_physical.test_valid_seed_passes_all_invariants[erp_sales] | PASS | 0.157 |
| tests.test_benchmark_physical.test_valid_seed_passes_all_invariants[wms_inventory] | PASS | 0.056 |
| tests.test_benchmark_physical.test_same_seed_produces_identical_database_bytes | PASS | 0.088 |
| tests.test_benchmark_physical.test_repeated_valid_business_movements_keep_distinct_identity | PASS | 0.047 |
| tests.test_benchmark_physical.test_refund_above_captured_prefix_fails | PASS | 0.055 |
| tests.test_benchmark_physical.test_return_quantity_over_sold_fails | PASS | 0.062 |
| tests.test_benchmark_physical.test_transfer_missing_leg_fails | PASS | 0.049 |
| tests.test_benchmark_physical.test_duplicate_source_leg_identity_is_rejected_by_schema | PASS | 0.052 |
| tests.test_benchmark_physical.test_negative_stock_prefix_fails | PASS | 0.050 |
| tests.test_benchmark_physical.test_bad_timezone_format_fails | PASS | 0.057 |
| tests.test_benchmark_physical.test_aggregate_overflow_fails | PASS | 0.062 |
| tests.test_benchmark_physical.test_foreign_key_violation_is_detected_and_connections_enable_fk | PASS | 0.060 |
| tests.test_benchmark_physical.test_incorrect_status_fails | PASS | 0.051 |
| tests.test_benchmark_physical.test_category_parent_cycle_fails[erp_sales] | PASS | 0.056 |
| tests.test_benchmark_physical.test_category_parent_cycle_fails[wms_inventory] | PASS | 0.053 |
| tests.test_benchmark_physical.test_database_check_rejects_amount_over_cap | PASS | 0.047 |
| tests.test_data.test_missing_file_stops_with_one_line_pointing_to_the_readme | PASS | 0.004 |
| tests.test_data.test_present_file_is_returned | PASS | 0.004 |
| tests.test_llm.test_second_identical_call_is_served_from_the_cache | PASS | 0.004 |
| tests.test_llm.test_refresh_calls_again_and_rewrites_the_file | PASS | 0.005 |
| tests.test_llm.test_a_different_model_is_a_different_cache_entry | PASS | 0.005 |
| tests.test_prompt.test_last_fence_wins | PASS | 0.000 |
| tests.test_prompt.test_unclosed_last_fence_still_wins | PASS | 0.000 |
| tests.test_prompt.test_no_fence_takes_the_whole_reply | PASS | 0.000 |
| tests.test_prompt.test_trailing_semicolon_is_trimmed | PASS | 0.000 |
| tests.test_prompt.test_prose_without_sql_is_no_sql | PASS | 0.000 |
| tests.test_prompt.test_sql_that_opens_with_comments_is_accepted | PASS | 0.000 |
| tests.test_prompt.test_cut_off_reply_is_no_sql_even_if_it_looks_like_sql | PASS | 0.000 |
| tests.test_prompt.test_bare_fence_counts | PASS | 0.000 |
| tests.test_prompt.test_fence_tagged_sqlite_counts | PASS | 0.000 |
| tests.test_prompt.test_lowercase_select_and_with_are_accepted | PASS | 0.000 |
| tests.test_prompt.test_prompt_with_evidence_matches_the_paper_template | PASS | 0.012 |
| tests.test_prompt.test_prompt_without_evidence_uses_the_clean_wording[None] | PASS | 0.012 |
| tests.test_prompt.test_prompt_without_evidence_uses_the_clean_wording[] | PASS | 0.011 |
| tests.test_report.test_table_a_gives_ex_without_and_with_evidence_next_to_the_paper | PASS | 0.000 |
| tests.test_report.test_table_a_marks_gpt_4_1_as_a_loose_reference_and_other_models_have_no_paper_row | PASS | 0.000 |
| tests.test_report.test_report_covers_exactly_the_models_passed | PASS | 0.000 |
| tests.test_report.test_table_b_splits_by_difficulty_with_the_paper_column_only_on_gpt_3_5_turbo | PASS | 0.000 |
| tests.test_report.test_verdict_table_counts_each_verdict_per_model_and_evidence_setting | PASS | 0.000 |
| tests.test_report.test_caveat_header_comes_first_and_counts_the_subset_from_the_runs | PASS | 0.000 |
| tests.test_report.test_failures_to_label_are_the_gpt_3_5_turbo_with_evidence_runs_that_ran_and_failed | PASS | 0.000 |
| tests.test_runner.test_select_returns_rows_and_column_names | PASS | 0.009 |
| tests.test_runner.test_delete_is_an_sql_error_and_leaves_the_file_alone | PASS | 0.011 |
| tests.test_runner.test_two_statements_is_an_sql_error_not_a_crash | PASS | 0.009 |
| tests.test_runner.test_never_ending_recursive_cte_is_a_timeout | PASS | 0.524 |
| tests.test_runner.test_deadline_covers_fetching_rows | PASS | 0.515 |
| tests.test_scoring.test_same_rows_is_a_match | PASS | 0.010 |
| tests.test_scoring.test_different_rows_is_a_mismatch_with_row_diff_counts | PASS | 0.010 |
| tests.test_scoring.test_row_order_and_duplicates_are_ignored | PASS | 0.009 |
| tests.test_scoring.test_integer_and_text_with_the_same_digits_differ | PASS | 0.010 |
| tests.test_scoring.test_column_order_matters | PASS | 0.009 |
| tests.test_scoring.test_different_column_count_is_a_mismatch_with_a_note | PASS | 0.009 |
| tests.test_scoring.test_predicted_sql_that_raises_is_an_sql_error_with_the_message | PASS | 0.010 |
| tests.test_scoring.test_predicted_sql_past_the_deadline_is_a_timeout | PASS | 0.525 |
| tests.test_scoring.test_no_predicted_sql_is_no_sql_in_reply_and_still_runs_the_ground_truth | PASS | 0.020 |
| tests.test_scoring.test_failing_ground_truth_sql_raises_instead_of_giving_a_verdict[SELECT nope FROM hero] | PASS | 0.010 |
| tests.test_scoring.test_failing_ground_truth_sql_raises_instead_of_giving_a_verdict[WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM n) SELECT count(*) FROM n] | PASS | 0.516 |

Generated from pytest JUnit XML. Invalid fixtures are isolated temporary database copies; the benchmark snapshots remain unchanged.
