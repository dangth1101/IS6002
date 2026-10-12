import sqlite3

import pytest

from bird_demo import data
from bird_demo.llm import Reply
from bird_demo.prompt import build_prompt, extract_sql


def reply(text: str, finish_reason: str = "stop") -> Reply:
    return Reply(text=text, finish_reason=finish_reason)


def test_last_fence_wins():
    text = "First try:\n```sql\nSELECT 1\n```\nBetter:\n```sql\nSELECT 2\n```\nDone."

    assert extract_sql(reply(text)) == "SELECT 2"


def test_unclosed_last_fence_still_wins():
    text = "Draft:\n```sql\nSELECT 1\n```\nFinal:\n```sql\nSELECT 2\n"

    assert extract_sql(reply(text)) == "SELECT 2"


def test_no_fence_takes_the_whole_reply():
    assert extract_sql(reply("  SELECT name FROM hero\n")) == "SELECT name FROM hero"


def test_trailing_semicolon_is_trimmed():
    assert extract_sql(reply("```sql\nSELECT 1;\n```")) == "SELECT 1"


def test_prose_without_sql_is_no_sql():
    assert extract_sql(reply("I can't answer that from these tables.")) is None


def test_cut_off_reply_is_no_sql_even_if_it_looks_like_sql():
    assert extract_sql(reply("SELECT name FROM hero WHERE height_cm >", finish_reason="length")) is None


def test_bare_fence_counts():
    assert extract_sql(reply("```\nSELECT 1\n```")) == "SELECT 1"


def test_fence_tagged_sqlite_counts():
    assert extract_sql(reply("```SQLite\nSELECT 1\n```")) == "SELECT 1"


def test_lowercase_select_and_with_are_accepted():
    assert extract_sql(reply("select 1")) == "select 1"
    assert extract_sql(reply("with t AS (SELECT 1) SELECT * FROM t")) == "with t AS (SELECT 1) SELECT * FROM t"


HERO_DDL = "CREATE TABLE hero (id INTEGER PRIMARY KEY, name TEXT, power_id INTEGER)"
POWER_DDL = "CREATE TABLE power (\n  id INTEGER PRIMARY KEY,\n  name TEXT\n)"


@pytest.fixture
def tiny_db(tmp_path, monkeypatch):
    """A two-table database where data.db_path("tiny") will find it."""
    monkeypatch.setattr(data, "DEV_DIR", tmp_path)
    path = tmp_path / "dev_databases" / "tiny" / "tiny.sqlite"
    path.parent.mkdir(parents=True)
    conn = sqlite3.connect(path)
    conn.execute(HERO_DDL)
    conn.execute(POWER_DDL)
    conn.execute("CREATE INDEX hero_name ON hero (name)")  # not a table, left out
    conn.close()
    return "tiny"


def test_prompt_with_evidence_matches_the_paper_template(tiny_db):
    prompt = build_prompt(tiny_db, "Which heroes can fly?", "can fly refers to power.name = 'Flight'")

    assert prompt == (
        "CREATE TABLE hero (id INTEGER PRIMARY KEY, name TEXT, power_id INTEGER)\n"
        "\n"
        "CREATE TABLE power (\n"
        "  id INTEGER PRIMARY KEY,\n"
        "  name TEXT\n"
        ")\n"
        "\n"
        "-- External Knowledge: can fly refers to power.name = 'Flight'\n"
        "-- Using valid SQLite and understading External Knowledge, answer the following questions for the tables provided above.\n"
        "-- Which heroes can fly?\n"
        "Generate the SQL after thinking step by step: "
    )


@pytest.mark.parametrize("evidence", [None, ""])
def test_prompt_without_evidence_uses_the_clean_wording(tiny_db, evidence):
    prompt = build_prompt(tiny_db, "How many heroes are there?", evidence)

    assert prompt == (
        "CREATE TABLE hero (id INTEGER PRIMARY KEY, name TEXT, power_id INTEGER)\n"
        "\n"
        "CREATE TABLE power (\n"
        "  id INTEGER PRIMARY KEY,\n"
        "  name TEXT\n"
        ")\n"
        "\n"
        "-- Using valid SQLite, answer the following questions for the tables provided above.\n"
        "-- How many heroes are there?\n"
        "Generate the SQL after thinking step by step: "
    )
