"""The batch report: our EX next to the paper's dev numbers.

Pure functions over the batch's run rows, the same rows it writes to
runs.csv, so the report always adds up from runs.csv. See SPEC.md section 9.
"""

from dataclasses import dataclass

from bird_demo.data import DEV_DIR, DIFFICULTIES
from bird_demo.scoring import Verdict

DASH = "—"  # no paper number, or no runs to take a share of
BIRD_DEV_DATABASES = 11
EVIDENCE_SETTINGS = ("off", "on")  # as written in runs.csv

# The model the paper's ChatGPT rows compare against: it gets the Table 4
# paper column and is the one whose failures get labelled by hand.
GPT_3_5 = "openai/gpt-3.5-turbo"


@dataclass(frozen=True)
class PaperRow:
    name: str
    without_evidence: float
    with_evidence: float


# Table 2, dev only, looked up by exact model id.
PAPER_TABLE_2 = {
    GPT_3_5: PaperRow('ChatGPT + COT (our prompt keeps "think step by step")', 25.88, 36.64),
    "openai/gpt-4.1": PaperRow("GPT-4 (different model, loose reference)", 30.90, 46.35),
}

# Table 4, dev only, shown on GPT_3_5 rows only. Keyed by Evidence setting.
# Values are simple / moderate / challenging / total.
PAPER_TABLE_4 = {
    "off": ("ChatGPT, no COT", (31.08, 13.29, 12.08, 24.05)),
    "on": ("ChatGPT + KG, no COT", (45.44, 26.14, 19.01, 37.22)),
}

# Failure causes are labelled by hand (SPEC.md section 10), only for runs
# whose Predicted SQL actually ran.
LABEL_VERDICTS = (Verdict.MISMATCH, Verdict.SQL_ERROR, Verdict.TIMEOUT)
FAILURE_COLUMNS = [
    "question_id", "question", "evidence", "ground_truth_sql", "predicted_sql", "verdict", "failure_cause", "note",
]


def select(runs: list[dict], model: str, evidence: str) -> list[dict]:
    return [r for r in runs if r["model"] == model and r["evidence"] == evidence]


def matches(runs: list[dict]) -> int:
    return sum(r["verdict"] == Verdict.MATCH for r in runs)


def ex(runs: list[dict]) -> float:
    """EX in percent. Every run counts in the denominator, No SQL in reply included."""
    return 100 * matches(runs) / len(runs)


def table_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def caveats(runs: list[dict]) -> list[str]:
    questions = {r["question_id"] for r in runs}
    db_ids = sorted({r["db_id"] for r in runs})
    return [
        "## Caveats",
        "",
        f"- Subset: {len(questions)} dev Questions from {len(db_ids)} of {BIRD_DEV_DATABASES} databases "
        f"({', '.join(db_ids)}), from `{DEV_DIR.name}`. Empty-Evidence, tied and revised Questions were removed.",
        "- The paper used all 1,534 dev Questions, an older dev version and a different call setup "
        "(completions endpoint, `SELECT` priming, and a no-Evidence prompt that still said "
        "`External Knowledge: None`). Its numbers are approximate.",
        f"- 1 Question = {100 / len(questions):g} EX points. No confidence intervals.",
    ]


def table_a(runs: list[dict], models: list[str]) -> list[str]:
    lines = [
        "## Table A: EX with and without Evidence (paper Table 2, dev)",
        "",
        table_row(["Model", "EX w/o Evidence", "EX w/ Evidence", "Difference", "Paper w/o", "Paper w/", "Paper row"]),
        table_row(["---", "---:", "---:", "---:", "---:", "---:", "---"]),
    ]
    for model in models:
        without = ex(select(runs, model, "off"))
        with_ = ex(select(runs, model, "on"))
        paper = PAPER_TABLE_2.get(model)
        lines.append(table_row([
            model,
            f"{without:.2f}",
            f"{with_:.2f}",
            f"{with_ - without:+.2f}",
            f"{paper.without_evidence:.2f}" if paper else DASH,
            f"{paper.with_evidence:.2f}" if paper else DASH,
            paper.name if paper else DASH,
        ]))
    return lines


def count_cell(runs: list[dict]) -> str:
    """`k/n (xx.xx%)`, with a dash for the percentage when there are no runs."""
    share = f"{ex(runs):.2f}%" if runs else DASH
    return f"{matches(runs)}/{len(runs)} ({share})"


def table_b(runs: list[dict], models: list[str]) -> list[str]:
    lines = [
        "## Table B: EX by difficulty (paper Table 4, dev)",
        "",
        table_row(["Model", "Evidence", *DIFFICULTIES, "total", "Paper (simple / moderate / challenging / total)"]),
        table_row(["---", "---", "---:", "---:", "---:", "---:", "---"]),
    ]
    for model in models:
        for evidence in EVIDENCE_SETTINGS:
            setting_runs = select(runs, model, evidence)
            by_difficulty = [count_cell([r for r in setting_runs if r["difficulty"] == d]) for d in DIFFICULTIES]
            if model == GPT_3_5:
                name, numbers = PAPER_TABLE_4[evidence]
                paper = f"{name}: " + " / ".join(f"{n:.2f}" for n in numbers)
            else:
                paper = DASH
            lines.append(table_row([model, evidence, *by_difficulty, count_cell(setting_runs), paper]))
    return lines


def verdict_table(runs: list[dict], models: list[str]) -> list[str]:
    lines = [
        "## Verdicts",
        "",
        table_row(["Model", "Evidence", *Verdict]),
        table_row(["---", "---", *["---:"] * len(Verdict)]),
    ]
    for model in models:
        for evidence in EVIDENCE_SETTINGS:
            setting_runs = select(runs, model, evidence)
            counts = [str(sum(r["verdict"] == v for r in setting_runs)) for v in Verdict]
            lines.append(table_row([model, evidence, *counts]))
    return lines


def render_report(runs: list[dict], models: list[str]) -> str:
    """The report as Markdown, covering exactly `models`, in that order."""
    runs = [r for r in runs if r["model"] in models]
    sections = [
        ["# Batch report"],
        caveats(runs),
        table_a(runs, models),
        table_b(runs, models),
        verdict_table(runs, models),
    ]
    return "\n\n".join("\n".join(lines) for lines in sections) + "\n"


def failures_to_label(runs: list[dict], dev: dict[int, dict]) -> list[dict]:
    """GPT_3_5's with-Evidence failures, with empty `failure_cause` and `note` to fill in by hand."""
    failures = []
    for r in select(runs, GPT_3_5, "on"):
        if r["verdict"] not in LABEL_VERDICTS:
            continue
        q = dev[r["question_id"]]
        failures.append({
            "question_id": r["question_id"],
            "question": q["question"],
            "evidence": q["evidence"],
            "ground_truth_sql": q["SQL"],
            "predicted_sql": r["predicted_sql"],
            "verdict": r["verdict"],
            "failure_cause": "",
            "note": "",
        })
    return failures
