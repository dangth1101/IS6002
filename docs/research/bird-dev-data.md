# BIRD dev data: where to get it and what's in it

Research for issue #2. Checked 2026-10-12 against the live download and the paper (`075280-1835open.pdf`).

## Download

- Official dev set: https://bird-bench.oss-cn-beijing.aliyuncs.com/dev.zip, linked from https://bird-bench.github.io/
- Size: 346,207,293 bytes (about 346 MB). Last modified 2024-06-29 (from the server's `Content-Length` and `Last-Modified` headers).
- Unzipped, the 11 `.sqlite` files total about 1.49 GB. So the "1.4 GB" figure is the unpacked size, not the download.
- The server accepts HTTP range requests. I read the file list and the small JSON files without downloading the full zip.
- License: CC BY-SA 4.0 (since 2024-04-27, per bird-bench.github.io).
- Paper split: 95 databases, 69 train / 11 dev / 15 hidden test. 9,428 train, 1,534 dev, 1,789 test Questions (paper §3.2 and datasheet appendix).

## Folder layout of `dev.zip`

```
dev_20240627/
  dev.json               741 KB   1,534 Question records
  dev.sql                272 KB   one Ground-truth SQL per line: "<SQL>\t<db_id>"
  dev_tables.json        158 KB   schema for the 11 databases (Spider format)
  dev_tied_append.json    26 KB   42 extra records, alternate Ground-truth SQL for ties
  dev_databases.zip      346 MB   nested zip, unpacks to:
    dev_databases/<db_id>/
      <db_id>.sqlite
      database_description/<table>.csv   one CSV per table
```

- The databases are a zip inside the zip. Unpack twice.
- The nested zip carries macOS junk (`.DS_Store`, `__MACOSX/`). Skip it when loading.
- `dev.sql` lines are in the same order as `dev.json` (line 1 = `question_id` 0).

## Fields on each Question record (`dev.json`)

All 1,534 records have exactly these six keys:

| Field | Meaning | Example (`question_id` 0) |
| --- | --- | --- |
| `question_id` | int, 0 to 1533, unique | `0` |
| `db_id` | which of the 11 databases | `"california_schools"` |
| `question` | the Question | "What is the highest eligible free rate for K-12 students in the schools in Alameda County?" |
| `evidence` | the Evidence sentence | "Eligible free rate for K-12 = \`Free Meal Count (K-12)\` / \`Enrollment (K-12)\`" |
| `SQL` | the Ground-truth SQL (SQLite dialect) | ``SELECT `Free Meal Count (K-12)` / `Enrollment (K-12)` FROM frpm WHERE ...`` |
| `difficulty` | `simple`, `moderate` or `challenging` | `"simple"` |

- 148 of 1,534 Questions have empty Evidence.
- Column names with spaces and brackets are quoted with backticks in the Ground-truth SQL. Prompts must show the real names.
- `dev_tied_append.json` uses the same six fields. Its 42 `question_id`s all exist in `dev.json` and give a second accepted Ground-truth SQL where `ORDER BY ... LIMIT 1` has ties (bird-bench.github.io news, 2023-07-14).

## Per-database extras

- `dev_tables.json`: one object per database with `db_id`, `table_names_original`, `table_names`, `column_names_original`, `column_names`, `column_types`, `primary_keys`, `foreign_keys`. Same shape as Spider's `tables.json`. Columns are `[table_index, name]`, with index -1 for `*`.
- `database_description/<table>.csv`: one per table. Header: `original_column_name,column_name,column_description,data_format,value_description`.
  - `column_name` is the expanded name and is often blank.
  - `value_description` explains coded values, e.g. financial `loan.status`: "'A' stands for contract finished, no problems; ..." and units like "unit：US dollar".
  - Watch out: files start with a UTF-8 BOM, some use full-width colons (`：`), and quoted values span lines. Read with a real CSV parser and `encoding="utf-8-sig"`.
  - The paper (§3.3) says these files give full schema names and value descriptions, built to help annotators.
- I read two CSVs (`financial/loan.csv`, `financial/client.csv`) from the official `minidev.zip`. Their byte sizes match the dev.zip copies exactly.

## The 11 dev databases

Counts computed from `dev.json` in the current `dev.zip`. Tables and columns from `dev_tables.json` (columns exclude `*`). `.sqlite` size is the uncompressed size from the zip's file list.

| db_id | Questions | simple | moderate | challenging | tables | columns | .sqlite |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| card_games | 191 | 125 | 53 | 13 | 6 | 115 | 250 MB |
| codebase_community | 186 | 151 | 30 | 5 | 8 | 71 | 459 MB |
| formula_1 | 174 | 117 | 43 | 14 | 13 | 94 | 21 MB |
| thrombosis_prediction | 163 | 50 | 85 | 28 | 3 | 64 | 7.0 MB |
| student_club | 158 | 101 | 48 | 9 | 8 | 48 | 2.5 MB |
| toxicology | 145 | 76 | 38 | 31 | 4 | 11 | 2.6 MB |
| superhero | 129 | 81 | 33 | 15 | 10 | 31 | 0.2 MB |
| european_football_2 | 129 | 65 | 50 | 14 | 7 | 199 | 570 MB |
| financial | 106 | 62 | 37 | 7 | 8 | 55 | 68 MB |
| california_schools | 89 | 54 | 30 | 5 | 3 | 89 | 11 MB |
| debit_card_specializing | 64 | 43 | 17 | 4 | 5 | 21 | 33 MB |
| **Total** | **1,534** | **925** | **464** | **145** | | | **1,424 MB** |

Sizes are MiB (1,048,576 bytes). Total is 1,493,287,936 bytes, about 1.49 GB decimal.

- Dev split is 60% simple, 30% moderate, 9.5% challenging.
- The paper's appendix B.1 says "simple (30%), moderate (60%), and challenging (10%)". The released dev data has simple and moderate the other way round. Trust the file.

## Dev set versions

- There is more than one dev set. Pick one and say which in the demo.
  - **2023 original.** This is what the paper's EX numbers use. The site only links the current zip.
  - **2023-09-25 cleanup.** All dev cases were re-checked. ChatGPT EX went from 37.22 to 42.24 (bird-bench.github.io news).
  - **`dev_20240627`.** This is what `dev.zip` serves today. The numbers above come from it.
  - **`bird_sql_dev_20251106`.** Questions only, no databases: https://huggingface.co/datasets/birdsql/bird_sql_dev_20251106 . Same 1,534 `question_id`s and the same 11 databases.
- The 2025-11 revision is a big change, not a typo fix. Compared with `dev_20240627`:
  - 619 records changed: question 182, Evidence 381, Ground-truth SQL 452, difficulty 86.
  - The split moves to 860 / 443 / 231 (simple / moderate / challenging).
  - Some Questions were rewritten from scratch. `question_id` 0 is now a multi-part question about charter status, grades, SAT level and deviation from the county average.
- Mini-Dev: 500 Questions over the same 11 databases, in SQLite, MySQL and PostgreSQL. Download: https://bird-bench.oss-cn-beijing.aliyuncs.com/minidev.zip (801 MB). Repo: https://github.com/bird-bench/mini_dev

## Sources

- Paper: Li et al., NeurIPS 2023, `075280-1835open.pdf` (§3.2 databases, §3.3 description files, appendix B.1 difficulty, datasheet splits)
- https://bird-bench.github.io/ (download links, news and changelog, license)
- https://bird-bench.oss-cn-beijing.aliyuncs.com/dev.zip (headers, zip file list, and `dev.json`, `dev.sql`, `dev_tables.json`, `dev_tied_append.json` read with range requests)
- https://github.com/AlibabaResearch/DAMO-ConvAI/tree/main/bird (README: layout and field meanings)
- https://huggingface.co/datasets/birdsql/bird_sql_dev_20251106 (2025-11 revision)
- https://github.com/bird-bench/mini_dev and https://bird-bench.oss-cn-beijing.aliyuncs.com/minidev.zip (Mini-Dev, description CSV sample)
