"""The demo screen. Pick a Subset Question (Scored run) and see its Verdict.

    uv run streamlit run app.py

Thin on purpose: the prompt, the LLM seam, the runner and scoring all come
from bird_demo/, the same code the batch uses. Every Run calls the LLM live.
See SPEC.md section 8; mockup/ shows the look.
"""

import streamlit as st
from openai import OpenAIError

from bird_demo.data import db_path, load_subset_questions
from bird_demo.llm import MAX_TOKENS, Reply, complete, default_model
from bird_demo.prompt import build_prompt, extract_sql
from bird_demo.runner import Rows, SqlError, Timeout
from bird_demo.scoring import ScoredRun, Verdict, score

MAX_ROWS_SHOWN = 1_000

# The banner's one-line reason when scoring gave no note. SQL error and
# Timeout always come with one (SQLite's message, the deadline).
REASONS = {
    Verdict.MATCH: "Same set of rows as the Ground-truth SQL.",
    Verdict.MISMATCH: "The Predicted SQL ran, but the rows differ from the Ground-truth SQL.",
    Verdict.NO_SQL: "The reply had no SQL to run.",
}


@st.cache_data
def subset_questions() -> list[dict]:
    return load_subset_questions()


def label(q: dict) -> str:
    return f"#{q['question_id']} · {q['db_id']} · {q['difficulty']} · {q['question']}"


def show_rows(result: Rows) -> None:
    shown = result.rows[:MAX_ROWS_SHOWN]
    total = len(result.rows)
    if total > MAX_ROWS_SHOWN:
        st.caption(f"showing {MAX_ROWS_SHOWN:,} of {total:,}")
    else:
        st.caption(f"{total:,} rows" if total != 1 else "1 row")
    if not shown:
        return
    # Built by column, without pandas. A repeated column name gets a suffix so it isn't lost.
    names: list[str] = []
    for name in result.columns:
        unique = name
        while unique in names:
            unique += "'"
        names.append(unique)
    st.dataframe({n: [row[i] for row in shown] for i, n in enumerate(names)}, hide_index=True)


def show_predicted(scored: ScoredRun, predicted_sql: str | None, reply: Reply) -> None:
    st.subheader("Predicted SQL")
    if predicted_sql is None:
        st.caption("Raw reply (no SQL found)")
        st.code(reply.text, language=None, wrap_lines=True)
        return
    st.code(predicted_sql, language="sql", wrap_lines=True)
    match scored.predicted:
        case SqlError(message=message):
            st.caption(f"Error: {message}")
        case Timeout(timeout_s=timeout_s):
            st.caption(f"Stopped after {timeout_s:g} s")
        case Rows() as rows:
            show_rows(rows)


def show_banner(scored: ScoredRun, reply: Reply) -> None:
    if reply.finish_reason == "length":  # extract_sql gives no SQL for these, so it's No SQL in reply
        reason = f"Reply cut off at {MAX_TOKENS} tokens"
    else:
        reason = scored.note or REASONS.get(scored.verdict, "")
    is_match = scored.verdict == Verdict.MATCH
    banner = st.success if is_match else st.error
    banner(f"**EX = {int(is_match)} · {scored.verdict}**  \n{reason}")


def scored_run(q: dict, use_evidence: bool, model: str) -> None:
    prompt = build_prompt(q["db_id"], q["question"], q["evidence"] if use_evidence else None)
    try:
        with st.spinner(f"Asking {model}…"):
            reply = complete(prompt, model)
    except OpenAIError as e:
        st.error(f"The LLM call failed after retries, so nothing was scored.  \n{e}")
        return
    predicted_sql = extract_sql(reply)
    with st.spinner("Running both SQLs…"):
        scored = score(db_path(q["db_id"]), predicted_sql, q["SQL"])

    show_banner(scored, reply)
    if scored.verdict in (Verdict.MATCH, Verdict.MISMATCH):
        left, right, _ = st.columns([1, 1, 2])
        left.metric("Rows only in Predicted", scored.only_in_predicted)
        right.metric("Rows only in Ground-truth", scored.only_in_ground_truth)
    with st.expander("Prompt sent to the LLM"):
        st.code(prompt, language=None, wrap_lines=True)

    left, right = st.columns(2)
    with left:
        show_predicted(scored, predicted_sql, reply)
    with right:
        st.subheader("Ground-truth SQL")
        st.code(q["SQL"], language="sql", wrap_lines=True)
        show_rows(scored.ground_truth)


def main() -> None:
    st.set_page_config(page_title="BIRD text-to-SQL demo", layout="wide")
    model = default_model()
    questions = subset_questions()

    with st.sidebar:
        st.caption("Model")
        st.code(model, language=None)

    st.title("BIRD text-to-SQL")
    # key + on_change="rerun" make .open say which tab is showing; that tab decides the run type.
    tab_pick, tab_type = st.tabs(["Pick a BIRD dev Question", "Type your own"], key="input_tab", on_change="rerun")
    with tab_pick:
        q = st.selectbox("Question", questions, format_func=label)
        st.caption(f"Evidence: {q['evidence']}")
        use_evidence = st.toggle("Use Evidence", value=True)
    with tab_type:
        st.info("Typing your own Question isn't built yet.")

    if st.button("Run", type="primary", disabled=bool(tab_type.open)):
        st.divider()
        scored_run(q, use_evidence, model)


try:
    main()
except SystemExit as stop:
    # data.require() and llm.env() stop with one line saying what to fix.
    st.error(str(stop))
