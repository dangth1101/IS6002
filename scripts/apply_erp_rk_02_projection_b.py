"""Record Benchmark Owner's ERP-RK-02 Option B projection alignment."""
from __future__ import annotations
import hashlib,json
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
AUTHORING=ROOT/"benchmark_data/authoring"
REGISTRY=AUTHORING/"dataset.json"
SQL=("WITH sku_qty AS (SELECT p.product_id,p.sku,p.product_name,p.base_unit,"
     "SUM(l.ordered_qty_milli) AS sold_qty_milli FROM PRODUCTS p "
     "JOIN SALES_ORDER_LINES l ON l.product_id=p.product_id "
     "JOIN SALES_ORDERS o ON o.order_id=l.order_id WHERE o.order_status='CONFIRMED' "
     "GROUP BY p.product_id,p.sku,p.product_name,p.base_unit), ranked AS ("
     "SELECT *,RANK() OVER(PARTITION BY base_unit ORDER BY sold_qty_milli DESC) AS rnk FROM sku_qty) "
     "SELECT sku,product_name,base_unit,sold_qty_milli,rnk FROM ranked WHERE rnk<=3 "
     "ORDER BY base_unit,rnk,product_id")

def main():
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    group=next(g for g in registry["groups"] if g["group_id"]=="ERP-RK-02")
    group["canonical_sql"]=SQL;group["canonical_sql_draft"]=SQL
    group["canonical_sql_sha256"]=hashlib.sha256(SQL.encode("utf-8")).hexdigest()
    group["human_review_issues"]=[]
    group["projection_alignment_decision"]={
        "status":"RESOLVED_BY_BENCHMARK_OWNER",
        "option":"B",
        "decision":"Remove product_id from the final SELECT; retain SKU, product_name, base_unit, sold_qty_milli, and rnk. Ranking partition and tie policy remain unchanged.",
        "date":date.today().isoformat(),
    }
    group["validation_status"]="PENDING_REVALIDATION"
    group["human_review_status"]="NEEDS_HUMAN_REVIEW"
    for question in registry["questions"]:
        if question["group_id"]=="ERP-RK-02":question["canonical_sql"]=SQL
    registry["authoring_revision"]="dev-v4-erp-rk02-projection-b"
    registry["authoring_revision_note"]="Owner chose Option B; final projection now contains five requested fields; all human review remains pending."
    registry["approval_note"]="All Intent Cards, SQL candidates, and question wordings remain pending human review; machine validation is not owner approval."
    REGISTRY.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    sql_path=AUTHORING/"ground_truth_candidates.sql"
    with sql_path.open("w",encoding="utf-8",newline="\n") as handle:
        handle.write("-- DRAFT ONLY: SQL candidates are not human-approved; see validation artifacts for machine checks.\n")
        for g in registry["groups"]:
            handle.write(f"\n-- {g['group_id']} | {g['db_id']} | {g['complexity']} | {g.get('validation_status','NEEDS_HUMAN_REVIEW')}\n")
            handle.write(g["canonical_sql_draft"].rstrip(";")+";\n")
    print(json.dumps({"group":"ERP-RK-02","option":"B","sql_sha256":group["canonical_sql_sha256"],
                      "registry_sha256":hashlib.sha256(REGISTRY.read_bytes()).hexdigest()},indent=2))
if __name__=="__main__":main()
