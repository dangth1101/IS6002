"""PROTOTYPE, throwaway. Answers ticket "What the demo screen shows" (#6).

Three structurally different layouts of the demo screen, switchable via ?variant=A|B|C
and the floating bar at the bottom (or the left/right arrow keys).
No LLM, no database: every outcome is canned mock data, picked in the sidebar.

Run:  uv run --with streamlit streamlit run prototype/demo_screen_prototype.py
"""

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="BIRD demo (prototype)", layout="wide")

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

# Each outcome: which question, what the model replied with Evidence on/off, and the verdict.
# verdict: match | mismatch | error | timeout | empty_match | no_sql | unscored
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
        on=dict(sql="SELECT MAX(a.`Free Meal Count (K-12)` / b.`Enrollment (K-12)`)\nFROM frpm a, frpm b, frpm c", cols=[], rows=None,
                error="Stopped after 30 s", verdict="timeout"),
        off=dict(sql="SELECT MAX(a.`Free Meal Count (K-12)` / b.`Enrollment (K-12)`)\nFROM frpm a, frpm b, frpm c", cols=[], rows=None,
                 error="Stopped after 30 s", verdict="timeout"),
    ),
    "Match on empty result": dict(
        q=Q_EMPTY,
        on=dict(sql="SELECT superhero_name FROM superhero\nWHERE eye_colour_id = 7 AND weight_kg > 1000",
                cols=["superhero_name"], rows=[], verdict="empty_match"),
        off=dict(sql="SELECT superhero_name FROM superhero\nWHERE eye_colour = 'Blue' AND weight_kg > 1000", cols=[], rows=None,
                 error="no such column: eye_colour", verdict="error"),
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
    question="How many schools are in Alameda County?",
    db="california_schools",
    sql="SELECT COUNT(*) FROM schools WHERE County = 'Alameda'",
    cols=["COUNT(*)"],
    rows=[(573,)],
)

VERDICT_TEXT = {
    "match": ("success", "EX = 1 · Match", "Same set of rows as the Ground-truth SQL."),
    "mismatch": ("error", "EX = 0 · Mismatch", "The query ran, but the rows differ from the Ground-truth SQL."),
    "error": ("error", "EX = 0 · SQL error", "The Predicted SQL failed to run."),
    "timeout": ("error", "EX = 0 · Timeout", "The Predicted SQL ran past the 30 s limit."),
    "empty_match": ("warning", "EX = 1 · Match on empty result",
                    "Both queries returned no rows. BIRD counts this as a match, but it proves little."),
    "no_sql": ("error", "EX = 0 · No SQL in reply", "The model's reply had no SQL to run. Raw reply below."),
}


def build_prompt(q, evidence_on):
    ev = q["evidence"] if evidence_on else "None"
    return f"CREATE TABLE frpm (...);\nCREATE TABLE schools (...);\n...\n-- External Knowledge: {ev}\n-- Question: {q['question']}"


def rows_df(cols, rows):
    if rows is None:
        return None
    return pd.DataFrame(rows, columns=cols or None)


def verdict_box(v, compact=False):
    kind, title, why = VERDICT_TEXT[v]
    box = getattr(st, kind)
    box(f"**{title}**" if compact else f"**{title}**  \n{why}")


def show_result(r):
    if r["sql"] is None:
        st.caption("Raw reply (no SQL found)"); st.code(r["raw"], language=None, wrap_lines=True)
        return
    st.code(r["sql"], language="sql")
    if r.get("error"):
        st.caption(f"Error: {r['error']}")
    else:
        df = rows_df(r["cols"], r["rows"])
        if len(df):
            st.dataframe(df, hide_index=True, width="stretch")
        else:
            st.caption("0 rows")


# ---------------------------------------------------------------- sidebar: mock controls
with st.sidebar:
    st.markdown("### PROTOTYPE controls")
    mode = st.radio("Run type", ["Scored (BIRD dev Question)", "Unscored (typed Question)"])
    outcome_key = st.selectbox("Mock outcome", list(OUTCOMES), disabled=mode.startswith("Unscored"))
    st.caption("These controls fake what the LLM and the database would return. Not part of the design.")
    st.divider()
    st.caption("Model: `openai/gpt-4.1` (read-only)")

scored = mode.startswith("Scored")
oc = OUTCOMES[outcome_key]
q = oc["q"]


# ---------------------------------------------------------------- variants
def variant_a():
    """Side by side: Predicted vs Ground-truth in two columns, verdict banner on top."""
    st.title("BIRD text-to-SQL")
    tab_pick, tab_type = st.tabs(["Pick a BIRD dev Question", "Type your own"])
    with tab_pick:
        st.selectbox("Question", [f"#{q['id']} · {q['db']} · {q['difficulty']} · {q['question']}"])
        st.caption(f"Evidence: {q['evidence']}")
    with tab_type:
        st.selectbox("Database", ["california_schools", "superhero"])
        st.text_input("Question", UNSCORED["question"])
    ev_on = st.toggle("Use Evidence", value=True, disabled=not scored)
    st.button("Run", type="primary")
    st.divider()

    if not scored:
        st.info("**Unscored run** · no Ground-truth SQL for a typed Question, so no EX verdict.")
        show_result(UNSCORED)
        return
    r = oc["on"] if ev_on else oc["off"]
    verdict_box(r["verdict"])
    left, right = st.columns(2)
    with left:
        st.subheader("Predicted SQL")
        show_result(r)
    with right:
        st.subheader("Ground-truth SQL")
        show_result(dict(sql=q["gt_sql"], cols=q["gt_cols"], rows=q["gt_rows"]))


def variant_b():
    """Pipeline: one vertical walk through Question → prompt → SQL → rows → verdict."""
    st.title("How one Question becomes SQL")
    c1, c2 = st.columns([3, 1])
    with c1:
        if scored:
            st.selectbox("BIRD dev Question", [f"#{q['id']} · {q['question']}"], label_visibility="collapsed")
        else:
            st.text_input("Your Question", UNSCORED["question"], label_visibility="collapsed")
    with c2:
        ev_on = st.toggle("Evidence", value=True, disabled=not scored)

    st.markdown("#### 1 · Question")
    if scored:
        st.write(q["question"])
        st.caption(f"{q['db']} · {q['difficulty']}")
        st.markdown("#### 2 · Evidence")
        st.write(q["evidence"] if ev_on else "_Off. The model sees `-- External Knowledge: None`._")
    else:
        st.write(UNSCORED["question"])
        st.markdown("#### 2 · Evidence")
        st.write("_None. A typed Question has no BIRD Evidence._")

    st.markdown("#### 3 · Prompt sent to the LLM")
    with st.expander("Show full prompt"):
        st.code(build_prompt(q if scored else {**q, "question": UNSCORED["question"]}, scored and ev_on), language="sql")

    r = (oc["on"] if ev_on else oc["off"]) if scored else UNSCORED
    st.markdown("#### 4 · Predicted SQL")
    if r["sql"] is None:
        st.caption("Raw reply (no SQL found)"); st.code(r["raw"], language=None, wrap_lines=True)
    else:
        st.code(r["sql"], language="sql")
    st.markdown("#### 5 · Rows")
    if r.get("error"):
        st.caption(f"Error: {r['error']}")
    elif r["rows"] is not None:
        df = rows_df(r["cols"], r["rows"])
        if len(df):
            st.dataframe(df, hide_index=True)
        else:
            st.caption("0 rows")

    st.markdown("#### 6 · Verdict")
    if not scored:
        st.info("Unscored run. No Ground-truth SQL to compare against.")
        return
    verdict_box(r["verdict"])
    if r["rows"] is not None:
        pred, gt = set(r["rows"]), set(q["gt_rows"])
        a, b = st.columns(2)
        a.metric("Rows only in Predicted", len(pred - gt))
        b.metric("Rows only in Ground-truth", len(gt - pred))
    with st.expander("Ground-truth SQL and rows"):
        show_result(dict(sql=q["gt_sql"], cols=q["gt_cols"], rows=q["gt_rows"]))


def variant_c():
    """Evidence A/B: every run is done twice, Evidence off vs on, side by side."""
    st.title("Does Evidence help?")
    if scored:
        st.selectbox("BIRD dev Question", [f"#{q['id']} · {q['db']} · {q['question']}"])
    else:
        st.text_input("Your Question", UNSCORED["question"])
    st.button("Run with and without Evidence", type="primary")
    st.divider()

    if not scored:
        st.info("**Unscored run** · a typed Question has no Evidence and no Ground-truth SQL, so there's only one column.")
        show_result(UNSCORED)
        return

    with st.expander(f"Ground-truth SQL · {len(q['gt_rows'])} rows"):
        show_result(dict(sql=q["gt_sql"], cols=q["gt_cols"], rows=q["gt_rows"]))

    off, on = st.columns(2)
    with off:
        st.subheader("Without Evidence")
        st.caption("`-- External Knowledge: None`")
        verdict_box(oc["off"]["verdict"], compact=True)
        show_result(oc["off"])
    with on:
        st.subheader("With Evidence")
        st.caption(q["evidence"])
        verdict_box(oc["on"]["verdict"], compact=True)
        show_result(oc["on"])


VARIANTS = {
    "A": ("Side by side", variant_a),
    "B": ("Pipeline", variant_b),
    "C": ("Evidence A/B", variant_c),
}

# ---------------------------------------------------------------- switcher
keys = list(VARIANTS)
current = st.query_params.get("variant", "A")
if current not in VARIANTS:
    current = "A"
VARIANTS[current][1]()

st.markdown(
    """<style>
    .st-key-proto_switcher {position: fixed; bottom: 18px; left: 50%; transform: translateX(-50%);
      z-index: 9999; width: 360px !important; background: #111; color: #fff; border-radius: 999px;
      padding: 6px 10px; box-shadow: 0 4px 16px rgba(0,0,0,.35);}
    .st-key-proto_switcher p {color: #fff; margin: 0; text-align: center; font-family: monospace;}
    .st-key-proto_switcher button {background: #333; color: #fff; border: none;}
    </style>""",
    unsafe_allow_html=True,
)


def go(step):
    i = (keys.index(current) + step) % len(keys)
    st.query_params["variant"] = keys[i]


with st.container(key="proto_switcher"):
    a, mid, b = st.columns([1, 3, 1], vertical_alignment="center")
    a.button("←", key="proto_prev", on_click=go, args=(-1,))
    mid.markdown(f"{current} ({VARIANTS[current][0]})")
    b.button("→", key="proto_next", on_click=go, args=(1,))

# Arrow keys cycle variants, unless typing in a field.
components.html(
    """<script>
    const doc = window.parent.document;
    if (!doc.__protoKeys) {
      doc.__protoKeys = true;
      doc.addEventListener('keydown', e => {
        const t = e.target;
        if (t.closest('input, textarea, [contenteditable]')) return;
        const k = e.key === 'ArrowLeft' ? 'proto_prev' : e.key === 'ArrowRight' ? 'proto_next' : null;
        if (k) doc.querySelector('.st-key-' + k + ' button')?.click();
      });
    }
    </script>""",
    height=0,
)
