"""Exports from available artifacts and real user-triggered demo runs."""
import csv, io, json
from bird_demo.benchmark.dashboard import owner_access_granted
import streamlit as st
from bird_demo.benchmark.dashboard import read_registry, load_table, ROOT, visible_run_artifact
st.set_page_config(page_title="BIRD-VN Reports",page_icon=":material/analytics:",layout="wide")
st.title("Reports & Run History")
st.caption("Dashboard không tạo kết quả giả. Demo Run chỉ lưu trong session và không phải official replicate.")
registry=read_registry();runs=st.session_state.get("birdvn_demo_runs",[])
with st.sidebar:
    token=st.text_input("Owner token for Final artifact exports",type="password",key="birdvn_report_token")
    owner=owner_access_granted(token)
if runs:
    flat=[]
    for run in runs:
        for item in run["results"]:
            result=item.get("run_result");sql_result=result.get("result") if isinstance(result,dict) else None
            flat.append({"group_id":run["group_id"],"model":run["model"],"mode":run["mode"],"question_id":item["question"]["question_id"],"question":item["question"]["question"],"sql":item.get("sql"),"elapsed_s":item.get("elapsed"),"execution_status":"success" if sql_result else "error/no_sql","row_count":len(sql_result.rows) if sql_result else None,"error":item.get("error")})
    st.dataframe(flat,hide_index=True,use_container_width=True)
    csv_buffer=io.StringIO();writer=csv.DictWriter(csv_buffer,fieldnames=flat[0].keys());writer.writeheader();writer.writerows(flat)
    st.download_button("Export demo runs CSV",csv_buffer.getvalue(),"bird_vn_demo_runs.csv","text/csv")
    st.download_button("Export demo runs JSON",json.dumps(flat,ensure_ascii=False,indent=2),"bird_vn_demo_runs.json","application/json")
else:st.info("Chưa có demo run trong phiên này.")
st.subheader("Saved artifacts")
run_dir=ROOT/"benchmark_data/runs"
files=sorted(run_dir.glob("*.json"),key=lambda p:p.stat().st_mtime,reverse=True) if run_dir.exists() else []
if files:
    st.dataframe([{"Artifact":p.name,"Bytes":p.stat().st_size,"Modified":p.stat().st_mtime} for p in files],hide_index=True)
    selected=st.selectbox("Inspect artifact",files,format_func=lambda p:p.name)
    artifact=json.loads(selected.read_text(encoding="utf-8"))
    if artifact.get("model_id","").startswith("offline") or artifact.get("warning"):
        st.warning("Đây là offline/mock artifact; không phải kết quả thực nghiệm từ model.")
    artifact=visible_run_artifact(artifact,registry,owner=owner)
    if not owner:st.caption("Final records are omitted without Owner access.")
    st.json(artifact)
else:st.info("Chưa có saved BIRD-VN run artifact. Dashboard không tạo kết quả mẫu.")
st.subheader("Research audit exports")
for fname in ["summary.json","ground_truth_validation_audit.csv","human_review_queue.csv","semantic_slot_flags.csv","similarity_low.csv","high_similarity_semantic_risk.csv","jaccard_36_review.csv"]:
    path=ROOT/"docs/benchmark/review/full_semantic_validation_sbert"/fname
    if not path.exists():continue
    payload=path.read_bytes(); mime="application/json" if fname.endswith("json") else "text/csv"
    if fname.endswith(".csv") and not owner:
        reader=csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))); fieldnames=reader.fieldnames or []; records=list(reader)
        if records and "split" in records[0]:records=[r for r in records if r["split"]=="development"]
        buffer=io.StringIO();writer=csv.DictWriter(buffer,fieldnames=fieldnames);writer.writeheader();writer.writerows(records);payload=buffer.getvalue().encode("utf-8")
    st.download_button(f"Tải {fname}"+(" (Development)" if fname.endswith(".csv") and not owner else ""),payload,fname,mime,key=f"export_{fname}")
