# BIRD Text-to-SQL Demo

A small demo of the BIRD benchmark (Li et al., NeurIPS 2023): turn a natural-language question into SQL with an LLM, run it on a BIRD database, and score it the way the paper does.

## Language

**Question**:
A natural-language request about the data in one BIRD database.
_Avoid_: query (that's the SQL), prompt

**Ground-truth SQL**:
The human-annotated SQL that BIRD pairs with a Question; the reference answer a prediction is compared against.
_Avoid_: gold SQL, correct SQL, expected query

**Predicted SQL**:
The SQL the LLM generates for a Question.
_Avoid_: generated query, model output

**Evidence**:
An external knowledge sentence for a Question, mapping its wording onto database values (e.g. "eligible for loans refers to type = 'OWNER'"). BIRD supplies it for dev Questions; the user may type one for an Unscored run.
_Avoid_: hint, context, knowledge

**Execution Accuracy (EX)**:
The share of Questions whose Predicted SQL returns the same result as the Ground-truth SQL when both are run.
_Avoid_: accuracy, score

**Subset**:
The fixed list of dev Questions that the batch eval and the app's dev picker both use, so every run scores the same Questions.
_Avoid_: sample, test set

**Scored run**:
Running a BIRD dev Question, which has Ground-truth SQL, so the result gets a Verdict.

**Verdict**:
The outcome of a Scored run, one of: Match, Mismatch, SQL error, Timeout, No SQL in reply. Only Match counts toward EX.
_Avoid_: result, status, score

**Failure cause**:
The hand-assigned main reason a failed Scored run went wrong, one of the paper's three (Wrong Schema Linking, Misunderstanding Database Content, Misunderstanding Knowledge Evidence) or Other with a short note. Only Mismatch, SQL error and Timeout runs get one.
_Avoid_: error type, error category

**Unscored run**:
Running a free-text Question the user typed; it has no Ground-truth SQL, so it shows SQL and rows only.
