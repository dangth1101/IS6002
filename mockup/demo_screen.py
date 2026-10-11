"""MOCKUP of the demo screen: the final design from ticket "What the demo screen shows" (#6).

The reference layout for the build. No LLM, no database: results are canned, and the
"Mock outcome" picker in the sidebar fakes what a run returns. Drop that picker when building.

Run:  uv run --with streamlit streamlit run mockup/demo_screen.py
"""

import pandas as pd
import streamlit as st

st.set_page_config(page_title="BIRD text-to-SQL demo", layout="wide")

# ---------------------------------------------------------------- mock data
# Questions 0 and 1 are real BIRD dev records (california_schools). Rows are invented.

Q0 = {
    "id": 0,
    "db": "california_schools",
    "difficulty": "simple",
    "question": "What is the highest eligible free rate for K-12 students in the schools in Alameda County?",
    "evidence": "Eligible free rate for K-12 = `Free Meal Count (K-12)` / `Enrollment (K-12)`",
    "gt_sql": "SELECT `Free Meal Count (K-12)` / `Enrollment (K-12)` FROM frpm\nWHERE `County Name` = 'Alameda'\nORDER BY (CAST(`Free Meal Count (K-12)` AS REAL) / `Enrollment (K-12)`) DESC\nLIMIT 1",
    "gt_cols": ["rate"],
    "gt_rows": [(1.0,)],
}
Q1 = {
    "id": 1,
    "db": "california_schools",
    "difficulty": "moderate",
    "question": "Please list the zip code of all the charter schools in Fresno County Office of Education.",
    "evidence": "Charter schools refers to `Charter School (Y/N)` = 1 in the table frpm",
    "gt_sql": "SELECT T2.Zip FROM frpm AS T1\nINNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode\nWHERE T1.`District Name` = 'Fresno County Office of Education'\n  AND T1.`Charter School (Y/N)` = 1",
    "gt_cols": ["Zip"],
    "gt_rows": [("93726-5309",), ("93628-9602",), ("93706-2611",)],
}
Q_EMPTY = {
    "id": 777,
    "db": "superhero",
    "difficulty": "simple",
    "question": "(mock) Which superheroes with blue eyes weigh over 1,000 kg?",
    "evidence": "blue eyes refers to colour = 'Blue' where eye_colour_id = colour.id; weigh over 1,000 kg refers to weight_kg > 1000",
    "gt_sql": "SELECT T1.superhero_name FROM superhero AS T1\nINNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id\nWHERE T2.colour = 'Blue' AND T1.weight_kg > 1000",
    "gt_cols": ["superhero_name"],
    "gt_rows": [],
}

# What a Scored run returns, with Evidence on and off.
OUTCOMES = {
    "Match": dict(
        q=Q0,
        on=dict(sql=Q0["gt_sql"], cols=["rate"], rows=[(1.0,)], verdict="match"),
        off=dict(
            sql="SELECT MAX(`Percent (%) Eligible Free (K-12)`) FROM frpm\nWHERE `County Name` = 'Alameda'",
            cols=["max"], rows=[(0.9,)], verdict="mismatch"),
    ),
    "Mismatch (extra column)": dict(
        q=Q1,
        on=dict(
            sql="SELECT T2.Zip, T2.School FROM frpm AS T1\nJOIN schools AS T2 ON T1.CDSCode = T2.CDSCode\nWHERE T1.`District Name` = 'Fresno County Office of Education'\n  AND T1.`Charter School (Y/N)` = 1",
            cols=["Zip", "School"],
            rows=[("93726-5309", "Edison Bethune Charter"), ("93628-9602", "Sierra Charter"), ("93706-2611", "Fresno Academy")],
            verdict="mismatch"),
        off=dict(
            sql="SELECT Zip FROM schools\nWHERE District = 'Fresno County Office of Education' AND Charter = 1",
            cols=["Zip"], rows=[("93726-5309",), ("93628-9602",), ("93706-2611",)], verdict="match"),
    ),
    "SQL error": dict(
        q=Q1,
        on=dict(sql="SELECT ZipCode FROM schools WHERE Charter = 1", cols=[], rows=None,
                error="no such column: ZipCode", verdict="error"),
        off=dict(sql="SELECT ZipCode FROM schools WHERE Charter = 1", cols=[], rows=None,
                 error="no such column: ZipCode", verdict="error"),
    ),
    "Timeout": dict(
        q=Q0,
        on=dict(sql="SELECT MAX(a.`Free Meal Count (K-12)` / b.`Enrollment (K-12)`)\nFROM frpm a, frpm b, frpm c",
                cols=[], rows=None, error="Stopped after 30 s", verdict="timeout"),
        off=dict(sql="SELECT MAX(a.`Free Meal Count (K-12)` / b.`Enrollment (K-12)`)\nFROM frpm a, frpm b, frpm c",
                 cols=[], rows=None, error="Stopped after 30 s", verdict="timeout"),
    ),
    "Match on empty result": dict(
        q=Q_EMPTY,
        on=dict(sql="SELECT superhero_name FROM superhero\nWHERE eye_colour_id = 7 AND weight_kg > 1000",
                cols=["superhero_name"], rows=[], verdict="empty_match"),
        off=dict(sql="SELECT superhero_name FROM superhero\nWHERE eye_colour = 'Blue' AND weight_kg > 1000",
                 cols=[], rows=None, error="no such column: eye_colour", verdict="error"),
    ),
    "No SQL in reply": dict(
        q=Q1,
        on=dict(sql=None, raw="I'm not sure which table marks a school as charter. Could you tell me the column name?",
                cols=[], rows=None, verdict="no_sql"),
        off=dict(sql=None, raw="I'm not sure which table marks a school as charter. Could you tell me the column name?",
                 cols=[], rows=None, verdict="no_sql"),
    ),
}
UNSCORED = dict(
    sql="SELECT COUNT(*) FROM schools WHERE County = 'Alameda'",
    cols=["COUNT(*)"],
    rows=[(573,)],
)

# The six verdict labels: banner colour, title, one-line reason.
VERDICTS = {
    "match": ("success", "EX = 1 · Match", "Same set of rows as the Ground-truth SQL."),
    "mismatch": ("error", "EX = 0 · Mismatch", "The query ran, but the rows differ from the Ground-truth SQL."),
    "error": ("error", "EX = 0 · SQL error", "The Predicted SQL failed to run."),
    "timeout": ("error", "EX = 0 · Timeout", "The Predicted SQL ran past the 30 s limit."),
    "empty_match": ("warning", "EX = 1 · Match on empty result",
                    "Both queries returned no rows. BIRD counts this as a match, but it proves little."),
    "no_sql": ("error", "EX = 0 · No SQL in reply", "The model's reply had no SQL to run."),
}


def build_prompt(question, evidence):
    return (
        "CREATE TABLE frpm (...);\nCREATE TABLE schools (...);\n...\n"
        f"-- External Knowledge: {evidence or 'None'}\n"
        f"-- Question: {question}"
    )


def show_sql_and_rows(r):
    if r["sql"] is None:
        st.caption("Raw reply (no SQL found)")
        st.code(r["raw"], language=None, wrap_lines=True)
        return
    st.code(r["sql"], language="sql")
    if r.get("error"):
        st.caption(f"Error: {r['error']}")
    elif r["rows"]:
        st.dataframe(pd.DataFrame(r["rows"], columns=r["cols"]), hide_index=True, width="stretch")
    else:
        st.caption("0 rows")


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.caption("Model")
    st.code("openai/gpt-4.1", language=None)
    st.divider()
    st.markdown("**Mockup only**")
    outcome = OUTCOMES[st.selectbox("Mock outcome", list(OUTCOMES))]
    st.caption("Fakes what a run returns. Not part of the design.")

q = outcome["q"]

# ---------------------------------------------------------------- input
st.title("BIRD text-to-SQL")

# on_change="rerun" + key makes .open tell us which tab is active: that tab decides Scored vs Unscored.
tab_pick, tab_type = st.tabs(["Pick a BIRD dev Question", "Type your own"], key="input_tab", on_change="rerun")
with tab_pick:
    st.selectbox("Question", [f"#{q['id']} · {q['db']} · {q['difficulty']} · {q['question']}"])
    st.caption(f"Evidence: {q['evidence']}")
with tab_type:
    db = st.selectbox("Database", ["california_schools", "superhero"])
    typed = st.text_input("Question", "How many schools are in Alameda County?")

scored = not tab_type.open
use_evidence = st.toggle("Use Evidence", value=True, disabled=not scored,
                         help=None if scored else "A typed Question has no BIRD Evidence.")
st.button("Run", type="primary")
st.divider()

# ---------------------------------------------------------------- result: Unscored run
if not scored:
    st.info("**Unscored run** · a typed Question has no Ground-truth SQL, so there's no EX verdict.")
    with st.expander("Prompt sent to the LLM"):
        st.code(build_prompt(typed, None), language="sql")
    st.subheader("Predicted SQL")
    show_sql_and_rows(UNSCORED)
    st.stop()

# ---------------------------------------------------------------- result: Scored run
r = outcome["on"] if use_evidence else outcome["off"]

# 1. Verdict banner
kind, title, why = VERDICTS[r["verdict"]]
getattr(st, kind)(f"**{title}**  \n{why}")

# 2. Row-diff counts (only when the Predicted SQL returned rows to compare)
if r["rows"] is not None:
    pred, gt = set(r["rows"]), set(q["gt_rows"])
    c1, c2, _ = st.columns([1, 1, 2])
    c1.metric("Rows only in Predicted", len(pred - gt))
    c2.metric("Rows only in Ground-truth", len(gt - pred))

# 3. Prompt sent, collapsed
with st.expander("Prompt sent to the LLM"):
    st.code(build_prompt(q["question"], q["evidence"] if use_evidence else None), language="sql")

# 4. Predicted vs Ground-truth
left, right = st.columns(2)
with left:
    st.subheader("Predicted SQL")
    show_sql_and_rows(r)
with right:
    st.subheader("Ground-truth SQL")
    show_sql_and_rows(dict(sql=q["gt_sql"], cols=q["gt_cols"], rows=q["gt_rows"]))
