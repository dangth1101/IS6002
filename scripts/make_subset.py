"""Pick the Subset and freeze it into subset.json. Run once; rerunning gives the same file.

    uv run python scripts/make_subset.py

See SPEC.md section 4 for the rules.
"""

import json
import random
from collections import Counter

from bird_demo.data import DB_IDS, DIFFICULTIES, SUBSET_PATH, db_path, load_dev, load_revised, load_tied
from bird_demo.runner import Rows, run

SEED = 6002
PICKS = {"simple": 15, "moderate": 8, "challenging": 2}
EXPECTED_POOL = {
    ("superhero", "simple"): 70,
    ("superhero", "moderate"): 28,
    ("superhero", "challenging"): 12,
    ("toxicology", "simple"): 57,
    ("toxicology", "moderate"): 26,
    ("toxicology", "challenging"): 21,
}


def collapse_whitespace(sql: str) -> str:
    return " ".join(sql.split())


def filter_pool(dev: list[dict], revised: list[dict], tied: list[dict]) -> list[dict]:
    revised_sql = {q["question_id"]: q["SQL"] for q in revised}
    tied_ids = {q["question_id"] for q in tied}
    return [
        q
        for q in dev
        if q["db_id"] in DB_IDS
        and q["evidence"].strip()
        and q["question_id"] not in tied_ids
        and collapse_whitespace(q["SQL"]) == collapse_whitespace(revised_sql[q["question_id"]])
    ]


def check_pool(pool: list[dict]) -> None:
    """Print the pool counts and stop if they aren't the expected ones."""
    counts = Counter((q["db_id"], q["difficulty"]) for q in pool)
    print("Pool after filters:")
    for db_id in DB_IDS:
        per = [counts[db_id, d] for d in DIFFICULTIES]
        split = " / ".join(f"{d} {n}" for d, n in zip(DIFFICULTIES, per))
        print(f"  {db_id:<11} {sum(per)} ({split})")
    if dict(counts) != EXPECTED_POOL:
        raise SystemExit("Pool counts differ from SPEC.md section 4. Is data/ the pinned version?")


def pick_subset(pool: list[dict]) -> list[dict]:
    rng = random.Random(SEED)
    chosen = []
    for db_id in DB_IDS:
        for difficulty in DIFFICULTIES:
            group = sorted(
                (q for q in pool if q["db_id"] == db_id and q["difficulty"] == difficulty),
                key=lambda q: q["question_id"],
            )
            chosen += rng.sample(group, PICKS[difficulty])
    return chosen


def check_ground_truth(chosen: list[dict]) -> None:
    """Every Ground-truth SQL must run, finish in time and return rows."""
    print(f"Running {len(chosen)} Ground-truth SQL...")
    failures = []
    for q in chosen:
        result = run(db_path(q["db_id"]), q["SQL"])
        if not isinstance(result, Rows):
            failures.append(f"#{q['question_id']}: {result}")
        elif not result.rows:
            failures.append(f"#{q['question_id']}: no rows")
    if failures:
        raise SystemExit("Ground-truth SQL failed, subset.json not written:\n  " + "\n  ".join(failures))


def main() -> None:
    pool = filter_pool(load_dev(), load_revised(), load_tied())
    check_pool(pool)

    chosen = pick_subset(pool)
    check_ground_truth(chosen)

    entries = sorted(
        ({"question_id": q["question_id"], "db_id": q["db_id"], "difficulty": q["difficulty"]} for q in chosen),
        key=lambda e: (e["db_id"], e["question_id"]),
    )
    SUBSET_PATH.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {SUBSET_PATH.name}: {len(entries)} Questions")


if __name__ == "__main__":
    main()
