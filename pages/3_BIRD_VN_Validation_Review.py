"""Ground-truth evidence and non-mutating human review workspace."""
import csv, io, json, time
import streamlit as st
from bird_demo.benchmark.dashboard import read_registry, load_table, load_json, ROOT, owner_access_granted
from bird_demo.benchmark.release import release_readiness
from bird_demo.benchmark.navigation import hide_secondary_bird_vn_pages
st.set_page_config(page_title="BIRD-VN Validation & Review",page_icon=":material/analytics:",layout="wide")
hide_secondary_bird_vn_pages()
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
    validation_path = "benchmark_data/authoring/ground_truth_validation.json" if split == "development" else "benchmark_data/authoring/ground_truth_validation_final.json"
    validation=load_json(validation_path) or {}
    expected_path = "benchmark_data/authoring/expected_outputs_dev.json" if split == "development" else "benchmark_data/authoring/expected_outputs_final.json"
    expected=load_json(expected_path) or {}
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
    st.caption("10 nhóm Development và 110 câu hỏi đã được duyệt theo quyết định có provenance. 40 nhóm Final vẫn NEEDS_HUMAN_REVIEW; expected outputs độc lập không đồng nghĩa với approval. Trang này chỉ đọc trạng thái đã ghi.")
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
        from bird_demo.benchmark.registry import load_registry, registry_hash, sha256_file
        frozen_registry=load_registry(ROOT/"benchmark_data/authoring/dataset.json",allow_draft=False)
        registry_ready=True
    except (OSError,ValueError,KeyError): registry_ready=False
    config_path=ROOT/"benchmark_data/official/frozen_config.json"
    integration_path=ROOT/"benchmark_data/official/implementation_validation.json"
    config_ready=config_path.is_file()
    frozen_config=load_json("benchmark_data/official/frozen_config.json") or {}
    implementation=load_json("benchmark_data/official/implementation_validation.json") or {}
    freeze_manifest=load_json("benchmark_data/official/frozen_registry_manifest.json") or {}
    try:
        config_hash_matches=implementation.get("config_sha256")==sha256_file(config_path)
        registry_hash_matches=implementation.get("registry_canonical_sha256")==registry_hash(frozen_registry)
        config_registry_matches=frozen_config.get("registry_canonical_sha256")==registry_hash(frozen_registry)
        freeze_integrity_matches=(freeze_manifest.get("registry_canonical_sha256")==registry_hash(frozen_registry)
            and freeze_manifest.get("frozen_config_sha256")==sha256_file(config_path)
            and bool(freeze_manifest.get("integrity_files_sha256"))
            and all((ROOT/rel).is_file() and sha256_file(ROOT/rel)==digest
                    for rel,digest in freeze_manifest.get("integrity_files_sha256",{}).items()))
    except (NameError,OSError,ValueError):
        config_hash_matches=False; registry_hash_matches=False; config_registry_matches=False; freeze_integrity_matches=False
    smoke_valid=(implementation.get("validation_type")=="OFFLINE_MOCK_IMPLEMENTATION_SMOKE"
        and implementation.get("empirical_result") is False
        and implementation.get("api_called") is False
        and implementation.get("replicate_count")==3
        and implementation.get("questions_per_replicate")==440
        and implementation.get("prediction_records_total")==1320
        and len(implementation.get("runs",[]))==3
        and all(run.get("prediction_records")==440 and run.get("execution_records")==440
                and run.get("all_sql_executed") and run.get("all_results_match_canonical")
                for run in implementation.get("runs",[])))
    integration_ready=bool(registry_ready and config_ready and config_hash_matches and registry_hash_matches
        and config_registry_matches and freeze_integrity_matches and smoke_valid)
    protocol=implementation.get("protocol_checks",{})
    d8_ready=bool(integration_ready and frozen_config.get("sql_execution_timeout_seconds")==30
        and protocol.get("D8_sql_timeout_seconds")==30 and protocol.get("D8_timeout_outcome_not_retried"))
    d9_ready=bool(integration_ready and frozen_config.get("replicates")==3
        and protocol.get("D9_three_complete_replicates"))
    d13_ready=bool(integration_ready and frozen_config.get("maximum_infrastructure_retries")==2
        and frozen_config.get("retry_only_transient_infrastructure_errors") is True
        and protocol.get("D13_transient_only_retry_cap_tested_by_unit_suite"))
    verified=release_readiness(ROOT)
    registry_ready=verified["registry_ready"]
    config_ready=verified["config_ready"]
    integration_ready=verified["freeze_integrity_ready"]
    d8_ready=verified["d8_ready"]
    d9_ready=verified["d9_ready"]
    d13_ready=verified["d13_ready"]
    gates=[("Dataset & SQL approved / registry frozen",registry_ready,"Release registry validation passed" if registry_ready else "Registry approval, integrity or expected-output gate failed"),("Frozen prompt/model/config",config_ready and config_hash_matches,"Frozen configuration hash is bound to the implementation check" if config_ready and config_hash_matches else "Missing frozen configuration or its hash does not match the recorded check"),("D8 fixed 30-second SQL timeout",d8_ready,"Mock Final pipeline verified; SQL execution timeout is 30 seconds and timeout is not retried" if d8_ready else "D8 integration evidence missing, stale or inconsistent"),("D9 exactly three complete replicates",d9_ready,"Offline mock completed 3 replicates × 440 Final questions; not an empirical result" if d9_ready else "Three-replicate integration evidence missing, stale or inconsistent"),("D13 transient-only retry cap and attempt audit",d13_ready,"Retry policy is capped at two transient infrastructure retries; verified by protocol tests" if d13_ready else "D13 implementation evidence missing or inconsistent"),("Owner run confirmation / API authorization",False,"Configuration freeze and mock validation do not authorize paid provider calls")]
    for label,ready,reason in gates: (st.success if ready else st.warning)(f"{'READY' if ready else 'BLOCKED'} · {label} — {reason}")
    st.caption("Offline mock evidence verifies implementation wiring only. Official Evaluation remains locked until the Benchmark Owner separately authorizes the real model run and associated cost.")
