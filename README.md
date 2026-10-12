# IS6002: BIRD text-to-SQL demo

A small demo based on the BIRD paper (Li et al., NeurIPS 2023, `075280-1835open.pdf`). An LLM turns a Question into SQL, the SQL runs on a BIRD database, and the result is scored with Execution Accuracy (EX).

- Terms: `CONTEXT.md`
- Plan and decisions: the [Wayfinder map](https://github.com/dangth1101/IS6002/issues/1)
- Build spec: `SPEC.md`
- `mockup/` and `prototype/` are design references for the screen, not shipped code

## Get the data

The BIRD data isn't in git. `data/` is ignored because the official zip is 346 MB. Download it once:

```sh
mkdir -p data && cd data

# dev_20240627: the Questions and databases the demo uses (from https://bird-bench.github.io/)
curl -LO https://bird-bench.oss-cn-beijing.aliyuncs.com/dev.zip
unzip -q dev.zip -x '__MACOSX/*' '*.DS_Store'

# Only unpack the two databases in the Subset (the full set is ~1.5 GB)
cd dev_20240627
unzip -q dev_databases.zip 'dev_databases/superhero/*' 'dev_databases/toxicology/*' -x '*.DS_Store'
cd ..

# dev_20251106: BIRD's Nov 2025 revision, Questions only. Used to filter out Questions whose Ground-truth SQL BIRD later fixed
mkdir -p dev_20251106
curl -L -o dev_20251106/dev.json \
  https://huggingface.co/datasets/birdsql/bird_sql_dev_20251106/resolve/main/data/dev_20251106-00000-of-00001.json
```

You should end up with:

```
data/
  dev.zip                            safe to delete after unpacking
  dev_20240627/
    dev.json                         1,534 Questions
    dev_tables.json                  schemas
    dev_tied_append.json             alternate Ground-truth SQL for 42 tied Questions
    dev_databases.zip
    dev_databases/
      superhero/superhero.sqlite
      superhero/database_description/*.csv
      toxicology/toxicology.sqlite
      toxicology/database_description/*.csv
  dev_20251106/
    dev.json                         same 1,534 question_ids, revised text and SQL
```

Notes:

- The description CSVs start with a BOM and have multi-line values. Read them with a CSV parser and `encoding="utf-8-sig"`.
- Data license: CC BY-SA 4.0.

## Set up and run

Needs [uv](https://docs.astral.sh/uv/). Python 3.12 is pinned.

```sh
uv sync
uv run pytest                            # no network, no data/ needed
uv run python scripts/make_subset.py     # once; rewrites subset.json
uv run streamlit run app.py
uv run python scripts/batch_eval.py --model openai/gpt-3.5-turbo --model openai/gpt-4.1
```

The app lets you pick a Subset Question, asks the LLM live on every Run, and shows the Verdict with both SQLs and their rows.

`subset.json` is committed, so you only rerun the Subset script to check it. It needs both `dev.json` files and gives a byte-identical file every time.

The batch runs every Subset Question with Evidence off and on for each `--model` (default `LLM_MODEL`). It writes one row per run to `results/runs.csv`, prints the report next to the paper's numbers and saves it as `results/report.md`. With `openai/gpt-3.5-turbo` in the run it also writes `results/failures_to_label.csv` for labelling by hand (SPEC.md section 10). Replies are cached in `.cache/llm/`, so a rerun makes no LLM calls; `--no-cache` calls again.

## LLM connection

Copy `.env.example` to `.env` and fill in `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL`.
