import sqlite3

import pytest

from bird_demo.scoring import GroundTruthError, Verdict, score


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "tiny.sqlite"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE hero (id INTEGER PRIMARY KEY, name TEXT, height_cm INTEGER)")
    conn.executemany("INSERT INTO hero VALUES (?, ?, ?)", [(1, "Ant", 150), (2, "Bee", 210), (3, "Cat", 210)])
    conn.commit()
    conn.close()
    return path


def test_same_rows_is_a_match(db):
    scored = score(db, "SELECT name FROM hero WHERE height_cm > 200", "SELECT name FROM hero WHERE height_cm > 200")

    assert scored.verdict == Verdict.MATCH


def test_different_rows_is_a_mismatch_with_row_diff_counts(db):
    scored = score(db, "SELECT name FROM hero", "SELECT name FROM hero WHERE height_cm > 200")

    assert scored.verdict == Verdict.MISMATCH
    assert scored.only_in_predicted == 1  # Ant
    assert scored.only_in_ground_truth == 0


def test_row_order_and_duplicates_are_ignored(db):
    scored = score(
        db,
        "SELECT height_cm FROM hero ORDER BY height_cm DESC",  # 210, 210, 150
        "SELECT DISTINCT height_cm FROM hero ORDER BY height_cm",  # 150, 210
    )

    assert scored.verdict == Verdict.MATCH


def test_integer_and_text_with_the_same_digits_differ(db):
    scored = score(db, "SELECT '1'", "SELECT 1")

    assert scored.verdict == Verdict.MISMATCH


def test_column_order_matters(db):
    scored = score(db, "SELECT name, id FROM hero", "SELECT id, name FROM hero")

    assert scored.verdict == Verdict.MISMATCH


def test_different_column_count_is_a_mismatch_with_a_note(db):
    scored = score(db, "SELECT id, name, height_cm FROM hero", "SELECT name FROM hero")

    assert scored.verdict == Verdict.MISMATCH
    assert scored.note == "column count differs (3 vs 1)"


def test_predicted_sql_that_raises_is_an_sql_error_with_the_message(db):
    scored = score(db, "SELECT nope FROM hero", "SELECT name FROM hero")

    assert scored.verdict == Verdict.SQL_ERROR
    assert scored.note == "no such column: nope"


NEVER_ENDS = "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM n) SELECT count(*) FROM n"


def test_predicted_sql_past_the_deadline_is_a_timeout(db):
    scored = score(db, NEVER_ENDS, "SELECT name FROM hero", timeout_s=0.5)

    assert scored.verdict == Verdict.TIMEOUT


def test_no_predicted_sql_is_no_sql_in_reply_and_still_runs_the_ground_truth(db):
    scored = score(db, None, "SELECT name FROM hero WHERE id = 1")

    assert scored.verdict == Verdict.NO_SQL
    assert scored.predicted is None
    assert scored.ground_truth.rows == [("Ant",)]


@pytest.mark.parametrize("ground_truth_sql", ["SELECT nope FROM hero", NEVER_ENDS])
def test_failing_ground_truth_sql_raises_instead_of_giving_a_verdict(db, ground_truth_sql):
    with pytest.raises(GroundTruthError):
        score(db, "SELECT name FROM hero", ground_truth_sql, timeout_s=0.5)
