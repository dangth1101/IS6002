"""BIRD-VN research dashboard, Development-first and read-only for benchmark sources."""
from __future__ import annotations
import json, os, time
from pathlib import Path
import streamlit as st
from openai import OpenAIError
from bird_demo.benchmark.dashboard import (ROOT, REGISTRY_PATH, AUDIT_DIR, read_registry, manifest_status,
    registry_file_hash, owner_access_granted, visible_groups, load_audit, load_similarity, load_slot_flags,
    schema_text, prompt_for, read_only_query, run_demo_question, diagnostic_gold, score_demo_results)
from bird_demo.llm import MAX_TOKENS, complete, default_model
from bird_demo.prompt import extract_sql
from bird_demo.runner import Rows, SqlError, Timeout

st.set_page_config(page_title="BIRD-VN-Robust-50", page_icon=":material/database:", layout="wide")
st.title("BIRD-VN-Robust-50")
st.session_state.setdefault("birdvn_demo_runs", [])
st.caption("Không gian nghiên cứu · dữ liệu nguồn ở chế độ chỉ đọc · quyết định Human Review không được ghi vào registry")
try:
    registry=read_registry(); manifest_ok,revision=manifest_status(); current_hash=registry_file_hash()
except Exception as exc:
    st.error(f"Không tải được benchmark registry: {exc}"); st.stop()
summary,audit_status=load_audit()
if not manifest_ok:
    if revision == "Registry hash mismatch":
        st.error(f"Registry hash không khớp manifest · {revision}")
    else:
        st.warning(f"Một audit/report artifact lệch manifest · {revision}. Playground vẫn tự kiểm tra riêng hash registry, SQL và SQLite trước khi chấm.")
else: st.caption(f"Revision `{revision}` · Registry SHA-256 `{current_hash}` · SBERT `{audit_status}")
if audit_status=="STALE": st.error("SBERT artifact không khớp registry/question lineage hiện hành; không hiển thị điểm.")
# Final is excluded from ordinary explorer/playground data selection.
all_groups=registry["groups"]
dev_groups=[g for g in all_groups if g["split"]=="development"]
questions_by_group={gid:sorted([q for q in registry["questions"] if q["group_id"]==gid],key=lambda q:q["q_index"]) for gid in {g["group_id"] for g in dev_groups}}

with st.sidebar:
    st.page_link("app.py", label="BIRD Original", icon=":material/database:")
    st.page_link("pages/1_BIRD_VN_Robust_50.py", label="BIRD-VN-Robust-50", icon=":material/language:")
    st.header("Benchmark status")
    st.metric("Semantic groups",len(all_groups)); st.metric("Questions",len(registry["questions"]))
    st.caption(f"Development {len(dev_groups)} nhóm · Final {sum(g['split']=='final' for g in all_groups)} nhóm")
    st.warning("Nội dung Final bị khóa khỏi luồng demo thông thường.")

summary_tab, explorer_tab, playground_tab=st.tabs(["Tổng quan","Dataset Explorer","LLM Playground"])
with summary_tab:
    st.subheader("Tổng quan benchmark")
    split_counts={s:sum(g["split"]==s for g in all_groups) for s in ("development","final")}
    domain_counts={"ERP":sum(g["db_id"]=="erp_sales" for g in all_groups),"WMS":sum(g["db_id"]=="wms_inventory" for g in all_groups)}
    c=st.columns(4)
    for col,label,value in zip(c,["C\u01a1 s\u1edf d\u1eef li\u1ec7u","Nh\u00f3m ng\u1eef ngh\u0129a","C\u00e2u h\u1ecfi","Bi\u1ebfn th\u1ec3"],[len(domain_counts),len(all_groups),len(registry["questions"]),sum(q["q_index"]>0 for q in registry["questions"]) ]):col.metric(label,value)
    left,right=st.columns(2)
    with left:
        st.markdown("**Phân bố split**"); st.bar_chart({"Groups":split_counts},horizontal=True,height=150)
        st.markdown("**Domain**"); st.bar_chart({"Groups":domain_counts},horizontal=True,height=150)
    with right:
        st.markdown("**Human review & ground truth**")
        pending=sum(g.get("intent_card_status")=="NEEDS_HUMAN_REVIEW" or g.get("ground_truth_review")=="NEEDS_HUMAN_REVIEW" for g in all_groups)
        st.metric("Nhóm cần Human Review",pending)
        status_counts={}
        for g in all_groups: status_counts[g.get("validation_status","UNKNOWN")]=status_counts.get(g.get("validation_status","UNKNOWN"),0)+1
        st.dataframe([{"Trạng thái":k,"Số nhóm":v} for k,v in status_counts.items()],hide_index=True,use_container_width=True)
        st.info("Kiểm tra tự động không đồng nghĩa Owner approval. Cả 40 nhóm Final đang BLOCKED vì thiếu expected outputs/oracle độc lập.")
    st.markdown("**Phân bố taxonomy paraphrase**")
    taxonomy={}
    for q in registry["questions"]:
        if q["q_index"]==0: continue
        key=(q["split"],q["variant_type"]); taxonomy[key]=taxonomy.get(key,0)+1
    st.dataframe([{"Split":split,"Variant type":kind,"Số câu":count} for (split,kind),count in sorted(taxonomy.items())],hide_index=True,use_container_width=True)
    st.markdown("**SBERT semantic similarity**")
    if audit_status!="CURRENT": st.warning("Không sử dụng điểm từ artifact cũ.")
    else:
        dist=summary["distribution"]["q00_to_variant"]["overall"]
        cols=st.columns(4)
        cols[0].metric("Cặp Q00–Qi",dist["count"])
        cols[1].metric("Trung bình cosine",f"{dist['mean']:.3f}")
        cols[2].metric("Trung vị",f"{dist['median']:.3f}")
        cols[3].metric("Khoảng giá trị",f"{dist['min']:.3f} – {dist['max']:.3f}")
        st.caption(f"Model {summary['model_id']} · snapshot {summary['model_revision']} · cosine không phải semantic accuracy.")
    st.markdown("**Official Evaluation readiness**")
    st.error("Chưa sẵn sàng · 10 nhóm Development vẫn chờ Owner review; 40 nhóm Final chưa có expected output/oracle độc lập; registry chưa freeze. Official Evaluation đang khóa.")

with explorer_tab:
    st.subheader("Dataset & Question Explorer · Development")
    col1,col2,col3=st.columns(3)
    domain=col1.selectbox("Domain",["Tất cả","ERP","WMS"],key="birdvn_ex_domain")
    competency=col2.selectbox("Competency",["Tất cả"]+sorted({g["competency"] for g in dev_groups}),key="birdvn_ex_comp")
    complexity=col3.selectbox("Complexity",["Tất cả"]+sorted({g["complexity"] for g in dev_groups}),key="birdvn_ex_complex")
    question_type=st.selectbox("Question type",["Tất cả","lexical","syntactic","reordering","mixed"],key="birdvn_ex_qtype")
    filtered=[g for g in dev_groups if (domain=="Tất cả" or (g["db_id"].startswith(domain.lower()))) and (competency=="Tất cả" or g["competency"]==competency) and (complexity=="Tất cả" or g["complexity"]==complexity)]
    if not filtered:st.info("Không có nhóm phù hợp.")
    else:
        group=st.selectbox("Semantic Group",filtered,format_func=lambda g:f"{g['group_id']} · {g['db_id']} · {g['competency']} · {g['complexity']}",key="birdvn_ex_group")
        qs=questions_by_group[group["group_id"]]; card=group["card_fields"]
        st.warning(f"{group['intent_card_status']} · Ground-truth {group['ground_truth_review']} · chưa phải approval")
        with st.expander("Intent Card · Business Rules · Semantic Slots",expanded=True):
            st.markdown(f"**Mô tả:** {card['brief']}")
            st.json({k:card.get(k) for k in ("entity_grain","projection","filters_group_time","aggregation_grouping","null_tie","business_rules") if k in card})
            st.markdown(f"**Competency:** {group['competency']} · **Complexity:** {group['complexity']}")
        st.markdown("#### Q00 · câu gốc")
        st.info(qs[0]["question"])
        visible_variants=[q for q in qs[1:] if question_type=="Tất cả" or q["variant_type"]==question_type]
        st.dataframe([{"ID":q["question_id"],"Type":q["variant_type"],"Câu hỏi":q["question"],"Review":q["variant_review"]} for q in visible_variants],hide_index=True,use_container_width=True)
        sims={}
        if audit_status=="CURRENT":
            for row in load_similarity():
                if row.get("group_id")==group["group_id"]: sims[row.get("question_id")]=row.get("cosine_similarity")
        st.caption("SBERT Q00–Qi · cosine similarity, không phải phần trăm tương đương ngữ nghĩa.")
        st.dataframe([{"Question":q["question_id"],"Similarity":sims.get(q["question_id"]),"Variant type":q["variant_type"]} for q in qs[1:]],hide_index=True)
        with st.expander("Semantic Glossary"):
            st.json(registry.get("semantic_glossary",{}))
        st.caption(f"SQL ứng viên · {group['validation_status']} · Hash `{group['canonical_sql_sha256']}`")
        st.code(group["canonical_sql_draft"],language="sql")
        st.warning("Ground-truth đang chờ duyệt; không hiển thị predicted correctness hoặc accuracy chính thức.")

with playground_tab:
    st.subheader("Interactive LLM Playground · chỉ Development")
    st.caption("Demo chỉ chạy khi người dùng chủ động bấm; không tính là official replicate. Provider có thể tính phí.")
    group=st.selectbox("Semantic Group",dev_groups,format_func=lambda g:f"{g['group_id']} · {g['db_id']}",key="birdvn_play_group")
    qs=questions_by_group[group["group_id"]]
    run_mode=st.radio("Chế độ",["Một câu","Cặp Q00 + Qi","Cả nhóm Q00–Q10"],horizontal=True,key="birdvn_play_mode")
    question_options=qs[1:] if run_mode=="Cặp Q00 + Qi" else qs
    question_state_key="birdvn_play_question"
    if st.session_state.get(question_state_key) not in question_options:
        st.session_state[question_state_key]=question_options[0]
    q=st.selectbox("Question",question_options,format_func=lambda q:f"Q{q['q_index']:02d} · {q['variant_type']} · {q['question'][:90]}",key=question_state_key)
    gold_context=None
    gold_context_error=None
    try:
        gold_context=diagnostic_gold(group)
        st.info(f"Sẽ chạy SQL canonical ở chế độ chỉ đọc trên snapshot đã kiểm tra hash. Trạng thái Owner: {gold_context['owner_status']}. Kết quả và metric là chẩn đoán trên SQL candidate, chưa phải official evaluation.")
    except Exception as exc:
        gold_context_error=str(exc)
        st.warning(f"Chưa thể chấm diagnostic cho nhóm này: {gold_context_error}")
    try:model_default=default_model()
    except SystemExit:model_default=""
    model=st.text_input("Model ID (LLM_MODEL hiện tại)",value=model_default,key="birdvn_play_model")
    cc1,cc2,cc3=st.columns(3)
    temperature=cc1.slider("Temperature",0.0,2.0,0.0,0.1,key="birdvn_play_temp")
    max_tokens=cc2.number_input("Max tokens",min_value=1,max_value=MAX_TOKENS,value=MAX_TOKENS,key="birdvn_play_tokens")
    db_id=group["db_id"]
    st.text_area("Schema context",schema_text(db_id),height=180,disabled=True,key="birdvn_play_schema")
    if run_mode=="Cả nhóm Q00–Q10":confirm=st.checkbox("Xác nhận tối đa 11 lần gọi API cho nhóm này.",key="birdvn_play_confirm")
    else:confirm=True
    clicked=st.button("Run LLM",type="primary",disabled=not model.strip() or not confirm,key="birdvn_play_run")
    if clicked:
        selected=([q] if run_mode=="Một câu" else [qs[0],q] if run_mode=="Cặp Q00 + Qi" else qs)
        results=[];progress=st.progress(0,text="Chuẩn bị demo run…")
        for i,item in enumerate(selected):
            with st.spinner(f"Đang gọi {model} · {item['question_id']}…"):
                outcome=run_demo_question(item["question"],db_id,group["card_fields"]["business_rules"],registry.get("semantic_glossary",{}),model.strip(),temperature=float(temperature),max_tokens=int(max_tokens),complete_fn=complete)
            elapsed=outcome["elapsed_s"]
            if outcome["error"]:
                results.append({"question":item,"error":outcome["error"],"elapsed":elapsed})
                st.error(f"Lỗi gọi LLM cho {item['question_id']}: {outcome['error']}")
                if len(selected)==11:break
            else:
                results.append({"question":item,"sql":outcome["sql"],"reply":outcome["reply"],"elapsed":elapsed,"run_result":outcome["execution"],"prompt":outcome["prompt"]})
            progress.progress((i+1)/len(selected),text=f"Đã xử lý {i+1}/{len(selected)} câu")
        canonical_execution=read_only_query(db_id,gold_context["canonical_sql"]) if gold_context else None
        st.session_state["birdvn_demo_runs"].append({"run_at":time.time(),"group_id":group["group_id"],"model":model.strip(),"mode":run_mode,"results":results,"canonical_sql":gold_context["canonical_sql"] if gold_context else None})
        if gold_context:
            st.markdown("#### SQL gốc · canonical SQL candidate")
            st.code(gold_context["canonical_sql"],language="sql")
            if isinstance(canonical_execution,dict):
                canonical_result=canonical_execution["result"]
                st.caption(f"SQL gốc chạy thành công · {len(canonical_result.rows)} dòng · {canonical_execution['elapsed_s']:.2f}s · snapshot `{gold_context['database_sha256'][:12]}…`")
                if canonical_execution["truncated"]:
                    st.warning("Kết quả SQL gốc vượt giới hạn hiển thị; không tính EX/RSS để tránh chấm dữ liệu bị cắt.")
                elif canonical_result.rows:
                    st.dataframe([dict(zip(canonical_result.columns,row)) for row in canonical_result.rows],hide_index=True,use_container_width=True)
                else:
                    st.info("SQL gốc chạy thành công và trả về 0 dòng.")
            elif isinstance(canonical_execution,Timeout):
                st.error(f"SQL gốc timeout sau {canonical_execution.timeout_s}s; không tính metric cho lượt này.")
            elif isinstance(canonical_execution,SqlError):
                st.error(f"SQL gốc lỗi; không tính metric cho lượt này: {canonical_execution.message}")
        for item in results:
            st.markdown(f"#### {item['question']['question_id']}")
            st.caption(item["question"]["question"])
            st.metric("LLM response time",f"{item['elapsed']:.2f}s")
            if item.get("error"):continue
            if item["sql"]:st.code(item["sql"],language="sql")
            else:st.warning("Không trích xuất được SELECT/WITH SQL.");st.code(item["reply"].text)
            outcome=item["run_result"]
            if isinstance(outcome,dict):
                result=outcome["result"];st.caption(f"Thực thi thành công · hiển thị {len(result.rows)} dòng · {outcome['elapsed_s']:.2f}s"+(" · đã giới hạn 500 dòng" if outcome["truncated"] else ""))
                if result.rows:st.dataframe([dict(zip(result.columns,row)) for row in result.rows],hide_index=True,use_container_width=True)
                else:st.info("Truy vấn thành công, không có dòng kết quả.")
            elif isinstance(outcome,Timeout):st.error(f"SQL timeout sau {outcome.timeout_s}s")
            elif isinstance(outcome,SqlError):st.error(f"SQL bị từ chối hoặc gặp lỗi: {outcome.message}")
            with st.expander("Prompt đã gửi"):st.code(item["prompt"])
        if gold_context and isinstance(canonical_execution,dict) and not canonical_execution["truncated"]:
            canonical_result=canonical_execution["result"]
            score=score_demo_results(qs,results,[list(row) for row in canonical_result.rows])
            metrics=score["metrics"]
            st.markdown("#### Đối chiếu và metric trong lượt demo này")
            metric_columns=st.columns(5)
            for column,label,key in zip(metric_columns,
                ["EX gốc · Q00","EX variants","EX các câu đã chạy","RSS · cặp Q00–Qi","Robust EX · đủ 11 câu"],
                ["ex_original","ex_variants","ex_overall","rss","robust_ex_all"]):
                rate=metrics[key]
                value="N/A" if rate["percent"] is None else f"{rate['percent']:.1f}%"
                column.metric(label,value,help=f"{rate['numerator']}/{rate['denominator']} theo outcome đã xác định trong lượt này")
            st.caption(f"Đã chạy {score['run_question_count']}/11 câu · {metrics['missing_questions']} câu có outcome hạ tầng/không chạy trong metric. Robust EX cần đủ 11 outcomes xác định trong cùng lượt. SQL error, timeout và no SQL tính là EX=0; lỗi provider/API và kết quả bị cắt dòng là unknown. Không cộng dồn thành replicate.")
            question_rows=[]
            for item in score["questions"]:
                verdict="—" if item["correct"] is None else "Đúng" if item["correct"] else "Sai"
                question_rows.append({"Question":item["question_id"],"Variant":item["variant_type"],
                    "Trạng thái":item["status"],"Số dòng":item["row_count"],"EX vs canonical":verdict})
            st.dataframe(question_rows,hide_index=True,use_container_width=True)
            for item in score["questions"]:
                if item["correct"] is False and item["status"]=="success":
                    with st.expander(f"So sánh dòng · {item['question_id']} · thiếu {item['canonical_only_count']}, dư {item['prediction_only_count']}"):
                        st.caption("SQL canonical chỉ có (tối đa 50 dòng)")
                        st.dataframe(item["canonical_only_rows"],hide_index=True,use_container_width=True)
                        st.caption("SQL dự đoán chỉ có (tối đa 50 dòng)")
                        st.dataframe(item["prediction_only_rows"],hide_index=True,use_container_width=True)
            with st.expander("Cơ sở đối chiếu và giới hạn"):
                st.write(f"Canonical SQL SHA-256: `{gold_context['canonical_sql_sha256']}`")
                st.write(f"SQLite snapshot SHA-256: `{gold_context['database_sha256']}`")
                st.write(f"Số dòng SQL candidate gốc: {score['canonical_row_count']} · so sánh theo BIRD set comparator (bỏ thứ tự dòng và duplicate rows).")
                st.warning("Metric chấm so với canonical SQL candidate chưa được Owner duyệt. Lượt Playground không thay thế 3 replicates, run artifacts đóng băng hoặc official evaluation.")
        elif gold_context and canonical_execution is not None:
            st.warning("Có kết quả LLM nhưng không có kết quả đầy đủ từ SQL canonical; không tính EX/RSS cho lượt này.")
        elif not gold_context:
            st.warning("Không thể nạp canonical SQL candidate hợp lệ; các kết quả LLM không được gán EX/RSS.")
