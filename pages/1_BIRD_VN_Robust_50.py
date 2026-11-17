"""BIRD-VN research dashboard, Development-first and read-only for benchmark sources."""
from __future__ import annotations
import json, os, time
from pathlib import Path
import streamlit as st
from openai import OpenAIError
from bird_demo.benchmark.dashboard import (ROOT, REGISTRY_PATH, AUDIT_DIR, read_registry, manifest_status,
    registry_file_hash, owner_access_granted, visible_groups, load_audit, load_similarity, load_slot_flags,
    schema_text, prompt_for, read_only_query, run_demo_question, diagnostic_gold, score_demo_results)
from bird_demo.benchmark.release import release_readiness
from bird_demo.benchmark.navigation import hide_secondary_bird_vn_pages
from bird_demo.llm import MAX_TOKENS, complete, model_choices
from bird_demo.prompt import extract_sql
from bird_demo.runner import Rows, SqlError, Timeout

st.set_page_config(page_title="BIRD-VN-Robust-50", page_icon=":material/database:", layout="wide")
hide_secondary_bird_vn_pages()

@st.dialog("Chi tiết kết quả theo câu hỏi", width="large")
def show_run_details(run_record):
    canonical_execution = run_record.get("canonical_execution")
    if isinstance(canonical_execution, dict):
        with st.expander("SQL gốc và kết quả chuẩn", expanded=False):
            st.code(run_record["canonical_sql"], language="sql")
            canonical_result = canonical_execution["result"]
            st.caption(f"{len(canonical_result.rows)} dòng · {', '.join(canonical_result.columns)}")
            if canonical_result.rows:
                st.dataframe([dict(zip(canonical_result.columns, row)) for row in canonical_result.rows], hide_index=True, use_container_width=True)

    for item in run_record["results"]:
        question = item["question"]
        with st.expander(f"{question['question_id']} · {question['variant_type']}", expanded=False):
            st.write(question["question"])
            st.caption(f"Thời gian LLM: {item['elapsed']:.2f}s")
            if item.get("error"):
                st.error(item["error"])
                continue
            if item.get("sql"):
                st.code(item["sql"], language="sql")
            else:
                st.warning("Không trích xuất được SQL từ phản hồi.")
                st.code(item["reply"].text)
            reply = item.get("reply")
            reasoning = getattr(reply, "reasoning", "")
            full_reply = reply.text.strip() if reply is not None and item.get("sql") else ""
            if reasoning or full_reply:
                with st.expander("Suy luận của mô hình"):
                    if reasoning:
                        st.caption("Reasoning tokens do mô hình trả về")
                        st.markdown(reasoning)
                    if full_reply:
                        st.caption("Toàn bộ phản hồi (SQL được trích xuất từ đây)")
                        st.markdown(full_reply)
            outcome = item.get("run_result")
            if isinstance(outcome, dict):
                result = outcome["result"]
                st.caption(f"{len(result.rows)} dòng · {', '.join(result.columns)} · {outcome['elapsed_s']:.2f}s")
                if outcome.get("truncated"):
                    st.warning("Kết quả bị giới hạn hiển thị; không dùng để chấm EX/RSS.")
                elif result.rows:
                    st.dataframe([dict(zip(result.columns, row)) for row in result.rows], hide_index=True, use_container_width=True)
                else:
                    st.info("Truy vấn thành công, không có dòng kết quả.")
            elif isinstance(outcome, Timeout):
                st.error(f"SQL timeout sau {outcome.timeout_s}s")
            elif isinstance(outcome, SqlError):
                st.error(f"SQL bị từ chối hoặc gặp lỗi: {outcome.message}")
            with st.expander("Prompt đã gửi"):
                st.code(item["prompt"])

st.title("BIRD-VN-Robust-50")
st.session_state.setdefault("birdvn_demo_runs", [])
st.caption("Không gian nghiên cứu · dữ liệu nguồn ở chế độ chỉ đọc · quyết định Human Review không được ghi vào registry")
try:
    registry=read_registry(); manifest_ok,revision=manifest_status(); current_hash=registry_file_hash()
except Exception as exc:
    st.error(f"Không tải được benchmark registry: {exc}"); st.stop()
summary,audit_status=load_audit()
if not manifest_ok:
    if revision == "Hash registry không khớp manifest":
        st.error(f"Registry hash không khớp manifest · {revision}")
    else:
        st.warning(f"Một audit/report artifact lệch manifest · {revision}. Playground vẫn tự kiểm tra riêng hash registry, SQL và SQLite trước khi chấm.")
else: st.caption(f"Revision `{revision}` · Registry SHA-256 `{current_hash}` · SBERT `{audit_status}")
if audit_status=="STALE": st.error("SBERT artifact không khớp registry/question lineage hiện hành; không hiển thị điểm.")
# Final is excluded from ordinary explorer/playground data selection.
all_groups=registry["groups"]
dev_groups=[g for g in all_groups if g["split"]=="development"]
final_groups=[g for g in all_groups if g["split"]=="final"]
questions_by_group={gid:sorted([q for q in registry["questions"] if q["group_id"]==gid],key=lambda q:q["q_index"]) for gid in {g["group_id"] for g in all_groups}}

with st.sidebar:
    st.page_link("app.py", label="BIRD Original", icon=":material/database:")
    st.page_link("pages/1_BIRD_VN_Robust_50.py", label="BIRD-VN-Robust-50", icon=":material/language:")
    st.header("Benchmark status")
    st.metric("Semantic groups",len(all_groups)); st.metric("Questions",len(registry["questions"]))
    # Tạm ẩn phần mô tả số nhóm và cảnh báo Final khỏi giao diện thanh bên.
    # st.caption(f"Development {len(dev_groups)} nhóm · Final {sum(g['split']=='final' for g in all_groups)} nhóm")
    # st.warning("Nội dung Final bị khóa khỏi luồng demo thông thường.")

summary_tab, explorer_tab, playground_tab=st.tabs(["Tổng quan","Khám phá dữ liệu","LLM Playground"])
split_labels={"development":"Tập phát triển","final":"Tập đánh giá cuối"}
variant_labels={"lexical":"Từ vựng","syntactic":"Cấu trúc câu","reordering":"Đảo thứ tự thông tin","mixed":"Kết hợp nhiều dạng"}
competency_labels={"Filter":"Lọc","Aggregate":"Tổng hợp","Group":"Phân nhóm","Ranking":"Xếp hạng","Join":"Kết nối bảng","Time":"Thời gian","NULL":"Giá trị NULL","Conditional":"Điều kiện"}
complexity_labels={"Simple":"Đơn giản","Moderate":"Trung bình","Challenging":"Nâng cao"}
status_labels={"VALIDATED_BY_AUTOMATION":"Đã kiểm tra tự động","NEEDS_HUMAN_REVIEW":"Chờ người kiểm duyệt","VALIDATED":"Đã kiểm chứng","APPROVED":"Đã duyệt","UNKNOWN":"Chưa xác định"}
review_labels={"ACCEPT":"Đã chấp nhận","REVISE":"Cần chỉnh sửa","REJECT":"Không chấp nhận","NEEDS_HUMAN_REVIEW":"Chờ người kiểm duyệt"}
with summary_tab:
    st.subheader("Tổng quan bộ đánh giá")
    split_counts={label:sum(g["split"]==value for g in all_groups) for label,value in (("Tập phát triển (Development)","development"),("Tập đánh giá cuối (Final)","final"))}
    domain_counts={"ERP":sum(g["db_id"]=="erp_sales" for g in all_groups),"WMS":sum(g["db_id"]=="wms_inventory" for g in all_groups)}
    c=st.columns(4)
    for col,label,value in zip(c,["Cơ sở dữ liệu","Nhóm ngữ nghĩa","Câu hỏi","Biến thể"],[len(domain_counts),len(all_groups),len(registry["questions"]),sum(q["q_index"]>0 for q in registry["questions"]) ]):col.metric(label,value)
    left,right=st.columns(2)
    with left:
        st.markdown("**Phân bố theo tập dữ liệu**"); st.bar_chart({"Số nhóm":split_counts},horizontal=True,height=150)
        st.markdown("**Miền nghiệp vụ**"); st.bar_chart({"Số nhóm":domain_counts},horizontal=True,height=150)
    with right:
        st.markdown("**Kiểm duyệt & SQL chuẩn**")
        pending=sum(g.get("intent_card_status")=="NEEDS_HUMAN_REVIEW" or g.get("ground_truth_review")=="NEEDS_HUMAN_REVIEW" or g.get("human_review_status")=="NEEDS_HUMAN_REVIEW" for g in all_groups)
        st.metric("Nhóm đang chờ kiểm duyệt",pending)
        status_counts={}
        for g in all_groups: status_counts[g.get("validation_status","UNKNOWN")]=status_counts.get(g.get("validation_status","UNKNOWN"),0)+1
        st.dataframe([{"Trạng thái":status_labels.get(k,k),"Số nhóm":v} for k,v in status_counts.items()],hide_index=True,use_container_width=True)
        release_status = release_readiness(ROOT)
        core_ready = all(release_status[key] for key in ("registry_ready", "config_ready", "freeze_integrity_ready", "d8_ready", "d9_ready", "d13_ready"))
        if core_ready:
            st.success(f"Danh mục dữ liệu đã được đóng băng · SHA-256 `{release_status['registry_sha256']}`")
            # Tạm ẩn ghi chú mô phỏng ngoại tuyến và trạng thái đánh giá chính thức.
            # st.info("Đã kiểm tra mô phỏng ngoại tuyến 3 lượt × 440 câu Final; đây không phải kết quả từ mô hình thật. Đánh giá chính thức (Official Evaluation) vẫn khóa vì chưa có xác nhận gọi API và chi phí.")
        else:
            st.warning("Các điều kiện phát hành chưa đạt; mở trang Kiểm duyệt để xem chi tiết.")
    st.markdown("**Phân bố dạng diễn đạt lại**")
    taxonomy={}
    for q in registry["questions"]:
        if q["q_index"]==0: continue
        key=(q["split"],q["variant_type"]); taxonomy[key]=taxonomy.get(key,0)+1
    st.dataframe([{"Tập dữ liệu":split_labels.get(split,split),"Dạng biến thể":variant_labels.get(kind,kind),"Số câu":count} for (split,kind),count in sorted(taxonomy.items())],hide_index=True,use_container_width=True)
    st.markdown("**Độ tương đồng ngữ nghĩa (SBERT)**")
    if audit_status!="CURRENT": st.warning("Không sử dụng điểm từ tệp kết quả cũ.")
    else:
        dist=summary["distribution"]["q00_to_variant"]["overall"]
        cols=st.columns(4)
        cols[0].metric("Số cặp Q00–Qi",dist["count"])
        cols[1].metric("Trung bình cosine",f"{dist['mean']:.3f}")
        cols[2].metric("Trung vị",f"{dist['median']:.3f}")
        cols[3].metric("Khoảng điểm",f"{dist['min']:.3f} – {dist['max']:.3f}")
        st.caption(f"Mô hình {summary['model_id']} · phiên bản dữ liệu {summary['model_revision']} · cosine chỉ đo độ gần, không phải độ chính xác ngữ nghĩa.")
    st.markdown("**Mức độ sẵn sàng chạy đánh giá chính thức**")
    release_status = release_readiness(ROOT)
    core_ready = all(release_status[key] for key in ("registry_ready", "config_ready", "freeze_integrity_ready", "d8_ready", "d9_ready", "d13_ready"))
    if core_ready:
        st.success("Danh mục dữ liệu, cấu hình và kiểm tra tích hợp ba lượt đã sẵn sàng về mặt kỹ thuật.")
        # Tạm ẩn cảnh báo đánh giá chính thức đang khóa.
        # st.warning("Đánh giá chính thức vẫn khóa; cần Chủ sở hữu bộ đánh giá xác nhận việc gọi mô hình và chi phí.")
    else:
        st.error(f"Chưa sẵn sàng về mặt kỹ thuật; xem trang Kiểm duyệt để biết điều kiện còn thiếu. Số nhóm đang chờ kiểm duyệt: {pending}.")

with explorer_tab:
    st.subheader("Khám phá bộ dữ liệu · 50 nhóm")
    col1,col2,col3=st.columns(3)
    split=st.selectbox("Tập dữ liệu",["Development","Final"],format_func=lambda value:"Tập phát triển (Development)" if value=="Development" else "Tập đánh giá cuối (Final)",key="birdvn_ex_split")
    explorer_groups=dev_groups if split=="Development" else final_groups
    domain=col1.selectbox("Miền nghiệp vụ",["Tất cả","ERP","WMS"],key="birdvn_ex_domain")
    competency=col2.selectbox("Năng lực truy vấn",["Tất cả"]+sorted({g["competency"] for g in explorer_groups}),format_func=lambda value:"Tất cả" if value=="Tất cả" else competency_labels.get(value,value),key="birdvn_ex_comp")
    complexity=col3.selectbox("Độ phức tạp",["Tất cả"]+sorted({g["complexity"] for g in explorer_groups}),format_func=lambda value:"Tất cả" if value=="Tất cả" else complexity_labels.get(value,value),key="birdvn_ex_complex")
    question_type=st.selectbox("Dạng biến thể",["Tất cả","lexical","syntactic","reordering","mixed"],format_func=lambda value:"Tất cả" if value=="Tất cả" else variant_labels.get(value,value),key="birdvn_ex_qtype")
    if split=="Final":
        st.info("Tập Final chỉ để xem tại đây. Không dùng các câu hỏi này để thử hoặc tinh chỉnh prompt/mô hình.")
    filtered=[g for g in explorer_groups if (domain=="Tất cả" or (g["db_id"].startswith(domain.lower()))) and (competency=="Tất cả" or g["competency"]==competency) and (complexity=="Tất cả" or g["complexity"]==complexity)]
    if not filtered:st.info("Không có nhóm nào phù hợp với điều kiện đã chọn.")
    else:
        group=st.selectbox("Nhóm ngữ nghĩa",filtered,format_func=lambda g:f"{g['group_id']} · {g['db_id']} · {competency_labels.get(g['competency'],g['competency'])} · {complexity_labels.get(g['complexity'],g['complexity'])}",key="birdvn_ex_group")
        qs=questions_by_group[group["group_id"]]; card=group["card_fields"]
        if group["split"]=="final":
            st.warning(f"Tập Final · Thẻ ý định: {status_labels.get(group['intent_card_status'],group['intent_card_status'])} · SQL chuẩn: {status_labels.get(group['ground_truth_review'],group['ground_truth_review'])} · chỉ xem")
        else:
            st.warning(f"Thẻ ý định: {status_labels.get(group['intent_card_status'],group['intent_card_status'])} · SQL chuẩn: {status_labels.get(group['ground_truth_review'],group['ground_truth_review'])} · chưa được duyệt toàn bộ")
        with st.expander("Thẻ ý định · Quy tắc nghiệp vụ · Các trường ngữ nghĩa",expanded=True):
            st.markdown(f"**Mô tả:** {card['brief']}")
            slot_labels={"entity_grain":"Đối tượng và mức chi tiết đầu ra","projection":"Các cột cần trả về","filters_group_time":"Điều kiện lọc, phân nhóm và thời gian","aggregation_grouping":"Phép tổng hợp và cách phân nhóm","null_tie":"NULL và quy tắc xử lý đồng hạng","business_rules":"Quy tắc nghiệp vụ"}
            st.json({slot_labels[k]:card.get(k) for k in slot_labels if k in card})
            st.markdown(f"**Năng lực truy vấn:** {competency_labels.get(group['competency'],group['competency'])} · **Độ phức tạp:** {complexity_labels.get(group['complexity'],group['complexity'])}")
        st.markdown("#### Q00 · câu hỏi gốc")
        st.info(qs[0]["question"])
        visible_variants=[q for q in qs[1:] if question_type=="Tất cả" or q["variant_type"]==question_type]
        st.dataframe([{"Mã câu hỏi":q["question_id"],"Dạng biến thể":variant_labels.get(q["variant_type"],q["variant_type"]),"Nội dung câu hỏi":q["question"],"Trạng thái duyệt":review_labels.get(q["variant_review"],q["variant_review"])} for q in visible_variants],hide_index=True,use_container_width=True)
        sims={}
        if audit_status=="CURRENT":
            for row in load_similarity():
                if row.get("group_id")==group["group_id"]: sims[row.get("question_id")]=row.get("cosine_similarity")
        st.caption("SBERT Q00–Qi · độ tương đồng cosin chỉ đo độ gần giữa cách diễn đạt, không khẳng định hai câu tương đương ngữ nghĩa.")
        st.dataframe([{"Mã câu hỏi":q["question_id"],"Điểm tương đồng cosin":sims.get(q["question_id"]),"Dạng biến thể":variant_labels.get(q["variant_type"],q["variant_type"])} for q in qs[1:]],hide_index=True)
        with st.expander("Bảng thuật ngữ nghiệp vụ"):
            st.json(registry.get("semantic_glossary",{}))
        if group["split"]=="development":
            st.caption(f"SQL ứng viên · Trạng thái: {status_labels.get(group['validation_status'],group['validation_status'])} · Mã kiểm tra: `{group['canonical_sql_sha256']}`")
            st.code(group["canonical_sql_draft"],language="sql")
            st.warning("SQL chuẩn còn chờ duyệt; chưa hiển thị kết quả đúng/sai hoặc độ chính xác chính thức.")
        else:
            st.caption("SQL chuẩn của tập Final được ẩn trong phần khám phá dữ liệu.")

with playground_tab:
    st.subheader("Interactive LLM Playground · Development")
    st.caption("Development có thể chạy demo thủ công. Final hiển thị để tra cứu nhưng bị khóa chạy LLM tại đây.")
    group=st.selectbox("Semantic Group",all_groups,format_func=lambda g:f"{g['group_id']} · {g['db_id']} · {g['split']}",key="birdvn_play_group")
    qs=questions_by_group[group["group_id"]]
    run_mode=st.radio("Chế độ",["Một câu","Cặp Q00 + Qi","Cả nhóm Q00–Q10"],horizontal=True,key="birdvn_play_mode")
    question_options=qs[1:] if run_mode=="Cặp Q00 + Qi" else qs
    question_state_key="birdvn_play_question"
    if st.session_state.get(question_state_key) not in question_options:
        st.session_state[question_state_key]=question_options[0]
    q=st.selectbox(
        "Question",
        question_options,
        format_func=lambda item:f"Q{item['q_index']:02d} · {item['variant_type']} · {item['question']}",
        key=question_state_key,
    )
    st.markdown("**Nội dung câu hỏi**")
    st.write(q["question"])
    if run_mode=="Cặp Q00 + Qi":
        st.caption(f"Đang chọn 1 trong {len(question_options)} biến thể; Q00 sẽ được chạy kèm để so sánh.")
    else:
        st.caption(f"Nhóm có đủ {len(qs)} câu hỏi: Q00–Q10.")
    with st.expander(f"Xem nội dung đầy đủ của cả {len(qs)} câu hỏi",expanded=False):
        for listed_question in qs:
            st.markdown(f"**Q{listed_question['q_index']:02d} · {listed_question['variant_type']}**")
            st.write(listed_question["question"])
    gold_context=None
    gold_context_error=None
    final_group=group["split"]=="final"
    if final_group:
        st.warning("Final đang ở chế độ chỉ xem. Không thể chạy LLM từ Playground; Official Evaluation là luồng riêng.")
    try:
        gold_context=diagnostic_gold(group)
        st.info(f"Sẽ chạy SQL canonical ở chế độ chỉ đọc trên snapshot đã kiểm tra hash. Trạng thái Owner: {gold_context['owner_status']}. Kết quả và metric là chẩn đoán trên SQL candidate, chưa phải official evaluation.")
    except Exception as exc:
        gold_context_error=str(exc)
        st.warning(f"Chưa thể chấm diagnostic cho nhóm này: {gold_context_error}")
    model=st.selectbox("Model",model_choices(),key="birdvn_play_model",accept_new_options=True,help="Model ID trên OpenRouter. Mặc định là LLM_MODEL; có thể gõ ID khác.") or ""
    cc1,cc2,cc3=st.columns(3)
    temperature=cc1.slider("Temperature",0.0,2.0,0.0,0.1,key="birdvn_play_temp")
    max_tokens=cc2.number_input("Max tokens",min_value=1,max_value=MAX_TOKENS,value=MAX_TOKENS,key="birdvn_play_tokens")
    db_id=group["db_id"]
    st.text_area("Schema context",schema_text(db_id),height=180,disabled=True,key="birdvn_play_schema")
    if run_mode=="Cả nhóm Q00–Q10":confirm=st.checkbox("Xác nhận tối đa 11 lần gọi API cho nhóm này.",key="birdvn_play_confirm")
    else:confirm=True
    clicked=st.button("Run LLM",type="primary",disabled=final_group or not model.strip() or not confirm,key="birdvn_play_run")
    fingerprint=(group["group_id"],run_mode,q["question_id"] if run_mode!="Cả nhóm Q00–Q10" else None,model.strip(),float(temperature),int(max_tokens))
    if clicked:
        selected=([q] if run_mode=="Một câu" else [qs[0],q] if run_mode=="Cặp Q00 + Qi" else qs)
        results=[];progress=st.progress(0,text="Chuẩn bị demo run…")
        for i,item in enumerate(selected):
            with st.spinner(f"Đang gọi {model} · {item['question_id']}…"):
                outcome=run_demo_question(item["question"],db_id,group["card_fields"]["business_rules"],registry.get("semantic_glossary",{}),model.strip(),temperature=float(temperature),max_tokens=int(max_tokens),complete_fn=complete)
            elapsed=outcome["elapsed_s"]
            if outcome["error"]:
                results.append({"question":item,"error":outcome["error"],"elapsed":elapsed})
                if len(selected)==11:break
            else:
                results.append({"question":item,"sql":outcome["sql"],"reply":outcome["reply"],"elapsed":elapsed,"run_result":outcome["execution"],"prompt":outcome["prompt"]})
            progress.progress((i+1)/len(selected),text="Đã xử lý "+str(i+1)+"/"+str(len(selected))+" câu")
        progress.empty()
        canonical_execution=read_only_query(db_id,gold_context["canonical_sql"]) if gold_context else None
        run_score=None
        if isinstance(canonical_execution,dict) and not canonical_execution["truncated"]:
            canonical_result=canonical_execution["result"]
            run_score=score_demo_results(qs,results,[list(row) for row in canonical_result.rows],list(canonical_result.columns))
        run_record={"run_at":time.time(),"group_id":group["group_id"],"model":model.strip(),"mode":run_mode,
                    "results":results,"canonical_sql":gold_context["canonical_sql"] if gold_context else None,
                    "canonical_execution":canonical_execution,"score":run_score,"fingerprint":fingerprint}
        st.session_state["birdvn_demo_runs"].append({key:run_record[key] for key in ("run_at","group_id","model","mode","results","canonical_sql")})
        st.session_state["birdvn_demo_last_result"]=run_record

    run_record=st.session_state.get("birdvn_demo_last_result")
    if run_record and run_record.get("fingerprint")==fingerprint:
        run_score=run_record.get("score")
        canonical_execution=run_record.get("canonical_execution")
        if run_score:
            metrics=run_score["metrics"]
            st.markdown("#### Chỉ số lượt chạy")
            metric_columns=st.columns(5)
            for column,label,key in zip(metric_columns,
                ["EX gốc · Q00","EX variants","EX các câu đã chạy","RSS · cặp Q00–Qi","Robust EX · đủ 11 câu"],
                ["ex_original","ex_variants","ex_overall","rss","robust_ex_all"]):
                rate=metrics[key]
                value="N/A" if rate["percent"] is None else f"{rate['percent']:.1f}%"
                column.metric(label,value,help=f"{rate['numerator']}/{rate['denominator']} theo outcome đã xác định trong lượt này")
            st.caption(f"Đã chạy {run_score['run_question_count']}/11 câu · {metrics['missing_questions']} câu có outcome hạ tầng/không chạy trong metric. SQL error, timeout và no SQL tính là EX=0; lỗi provider/API và kết quả bị cắt dòng là unknown. Không cộng dồn thành replicate.")
            st.markdown("#### So sánh ngắn với SQL gốc")
            question_rows=[]
            for item in run_score["questions"]:
                if item["status"]=="not_run":
                    continue
                verdict="—" if item["correct"] is None else "Đúng" if item["correct"] else "Sai"
                if item["columns_match"] is None:
                    column_diff="Chưa có kết quả"
                elif not item["column_differences"]:
                    column_diff="Khớp"
                else:
                    column_diff="; ".join(f"{diff['canonical'] or '-'} → {diff['generated'] or '-'}" for diff in item["column_differences"])
                question_rows.append({"Câu hỏi":item["question_id"],"Trạng thái":item["status"],
                    "EX":verdict,"Dòng trả về":item["row_count"],
                    "Cột chiếu khác":column_diff})
            st.dataframe(question_rows,hide_index=True,use_container_width=True,height=min(420,40*(len(question_rows)+1)))
        else:
            st.warning("Không có kết quả đầy đủ từ SQL gốc; không tính EX/RSS cho lượt này.")
            status_rows=[]
            for item in run_record["results"]:
                outcome=item.get("run_result")
                row_count=len(outcome["result"].rows) if isinstance(outcome,dict) and not outcome.get("truncated") else None
                status_rows.append({"Câu hỏi":item["question"]["question_id"],"Trạng thái":"error" if item.get("error") else "success" if isinstance(outcome,dict) else "unknown","Số dòng":row_count})
            st.dataframe(status_rows,hide_index=True,use_container_width=True)

        if isinstance(canonical_execution,Timeout):
            st.error(f"SQL gốc timeout sau {canonical_execution.timeout_s}s")
        elif isinstance(canonical_execution,SqlError):
            st.error(f"SQL gốc bị từ chối hoặc gặp lỗi: {canonical_execution.message}")
        elif isinstance(canonical_execution,dict) and canonical_execution.get("truncated"):
            st.warning("Kết quả SQL gốc vượt giới hạn hiển thị; không tính EX/RSS.")
        if st.button("Xem chi tiết SQL và kết quả từng câu",key="birdvn_show_run_details"):
            show_run_details(run_record)
    elif run_record:
        st.caption("Kết quả lượt trước đang ẩn vì bạn đã đổi cấu hình demo.")
