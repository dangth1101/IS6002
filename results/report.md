# Batch report

## Caveats

- Subset: 50 dev Questions from 2 of 11 databases (superhero, toxicology), from `dev_20240627`. Empty-Evidence, tied and revised Questions were removed.
- The paper used all 1,534 dev Questions, an older dev version and a different call setup (completions endpoint, `SELECT` priming, and a no-Evidence prompt that still said `External Knowledge: None`). Its numbers are approximate.
- 1 Question = 2 EX points. No confidence intervals.

## Table A: EX with and without Evidence (paper Table 2, dev)

| Model | EX w/o Evidence | EX w/ Evidence | Difference | Paper w/o | Paper w/ | Paper row |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| openai/gpt-3.5-turbo | 28.00 | 66.00 | +38.00 | 25.88 | 36.64 | ChatGPT + COT (our prompt keeps "think step by step") |
| openai/gpt-4.1 | 40.00 | 68.00 | +28.00 | 30.90 | 46.35 | GPT-4 (different model, loose reference) |

## Table B: EX by difficulty (paper Table 4, dev)

| Model | Evidence | simple | moderate | challenging | total | Paper (simple / moderate / challenging / total) |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| openai/gpt-3.5-turbo | off | 11/30 (36.67%) | 3/16 (18.75%) | 0/4 (0.00%) | 14/50 (28.00%) | ChatGPT, no COT: 31.08 / 13.29 / 12.08 / 24.05 |
| openai/gpt-3.5-turbo | on | 23/30 (76.67%) | 10/16 (62.50%) | 0/4 (0.00%) | 33/50 (66.00%) | ChatGPT + KG, no COT: 45.44 / 26.14 / 19.01 / 37.22 |
| openai/gpt-4.1 | off | 14/30 (46.67%) | 5/16 (31.25%) | 1/4 (25.00%) | 20/50 (40.00%) | — |
| openai/gpt-4.1 | on | 22/30 (73.33%) | 12/16 (75.00%) | 0/4 (0.00%) | 34/50 (68.00%) | — |

## Verdicts

| Model | Evidence | Match | Mismatch | SQL error | Timeout | No SQL in reply |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| openai/gpt-3.5-turbo | off | 14 | 31 | 0 | 1 | 4 |
| openai/gpt-3.5-turbo | on | 33 | 15 | 2 | 0 | 0 |
| openai/gpt-4.1 | off | 20 | 29 | 0 | 0 | 1 |
| openai/gpt-4.1 | on | 34 | 16 | 0 | 0 | 0 |
