"""SBERT and paraphrase robustness analysis from verified artifacts and actual demo runs."""
import streamlit as st
from bird_demo.benchmark.navigation import hide_secondary_bird_vn_pages
from bird_demo.benchmark.dashboard import read_registry, load_audit, load_similarity, load_table, manifest_status
from bird_demo.benchmark.dashboard import q00_pair_stability
st.set_page_config(page_title="BIRD-VN Analysis",page_icon=":material/analytics:",layout="wide")
hide_secondary_bird_vn_pages()
st.title("Phân tích · Paraphrase robustness & SBERT")
registry=read_registry();summary,status=load_audit();manifest_ok,manifest=manifest_status()
if status!="CURRENT":st.error("SBERT artifact is STALE. Cosine scores are suppressed until source lineage is refreshed.")
else:
    st.caption(f"SBERT artifact CURRENT · {summary['model_id']} · revision `{summary['model_revision']}` · CPU")
    metrics=summary["distribution"]["q00_to_variant"]
    c=st.columns(5)
    for col,label,key in zip(c,["Pairs","Mean cosine","Median","P05","P95"],["count","mean","median","p05","p95"]):col.metric(label,metrics["overall"][key])
    st.caption("Cosine similarity đo độ gần trong embedding space; không phải semantic accuracy và không tự duyệt câu hỏi.")
    st.subheader("Phân bố theo split và domain")
    split_domain=[]
    for dimension,items in (("Split",metrics["split"]),("Domain",metrics["domain"])):
        for name,stats in items.items():split_domain.append({"Phân nhóm":dimension,"Nhóm":name,"n":stats["count"],"Mean":stats["mean"],"Median":stats["median"],"P05":stats["p05"],"P95":stats["p95"]})
    st.dataframe(split_domain,hide_index=True,use_container_width=True)
    qrows=load_similarity()
    st.subheader("Cosine similarity distribution")
    st.bar_chart({"Cosine Q00–Qi": [float(r["cosine_similarity"]) for r in qrows if r.get("split")=="development"]})
    st.caption("Phân bố điểm theo từng cặp. Muốn mở dữ liệu chi tiết Final cần Owner token cấu hình phía server.")
    st.subheader("Theo variant type · Development")
    dev=[r for r in qrows if r.get("split")=="development"]
    types=sorted({r["variant_type"] for r in dev})
    st.dataframe([{"Variant type":t,"n":sum(r["variant_type"]==t for r in dev),"Mean cosine":sum(float(r["cosine_similarity"]) for r in dev if r["variant_type"]==t)/max(1,sum(r["variant_type"]==t for r in dev))} for t in types],hide_index=True)
    groups=[g for g in registry["groups"] if g["split"]=="development"]
    group=st.selectbox("Group detail (Development)",groups,format_func=lambda g:g["group_id"])
    bars=[r for r in dev if r["group_id"]==group["group_id"]]
    st.bar_chart({"Cosine":{r["question_id"]:float(r["cosine_similarity"]) for r in bars}})
    st.subheader("Các cặp similarity thấp")
    low=load_table("similarity_low.csv"); st.dataframe([r for r in low if r.get("split")=="development"][:100],hide_index=True,use_container_width=True)
    st.subheader("Similarity cao có nguy cơ khác ngữ nghĩa")
    high=load_table("high_similarity_semantic_risk.csv"); st.dataframe([r for r in high if r.get("split")=="development"][:100],hide_index=True,use_container_width=True)
    st.subheader("Các cặp biến thể gần trùng")
    dup=load_table("within_group_variant_overlap.csv"); st.dataframe([r for r in dup if r.get("split")=="development"][:100],hide_index=True,use_container_width=True)
    st.subheader("Độ tương đồng thấp/cao giữa các cặp trong nhóm")
    low_within=load_table("within_group_low_similarity.csv"); high_within=load_table("within_group_high_similarity.csv")
    low_tab,high_tab=st.tabs(["Thấp","Cao"])
    with low_tab:st.dataframe([r for r in low_within if r.get("split")=="development"][:100],hide_index=True,use_container_width=True)
    with high_tab:st.dataframe([r for r in high_within if r.get("split")=="development"][:100],hide_index=True,use_container_width=True)
    st.subheader("Jaccard screening")
    jaccard=load_table("jaccard_36_review.csv"); st.dataframe([r for r in jaccard if r.get("split")=="development"],hide_index=True,use_container_width=True)
    st.subheader("Semantic slot review queue")
    flags=load_table("semantic_slot_flags.csv"); st.dataframe([r for r in flags if r.get("group_id") in {g["group_id"] for g in groups}],hide_index=True,use_container_width=True)

st.divider();st.subheader("Robustness trên Demo Run thật")
runs=st.session_state.get("birdvn_demo_runs",[])
if not runs:st.info("Chưa có Demo Run trong phiên này. Không dùng kết quả dự đoán giả.")
else:
    for ri,run in enumerate(reversed(runs),1):
        with st.expander(f"Demo {ri} · {run['group_id']} · {run['model']} · {run['mode']}"):
            successful=[x for x in run["results"] if x.get("sql") and isinstance(x.get("run_result"),dict)]
            st.caption(f"Đã thực thi {len(successful)}/{len(run['results'])} · Ground-truth chưa được duyệt: không tính correctness/EX.")
            pairs=q00_pair_stability(run["results"])
            if pairs:
                stable=sum(p["Rows stable"] for p in pairs)
                st.metric("RSS (các cặp Q00–Qi đã chạy)",f"{stable}/{len(pairs)}",help="Result stability; does not imply correctness")
                st.dataframe(pairs,hide_index=True)
            else:st.caption("Cần có Q00 và ít nhất một Qi đã thực thi thành công để đo RSS.")
