# Build spec: BIRD text-to-SQL demo

What to build, in full. Each section ends with a "Done when" list and a "Decided in" link. The tickets hold the reasons, but you shouldn't need them to build anything.

- Terms come from [`CONTEXT.md`](CONTEXT.md) and are used exactly: Question, Ground-truth SQL, Predicted SQL, Evidence, EX, Subset, Scored run, Unscored run, Verdict, Failure cause.
- Sections are in build order. Each one only uses what the sections above it built.
- If something here turns out wrong during the build, fix this file in the same PR.

## 1. Purpose and scope

Two parts, both on the presenter's laptop:

- **Streamlit app.** Pick a dev Question from the Subset (Scored run) or type your own (Unscored run). An LLM writes the Predicted SQL, the SQL runs on the BIRD SQLite database, and the app shows the rows and, for a Scored run, a Verdict.
- **Batch script.** Runs every Subset Question with and without Evidence on two models and prints EX next to the paper's Table 2 and Table 4 dev rows.

Out of scope:

- VES (the paper's efficiency score)
- All 11 dev databases, and the hidden test set
- Fine-tuned baselines (T5) and multi-step methods (DIN-SQL, COT few-shot)
- An LLM judge, or showing a Failure cause in the app
- Hosting (Streamlit Cloud or anything else)

Decided in: [map](https://github.com/dangth1101/IS6002/issues/1), [How the project is laid out and run](https://github.com/dangth1101/IS6002/issues/12)

## 2. Setup

- `uv` with `pyproject.toml` and `uv.lock`, Python 3.12. Package installs editable (uv's default with a build backend).
- Runtime deps: `streamlit` (>= 1.65, for `st.tabs(..., on_change="rerun")`), `openai`, `python-dotenv`. Dev dep: `pytest`. No pandas.
- Data: follow the "Get the data" steps in [`README.md`](README.md). You end up with `data/dev_20240627/` (Questions + superhero and toxicology `.sqlite` files) and `data/dev_20251106/dev.json`. `data/` is gitignored.
- Config: `.env` from [`.env.example`](.env.example), keys `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`. Loaded once by `python-dotenv` in `bird_demo/llm.py`. `.streamlit/secrets.toml` is not used.
- If `data/` or a needed `.sqlite` file is missing, the app and both scripts stop with one line pointing to the README.

Done when:

- `uv sync` installs cleanly and `uv run pytest` runs (even with no tests yet).

Decided in: [How the project is laid out and run](https://github.com/dangth1101/IS6002/issues/12), [Where to get BIRD dev data and what's in it](https://github.com/dangth1101/IS6002/issues/2), [this ticket](https://github.com/dangth1101/IS6002/issues/14) (missing-data message)

## 3. Layout

```
bird_demo/
  data.py      paths, load dev.json / subset.json / DDL
  llm.py       complete(), cached_complete(), loads .env
  prompt.py    build_prompt(), extract_sql()
  runner.py    read-only SQLite run, 30 s deadline
  scoring.py   Verdict + set-equality match
app.py                     Streamlit, thin
scripts/make_subset.py     thin
scripts/batch_eval.py      thin
tests/
subset.json                committed, repo root
results/                   batch output, final run committed
.cache/llm/                reply cache, gitignored
mockup/  prototype/        design references, not shipped code
```

- Entry scripts stay thin. Everything the app and the batch share lives in `bird_demo/`, so the two can't drift apart.
- Data paths are constants in `data.py`: `data/dev_20240627` and `data/dev_20251106`. No env var for them.
- Add `.cache/` to `.gitignore`.

Run commands (go in the README, no Makefile, no entry points):

```
uv run python scripts/make_subset.py     # once; rewrites subset.json
uv run streamlit run app.py
uv run python scripts/batch_eval.py --model openai/gpt-3.5-turbo --model openai/gpt-4.1
```

Decided in: [How the project is laid out and run](https://github.com/dangth1101/IS6002/issues/12)

## 4. Data and the Subset

### Source data

- Pinned version: `dev_20240627` (what `dev.zip` serves today). Each record in `dev.json` has `question_id`, `db_id`, `question`, `evidence`, `SQL` (the Ground-truth SQL), `difficulty` (`simple` / `moderate` / `challenging`).
- `data/dev_20251106/dev.json` (BIRD's Nov 2025 revision) is only used by `make_subset.py` as a filter. Same `question_id`s.
- `dev_tied_append.json` lists 42 Questions with an alternate Ground-truth SQL. Also only used as a filter.
- Description CSVs aren't used by the demo.

### `scripts/make_subset.py`

1. Take the `dev_20240627` Questions with `db_id` in `superhero`, `toxicology`.
2. Drop a Question if any of these is true:
   - its `evidence` is empty
   - its `question_id` is in `dev_tied_append.json`
   - its `SQL` differs from the `dev_20251106` record's `SQL` after collapsing all whitespace runs to one space and trimming
3. Expected pool: superhero 110 (70 simple / 28 moderate / 12 challenging), toxicology 104 (57 / 26 / 21). Print these counts.
4. Sample with `rng = random.Random(6002)`. For each database (superhero, then toxicology) and each difficulty (simple, moderate, challenging), sort that group by `question_id` and `rng.sample` 15 / 8 / 2.
5. Run every chosen Ground-truth SQL through the runner (section 7). Assert each one runs without error, finishes within the timeout, and returns at least one row. Fail loudly otherwise.
6. Write `subset.json`: a plain JSON list of `{"question_id", "db_id", "difficulty"}`, sorted by `db_id` then `question_id`, 2-space indent, trailing newline. Question text, Evidence and SQL are always read from `dev.json`, never copied here.

### Who reads what

- The batch script and the app's dev picker read only `subset.json` (plus `dev_20240627/dev.json` for text and SQL).
- Generating the Subset needs both `dev.json` files. Running only needs `subset.json`, `dev_20240627/dev.json` and the two `.sqlite` files.

Done when:

- `subset.json` has 50 entries: 15 / 8 / 2 per database.
- Running the script twice gives a byte-identical file.
- The printed pool counts match step 3.

Decided in: [Which databases and questions go in the subset](https://github.com/dangth1101/IS6002/issues/7), [How the demo scores a run](https://github.com/dangth1101/IS6002/issues/8) (the assert), [this ticket](https://github.com/dangth1101/IS6002/issues/14) (seed, sort order, file shape, whitespace rule)

## 5. LLM seam (`bird_demo/llm.py`)

```python
@dataclass(frozen=True)
class Reply:
    text: str
    finish_reason: str   # "stop", "length", ...

def complete(prompt: str, model: str) -> Reply: ...
def cached_complete(prompt: str, model: str, refresh: bool = False) -> Reply: ...
```

- One OpenAI-compatible client built from `LLM_BASE_URL` and `LLM_API_KEY`, with `max_retries=3` (the client's own exponential backoff).
- `complete` sends one chat call: a single **user** message holding the whole prompt, no system message. `temperature=0` always (OpenRouter drops it for models that don't support it), `max_tokens=1024`, no tools, no streaming.
- Raw text in, raw reply out. No prompt building and no SQL extraction here.
- `cached_complete` wraps `complete` with an on-disk cache at `.cache/llm/<sha256(model + prompt)>.json`, one file per reply, holding `model`, `prompt`, `text`, `finish_reason`. `refresh=True` skips the cache read but still writes.
- The app calls `complete` (always live). The batch calls `cached_complete`.
- If the call still fails after retries, the exception propagates. The app shows it with `st.error` and scores nothing; the batch stops (section 9).
- Default model for the app: `LLM_MODEL` (expected `openai/gpt-4.1`). The batch takes models from `--model`.

Switching provider is config only: Ollama works by setting `LLM_BASE_URL=http://localhost:11434/v1`.

Done when:

- A one-line script calling `complete("Say hi", "openai/gpt-4.1")` returns a `Reply` with `finish_reason == "stop"`.
- Calling `cached_complete` twice with the same arguments makes one HTTP call.

Decided in: [Which LLM to start with and how switching works](https://github.com/dangth1101/IS6002/issues/5), [What prompt the demo sends](https://github.com/dangth1101/IS6002/issues/9) (no system message, `max_tokens`), [this ticket](https://github.com/dangth1101/IS6002/issues/14) (signature with `model` and `Reply`, retries, always sending temperature)

## 6. Prompt and SQL extraction (`bird_demo/prompt.py`)

### `build_prompt(db_id: str, question: str, evidence: str | None) -> str`

Schema (DDL) comes from:

```sql
SELECT sql FROM sqlite_master WHERE type = 'table' AND sql IS NOT NULL ORDER BY rowid
```

with each statement copied as is and joined by one blank line.

With Evidence (copy exactly, including the typo "understading" and the trailing space after the colon):

```
<DDL>

-- External Knowledge: <Evidence>
-- Using valid SQLite and understading External Knowledge, answer the following questions for the tables provided above.
-- <Question>
Generate the SQL after thinking step by step: 
```

Without Evidence (Evidence toggle off, or an Unscored run with an empty Evidence box):

```
<DDL>

-- Using valid SQLite, answer the following questions for the tables provided above.
-- <Question>
Generate the SQL after thinking step by step: 
```

Differences from BIRD's code, on purpose:

- No `SELECT ` line at the end. That primed a completions model, and in a chat message it would be a stray word.
- The no-Evidence form uses the clean wording. BIRD's code actually sent `-- External Knowledge: None` because of a dead-code bug. The batch report caveat mentions this.

Nothing else: no sample rows, no column descriptions, no format instruction.

### `extract_sql(reply: Reply) -> str | None`

1. If `reply.finish_reason == "length"`, return `None` (the reply was cut off).
2. If the reply has fenced code blocks, take the **last** one, whatever its language tag (```` ```sql ````, ```` ```SQLite ````, bare ```` ``` ````).
3. Otherwise take the whole reply.
4. Trim whitespace and one trailing `;`.
5. If it doesn't start with `SELECT` or `WITH` (case-insensitive) after any leading `--` or `/* */` comments, return `None`. Models often write their step-by-step notes as SQL comments before the query.

`None` means the Verdict "No SQL in reply". This check catches bad extraction. It isn't a security measure; the read-only connection is.

Done when:

- The tests in section 11 for `build_prompt` and `extract_sql` pass.

Decided in: [What prompt the demo sends](https://github.com/dangth1101/IS6002/issues/9), [What prompt the paper's LLM baselines used](https://github.com/dangth1101/IS6002/issues/4), [Which LLM to start with and how switching works](https://github.com/dangth1101/IS6002/issues/5) (extraction), [this ticket](https://github.com/dangth1101/IS6002/issues/14) (DDL query, any fence tag, case-insensitive check)

## 7. Running SQL and scoring

### Runner (`bird_demo/runner.py`)

One runner for the Predicted SQL, the Ground-truth SQL, the app and the batch.

- Open with `sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)` (same as `f"file:{path}?mode=ro"`, but escapes spaces and `?` in the path). Read-only is the safety line: BIRD's official script opens read-write, so a Predicted `DROP TABLE` would stick.
- One statement only. `cursor.execute` already rejects more than one, and that comes back as an SQL error.
- `TIMEOUT_S = 30`, one constant, applied to each query on its own. The runner takes it as a parameter, `run(db_path, sql, timeout_s=TIMEOUT_S)`, so tests can pass a short one.
- The deadline covers `execute` and `fetchall` together. SQLite does most of its work while rows are fetched.
- Enforce it with `conn.set_progress_handler` and a deadline: the handler returns non-zero once the deadline passes, and the error raised after that point is a timeout, not an SQL error. No thread killing.
- Any other `sqlite3.Error` is an SQL error. That includes `ProgrammingError`, which is what two statements raise.
- Result is one of: rows (with column names from `cursor.description`), an SQL error (SQLite's message), or a timeout.
- Fetch every row. Scoring needs all of them.

### Scoring (`bird_demo/scoring.py`)

Match rule, copied from BIRD's official evaluation:

- EX = 1 only if `set(predicted_rows) == set(ground_truth_rows)`.
- Row order and duplicate rows are ignored. Column order, column count and value types still matter (`(a, b)` ≠ `(b, a)`, `1` ≠ `'1'`, no float tolerance). Column names are ignored.

Five Verdicts, checked in this order:

| Verdict | When | EX |
| --- | --- | --- |
| No SQL in reply | `extract_sql` returned `None` | 0 |
| SQL error | Predicted SQL raised | 0 |
| Timeout | Predicted SQL passed 30 s | 0 |
| Match | sets equal | 1 |
| Mismatch | sets differ | 0 |

- Mismatch carries a note when the column counts differ: "column count differs (3 vs 1)". The Verdict doesn't change.
- If the **Ground-truth SQL** fails at runtime, raise and stop. It's never a Verdict. After the Subset assert it can only mean a broken setup.
- There's no empty-vs-empty case. The Subset assert guarantees every Ground-truth SQL returns rows.
- The EX denominator is every Question run, No SQL in reply included.
- Row-diff counts for the app: `len(set(pred) - set(gt))` and `len(set(gt) - set(pred))`.

Done when:

- The runner and scoring tests in section 11 pass.
- Running each Subset Question's Ground-truth SQL as if it were the Predicted SQL gives Match for all 50.

Decided in: [How the demo scores a run](https://github.com/dangth1101/IS6002/issues/8), [How the official BIRD evaluation decides a match](https://github.com/dangth1101/IS6002/issues/3), [this ticket](https://github.com/dangth1101/IS6002/issues/14) (timeout parameter, deadline covers fetching, any `sqlite3.Error` is SQL error)

## 8. App (`app.py`)

See [`mockup/`](mockup/) for the look. Where the mockup and this text disagree, this text wins. The mockup still shows six Verdicts and a disabled Evidence toggle on the "Type your own" tab; both are out of date.

### Screen, top to bottom

- **Sidebar:** the active model (`LLM_MODEL`), read-only. No dropdown.
- **Two input tabs**, `st.tabs(["Pick a BIRD dev Question", "Type your own"], key="input_tab", on_change="rerun")`. The open tab decides the run type: the first is a Scored run, the second an Unscored run.
  - **Pick a BIRD dev Question:**
    - selectbox over the Subset, in `subset.json` order, each option labelled `#<question_id> · <db_id> · <difficulty> · <Question>`
    - the Question's Evidence as a caption under it
    - "Use Evidence" toggle, default on. Off sends the no-Evidence prompt. BIRD's Evidence can't be edited.
  - **Type your own:**
    - database select: superhero, toxicology
    - Question text box
    - "Evidence (optional)", a single-line `text_input`. Placeholder per database: superhero `tall refers to height_cm > 200`, toxicology `carcinogenic refers to label = '+'`. Trimmed; empty means no Evidence. No toggle on this tab.
- **Run** button.

### Scored run output

1. **Verdict banner:** the Verdict as the title, plus a one-line reason (SQLite's message for SQL error, the column-count note for Mismatch, "Reply cut off at 1024 tokens" when `finish_reason == "length"`). Match is green and every other Verdict is not.
2. **Row-diff counts:** "Rows only in Predicted: N" and "Rows only in Ground-truth: M". Only when the Predicted SQL ran (Match or Mismatch).
3. **"Prompt sent to the LLM"** expander, collapsed, showing the exact `build_prompt` output.
4. **Two columns.** Left: Predicted SQL and its rows. Right: Ground-truth SQL and its rows. If the Predicted SQL failed, its error text replaces the rows. For No SQL in reply, the raw reply replaces the Predicted SQL.

### Unscored run output

1. Info line: "No Ground-truth SQL, so no EX verdict."
2. "Prompt sent to the LLM" expander, collapsed. Shows the typed Evidence when there was one.
3. One column: the Predicted SQL and its rows, or the error text. If `extract_sql` returned `None`, show "No SQL found in the reply" and the raw reply. That's a message, not a Verdict.

### Behaviour

- Every click calls the LLM live (`complete`, no cache).
- Tables show at most the first 1,000 rows with "showing 1,000 of N" when there are more, with column headers from the cursor.
- An LLM call that fails after retries shows `st.error` with the message. No Verdict, nothing scored.
- No Failure cause anywhere in the app.

Done when:

- A dev Question with Evidence on gives a banner, diff counts, the expander and both columns.
- The same Question twice in a row gives the same Predicted SQL (temperature 0).
- A typed Question with and without typed Evidence shows the info line and one column, and the expander shows the right template.
- A typed Question asking to delete rows doesn't change the `.sqlite` file (read-only).

Decided in: [What the demo screen shows](https://github.com/dangth1101/IS6002/issues/6), [Can a typed Question carry typed Evidence](https://github.com/dangth1101/IS6002/issues/10), [How the demo scores a run](https://github.com/dangth1101/IS6002/issues/8) (five Verdicts), [Does the demo label why a run failed](https://github.com/dangth1101/IS6002/issues/11), [this ticket](https://github.com/dangth1101/IS6002/issues/14) (picker order, toggle default, row cap, LLM error, Unscored no-SQL message)

## 9. Batch eval (`scripts/batch_eval.py`)

### Flags

- `--model`, repeatable, overrides `LLM_MODEL`. The report covers exactly the models passed.
- `--no-cache`: calls `cached_complete(..., refresh=True)`.
- Evidence off and on always both run.

### Run

- Sequential. Loop: model → Evidence (off, then on) → Questions in `subset.json` order. 50 × 2 × 2 = 200 runs for the two-model command.
- One progress line per run, e.g. `[37/200] openai/gpt-4.1 · evidence · #1234 → Match`.
- An LLM call that still fails after the client's retries stops the whole batch with a clear error. Nothing is scored for that call. Finished replies stay cached, so a rerun only pays for what's missing.

### Output

Printed, and also written to `results/report.md`, in this order:

1. **Caveat header**
   - Subset: 50 dev Questions from 2 of 11 databases (superhero, toxicology), from `dev_20240627`. Empty-Evidence, tied and revised Questions were removed.
   - The paper used all 1,534 dev Questions, an older dev version and a different call setup (completions endpoint, `SELECT` priming, and a no-Evidence prompt that still said `External Knowledge: None`). Its numbers are approximate.
   - 1 Question = 2 EX points. No confidence intervals.
2. **Table A**, shaped like Table 2. One row per model: EX without Evidence, EX with Evidence, difference, then the paper's two dev numbers and which paper row they come from.
3. **Table B**, shaped like Table 4. One row per model × Evidence setting: simple, moderate, challenging, total, each cell `k/n (xx.xx%)`, then the paper's numbers.
4. **Verdict table.** One row per model × Evidence setting, one column per Verdict (Match, Mismatch, SQL error, Timeout, No SQL in reply). Format failures show up here on their own.

Numbers: EX to 2 decimals, difference signed (`+12.00`). No per-database split in the printout; it's in `runs.csv`.

### Paper numbers (dev only, never test)

Table A, looked up by exact model id:

| Model id | Paper row | w/o Evidence | w/ Evidence | Note |
| --- | --- | ---: | ---: | --- |
| `openai/gpt-3.5-turbo` | ChatGPT + COT | 25.88 | 36.64 | our prompt keeps "think step by step" |
| `openai/gpt-4.1` | GPT-4 | 30.90 | 46.35 | different model, loose reference |
| anything else | — | — | — | |

Table B, only on `openai/gpt-3.5-turbo` rows (marked "no COT"), "—" elsewhere:

| Paper row | Our row | simple | moderate | challenging | total |
| --- | --- | ---: | ---: | ---: | ---: |
| ChatGPT | gpt-3.5-turbo, no Evidence | 31.08 | 13.29 | 12.08 | 24.05 |
| ChatGPT + KG | gpt-3.5-turbo, with Evidence | 45.44 | 26.14 | 19.01 | 37.22 |

### Files

Fixed paths under `results/`, overwritten every run, written with stdlib `csv`:

- `results/runs.csv`: one row per run. Columns `question_id, db_id, difficulty, model, evidence, verdict, predicted_sql, error`.
- `results/report.md`: the printed output above.
- `results/failures_to_label.csv`: only the `openai/gpt-3.5-turbo` with-Evidence runs whose Verdict is Mismatch, SQL error or Timeout. Columns `question_id, question, evidence, ground_truth_sql, predicted_sql, verdict, failure_cause, note`, the last two empty. Only written when that model is in the run.
- The script never reads or writes `results/labels.csv` (section 10).
- The committed `results/` must come from one run with both models. Never merge older runs.

Done when:

- The two-model command finishes and writes all three files.
- Running it again does no HTTP calls and gives identical files.
- Table A's rows add up from `runs.csv`.

Decided in: [What the batch eval reports](https://github.com/dangth1101/IS6002/issues/13), [How the project is laid out and run](https://github.com/dangth1101/IS6002/issues/12) (flags), [this ticket](https://github.com/dangth1101/IS6002/issues/14) (sequential, progress line, Table B paper column, number format)

## 10. Failure labelling (by hand)

Not code. Done by the presenter after the final batch run, for one slide.

1. Copy `results/failures_to_label.csv` to `results/labels.csv`. Expect about 20 to 30 rows.
2. Fill `failure_cause` with one of: Wrong Schema Linking, Misunderstanding Database Content, Misunderstanding Knowledge Evidence, Other. For Other, add a short `note` (e.g. "dialect: YEAR()", "Ground-truth looks wrong", "ambiguous Question").
3. On the slide: percentages over the paper's three causes next to the paper's 41.6 / 40.8 / 17.6, with the Other count shown separately and the sample marked as small and illustrative.

No SQL in reply runs aren't labelled. The batch report never reads `labels.csv`.

Decided in: [Does the demo label why a run failed](https://github.com/dangth1101/IS6002/issues/11)

## 11. Tests

pytest, under `tests/`. Temp or in-memory SQLite only, `complete` stubbed, never touches `data/`, no live LLM calls, no app tests.

- `extract_sql`: last fence wins; bare fence; fence tagged `SQLite`; no fence; trailing `;` trimmed; lowercase `select` accepted; leading SQL comments accepted; prose returns `None`; `finish_reason == "length"` returns `None`.
- `build_prompt`: snapshot of both templates against a tiny two-table schema, typo and trailing space included.
- scoring: set equality; row order ignored; duplicates ignored; different column count is Mismatch with the note; `1` vs `'1'` is Mismatch.
- runner: a write (`DELETE`) on the read-only connection is an SQL error; a recursive CTE that never ends is a Timeout (pass `timeout_s=0.5`); two statements is an SQL error, not a crash.
- `cached_complete`: the second call with the same arguments doesn't call the stub; `refresh=True` calls it again and rewrites the file.

Done when:

- `uv run pytest` passes with no network and no `data/`.

Decided in: [How the project is laid out and run](https://github.com/dangth1101/IS6002/issues/12)

## 12. README

Part of the build. The README gets:

- the three run commands from section 3
- a line that `mockup/` and `prototype/` are design references, not shipped code
- a pointer to this file

Decided in: [How the project is laid out and run](https://github.com/dangth1101/IS6002/issues/12), [this ticket](https://github.com/dangth1101/IS6002/issues/14)
