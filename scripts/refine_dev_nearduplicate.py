"""Refine a Development wording variant flagged as near-duplicate of its anchor."""
import csv,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AUTH=ROOT/"benchmark_data/authoring"
REG=AUTH/"dataset.json"; RECORDS=AUTH/"validation_records.json"
QID="ERP-EF-01-Q03"
OLD="Liệt kê từng đơn ở trạng thái CONFIRMED, gồm mã đơn, số đơn, mã khách hàng, ngày đặt và trạng thái."
NEW="Tra cứu các sales order đã được xác nhận, bao gồm mã định danh nội bộ (order_id), số đơn bán (order_no), mã khách hàng (customer_id), ngày đặt và trạng thái."
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 d=json.loads(REG.read_text(encoding='utf-8')); q=next(x for x in d['questions'] if x['question_id']==QID)
 if q['question'] not in (OLD,NEW):raise RuntimeError('Unexpected current Q03 wording')
 q['question']=NEW;q['variant_review']='NEEDS_HUMAN_REVIEW';q['review_notes']='Lexical wording refined to reduce near-duplicate similarity and name customer_id explicitly; still needs human review.'
 REG.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 rec=json.loads(RECORDS.read_text(encoding='utf-8'))
 r=next(x for x in rec if x['group_id']=='ERP-EF-01')
 item=next(x for x in r['question_reviews'] if x['question_id']==QID);item['question']=NEW;item['review_status']='NEEDS_HUMAN_REVIEW'
 RECORDS.write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 p=ROOT/'docs/benchmark/review/dev_human_approval/DEV_V2_TO_V3_CHANGELOG.csv'
 rows=list(csv.DictReader(p.open(encoding='utf-8-sig')))
 item=next(x for x in rows if x['question_id']==QID);item['revised_wording']=NEW;item['reason'] += ' Wording further differentiated from Q0 while preserving customer_id as an ID, not a name.'
 with p.open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=['question_id','original_wording','revised_wording','reason']);w.writeheader();w.writerows(rows)
 gpath=AUTH/'ground_truth_validation.json';g=json.loads(gpath.read_text(encoding='utf-8'));g['validation_records_sha256']=sha(RECORDS);g['question_wording_revision']='dev-v3 targeted wording corrections; SQL/output evidence unchanged; ERP-RK-02 projection awaits Owner decision';gpath.write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('Updated',QID,'status remains NEEDS_HUMAN_REVIEW')
if __name__=='__main__':main()
