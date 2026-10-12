from bird_demo.report import GPT_3_5 as GPT35, failures_to_label, render_report


def run(question_id, model, evidence, verdict, difficulty="simple", db_id="superhero", predicted_sql="SELECT 1", error=""):
    """One runs.csv row, as the batch builds it."""
    return {
        "question_id": question_id,
        "db_id": db_id,
        "difficulty": difficulty,
        "model": model,
        "evidence": evidence,
        "verdict": verdict,
        "predicted_sql": predicted_sql,
        "error": error,
    }


def test_table_a_gives_ex_without_and_with_evidence_next_to_the_paper():
    runs = [
        run(1, GPT35, "off", "Match"),
        run(2, GPT35, "off", "Mismatch"),
        run(3, GPT35, "off", "SQL error"),
        run(4, GPT35, "off", "No SQL in reply"),
        run(1, GPT35, "on", "Match"),
        run(2, GPT35, "on", "Match"),
        run(3, GPT35, "on", "Match"),
        run(4, GPT35, "on", "Timeout"),
    ]

    report = render_report(runs, [GPT35])

    assert (
        f'| {GPT35} | 25.00 | 75.00 | +50.00 | 25.88 | 36.64 | ChatGPT + COT (our prompt keeps "think step by step") |'
        in report.splitlines()
    )


def test_table_a_marks_gpt_4_1_as_a_loose_reference_and_other_models_have_no_paper_row():
    runs = [run(1, m, e, "Match") for m in ("openai/gpt-4.1", "x/other") for e in ("off", "on")]

    lines = render_report(runs, ["openai/gpt-4.1", "x/other"]).splitlines()

    assert "| openai/gpt-4.1 | 100.00 | 100.00 | +0.00 | 30.90 | 46.35 | GPT-4 (different model, loose reference) |" in lines
    assert "| x/other | 100.00 | 100.00 | +0.00 | — | — | — |" in lines


def test_report_covers_exactly_the_models_passed():
    runs = [run(1, m, e, "Match") for m in (GPT35, "openai/gpt-4.1") for e in ("off", "on")]

    report = render_report(runs, [GPT35])

    assert GPT35 in report
    assert "gpt-4.1" not in report


def test_table_b_splits_by_difficulty_with_the_paper_column_only_on_gpt_3_5_turbo():
    runs = [
        run(1, GPT35, "off", "Match", "simple"),
        run(2, GPT35, "off", "Mismatch", "simple"),
        run(3, GPT35, "off", "Match", "moderate"),
        run(4, GPT35, "off", "Timeout", "challenging"),
        run(1, GPT35, "on", "Match", "simple"),
        run(2, GPT35, "on", "Match", "simple"),
        run(3, GPT35, "on", "Match", "moderate"),
        run(4, GPT35, "on", "Match", "challenging"),
        run(1, "openai/gpt-4.1", "off", "Match", "simple"),
        run(1, "openai/gpt-4.1", "on", "SQL error", "simple"),
    ]

    lines = render_report(runs, [GPT35, "openai/gpt-4.1"]).splitlines()

    assert (
        f"| {GPT35} | off | 1/2 (50.00%) | 1/1 (100.00%) | 0/1 (0.00%) | 2/4 (50.00%) "
        "| ChatGPT, no COT: 31.08 / 13.29 / 12.08 / 24.05 |"
    ) in lines
    assert (
        f"| {GPT35} | on | 2/2 (100.00%) | 1/1 (100.00%) | 1/1 (100.00%) | 4/4 (100.00%) "
        "| ChatGPT + KG, no COT: 45.44 / 26.14 / 19.01 / 37.22 |"
    ) in lines
    assert "| openai/gpt-4.1 | off | 1/1 (100.00%) | 0/0 (—) | 0/0 (—) | 1/1 (100.00%) | — |" in lines
    assert "| openai/gpt-4.1 | on | 0/1 (0.00%) | 0/0 (—) | 0/0 (—) | 0/1 (0.00%) | — |" in lines


def test_verdict_table_counts_each_verdict_per_model_and_evidence_setting():
    runs = [
        run(1, GPT35, "off", "Match"),
        run(2, GPT35, "off", "No SQL in reply"),
        run(3, GPT35, "off", "No SQL in reply"),
        run(1, GPT35, "on", "Mismatch"),
        run(2, GPT35, "on", "SQL error"),
        run(3, GPT35, "on", "Timeout"),
    ]

    lines = render_report(runs, [GPT35]).splitlines()

    assert "| Model | Evidence | Match | Mismatch | SQL error | Timeout | No SQL in reply |" in lines
    assert f"| {GPT35} | off | 1 | 0 | 0 | 0 | 2 |" in lines
    assert f"| {GPT35} | on | 0 | 1 | 1 | 1 | 0 |" in lines


def test_caveat_header_comes_first_and_counts_the_subset_from_the_runs():
    runs = [
        run(question_id, GPT35, evidence, "Match", db_id=db_id)
        for question_id, db_id in ((1, "superhero"), (2, "toxicology"), (3, "toxicology"), (4, "superhero"))
        for evidence in ("off", "on")
    ]

    lines = render_report(runs, [GPT35]).splitlines()

    assert lines[0] == "# Batch report"
    assert (
        "- Subset: 4 dev Questions from 2 of 11 databases (superhero, toxicology), from `dev_20240627`. "
        "Empty-Evidence, tied and revised Questions were removed."
    ) in lines
    assert (
        "- The paper used all 1,534 dev Questions, an older dev version and a different call setup "
        "(completions endpoint, `SELECT` priming, and a no-Evidence prompt that still said "
        "`External Knowledge: None`). Its numbers are approximate."
    ) in lines
    assert "- 1 Question = 25 EX points. No confidence intervals." in lines
    headings = [line for line in lines if line.startswith("## ")]
    assert headings == [
        "## Caveats",
        "## Table A: EX with and without Evidence (paper Table 2, dev)",
        "## Table B: EX by difficulty (paper Table 4, dev)",
        "## Verdicts",
    ]


def test_failures_to_label_are_the_gpt_3_5_turbo_with_evidence_runs_that_ran_and_failed():
    dev = {
        q: {"question_id": q, "question": f"Question {q}?", "evidence": f"evidence {q}", "SQL": f"SELECT {q}"}
        for q in range(1, 7)
    }
    runs = [
        run(1, GPT35, "on", "Mismatch", predicted_sql="SELECT 10"),
        run(2, GPT35, "on", "Match"),
        run(3, GPT35, "on", "SQL error", predicted_sql="SELECT nope", error="no such column: nope"),
        run(4, GPT35, "on", "No SQL in reply", predicted_sql=""),
        run(5, GPT35, "on", "Timeout", predicted_sql="WITH RECURSIVE n"),
        run(6, GPT35, "off", "Mismatch"),
        run(6, "openai/gpt-4.1", "on", "Mismatch"),
    ]

    failures = failures_to_label(runs, dev)

    assert failures == [
        {"question_id": 1, "question": "Question 1?", "evidence": "evidence 1", "ground_truth_sql": "SELECT 1",
         "predicted_sql": "SELECT 10", "verdict": "Mismatch", "failure_cause": "", "note": ""},
        {"question_id": 3, "question": "Question 3?", "evidence": "evidence 3", "ground_truth_sql": "SELECT 3",
         "predicted_sql": "SELECT nope", "verdict": "SQL error", "failure_cause": "", "note": ""},
        {"question_id": 5, "question": "Question 5?", "evidence": "evidence 5", "ground_truth_sql": "SELECT 5",
         "predicted_sql": "WITH RECURSIVE n", "verdict": "Timeout", "failure_cause": "", "note": ""},
    ]
