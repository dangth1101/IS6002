import sqlite3

import pytest

from bird_demo.runner import Rows, SqlError, Timeout, run


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "tiny.sqlite"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE hero (id INTEGER PRIMARY KEY, name TEXT)")
    conn.executemany("INSERT INTO hero VALUES (?, ?)", [(1, "Ant"), (2, "Bee")])
    conn.commit()
    conn.close()
    return path


def test_select_returns_rows_and_column_names(db):
    result = run(db, "SELECT id, name AS hero_name FROM hero ORDER BY id")

    assert result == Rows(columns=["id", "hero_name"], rows=[(1, "Ant"), (2, "Bee")])


def test_delete_is_an_sql_error_and_leaves_the_file_alone(db):
    result = run(db, "DELETE FROM hero")

    assert isinstance(result, SqlError)
    assert "readonly" in result.message
    assert run(db, "SELECT count(*) FROM hero").rows == [(2,)]


def test_two_statements_is_an_sql_error_not_a_crash(db):
    result = run(db, "SELECT 1; SELECT 2")

    assert isinstance(result, SqlError)


NEVER_ENDS = "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM n)"


def test_never_ending_recursive_cte_is_a_timeout(db):
    result = run(db, f"{NEVER_ENDS} SELECT count(*) FROM n", timeout_s=0.5)

    assert result == Timeout(timeout_s=0.5)


def test_deadline_covers_fetching_rows(db):
    # The first row comes back from execute at once; the hang is in fetchall.
    result = run(db, f"{NEVER_ENDS} SELECT x FROM n WHERE x = 1 OR x < 0", timeout_s=0.5)

    assert result == Timeout(timeout_s=0.5)
