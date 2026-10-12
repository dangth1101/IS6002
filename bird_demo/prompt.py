"""Build the prompt the LLM gets, and pull the Predicted SQL out of its reply."""

import re

from bird_demo.data import load_ddl
from bird_demo.llm import Reply

# A fence left open (the model just stopped) runs to the end of the reply.
FENCE = re.compile(r"```[^\n]*\n(.*?)(?:```|\Z)", re.DOTALL)
# Leading SQL comments are skipped: models often write their step-by-step notes as comments.
STARTS_LIKE_SQL = re.compile(r"(?:\s*(?:--[^\n]*|/\*.*?\*/))*\s*(SELECT|WITH)\b", re.IGNORECASE | re.DOTALL)

# Copied from BIRD's code, typo "understading" and the trailing space included.
# Left out on purpose: the final "SELECT " line, which primed a completions model.
WITH_EVIDENCE = """{ddl}

-- External Knowledge: {evidence}
-- Using valid SQLite and understading External Knowledge, answer the following questions for the tables provided above.
-- {question}
Generate the SQL after thinking step by step: """

# BIRD's code sent "External Knowledge: None" here because of a dead-code bug.
# The demo uses the clean wording; the batch report says so.
WITHOUT_EVIDENCE = """{ddl}

-- Using valid SQLite, answer the following questions for the tables provided above.
-- {question}
Generate the SQL after thinking step by step: """


def build_prompt(db_id: str, question: str, evidence: str | None) -> str:
    """The whole prompt, sent as one user message. Empty Evidence means none."""
    if not evidence:
        return WITHOUT_EVIDENCE.format(ddl=load_ddl(db_id), question=question)
    return WITH_EVIDENCE.format(ddl=load_ddl(db_id), evidence=evidence, question=question)


def extract_sql(reply: Reply) -> str | None:
    """The Predicted SQL, or None for the Verdict "No SQL in reply"."""
    if reply.finish_reason == "length":
        return None  # cut off at max_tokens
    fences = FENCE.findall(reply.text)
    sql = fences[-1] if fences else reply.text
    sql = sql.strip().removesuffix(";").strip()
    # Catches bad extraction, not a security check: the read-only connection is that.
    if not STARTS_LIKE_SQL.match(sql):
        return None
    return sql
