"""Paths to the BIRD data and loaders for it.

Paths are constants, not env vars. `data/` is gitignored; the README says how
to download it.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEV_DIR = ROOT / "data" / "dev_20240627"
REVISED_DIR = ROOT / "data" / "dev_20251106"
SUBSET_PATH = ROOT / "subset.json"

DB_IDS = ("superhero", "toxicology")
DIFFICULTIES = ("simple", "moderate", "challenging")


def require(path: Path) -> Path:
    """Return `path`, or stop with one line pointing to the README."""
    if not path.exists():
        try:
            shown = path.relative_to(ROOT)
        except ValueError:
            shown = path
        raise SystemExit(f"Missing {shown}. Follow 'Get the data' in README.md.")
    return path


def read_json(path: Path) -> list[dict]:
    return json.loads(require(path).read_text(encoding="utf-8"))


def load_dev() -> list[dict]:
    """The dev_20240627 Questions, with their Evidence and Ground-truth SQL."""
    return read_json(DEV_DIR / "dev.json")


def load_revised() -> list[dict]:
    """BIRD's Nov 2025 revision of the same Questions. A filter for make_subset.py only."""
    return read_json(REVISED_DIR / "dev.json")


def load_tied() -> list[dict]:
    """The 42 Questions with an alternate Ground-truth SQL. A filter for make_subset.py only."""
    return read_json(DEV_DIR / "dev_tied_append.json")


def db_path(db_id: str) -> Path:
    return require(DEV_DIR / "dev_databases" / db_id / f"{db_id}.sqlite")
