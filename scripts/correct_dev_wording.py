"""Apply only confirmed Development wording defects; never touch SQL or Final."""
from __future__ import annotations

import hashlib
import json
import csv
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
AUTH=ROOT/"benchmark_data/authoring"
REG=AUTH/"dataset.json"
RECORDS=AUTH/"validation_records.json"
GROUND=AUTH/"ground_truth_validation.json"
CARDS=ROOT/"docs/benchmark/intent_cards/INTENT_CARDS_DRAFT.md"
CHANGELOG=ROOT/"docs/benchmark/review/dev_human_approval/DEV_V2_TO_V3_CHANGELOG.csv"
MARKERS=("(projection reordered)","(lexical + reordered)","(lexical + reordering)","(lexical + reordered)","(lexical)","(syntactic)","(reordered)")

CHANGES={
 "ERP-EF-01-Q01":("Cho biết các đơn hàng đã xác nhận; với mỗi đơn, nêu mã đơn, số đơn, mã khách, ngày đặt và trạng thái.",
  "Liệt kê từng đơn đã xác nhận, gồm mã đơn, số đơn, mã khách hàng, ngày đặt và trạng thái.",
  "Phân biệt rõ mã khách hàng (customer_id), không diễn đạt thành tên khách hàng."),
 "ERP-EF-01-Q03":("Tra cứu các đơn ở trạng thái CONFIRMED, gồm mã đơn, số đơn, khách hàng, ngày đặt và trạng thái.",
  "Liệt kê từng đơn ở trạng thái CONFIRMED, gồm mã đơn, số đơn, mã khách hàng, ngày đặt và trạng thái.",
  "Nêu rõ customer_id là mã khách hàng; câu hỏi không yêu cầu tên khách hàng."),
 "WMS-AG-02-Q05":("Hãy lập một dòng cho mỗi SKU KG có outbound shipment movement: cộng độ lớn các delta âm của chứng từ SHIPMENT đã POSTED trong toàn lịch sử.",
  "Với mỗi SKU có base_unit KG và movement âm thuộc SHIPMENT POSTED, trả product ID, SKU, base unit và tổng lượng xuất (milli-KG) trên toàn bộ lịch sử.",
  "Bổ sung đầy đủ bốn cột SQL projection; giữ shipment/status/unit và phạm vi toàn lịch sử."),
 "WMS-AG-02-Q02":("Cho biết mỗi mặt hàng đơn vị KG đã giao khách bao nhiêu lượng: chỉ tính movement âm của SHIPMENT POSTED và trả ID, SKU, đơn vị, tổng milli-KG.",
  "Trong toàn bộ lịch sử, với mỗi product base_unit KG có movement âm của SHIPMENT POSTED, trả product ID, SKU, base unit và tổng lượng xuất (milli-KG).",
  "Làm rõ projection, cohort có movement và phạm vi thời gian không giới hạn."),
 "WMS-AG-02-Q03":("Tính tổng lượng xuất kho cho khách của từng SKU cơ sở KG từ các shipment đã hạch toán; hiển thị product ID, SKU, base unit và milli-KG.",
  "Trong toàn bộ lịch sử, với mỗi SKU base_unit KG có movement âm thuộc SHIPMENT POSTED, trả product ID, SKU, base unit và tổng lượng xuất milli-KG.",
  "Nêu rõ toàn bộ lịch sử, cohort và projection đang được SQL trả về."),
 "WMS-AG-02-Q04":("Mỗi SKU KG có bao nhiêu milli-KG đã xuất cho khách qua SHIPMENT POSTED? Trả product ID, mã SKU, base unit và tổng lượng.",
  "Trong toàn bộ lịch sử, mỗi SKU KG có tổng lượng milli-KG đã xuất qua movement âm thuộc SHIPMENT POSTED là bao nhiêu? Trả product ID, SKU, base unit và tổng lượng.",
  "Giữ measure, status/type, đơn vị và bổ sung phạm vi không giới hạn ngày."),
 "WMS-AG-02-Q06":("Cần tổng lượng giao theo product ở đơn vị milli-KG, cùng product ID/SKU/base unit; chỉ xét các movement âm thuộc shipment đã ghi sổ.",
  "Trong toàn bộ lịch sử, chỉ xét movement âm thuộc SHIPMENT POSTED của product base_unit KG; trả product ID, SKU, base unit và tổng lượng xuất milli-KG.",
  "Nêu rõ filter product/unit, document status/type, time scope và toàn bộ projection."),
 "WMS-AG-02-Q07":("Trước tiên giới hạn chứng từ vào SHIPMENT POSTED và movement âm; kế đó chọn product base_unit KG, nhóm theo SKU rồi cộng lượng xuất milli-unit.",
  "Trong toàn bộ lịch sử, chọn movement âm của SHIPMENT POSTED thuộc product base_unit KG, rồi nhóm theo product; trả product ID, SKU, base unit và tổng lượng xuất milli-KG.",
  "Bổ sung projection và làm rõ không có bộ lọc thời gian."),
 "WMS-AG-02-Q09":("Cộng lượng giao khách đã hoàn tất (lexical) cho mỗi SKU KG, dùng riêng movement âm của shipment đã ghi sổ; trả ID/SKU/unit/tổng milli-KG (syntactic).",
  "Trong toàn bộ lịch sử, tổng hợp lượng xuất milli-KG cho mỗi product base_unit KG từ movement âm thuộc SHIPMENT POSTED; trả product ID, SKU, base unit và tổng lượng.",
  "Xóa taxonomy notes, ghi rõ toàn bộ projection và không giới hạn ngày."),
 "WMS-AG-02-Q10":("Chỉ chọn shipment POSTED có delta âm trên SKU KG, rồi tổng hợp theo product (reordered); xuất product ID, SKU, đơn vị và tổng lượng milli-KG đã xuất (lexical).",
  "Trong toàn bộ lịch sử, chọn movement âm thuộc SHIPMENT POSTED của SKU KG, tổng hợp theo product rồi trả product ID, SKU, base unit và tổng lượng xuất milli-KG.",
  "Bỏ chú thích biên soạn, nêu rõ base unit và phạm vi thời gian."),
 "WMS-CD-02-Q03":("Tra cứu chênh lệch giữa lượng kế hoạch và lượng đã phát sinh ở mỗi cặp chứng từ–SKU, gồm đủ trạng thái; transfer đếm leg nguồn một lần, các loại đã POSTED khác theo movement rules.",
  "Với mỗi document × SKU ở mọi trạng thái, trả document ID/no/type/status, SKU, base unit, planned quantity và executed quantity riêng theo milli-unit; non-POSTED có executed=0, TRANSFER lấy SOURCE một lần, loại POSTED khác theo movement rules.",
  "Loại bỏ hàm ý tạo cột chênh lệch; nêu hai measure riêng cùng projection, grain và status rules."),
 "WMS-CD-02-Q01":("Đối chiếu lượng dự kiến với lượng thực hiện cho từng SKU trên từng chứng từ kho; giữ cả DRAFT, POSTED, CANCELLED, đơn vị milli-unit và quy ước transfer lấy SOURCE một lần.",
  "Với mỗi document × SKU ở mọi trạng thái, trả document ID, document number, type, status, SKU, base unit, planned quantity và executed quantity riêng theo milli-unit; non-POSTED có executed=0, TRANSFER lấy SOURCE một lần.",
  "Nêu đủ projection và hai lượng riêng; giữ mọi status và transfer rule."),
 "WMS-CD-02-Q02":("Theo từng document và SKU, cho biết planned so với executed quantity (milli-unit), kèm trạng thái/loại chứng từ và base unit; chứng từ chưa ghi sổ có executed bằng 0.",
  "Với mọi document × SKU, trả document ID/no/type/status, SKU/base unit, planned quantity và executed quantity riêng theo milli-unit; gồm mọi trạng thái, non-POSTED có executed=0, TRANSFER lấy SOURCE một lần.",
  "Làm rõ full projection, non-POSTED rule và transfer rule."),
 "WMS-CD-02-Q04":("Mỗi cặp document × SKU có ID/số chứng từ, type/status, SKU/base unit, planned milli-quantity và executed milli-quantity nào? Với status khác POSTED, executed là 0.",
  "Mỗi cặp document × SKU có document ID/no/type/status, SKU/base unit, planned quantity và executed quantity riêng theo milli-unit nào? Non-POSTED có executed=0; TRANSFER lấy SOURCE một lần.",
  "Bổ sung đầy đủ status/type và quy tắc transfer."),
 "WMS-CD-02-Q05":("Hãy lập bảng đối chiếu ở grain document–SKU, bao gồm mọi trạng thái. Trình bày định danh chứng từ, SKU, đơn vị, lượng planned và executed theo milli-unit; transfer lấy SOURCE leg, non-POSTED bằng 0.",
  "Lập bảng cho mọi document × SKU và mọi trạng thái, gồm document ID/no/type/status, SKU/base unit, planned quantity và executed quantity riêng theo milli-unit; non-POSTED bằng 0, TRANSFER lấy SOURCE một lần.",
  "Thay ‘định danh’ mơ hồ bằng toàn bộ cột chứng từ và giữ hai measure độc lập."),
 "WMS-CD-02-Q07":("Giữ trước tất cả document status và tính planned quantity theo document × SKU; sau đó lấy executed từ movement POSTED, dùng SOURCE một lần cho TRANSFER, rồi trả định danh chứng từ/SKU/unit và cả hai lượng milli-unit.",
  "Cho mọi document × SKU, giữ mọi trạng thái và trả document ID/no/type/status, SKU/base unit, planned và executed quantity riêng theo milli-unit; executed chỉ từ POSTED movement, TRANSFER lấy SOURCE một lần.",
  "Làm rõ projection và không gộp planned/executed thành measure khác."),
 "WMS-CD-02-Q09":("So sánh lượng dự kiến với lượng đã ghi nhận cho từng cặp chứng từ–mặt hàng (lexical), giữ cả trạng thái; transfer chỉ tính leg nguồn một lần và trạng thái chưa POSTED cho lượng thực hiện bằng không (syntactic).",
  "Đối chiếu riêng planned quantity và executed quantity theo milli-unit cho mỗi document × SKU; trả document ID/no/type/status, SKU/base unit, gồm mọi trạng thái; TRANSFER lấy SOURCE một lần, non-POSTED có executed=0.",
  "Xóa chú thích taxonomy, nêu đủ projection và hai measure riêng."),
 "WMS-JN-04-Q09":("Liệt kê từng chân luân chuyển kho (lexical) của chứng từ đã ghi sổ, rồi nối chi tiết SKU/kho và trả signed quantity cùng thời gian UTC (syntactic).",
  "Với từng movement leg của TRANSFER POSTED, trả document ID/no, line number, SKU, leg number/role, warehouse nguồn/đích, signed quantity milli-unit và thời điểm movement UTC.",
  "Khôi phục đầy đủ document/line/leg identity, hai warehouse, signed quantity và timestamp đã bị rút gọn."),
 "ERP-JN-02-Q10":("Trả trước projection gồm order number/date, SKU/name, ordered milli-quantity và net VND cho mỗi dòng hàng; lọc các đơn có trạng thái CONFIRMED (lexical + reordering).",
  "Với mỗi order line thuộc đơn CONFIRMED, trả số đơn, ngày đặt, SKU, tên sản phẩm, ordered quantity milli-unit và line net VND.",
  "Bỏ chú thích biên soạn và dùng tiếng Việt rõ ràng, giữ nguyên line grain, filter và sáu cột output."),
 "WMS-CD-02-Q09":("So sánh lượng dự kiến với lượng đã ghi nhận cho từng cặp chứng từ–mặt hàng (lexical), giữ cả trạng thái; transfer chỉ tính leg nguồn một lần và trạng thái chưa POSTED cho lượng thực hiện bằng không (syntactic).",
  "Đối chiếu riêng planned quantity và executed quantity theo milli-unit cho từng document × SKU, gồm mọi trạng thái; TRANSFER chỉ tính SOURCE một lần, non-POSTED có executed=0, loại POSTED khác theo movement rules.",
  "Xóa taxonomy notes và làm rõ hai measure riêng, grain, status và transfer rule."),
}

GB03={
"ERP-GB-03-Q00":"Với mỗi sales rep có ít nhất một đơn CONFIRMED, cho biết mã sales rep, tên nhân viên nếu có và số đơn CONFIRMED; tạo thêm một nhóm NULL chưa gán khi có đơn CONFIRMED không có sales rep.",
"ERP-GB-03-Q01":"Với từng nhân viên kinh doanh có đơn đã xác nhận, nêu mã sales rep, tên nếu có và số đơn; nếu có đơn CONFIRMED chưa gán người phụ trách, tính chúng trong một nhóm NULL riêng.",
"ERP-GB-03-Q02":"Thống kê số đơn CONFIRMED theo sales rep có đơn, gồm mã rep, tên nếu có và số đơn; giữ nhóm NULL riêng nếu có đơn chưa gán sales rep.",
"ERP-GB-03-Q03":"Với mỗi người phụ trách bán hàng có ít nhất một đơn ở trạng thái CONFIRMED, cho biết mã, tên nếu có và số đơn; thêm nhóm NULL nếu tồn tại đơn đã xác nhận chưa gán người phụ trách.",
"ERP-GB-03-Q04":"Mỗi sales rep có đơn CONFIRMED có mã nào, tên nào nếu có và bao nhiêu đơn? Nếu có đơn chưa gán rep, trình bày chúng thành nhóm NULL riêng.",
"ERP-GB-03-Q05":"Lập bảng theo sales rep có đơn CONFIRMED, gồm mã rep, tên nếu có và số đơn; biểu diễn đơn đã xác nhận chưa gán rep thành nhóm NULL nếu có.",
"ERP-GB-03-Q06":"Tạo một dòng cho mỗi sales rep có đơn đã xác nhận, gồm mã, tên nếu có và số đơn; nếu có đơn CONFIRMED không gán rep, thêm một dòng nhóm NULL.",
"ERP-GB-03-Q07":"Chỉ lấy đơn CONFIRMED trong toàn bộ dữ liệu; nhóm chúng theo sales rep có đơn, rồi trả mã, tên nếu có và số đơn. Đơn chưa gán rep thuộc nhóm NULL riêng nếu có.",
"ERP-GB-03-Q08":"Kết quả cần mã sales rep, tên nếu có và số đơn cho mỗi rep có đơn CONFIRMED; giữ nhóm NULL riêng khi có đơn đã xác nhận chưa gán rep.",
"ERP-GB-03-Q09":"Phân nhóm các đơn CONFIRMED theo người phụ trách bán hàng có đơn, kể cả nhóm NULL nếu có đơn chưa phân công; cho biết mã/tên nếu có và số đơn.",
"ERP-GB-03-Q10":"Bao nhiêu đơn CONFIRMED thuộc mỗi sales rep có đơn? Trình bày mã rep, tên nếu có và số lượng; tính đơn chưa gán trong nhóm NULL riêng nếu có.",
}


def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 reg=json.loads(REG.read_text(encoding="utf-8")); dev={q["question_id"]:q for q in reg["questions"] if q["split"]=="development"}
 if len(dev)!=110:raise RuntimeError(f"Expected 110 Development questions, got {len(dev)}")
 changelog=[]; marker_ids=[]
 for qid,q in dev.items():
  original=q["question"]; revised=original
  for marker in MARKERS:
   if marker in revised:
    revised=revised.replace(" "+marker,"").replace(marker,"")
    marker_ids.append(qid)
  revised=re.sub(r"\s+([,.;?])",r"\1",revised)
  revised=re.sub(r"\s{2,}"," ",revised).strip()
  if revised!=original:
   q["question"]=revised
   changelog.append({"question_id":qid,"original_wording":original,"revised_wording":revised,"reason":"Removed editorial taxonomy annotation from question text; taxonomy remains in variant_type/secondary_tags."})
 for qid,(old,new,reason) in CHANGES.items():
  q=dev[qid]
  if q["question"]!=old:
   # Old may already have had its inline marker stripped above.
   if re.sub(r"\s+([,.;?])",r"\1",old.replace(" (lexical)","").replace(" (syntactic)","").replace(" (reordered)","").replace(" (projection reordered)","").replace(" (lexical + reordered)","").replace(" (lexical + reordering)","")).strip()!=q["question"]:
    raise RuntimeError(f"Unexpected source wording for targeted correction {qid}: {q['question']}")
  if q["question"]!=new:
   changelog.append({"question_id":qid,"original_wording":q["question"],"revised_wording":new,"reason":reason})
   q["question"]=new
 for qid,new in GB03.items():
  q=dev[qid]
  if q["question"]!=new:
   changelog.append({"question_id":qid,"original_wording":q["question"],"revised_wording":new,"reason":"Clarified cohort: only sales reps with CONFIRMED orders; NULL bucket exists only when unassigned confirmed orders exist."})
   q["question"]=new
 # ERP-RK-02 mismatch is explicitly held for Owner decision; do not edit SQL or its wording.
 rk=next(g for g in reg["groups"] if g["group_id"]=="ERP-RK-02")
 rk["human_review_issues"]=[{
  "status":"NEEDS_OWNER_DECISION",
  "issue":"Canonical SQL projects product_id, but Intent Card and Q0-Q10 request SKU/name/base_unit/quantity/rank without product_id.",
  "options":["Add product_id to Intent Card and all 11 questions, retaining SQL projection.","Remove product_id from SQL SELECT, retaining the current requested projection."],
  "recommendation":"Owner should choose one consistent projection; do not execute/approve a release gold until aligned."
 }]
 reg["paraphrase_revision"]="dev-v3"
 reg["paraphrase_revision_note"]="Targeted wording corrections; inline taxonomy notes removed; ERP-RK-02 product_id projection mismatch held for Owner decision."
 reg["human_review_status"]="NEEDS_HUMAN_REVIEW"
 REG.write_text(json.dumps(reg,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

 # Update Intent Card briefs only when matching Development original wording changed.
 cards=CARDS.read_text(encoding="utf-8").splitlines()
 q0_by_group={qid.rsplit("-Q",1)[0]:dev[qid]["question"] for qid in dev if qid.endswith("Q00")}
 for i,line in enumerate(cards):
  for gid,text in q0_by_group.items():
   if line.startswith(f"| {gid} |"):
    cells=line.split("|"); cells[3]=" "+text+" "; cards[i]="|".join(cells)
 CARDS.write_text("\n".join(cards)+"\n",encoding="utf-8")
 for gid,text in q0_by_group.items():
  group=next(g for g in reg["groups"] if g["group_id"]==gid)
  group["card_fields"]["brief"]=text
 reg["source_hashes"]["intent_cards"]=sha(CARDS)
 REG.write_text(json.dumps(reg,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

 # Validation records continue to require human review and show the current wording.
 records=json.loads(RECORDS.read_text(encoding="utf-8"))
 for rec in records:
  gid=rec["group_id"]
  if gid not in {x[:-3] for x in q0_by_group}:continue
  qs=sorted((q for q in dev.values() if q["group_id"]==gid),key=lambda x:x["q_index"])
  for old_review,q in zip(rec.get("question_reviews",[]),qs):
   old_review["question"]=q["question"]; old_review["variant_type"]=q["variant_type"]
   old_review["secondary_tags"]=q.get("secondary_tags",[]); old_review["review_status"]="NEEDS_HUMAN_REVIEW"
  rec["wording_revision"]="dev-v3"; rec["ground_truth_status"]="NEEDS_HUMAN_REVIEW"
  rec["human_review_status"]="NEEDS_HUMAN_REVIEW"
  rec["owner_approval"]={"status":"PENDING","approver":None,"date":None,"rationale":None}
  if gid=="ERP-RK-02":rec["outstanding_issues"]=["NEEDS_OWNER_DECISION: SQL includes product_id but question/card projection does not; choose aligned projection before approving."]
 RECORDS.write_text(json.dumps(records,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 ground=json.loads(GROUND.read_text(encoding="utf-8")); ground["validation_records_sha256"]=sha(RECORDS)
 ground["question_wording_revision"]="dev-v3 wording-only corrections; SQL and output evidence unchanged; ERP-RK-02 projection awaits Owner decision"
 GROUND.write_text(json.dumps(ground,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

 with CHANGELOG.open("w",newline="",encoding="utf-8-sig") as f:
  w=csv.DictWriter(f,fieldnames=["question_id","original_wording","revised_wording","reason"]);w.writeheader();w.writerows(changelog)
 auditpath=ROOT/"docs/benchmark/review/dev_human_approval/DEV_V2_TO_V3_CHANGELOG.csv"
 qa=AUTH/"dev_paraphrase_quality_audit.json"
 oldaudit=json.loads(qa.read_text(encoding="utf-8")); oldaudit["revision"]="dev-v3"; oldaudit["wording_change_count"]=len(changelog)
 oldaudit["wording_change_log_path"]="docs/benchmark/review/dev_human_approval/DEV_V2_TO_V3_CHANGELOG.csv"
 oldaudit["q0_needs_owner_decision"]=["ERP-RK-02: SQL projects product_id but card/questions do not; Owner must select one aligned projection."]
 oldaudit["editorial_annotation_occurrences_remaining"]=sum(bool(re.search(r"\((?:lexical|syntactic|reordered|projection reordered)",q["question"],re.I)) for q in dev.values())
 oldaudit["source_hashes"]["registry"]=sha(REG); oldaudit["source_hashes"]["validation_records"]=sha(RECORDS)
 qa.write_text(json.dumps(oldaudit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"development_questions":len(dev),"question_text_changes":len(changelog),"editorial_marker_questions_scrubbed":len(set(marker_ids)),"owner_decisions":["ERP-RK-02 product_id projection"],"registry_sha256":sha(REG),"changelog_sha256":sha(CHANGELOG)},ensure_ascii=False,indent=2))

if __name__=="__main__":main()
