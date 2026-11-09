"""Write question-level v2→v3 wording change log from captured prior text."""
from __future__ import annotations
import csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from correct_dev_wording import CHANGES,GB03
REG=ROOT/"benchmark_data/authoring/dataset.json"
OUT=ROOT/"docs/benchmark/review/dev_human_approval/DEV_V2_TO_V3_CHANGELOG.csv"

GB_OLD={
"ERP-GB-03-Q00":"Với mỗi sales rep có confirmed orders, kể cả một nhóm riêng cho sales rep chưa gán (NULL), cho biết mã sales rep, tên nếu có và số đơn CONFIRMED trong toàn bộ dữ liệu.",
"ERP-GB-03-Q01":"Theo từng nhân viên kinh doanh có đơn đã xác nhận, kể cả nhóm chưa phân công, cho biết mã, tên nếu có và số đơn.",
"ERP-GB-03-Q02":"Thống kê số đơn CONFIRMED của từng sales rep; giữ cả nhóm chưa được gán nhân viên và trả mã, tên nếu có.",
"ERP-GB-03-Q03":"Cho biết mỗi người phụ trách bán hàng có bao nhiêu đơn ở trạng thái xác nhận, kể cả phần chưa gán; kèm mã và tên nếu có.",
"ERP-GB-03-Q04":"Mỗi nhóm sales rep (kể cả NULL chưa gán) có mã nào, tên nào nếu có, và bao nhiêu confirmed orders?",
"ERP-GB-03-Q05":"Hãy lập bảng theo sales rep, gồm mã rep, tên nếu có và số đơn CONFIRMED; biểu diễn giá trị NULL thành nhóm chưa gán.",
"ERP-GB-03-Q06":"Cần một dòng cho mỗi sales rep có đơn đã xác nhận (kể cả NULL): mã rep, tên nếu có, tổng số đơn.",
"ERP-GB-03-Q07":"Trước hết xét mọi đơn không giới hạn thời gian và chỉ giữ CONFIRMED; sau đó nhóm theo sales rep, gồm NULL, rồi trả mã, tên nếu có và số đơn.",
"ERP-GB-03-Q08":"Kết quả cần mã sales rep, tên nếu có và số đơn. Hãy đếm trên các đơn CONFIRMED theo từng rep, đồng thời giữ nhóm NULL chưa gán.",
"ERP-GB-03-Q09":"Phân nhóm theo người phụ trách bán hàng (cả nhóm chưa phân công), rồi cho biết mã/tên nếu có và số đơn đã xác nhận (lexical + reordered).",
"ERP-GB-03-Q10":"Bao nhiêu đơn CONFIRMED thuộc từng sales rep, tính cả nhóm NULL? Trình bày mỗi nhóm thành mã rep, tên nếu có và số lượng đơn.",
}
MARKED_OLD={
"ERP-EF-01-Q09":"Tìm các đơn bán đã được chốt (lexical), rồi trình bày từng đơn dưới dạng mã đơn, số đơn, mã khách hàng, ngày đặt và trạng thái (projection reordered).",
"ERP-RK-02-Q09":"Trong mỗi cohort đơn vị cơ sở, hãy xếp các mặt hàng dẫn đầu (lexical) theo tổng lượng ordered ở đơn đã chốt; xuất SKU/tên/đơn vị/tổng milli-unit/hạng và giữ đồng hạng thứ ba (syntactic).",
"ERP-RK-02-Q10":"Hãy trả trước SKU, tên, đơn vị, tổng ordered milli-unit và thứ hạng: dùng các đơn CONFIRMED, cộng theo SKU, phân hạng riêng mỗi base unit và giữ mọi trường hợp hòa tại hạng 3 (lexical + reordered).",
"ERP-JN-02-Q09":"Với từng chi tiết đơn bán đã chốt (lexical), nối thông tin mặt hàng và trình bày bộ số đơn, ngày, SKU/tên, lượng milli-unit, net VND (syntactic).",
"ERP-TM-02-Q09":"Tổng hợp các đơn vị giao đã hoàn tất (lexical) mỗi ngày theo giờ Việt Nam; dùng delivered time UTC và lọc local-year 2025, chỉ xuất các ngày có chuyến cùng số lượng (syntactic).",
"ERP-TM-02-Q10":"Trước hết chọn event DELIVERED trong năm địa phương 2025, rồi đếm shipment theo ngày sau quy đổi UTC→Asia/Ho_Chi_Minh; trả ngày và count, không sinh ngày 0 (lexical + reordered).",
"WMS-EF-01-Q09":"Liệt kê các phiếu kho đã ghi sổ (lexical), mỗi phiếu là một dòng gồm ID, số hiệu, loại, trạng thái và business date (syntactic).",
"WMS-EF-01-Q10":"Trả projection ID/no/type/status/business date cho từng chứng từ; trước tiên giới hạn inventory document ở trạng thái POSTED (lexical + reordered).",
"WMS-EF-02-Q09":"Tìm các mặt hàng tính theo kilogram (lexical), rồi trình bày ID/SKU/tên/đơn vị/category ID, kể cả category chưa gán (syntactic).",
"WMS-EF-02-Q10":"Trả product ID, SKU, tên, base unit và category ID; bộ lọc catalog là KG, còn NULL category vẫn được giữ (lexical + reordered).",
"WMS-JN-04-Q10":"Mỗi row tương ứng một movement leg; trước hết giới hạn transfer POSTED, sau đó xuất chứng từ/line/SKU/leg-role/kho nguồn-đích/signed milli-qty/timestamp UTC (lexical + reordered).",
"WMS-CD-02-Q10":"Trước hết phân nhóm document × SKU trên mọi trạng thái, rồi xuất ID/no/type/status, SKU/unit và hai lượng milli-unit; DRAFT/CANCELLED có executed=0, TRANSFER lấy SOURCE, loại POSTED khác theo rules (lexical + reordered).",
}
REASONS={qid:reason for qid,(_,_,reason) in CHANGES.items()}
for qid in GB03:REASONS[qid]="Clarified sales-rep cohort to reps with confirmed orders and retained a NULL bucket only when unassigned confirmed orders exist."
for qid in MARKED_OLD:REASONS[qid]=REASONS.get(qid,"Removed editorial taxonomy note(s); transformation labels remain in metadata.")

def main():
 reg=json.loads(REG.read_text(encoding='utf-8')); qs={q['question_id']:q for q in reg['questions']}
 originals={qid:old for qid,(old,_,_) in CHANGES.items()}
 originals.update(GB_OLD); originals.update(MARKED_OLD)
 rows=[]
 for qid,old in originals.items():
  q=qs[qid]
  reason=REASONS[qid]
  if qid in MARKED_OLD: reason += " Editorial classification was removed from the text; variant_type/secondary_tags carry it."
  rows.append({"question_id":qid,"original_wording":old,"revised_wording":q['question'],"reason":reason})
 with OUT.open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=['question_id','original_wording','revised_wording','reason']);w.writeheader();w.writerows(rows)
 print(json.dumps({"change_log_rows":len(rows),"unique_questions":len({x['question_id'] for x in rows})},indent=2))
if __name__=='__main__':main()
