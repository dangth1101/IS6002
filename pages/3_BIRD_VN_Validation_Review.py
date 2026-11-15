"""Ground-truth evidence and non-mutating human review workspace."""
import csv, io, json, time
import streamlit as st
from bird_demo.benchmark.dashboard import read_registry, load_table, load_json, ROOT, owner_access_granted
st.set_page_config(page_title="BIRD-VN Validation & Review",page_icon=":material/analytics:",layout="wide")
st.title("Validation & Human Review")
registry=read_registry(); evidence=load_table("ground_truth_validation_audit.csv");groups={g["group_id"]:g for g in registry["groups"]}
with st.sidebar:
    st.subheader("Owner Review access")
    owner_token=st.text_input("Owner access token",type="password",key="birdvn_owner_token")
    final_owner=owner_access_granted(owner_token)
    st.caption("Token được so khớp với BIRD_VN_OWNER_TOKEN cấu hình phía server.")

t1,t2,t3=st.tabs(["Ground-truth evidence","Human Review queue","Official Evaluation gates"])
with t1:
    st.caption("Bằng chứng hiển thị đúng theo artifacts hiện có; không có thao tác sửa trạng thái/approval.")
    split_options=["development","final"] if final_owner else ["development"]
    if not final_owner: st.info("Final chỉ mở trong Owner Review khi server cấu hình BIRD_VN_OWNER_TOKEN và token hợp lệ.")
    split=st.radio("Split",split_options,horizontal=True,key="birdvn_validation_split")
    subset=[r for r in evidence if r["split"]==split]
    st.dataframe(subset,hide_index=True,use_container_width=True)
    selected=st.selectbox("Semantic Group",[r["group_id"] for r in subset],key="birdvn_val_group")
    group=groups[selected];st.warning(f"Intent {group['intent_card_status']} · Ground-truth {group['ground_truth_review']} · machine {group['validation_status']}")
    if split=="development" or final_owner:
        st.markdown("#### Intent Card");st.json(group["card_fields"])
        st.markdown("#### Canonical SQL candidate");st.code(group["canonical_sql_draft"],language="sql")
    else:st.info("Final SQL, Intent and question details are not displayed without Owner access.")
    validation=load_json("benchmark_data/authoring/ground_truth_validation.json") or {}
    expected=load_json("benchmark_data/authoring/expected_outputs_dev.json") or {}
    result=next((r for r in validation.get("results",[]) if r.get("group_id")==selected),None)
    exp=next((r for r in expected.get("expected_outputs",[]) if r.get("group_id")==selected),None)
    if result:st.markdown("#### Execution evidence");st.json(result)
    else:st.info("Execution evidence absent.")
    if exp:st.markdown("#### Independent expected output");st.json(exp)
    else:st.warning("Chưa có expected output/oracle; không tự suy ra từ canonical SQL.")
with t2:
    st.subheader("Owner review queue")
    queue=load_table("human_review_queue.csv"); gaps=load_table("intent_sql_evidence_gaps.csv")
    st.dataframe(queue,hide_index=True,use_container_width=True)
    st.caption("Mọi quyết định đang chờ. Ghi chú tại đây chỉ xuất thành review proposal; registry không đổi.")
    dev_groups=[g for g in registry["groups"] if g["split"]=="development"]
    group=st.selectbox("Nhóm cần review",dev_groups,format_func=lambda g:g["group_id"],key="birdvn_review_group")
    with st.form("birdvn_review_note"):
        decision=st.selectbox("Đề xuất quyết định",["ACCEPT","REVISE","REJECT"])
        question_id=st.text_input("Question ID (optional)")
        comment=st.text_area("Review comment")
        suggested=st.text_area("Suggested wording (optional)")
        confirm=st.checkbox("Xác nhận đây là ghi chú do tôi nhập; không phải approval chính thức.")
        submit=st.form_submit_button("Export review note",disabled=not confirm)
    if submit:
        payload={"created_at_epoch":time.time(),"registry_sha256":__import__('hashlib').sha256((ROOT/'benchmark_data/authoring/dataset.json').read_bytes()).hexdigest(),"group_id":group["group_id"],"question_id":question_id or None,"proposed_decision":decision,"comment":comment,"suggested_wording":suggested,"approval_status":"NEEDS_HUMAN_REVIEW","is_official_approval":False}
        st.download_button("Download JSON review note",json.dumps(payload,ensure_ascii=False,indent=2),file_name=f"review-{group['group_id']}.json",mime="application/json")
with t3:
    st.error("Official Evaluation chưa sẵn sàng")
    try:
        from bird_demo.benchmark.registry import load_registry
        load_registry(ROOT/"benchmark_data/authoring/dataset.json",allow_draft=False)
        registry_ready=True
    except (OSError,ValueError,KeyError): registry_ready=False
    config_ready=(ROOT/"benchmark_data/official/frozen_config.json").is_file()
    gates=[("Dataset & SQL approved / registry frozen",registry_ready,"Release registry validation passed" if registry_ready else "Registry remains draft/unfrozen; approval or expected-output gates remain"),("Frozen prompt/model/config",config_ready,"Frozen configuration found" if config_ready else "No frozen evaluation configuration artifact"),("D8 fixed 30-second SQL timeout",False,"Read-only 30-second SQL runner is unit tested; full official integration remains unverified"),("D9 exactly three complete replicates",False,"Three-replicate collector is unit tested; release/config gates block execution"),("D13 transient-only retry cap and attempt audit",False,"Retries classified transient infrastructure failures only, at most three attempts with bounded backoff; end-to-end integration unverified"),("Owner run confirmation",False,"No official run authorization; this UI does not launch official evaluation")]
    for label,ready,reason in gates: (st.success if ready else st.warning)(f"{'READY' if ready else 'BLOCKED'} · {label} — {reason}")
    st.caption("No button can start official evaluation in this draft application. Do not treat demo runs as official replicates.")
