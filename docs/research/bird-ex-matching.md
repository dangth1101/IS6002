# How the official BIRD evaluation decides a match (EX)

Question: when does BIRD's official script count a Predicted SQL as matching the Ground-truth SQL?

Short answer: it runs both on the same SQLite file, calls `fetchall()` on each, and scores 1 if `set(predicted_rows) == set(ground_truth_rows)`. Anything else, including a timeout or an exception from either query, scores 0.

## Sources

- [S1] Official EX script: `bird/llm/src/evaluation.py` in AlibabaResearch/DAMO-ConvAI at commit `188835d` (file last changed in `dec31ae`, 2023-06-14).
  https://github.com/AlibabaResearch/DAMO-ConvAI/blob/188835d4f9948563a6b9c8ac50cd0f3ae4021ed6/bird/llm/src/evaluation.py
- [S2] Run script with the settings used: `bird/llm/run/run_evaluation.sh`, same commit.
  https://github.com/AlibabaResearch/DAMO-ConvAI/blob/188835d4f9948563a6b9c8ac50cd0f3ae4021ed6/bird/llm/run/run_evaluation.sh
- [S3] BIRD README, "Evaluation" section, same commit.
  https://github.com/AlibabaResearch/DAMO-ConvAI/blob/188835d4f9948563a6b9c8ac50cd0f3ae4021ed6/bird/README.md
- [S4] Newer official copy for BIRD Mini-Dev: `evaluation/evaluation_ex.py` and `evaluation/evaluation_utils.py` in bird-bench/mini_dev at commit `abd11b6`.
  https://github.com/bird-bench/mini_dev/blob/abd11b6db92a1c9f809b32f7564c7c71b34d67f0/evaluation/evaluation_ex.py
  https://github.com/bird-bench/mini_dev/blob/abd11b6db92a1c9f809b32f7564c7c71b34d67f0/evaluation/evaluation_utils.py
- [P] The paper (`075280-1835open.pdf`): Section 5, eq. 2–3 (p. 6); Appendix B.7 "Evaluation Details" (p. 24); Appendix B.8 "VES Details" (p. 25).
- [F] Kim et al., "FLEX: Expert-level False-Less EXecution Metric for Text-to-SQL Benchmark", NAACL 2025. https://aclanthology.org/2025.naacl-long.228/ (arXiv:2409.19014)
- [W] Wretblad et al., "Understanding the Effects of Noise in Text-to-SQL: An Examination of the BIRD-Bench Benchmark", arXiv:2402.12243 (2024). https://arxiv.org/abs/2402.12243
- [L] Local check: a small Python 3.12.10 / SQLite 3.49.1 script that recreates the comparison on a toy table (not the BIRD script itself).

## The comparison function

From [S1], lines 17–28:

```python
def execute_sql(predicted_sql,ground_truth, db_path):
    conn = sqlite3.connect(db_path)
    # Connect to the database
    cursor = conn.cursor()
    cursor.execute(predicted_sql)
    predicted_res = cursor.fetchall()
    cursor.execute(ground_truth)
    ground_truth_res = cursor.fetchall()
    res = 0
    if set(predicted_res) == set(ground_truth_res):
        res = 1
    return res
```

The wrapper, lines 32–48:

```python
def execute_model(predicted_sql,ground_truth, db_place, idx, meta_time_out):
    try:
        res = func_timeout(meta_time_out, execute_sql,
                                  args=(predicted_sql, ground_truth, db_place))
    except KeyboardInterrupt:
        sys.exit(0)
    except FunctionTimedOut:
        result = [(f'timeout',)]
        res = 0
    except Exception as e:
        result = [(f'error',)]  # possibly len(query) > 512 or not executable
        res = 0
    result = {'sql_idx': idx, 'res': res}
    return result
```

The Mini-Dev copy [S4] has the same check, moved into `calculate_ex` (`if set(predicted_res) == set(ground_truth_res): res = 1`).

## Set vs ordered, duplicates, columns

- It's a set comparison. Each row is a Python tuple, and the rows go into a `set` [S1 l.26].
- Row order is ignored. `ORDER BY` direction never affects EX [S1; L].
- Duplicate rows are ignored. `SELECT a` and `SELECT DISTINCT a` match [L].
- Column order inside a row matters. `(a, b)` and `(b, a)` are different tuples, so `SELECT fname, lname` fails against `SELECT lname, fname` [L]. FLEX lists this as a false negative example [F, Table 2].
- Column count matters. An extra or missing column changes the tuple, so it fails [L].
- Column names and aliases are ignored. `fetchall()` returns values only [S1].
- Values compare with Python `==` on what sqlite3 returns: `1` matches `1.0`, `1` does not match `'1'`, `0.1+0.2` does not match `0.3`, and `NULL` rows match `NULL` rows [L]. There's no float tolerance or rounding.
- The paper says this was a deliberate choice. Annotators disagreed on when to use `DISTINCT`, so the authors used "HashSet rather than List" to absorb that. They accept false positives on questions that need a specific order, and estimate those at under 1% of BIRD [P, B.7].
- The paper's formula (eq. 3) only says `1(V, V̂) = 1 if V = V̂`, with V the "result set". The code is what actually defines "=" [P, §5].

## Timeouts, errors, empty results

- Timeout: `func_timeout(meta_time_out, ...)` wraps the whole `execute_sql` call. One 30 s budget covers both queries together, not each query on its own [S1 l.34; S2 `meta_time_out=30.0`].
- Timeout scores 0 [S1 l.38–40].
- Any exception scores 0. That includes a syntax error, a missing column, a Ground-truth SQL that fails, and a bad DB path [S1 l.41–43]. Errors are not reported separately. The `'timeout'` and `'error'` strings are assigned and then thrown away (`result` is overwritten on l.46).
- Multiple statements in one Predicted SQL raise `ProgrammingError: You can only execute one statement at a time` from `cursor.execute`, so they score 0 [L].
- Empty vs empty is a match: `set() == set()` is True [L]. If the Ground-truth SQL returns no rows, any Predicted SQL that also returns no rows (for example, a wrong `WHERE` value) scores 1.
- Missing prediction: if a prediction entry isn't a string, the script substitutes `" "` on the `financial` DB, which errors and scores 0 [S1 l.57–60].

## How queries are executed

- Connection: plain `sqlite3.connect(db_path)`. It's not read-only (`mode=ro` is not used), no `PRAGMA`s are set, and the old script never closes the connection [S1 l.18]. Mini-Dev adds `conn.close()` [S4 utils l.65].
- Both queries run on the same connection and cursor, Predicted SQL first, then Ground-truth SQL [S1 l.21–24].
- Parallelism: `multiprocessing.Pool(processes=num_cpus)` with `apply_async`. One task per Question, collected by a callback into a global list, then sorted by index [S1 l.75–85]. The official run uses `num_cpus=16` [S2]. Mini-Dev's run script marks `num_cpus=16` and `meta_time_out=30.0` as "DO NOT CHANGE THIS" [S4 run_evaluation.sh].
- DB file: the old script takes the DB name from the prediction file's `\t----- bird -----\t<db_id>` suffix [S1 l.58–62]. Mini-Dev takes it from the Ground-truth file instead (`db_places=db_paths_gt`) [S4 l.140].
- Scores are broken down by the `difficulty` field in `dev.json` (simple / moderate / challenging), plus a total [S1 l.87–108].
- VES (`evaluation_ves.py`) reuses the same set check as its gate, then times each query. The paper repeats that 100 times and drops outliers beyond 3 std [P, B.8]. The README says the test-set VES run uses a 3 s/example timeout and reports the best of 5 [S3]. That applies to VES only, not EX.

## Known quirks and criticisms

- Order-blind false positives on "in descending order" style questions. The authors acknowledge these and put them at under 1% [P, B.7].
- Coincidental matches. A wrong query can return the right rows because of the current data. FLEX's example is an extra `age < 19` filter on a DB with no student over 18 [F, Table 2]. Empty-vs-empty is the extreme case of this.
- On 200 BIRD pairs, EX agreed with human experts at Cohen's kappa 62.0, with 21 false positives and 17 false negatives. FLEX raises BIRD scores by about 2.6 points on average and changes model rankings. On hard BIRD questions, false positives outnumbered false negatives [F, §4.2, §7.2, §7.4].
- False negatives from a different output shape (column order, extra columns) and from wrong Ground-truth SQL. For the top 10 models on BIRD, FLEX attributes 58.13% of false negatives to output structure and 54.54% to incorrect ground truth. The categories overlap [F, §7.3].
- Noisy labels. In the BIRD dev `financial` DB, 52 of 106 pairs (49%) had noise and 22 (20.7%) had wrong Ground-truth SQL. Scored against corrected SQL, a zero-shot GPT-3.5 baseline beat DIN-SQL and MAC-SQL [W]. The BIRD team keeps a public list of annotation issues: https://github.com/AlibabaResearch/DAMO-ConvAI/issues/39 .
- Side effect risk (our own check, not from a paper). The connection is read-write and nothing filters statement types. In Python's default sqlite3 mode, a Predicted `DELETE` is rolled back because it's never committed. A Predicted `DROP TABLE` is DDL, which doesn't open an implicit transaction, so it persists in the DB file [L].

## What this means for the demo

- To report EX "the way the paper does", copy the rule exactly: `set(pred_rows) == set(gt_rows)`, one 30 s budget per Question, and score 0 on timeout or error.
- Open BIRD DBs read-only (`sqlite3.connect("file:<path>?mode=ro", uri=True)`). It doesn't change any EX verdict, and it closes the DROP hole above.
- In the UI, show the reason for a verdict: match, mismatch, error, timeout. Also flag "match on empty result" so a lucky pass is visible.
