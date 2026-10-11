# What prompt BIRD's LLM baselines used

Question: what did the paper's in-context-learning baselines (ChatGPT, GPT-4, Claude-2, Codex, Palm-2) send to the model, and how was the Predicted SQL pulled out of the reply?

Short answer: a zero-shot "programming" prompt. All `CREATE TABLE` statements, then the Evidence as a SQL comment, a one-line instruction, the Question as a comment, and the text `SELECT ` for the model to continue. No sample rows, no column descriptions. The released code and the paper disagree on some details (below).

## Sources

- Paper: Li et al., NeurIPS 2023, `075280-1835open.pdf` in this repo. Section 6.1 (PDF p.7), 6.5 (p.9), Appendix B.4 (p.22), Figure 9 (p.24).
- Official code, AlibabaResearch/DAMO-ConvAI at commit `188835d`. The `bird/llm` folder has a single commit (`03898f5f9f`, 2023-05-04), so this is the only version that was ever published.
  - Prompt builder and API call: https://github.com/AlibabaResearch/DAMO-ConvAI/blob/188835d4f9948563a6b9c8ac50cd0f3ae4021ed6/bird/llm/src/gpt_request.py
  - Run script: https://github.com/AlibabaResearch/DAMO-ConvAI/blob/188835d4f9948563a6b9c8ac50cd0f3ae4021ed6/bird/llm/run/run_gpt.sh
  - CoT reply parser: https://github.com/AlibabaResearch/DAMO-ConvAI/blob/188835d4f9948563a6b9c8ac50cd0f3ae4021ed6/bird/llm/src/post_process_cot.py
  - Evaluator (reads predictions): https://github.com/AlibabaResearch/DAMO-ConvAI/blob/188835d4f9948563a6b9c8ac50cd0f3ae4021ed6/bird/llm/src/evaluation.py
  - Released ChatGPT predictions: https://github.com/AlibabaResearch/DAMO-ConvAI/blob/188835d4f9948563a6b9c8ac50cd0f3ae4021ed6/bird/llm/exp_result/turbo_output/predict_dev.json and `.../turbo_output_kg/predict_dev.json`
- Later official code (not the paper's baselines, for comparison only): https://github.com/bird-bench/mini_dev/blob/abd11b6db92a1c9f809b32f7564c7c71b34d67f0/llm/src/prompt.py

## What the paper says

- ICL models were run zero-shot: "a zero-shot generation strategy is the most appropriate" since models can't see the eval databases or Ground-truth SQL (B.4, p.22; also 6.1, p.7).
- Models: Codex `code-davinci-002`, ChatGPT `gpt-3.5-turbo`, GPT-4 `gpt-4-32k`, Claude-2 `claude-2.0`, Palm-2 `text-bison-001` (6.1, p.7).
- "We employ programming-based prompts, as described in [39]" ([39] = Rajkumar et al. 2022, arXiv 2204.00498), called through the Azure OpenAI API (B.4).
- Temperature 0 "to ensure reproduction" (B.4).
- With vs without Evidence: two runs per model. Without, the Evidence sentence is simply not given. With, it is "naively concatenate[d]" with the Question and schema (6.5 p.9; B.4 "Knowledge Fusion").
- ChatGPT + COT: add "Let's think step by step." before SQL generation. ChatGPT's output was "too uncertain with many unexpected explanations", so they added a 1-shot pseudo example to fix the reasoning steps and output format (B.4). Only ChatGPT got a COT variant (Table 2).
- The same prompt was used for the Spider vs BIRD comparison (6.3, p.8).
- Figure 9 (p.24) shows the COT prompt layout, top to bottom: 1-shot pseudo example, `CREATE TABLE` DDL for every table, `-- External Knowledge: ...`, task instruction, `-- <Question>`, `The final SQL is: Let's think step by step.`. Expected reply: numbered steps, then `Finally the SQL is: SELECT ...`.
- The paper has no released code for GPT-4, Claude-2 or Palm-2. Only the OpenAI script exists.

## What the code sends (`gpt_request.py`)

### Schema

- `generate_schema_prompt(db_path, num_rows=None)`: for each table, the raw `sql` column from `sqlite_master`. That is the original `CREATE TABLE` text, with its own formatting, keys and foreign keys.
- Tables are joined with `"\n\n"`.
- `num_rows=None` at the only call site, so no sample rows. (The code can add `/* 3 example rows: SELECT * FROM t LIMIT 3; ... */` blocks, but it's switched off.)
- No column descriptions. BIRD's `database_description/*.csv` files are never read.
- Bug: the skip check is `if table == 'sqlite_sequence'`, but `table` is a tuple, so `sqlite_sequence` is never skipped and shows up in the prompt when a DB has it.

### Question and Evidence, verbatim

```python
def generate_comment_prompt(question, knowledge=None):
    pattern_prompt_no_kg = "-- Using valid SQLite, answer the following questions for the tables provided above."
    pattern_prompt_kg = "-- Using valid SQLite and understading External Knowledge, answer the following questions for the tables provided above."
    # question_prompt = "-- {}".format(question) + '\n SELECT '
    question_prompt = "-- {}".format(question)
    knowledge_prompt = "-- External Knowledge: {}".format(knowledge)

    if not knowledge_prompt:
        result_prompt = pattern_prompt_no_kg + '\n' + question_prompt
    else:
        result_prompt = knowledge_prompt + '\n' + pattern_prompt_kg + '\n' + question_prompt

    return result_prompt

def cot_wizard():
    cot = "\nGenerate the SQL after thinking step by step: "
    return cot

def generate_combined_prompts_one(db_path, question, knowledge=None):
    schema_prompt = generate_schema_prompt(db_path, num_rows=None) # This is the entry to collect values
    comment_prompt = generate_comment_prompt(question, knowledge)

    combined_prompts = schema_prompt + '\n\n' + comment_prompt + cot_wizard() + '\nSELECT '
    # combined_prompts = few_shot() + '\n\n' + schema_prompt + '\n\n' + comment_prompt
    return combined_prompts
```

("understading" is their typo, kept as-is.)

Rendered prompt, with Evidence:

```text
CREATE TABLE customers
(
    ...
)

CREATE TABLE gasstations
(
    ...
)

-- External Knowledge: <Evidence>
-- Using valid SQLite and understading External Knowledge, answer the following questions for the tables provided above.
-- <Question>
Generate the SQL after thinking step by step: 
SELECT 
```

- Evidence goes **before** the instruction and Question, on its own `-- External Knowledge:` line.
- Bug: `knowledge_prompt` is always a non-empty string, so `if not knowledge_prompt` is never true. The "without Evidence" run (`--use_knowledge False`) passes `knowledge=None` and gets `-- External Knowledge: None` plus the "understading External Knowledge" instruction. The clean no-Evidence wording (`-- Using valid SQLite, answer the following questions for the tables provided above.`) is dead code.
- `cot_wizard()` is appended every time. The `--chain_of_thought` flag only changes the output filename (`predict_dev_cot.json`), not the prompt.
- The prompt ends in `SELECT `, so the model has to continue the query right away. "Thinking step by step" can't actually happen before the SQL on this path.

### Few-shot

- `few_shot()` and `few_shot_no_kg()` hold the 1-shot `singer` example from Figure 9, but the only line that uses it is commented out. The released script is zero-shot.
- The 1-shot demo text, verbatim (with Evidence version):

```text
CREATE TABLE singer
(
    singer_id         TEXT not null
        primary key,
    nation       TEXT  not null,
    sname       TEXT null,
    dname       TEXT null,
    cname       TEXT null,
    age    INTEGER         not null,
    year  INTEGER          not null,
    birth_year  INTEGER          null,
    salary  REAL          null,
    city TEXT          null,
    phone_number   INTEGER          null,
--     tax   REAL      null,
)
-- External Knowledge: age = year - birth_year;
-- Using valid SQLite and understading External Knowledge, answer the following questions for the tables provided above.
-- How many singers in USA who is older than 27?
The final SQL is: Let's think step by step.
1. referring to external knowledge, we need to filter singers 'by year' - 'birth_year' > 27; 2. we should find out the singers of step 1 in which nation = 'US', 3. use COUNT() to count how many singers. Finally the SQL is: SELECT COUNT(*) FROM singer WHERE year - birth_year > 27;</s>
```

- Note the demo SQL forgets `nation = 'US'` even though step 2 says it. Figure 9 also leaves out the `-- How many singers...` Question line.

### API call and SQL extraction

```python
result = openai.Completion.create(engine=engine, prompt=prompt, max_tokens=256, temperature=0, stop=stop)
# called with stop=['--', '\n\n', ';', '#']
...
sql = 'SELECT' + plain_result['choices'][0]['text']
...
sql = sql + '\t----- bird -----\t' + db_id
```

- Legacy completions endpoint, one Question per call, `temperature=0`, `max_tokens=256`.
- Stop sequences `--`, blank line, `;`, `#` cut the reply at the end of the first statement. The `;` itself is dropped.
- Predicted SQL = `"SELECT"` + the completion text. No other cleanup, no execution check, no retry on bad SQL.
- On an API exception the string `error:<message>` is saved as the "SQL". It fails at execution and counts as wrong.
- Each line is stored as `<sql>\t----- bird -----\t<db_id>` in `predict_dev.json`. The evaluator splits on that marker.

### COT reply parsing (`post_process_cot.py`)

```python
cot, sql = v.split(': SELECT')
clean_sql = 'SELECT' + sql
...
clean_sql = 0 # filter resutls without valid SQL, i.e., too long, etc.
```

- Expects exactly one `: SELECT` (from `Finally the SQL is: SELECT ...`). Zero or two matches gives `0`.
- `evaluation.py` turns a non-string prediction into `" "` run against `financial`, so it scores as wrong.

## Code vs paper mismatches

- COT trigger text: paper says `The final SQL is: Let's think step by step.`; the code says `Generate the SQL after thinking step by step: ` and then forces `SELECT `.
- 1-shot example: paper says ChatGPT COT used it; code has it commented out.
- `run_gpt.sh` runs `gpt-3.5-turbo` through `openai.Completion.create`. That chat model isn't served on the legacy completions endpoint, so the script as committed can't have produced the ChatGPT numbers. The paper says Azure OpenAI was used.
- The released ChatGPT predictions look like they came from the COT path, not this script: 54 of 1534 entries (no Evidence) and 14 of 1534 (with Evidence) are the integer `0` that only `post_process_cot.py` writes, and most SQL strings end in `;`, which the zero-shot stop list would strip.
- Takeaway: the paper's exact ChatGPT/GPT-4/Claude-2 prompts are not fully reproducible from the repo. The structure is clear; the exact wording per run is not.

## Later fix (mini_dev, 2024, for comparison)

- `bird-bench/mini_dev/llm/src/prompt.py` fixes the Evidence bug (`if knowledge`), puts `-- External Knowledge:` **after** the Question, adds a dialect name, keeps a step-by-step line, and adds a plain instruction: "You only need to return the result {sql_dialect} SQL code start from SELECT". Not what the paper's baselines used.

## What this means for the demo

- To match the paper's zero-shot baseline: DDL from `sqlite_master`, Evidence line before the instruction, Question as a comment, end with `SELECT `, temperature 0, stop at `;` / blank line / `--` / `#`, prepend `SELECT`.
- For the "without Evidence" run, use the clean `pattern_prompt_no_kg` wording on purpose, and say we did. BIRD's own script sent `-- External Knowledge: None`.
- With a chat model (no raw completion endpoint), you can't force the reply to start mid-`SELECT`. Ask for SQL only and strip code fences, or parse `Finally the SQL is:` like `post_process_cot.py` does.
