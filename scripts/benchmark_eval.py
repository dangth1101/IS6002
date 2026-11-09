"""Offline evaluator for saved Text-to-SQL predictions. It never contacts a model."""

from __future__ import annotations

import argparse
from pathlib import Path

from bird_demo.benchmark.evaluator import evaluate_saved_predictions
from bird_demo.data import ROOT


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=ROOT / "benchmark_data/authoring/dataset.json")
    parser.add_argument("--predictions", type=Path, required=True, help="JSON with one saved prediction per question")
    parser.add_argument("--output", type=Path, default=ROOT / "benchmark_data/runs/offline_run.json")
    parser.add_argument("--model-id", default="offline-fixture")
    parser.add_argument("--run-id", default="offline")
    parser.add_argument("--replicate", type=int, default=0)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--allow-draft", action="store_true", help="For offline smoke tests only; output is not empirical")
    args = parser.parse_args()
    artifact = evaluate_saved_predictions(
        repository_root=ROOT,
        registry_path=args.registry,
        predictions_path=args.predictions,
        output_path=args.output,
        model_id=args.model_id,
        run_id=args.run_id,
        replicate_id=args.replicate,
        timeout_s=args.timeout,
        allow_draft=args.allow_draft,
    )
    print(f"Saved {len(artifact['question_records'])} question records to {args.output}")
    for split, metrics in artifact["metrics_by_split"].items():
        ex = metrics["ex_overall"]
        print(f"{split}: EX {ex['numerator']}/{ex['denominator']} ({ex['percent']})")
    if artifact.get("warning"):
        print(artifact["warning"])


if __name__ == "__main__":
    main()
