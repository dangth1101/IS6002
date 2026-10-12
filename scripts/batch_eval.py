"""Run every Subset Question with Evidence off and on, per model, and score it.

    uv run python scripts/batch_eval.py --model openai/gpt-3.5-turbo --model openai/gpt-4.1

Replies are cached under .cache/llm/, so a rerun only pays for what's missing.
See SPEC.md section 9.
"""

import argparse
import csv

from openai import OpenAIError

from bird_demo.data import ROOT, db_path, load_dev, load_subset
from bird_demo.llm import cached_complete, default_model
from bird_demo.prompt import build_prompt, extract_sql
from bird_demo.scoring import Verdict, score

RESULTS_DIR = ROOT / "results"
EVIDENCE_SETTINGS = (False, True)  # off, then on
RUNS_COLUMNS = ["question_id", "db_id", "difficulty", "model", "evidence", "verdict", "predicted_sql", "error"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", action="append", help="model id, repeatable (default: LLM_MODEL)")
    parser.add_argument("--no-cache", action="store_true", help="call the LLM again and overwrite cached replies")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    models = args.model or [default_model()]
    dev = {q["question_id"]: q for q in load_dev()}
    questions = [dev[entry["question_id"]] for entry in load_subset()]

    total = len(models) * len(EVIDENCE_SETTINGS) * len(questions)
    runs: list[dict] = []
    for model in models:
        for use_evidence in EVIDENCE_SETTINGS:
            for q in questions:
                evidence = q["evidence"] if use_evidence else None
                prompt = build_prompt(q["db_id"], q["question"], evidence)
                try:
                    reply = cached_complete(prompt, model, refresh=args.no_cache)
                except OpenAIError as e:
                    raise SystemExit(
                        f"LLM call failed for {model} #{q['question_id']} after retries: {e}\n"
                        "Finished replies are cached, so rerunning only pays for the rest."
                    )
                predicted_sql = extract_sql(reply)
                scored = score(db_path(q["db_id"]), predicted_sql, q["SQL"])

                label = "evidence" if use_evidence else "no evidence"
                print(f"[{len(runs) + 1}/{total}] {model} · {label} · #{q['question_id']} → {scored.verdict}", flush=True)
                runs.append({
                    "question_id": q["question_id"],
                    "db_id": q["db_id"],
                    "difficulty": q["difficulty"],
                    "model": model,
                    "evidence": "on" if use_evidence else "off",
                    "verdict": scored.verdict,
                    "predicted_sql": predicted_sql or "",
                    "error": scored.note if scored.verdict in (Verdict.SQL_ERROR, Verdict.TIMEOUT) else "",
                })

    # Written only after every run finished, so the file always holds one whole run.
    RESULTS_DIR.mkdir(exist_ok=True)
    with open(RESULTS_DIR / "runs.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RUNS_COLUMNS)
        writer.writeheader()
        writer.writerows(runs)
    print(f"Wrote {len(runs)} runs to results/runs.csv")


if __name__ == "__main__":
    main()
