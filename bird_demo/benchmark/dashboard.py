"""Read-only BIRD-VN dashboard data and safe interactive SQL helpers."""
from __future__ import annotations
import csv, hashlib, hmac, inspect, json, os, re, sqlite3, time
from copy import deepcopy
from pathlib import Path
from typing import Any
from bird_demo.data import ROOT
from bird_demo.benchmark.registry import file_matches_sha256, load_registry, sha256_file
from bird_demo.runner import Rows, SqlError, Timeout
from bird_demo.benchmark.metrics import result_equal
from bird_demo.benchmark.metrics import INFRA_FAILURE, Observation, metric_summary
from bird_demo.benchmark.field_contracts import (
    COMPARATOR_VERSION,
    EVALUATION_PROTOCOL_VERSION,
    bind_output_contract,
    make_output_contract,
    compare_named_results,
    GROUP_COLUMN_ALIASES,
    align_result,
)
from bird_demo.prompt import extract_sql
from bird_demo.llm import Reply

REGISTRY_PATH = ROOT / "benchmark_data/authoring/dataset.json"
AUDIT_DIR = ROOT / "docs/benchmark/review/full_semantic_validation_sbert"
PHYSICAL_DIR = ROOT / "benchmark_data/physical"
MAX_DISPLAY_ROWS = 500
DEMO_TIMEOUT_S = 30
_OUTPUT_CONTRACT_CACHE: dict[tuple[str, str, str], dict[str, Any]] = {}

# The benchmark manifest pins research inputs/evidence, not Streamlit presentation code.
UI_ARTIFACTS = {"app.py"}

def is_ui_artifact(rel: str) -> bool:
    normalized = rel.replace("\\", "/")
    return normalized in UI_ARTIFACTS or normalized.startswith("pages/")

def read_registry(): return load_registry(REGISTRY_PATH, allow_draft=True)
def registry_file_hash(): return hashlib.sha256(REGISTRY_PATH.read_bytes()).hexdigest()
def manifest_status():
    manifest_path=ROOT / "benchmark_data/authoring/dev_v6_vietnamese_first_manifest.json"
    if not manifest_path.exists(): return False, "Không tìm thấy manifest"
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("registry_sha256") != registry_file_hash(): return False, "Hash registry không khớp manifest"
    for rel,digest in manifest.get("files",{}).items():
        if is_ui_artifact(rel):
            continue
        if not file_matches_sha256(ROOT/rel,digest): return False, f"Artifact lệch manifest: {rel}"
    return True, manifest.get("revision", "unknown")
def owner_access_granted(token: str | None) -> bool:
    expected=os.environ.get("BIRD_VN_OWNER_TOKEN")
    return bool(expected and token and hmac.compare_digest(token,expected))
def visible_groups(registry, *, include_final=False):
    return [g for g in registry["groups"] if include_final or g["split"]=="development"]
def load_audit():
    summary_path=AUDIT_DIR/"summary.json"
    summary=json.loads(summary_path.read_text(encoding="utf-8"))
    current=registry_file_hash(); manifest_ok,_=manifest_status()
    current_questions={q["question_id"]:q["question"] for q in read_registry()["questions"]}
    rows=load_similarity()
    lineage_ok=bool(rows) and all(current_questions.get(r["question_id"])==r["variant_text"] and current_questions.get(r["group_id"]+"-Q00")==r["original_q0"] for r in rows)
    question_count=len(current_questions)==550 and len(rows)==500
    artifact_hashes=summary.get("report_artifact_sha256",{})
    artifacts_ok=bool(artifact_hashes) and all(file_matches_sha256(AUDIT_DIR/name,digest) for name,digest in artifact_hashes.items())
    status="CURRENT" if summary.get("registry_sha256")==current and manifest_ok and summary.get("question_texts_match_sbert_audit") and lineage_ok and question_count and artifacts_ok else "STALE"
    return summary,status

def load_similarity():
    path=AUDIT_DIR/"q00_variant_similarity.csv"
    with path.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def load_slot_flags():
    path=AUDIT_DIR/"semantic_slot_flags.csv"
    with path.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def load_table(name):
    path=AUDIT_DIR/name
    with path.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def load_json(rel):
    path=ROOT/rel
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def diagnostic_gold(group: dict[str, Any]) -> dict[str, Any]:
    """Prepare the current Development SQL candidate for a read-only diagnostic run.

    This does not assert that the candidate is Owner-approved ground truth. The page
    executes it read-only alongside the LLM prediction and labels all resulting scores
    as diagnostic while human review is pending.
    """
    if group.get("split") != "development":
        raise ValueError("Diagnostic scoring is limited to Development groups.")
    registry = read_registry()
    manifest = load_json("benchmark_data/authoring/dev_v6_vietnamese_first_manifest.json")
    if not manifest or manifest.get("registry_sha256") != registry_file_hash():
        raise ValueError("Registry data hash does not match the current dataset manifest.")
    if manifest.get("files", {}).get("benchmark_data/authoring/dataset.json") != registry_file_hash():
        raise ValueError("Registry file is not pinned by the dataset manifest.")
    current_group = next((g for g in registry["groups"] if g["group_id"] == group["group_id"]), None)
    if current_group is None or current_group.get("canonical_sql_sha256") != group.get("canonical_sql_sha256"):
        raise ValueError("Selected group does not match the current registry.")
    physical_manifest = load_json("benchmark_data/physical/build_manifest.json")
    if not physical_manifest:
        raise ValueError("Physical database manifest is missing.")

    group_id = group["group_id"]
    canonical_sql = current_group.get("canonical_sql_draft") or current_group.get("canonical_sql")
    sql_hash = hashlib.sha256((canonical_sql or "").encode("utf-8")).hexdigest()
    if sql_hash != group.get("canonical_sql_sha256"):
        raise ValueError("Canonical SQL candidate hash does not match the registry.")
    db_path = PHYSICAL_DIR / f"{group['db_id']}.sqlite"
    if not db_path.is_file():
        raise ValueError("Frozen Development snapshot is missing.")
    db_hash = sha256_file(db_path)
    manifest_entry = physical_manifest.get("databases", {}).get(group["db_id"], {}).get("sha256")
    if not manifest_entry or manifest_entry != db_hash:
        raise ValueError("Frozen snapshot does not match the physical build manifest.")
    return {"canonical_sql": canonical_sql, "database_sha256": db_hash,
            "canonical_sql_sha256": sql_hash,
            "owner_status": current_group.get("ground_truth_review", "NEEDS_HUMAN_REVIEW")}


def score_demo_results(questions: list[dict[str, Any]], results: list[dict[str, Any]], canonical_rows: list[list[Any]], canonical_columns: list[str] | None = None, *, output_contract: dict[str, Any] | None = None) -> dict[str, Any]:
    """Score a demo run by named output fields; column order is not semantically significant."""
    ordered = sorted(questions, key=lambda item: item["q_index"])
    group_ids = {item["group_id"] for item in ordered}
    if len(group_ids) != 1 or len(ordered) != 11:
        raise ValueError("Demo scoring requires exactly one complete 11-question Semantic Group.")
    group_id = next(iter(group_ids))
    qids = [item["question_id"] for item in ordered]
    observations = {qid: Observation(INFRA_FAILURE) for qid in qids}
    run_status: dict[str, str] = {}
    predicted_rows: dict[str, list[list[Any]] | None] = {}
    predicted_columns: dict[str, list[str] | None] = {}
    comparisons: dict[str, dict[str, Any]] = {}
    expected_columns = list(canonical_columns or [])
    aliases = (output_contract or {}).get("aliases", GROUP_COLUMN_ALIASES.get(group_id, {}))
    for item in results:
        question = item.get("question", {})
        qid = question.get("question_id")
        if qid not in observations:
            continue
        if item.get("error"):
            status, rows, columns = "infra_error", None, None
        else:
            execution = item.get("run_result")
            if isinstance(execution, dict):
                if execution.get("truncated"):
                    status, rows, columns = "result_truncated", None, None
                else:
                    result = execution["result"]
                    rows, columns, status = [list(row) for row in result.rows], list(result.columns), "success"
            elif isinstance(execution, Timeout):
                status, rows, columns = "timeout", None, None
            elif isinstance(execution, SqlError):
                status, rows, columns = "sql_error", None, None
            elif item.get("reply") is not None and not item.get("sql"):
                status, rows, columns = "no_sql", None, None
            else:
                status, rows, columns = "infra_error", None, None
        run_status[qid] = status
        predicted_rows[qid] = rows
        predicted_columns[qid] = columns
        if status == "success":
            comparison = compare_named_results(rows or [], columns, canonical_rows, expected_columns, aliases)
            comparisons[qid] = comparison
            observations[qid] = Observation(
                status, rows, correct=comparison["correct"],
                comparison_rows=comparison.get("normalized_rows"),
                projection_valid=comparison.get("projection_valid"),
            )
        elif status in {"timeout", "sql_error", "no_sql"}:
            observations[qid] = Observation(status, correct=False)
        # Provider/infrastructure errors and display-truncated output stay UNKNOWN.

    qids_by_group = {group_id: qids}
    summary = metric_summary([group_id], qids_by_group, observations)
    details = []
    canonical_set = set(map(tuple, canonical_rows))
    canonical_columns = list(canonical_columns or [])
    for question in ordered:
        qid = question["question_id"]
        observation = observations[qid]
        rows = predicted_rows.get(qid)
        columns = predicted_columns.get(qid)
        comparison = comparisons.get(qid)
        normalized_rows = comparison.get("normalized_rows") if comparison else None
        predicted_set = set(map(tuple, normalized_rows)) if normalized_rows is not None else set()
        canonical_only = list(canonical_set - predicted_set) if rows is not None else []
        prediction_only = list(predicted_set - canonical_set) if rows is not None else []
        column_differences = (
            [{"position": None, "canonical": name, "generated": None, "kind": "missing"}
             for name in comparison.get("projection_missing", [])]
            + [{"position": None, "canonical": None, "generated": name, "kind": "extra"}
              for name in comparison.get("projection_extra", [])]
            + [{"position": None, "canonical": name, "generated": None, "kind": "duplicate"}
              for name in comparison.get("projection_duplicate_fields", [])]
        ) if comparison else []
        if comparison and not comparison.get("projection_valid"):
            canonical_only = []
            prediction_only = []
        details.append({"question_id": qid, "variant_type": question["variant_type"],
                        "status": run_status.get(qid, "not_run"), "known": observation.outcome_known,
                        "correct": observation.is_correct,
                        "row_count": len(rows) if rows is not None else None,
                        "canonical_row_count": len(canonical_rows),
                        "columns_match": comparison.get("projection_valid") if comparison else None,
                        "column_order_match": comparison.get("column_order_match") if comparison else None,
                        "projection_status": comparison.get("projection_status") if comparison else None,
                        "projection_missing": comparison.get("projection_missing", []) if comparison else [],
                        "projection_extra": comparison.get("projection_extra", []) if comparison else [],
                        "projection_duplicate_fields": comparison.get("projection_duplicate_fields", []) if comparison else [],
                        "aliases_applied": comparison.get("aliases_applied", []) if comparison else [],
                        "canonical_columns": canonical_columns,
                        "generated_columns": columns,
                        "column_differences": column_differences,
                        "canonical_only_rows": [list(row) for row in canonical_only[:50]],
                        "prediction_only_rows": [list(row) for row in prediction_only[:50]],
                        "canonical_only_count": len(canonical_only),
                        "prediction_only_count": len(prediction_only)})
    return {"metrics": summary, "questions": details, "canonical_row_count": len(canonical_rows),
            "canonical_columns": canonical_columns,
            "output_contract": output_contract,
            "comparator_version": COMPARATOR_VERSION,
            "evaluation_protocol_version": EVALUATION_PROTOCOL_VERSION,
            "run_question_count": len(results), "scoring_status": "DIAGNOSTIC_ONLY_OWNER_REVIEW_PENDING"}

def read_only_query(db_id: str, sql: str, *, timeout_s: float=DEMO_TIMEOUT_S, max_rows: int=MAX_DISPLAY_ROWS):
    if db_id not in {"erp_sales","wms_inventory"}: return SqlError("Unknown database")
    if not re.match(r"^\s*(SELECT|WITH)\b",sql,re.I): return SqlError("Chỉ chấp nhận một truy vấn SELECT/WITH")
    path=(PHYSICAL_DIR/f"{db_id}.sqlite").resolve()
    uri=path.as_uri()+"?mode=ro&immutable=1"
    conn=sqlite3.connect(uri,uri=True)
    allowed={sqlite3.SQLITE_SELECT,sqlite3.SQLITE_READ,sqlite3.SQLITE_FUNCTION,sqlite3.SQLITE_RECURSIVE}
    def authorize(action,arg1,arg2,db,trigger):
        if action in allowed:return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    start=time.monotonic();deadline=start+timeout_s
    conn.set_authorizer(authorize)
    conn.set_progress_handler(lambda: int(time.monotonic()>deadline),1000)
    try:
        cur=conn.execute(sql)
        rows=cur.fetchmany(max_rows+1)
        truncated=len(rows)>max_rows
        rows=rows[:max_rows]
        return {"result":Rows([c[0] for c in cur.description or []],rows),"elapsed_s":time.monotonic()-start,"truncated":truncated,"display_limit":max_rows}
    except sqlite3.Error as e:
        if time.monotonic()>deadline or "interrupted" in str(e).lower():return Timeout(timeout_s)
        return SqlError(str(e))
    finally:conn.close()

def schema_text(db_id):
    if db_id not in {"erp_sales","wms_inventory"}:raise ValueError("Unknown database")
    return (PHYSICAL_DIR/f"schema_{db_id}.sql").read_text(encoding="utf-8")


def output_contract_for(group: dict[str, Any]) -> dict[str, Any]:
    """Build field descriptions from canonical projection metadata without returning rows or SQL."""
    db_id = group.get("db_id")
    if db_id not in {"erp_sales", "wms_inventory"}:
        raise ValueError("Unknown database")
    sql = group.get("canonical_sql_draft") or group.get("canonical_sql")
    if not sql:
        raise ValueError(f"{group.get('group_id')}: canonical SQL candidate is missing")
    sql_hash = hashlib.sha256(sql.encode("utf-8")).hexdigest()
    card_hash = hashlib.sha256(json.dumps(group.get("card_fields"), ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    cache_key = (group["group_id"], sql_hash, card_hash)
    if cache_key in _OUTPUT_CONTRACT_CACHE:
        contract = deepcopy(_OUTPUT_CONTRACT_CACHE[cache_key])
    else:
        path = (PHYSICAL_DIR / f"{db_id}.sqlite").resolve()
        connection = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)
        try:
            cursor = connection.execute(f"SELECT * FROM ({sql}) AS benchmark_output_contract LIMIT 0")
            columns = [item[0] for item in cursor.description or []]
        finally:
            connection.close()
        contract = bind_output_contract(
            make_output_contract(group["group_id"], columns, group.get("card_fields")), group
        )
        _OUTPUT_CONTRACT_CACHE[cache_key] = deepcopy(contract)
    contract["owner_review_status"] = bind_output_contract(
        {key: value for key, value in contract.items() if key != "owner_review_status"}, group
    )["owner_review_status"]
    return contract


# Human-readable field names are added to the model context without renaming
# frozen SQLite columns or changing the benchmark snapshots.
FIELD_TERMINOLOGY = {
    "erp_sales": [
        "CUSTOMERS.customer_id: ID nội bộ duy nhất của khách hàng, dùng để liên kết bảng; không phải mã khách hàng hiển thị.",
        "CUSTOMERS.customer_code: mã khách hàng nghiệp vụ, dùng khi yêu cầu mã khách hàng.",
        "EMPLOYEES.employee_id: ID nội bộ của nhân viên; EMPLOYEES.employee_code: mã nhân viên nghiệp vụ. SALES_ORDERS.sales_rep_id lưu employee_id của người phụ trách, không phải employee_code.",
        "PRODUCTS.product_id: ID nội bộ của sản phẩm; PRODUCTS.sku: mã SKU của sản phẩm. Không dùng hai trường thay thế cho nhau.",
        "SALES_ORDERS.order_id: ID nội bộ của đơn hàng; SALES_ORDERS.order_no: số đơn hàng hiển thị/nghiệp vụ. Nếu yêu cầu cả mã định danh và số đơn, trả lần lượt order_id và order_no.",
        "SALES_ORDER_LINES.order_line_id: ID nội bộ của dòng đơn; line_no: số thứ tự dòng trong đơn; product_id là khóa liên kết đến PRODUCTS.product_id.",
        "SALES_SHIPMENTS.shipment_id: ID nội bộ của lần giao; shipment_no: số phiếu giao.",
        "SALES_RETURNS.return_id: ID nội bộ của lần trả hàng; return_no: số phiếu trả.",
        "PAYMENT_TRANSACTIONS.payment_txn_id: ID nội bộ giao dịch; transaction_ref: mã tham chiếu giao dịch, không phải order_id.",
        "PRODUCT_CATEGORIES.category_id là ID nội bộ danh mục; schema không có category_code.",
    ],
    "wms_inventory": [
        "CUSTOMERS.customer_id: ID nội bộ duy nhất của khách hàng, dùng để liên kết bảng; CUSTOMERS.customer_code: mã khách hàng nghiệp vụ.",
        "SUPPLIERS.supplier_id: ID nội bộ nhà cung cấp; SUPPLIERS.supplier_code: mã nhà cung cấp nghiệp vụ.",
        "PRODUCTS.product_id: ID nội bộ của sản phẩm; PRODUCTS.sku: mã SKU của sản phẩm. Không dùng hai trường thay thế cho nhau.",
        "WAREHOUSES.warehouse_id: ID nội bộ kho; WAREHOUSES.warehouse_code: mã kho nghiệp vụ.",
        "LOCATIONS.location_id: ID nội bộ vị trí; LOCATIONS.location_code: mã vị trí trong kho.",
        "INVENTORY_DOCUMENTS.document_id: ID nội bộ chứng từ; document_no: số chứng từ hiển thị/nghiệp vụ. Nếu yêu cầu cả mã định danh và số chứng từ, trả lần lượt document_id và document_no.",
        "INVENTORY_DOCUMENT_LINES.document_line_id: ID nội bộ dòng chứng từ; line_no: số thứ tự dòng; product_id là khóa liên kết đến PRODUCTS.product_id.",
        "INVENTORY_MOVEMENTS.movement_id: ID nội bộ biến động; movement_leg_no: số thứ tự nhánh biến động; source_movement_ref là tham chiếu nguồn, không phải mã chứng từ.",
        "PRODUCT_CATEGORIES.category_id là ID nội bộ danh mục; schema không có category_code.",
    ],
}


def prompt_for(question, db_id, business_rules, glossary, output_contract=None):
    if isinstance(glossary,dict): terms="\n".join(f"- {k}: {v}" for k,v in glossary.items())
    else: terms="\n".join(f"- {item.get('vi')}: {item.get('technical')}" for item in glossary)
    field_terms="\n".join(f"- {item}" for item in FIELD_TERMINOLOGY[db_id])
    contract_text = "Không có hợp đồng trường đầu ra cho câu hỏi này."
    if output_contract:
        contract_lines = [f"- {item['column']}: {item['meaning']}" for item in output_contract.get("fields", [])]
        contract_text = (
            f"Semantic Group: {output_contract.get('group_id', 'unknown')}\n"
            f"Output field contract review: {output_contract.get('owner_review_status', 'PENDING')}\n"
            f"Trạng thái: {output_contract.get('status', 'unknown')}\n"
            "Tập trường bắt buộc (không phụ thuộc thứ tự cột):\n"
            + "\n".join(contract_lines)
            + "\nTrả đúng tập trường này, không thiếu và không thêm trường khác. "
            "Ưu tiên dùng đúng tên trường chuẩn đã liệt kê."
        )
    return (
        f"{schema_text(db_id)}\n\n"
        f"Quy tắc nghiệp vụ mô phỏng: {business_rules}\n\n"
        f"Thuật ngữ nghiệp vụ:\n{terms}\n\n"
        f"Phân biệt tên trường và cách gọi:\n{field_terms}\n\n"
        f"Hợp đồng trường đầu ra của Intent:\n{contract_text}\n\n"
        "Quy tắc chọn trường: tên cột trong lược đồ là tên vật lý cần dùng trong SQL. "
        "Các cột có hậu tố _id là ID nội bộ/khóa liên kết; các cột *_code hoặc sku là mã nghiệp vụ; "
        "các cột *_no là số chứng từ/đơn hiển thị. Riêng trong bộ dữ liệu này, khi câu hỏi yêu cầu đồng thời ‘mã sản phẩm’ và ‘SKU’, "
        "mã sản phẩm là product_id còn SKU là sku; khi yêu cầu ‘mã đơn hàng’ và ‘số đơn hàng’, lần lượt là order_id và order_no; "
        "khi yêu cầu ‘mã chứng từ’ và ‘số chứng từ’, lần lượt là document_id và document_no. "
        "Không thay ID bằng mã, mã bằng ID, hoặc số chứng từ bằng ID. "
        "Nếu câu hỏi yêu cầu cả hai khái niệm, hãy chọn cả hai cột tương ứng. Dựa vào nghĩa được yêu cầu, "
        "không suy luận rằng từ tiếng Việt chung chung ‘mã’ luôn đồng nghĩa với *_id.\n\n"
        f"Câu hỏi: {question}\n"
        "Chỉ trả về đúng một câu lệnh SQL SQLite hợp lệ bắt đầu bằng SELECT hoặc WITH. "
        "Không kèm giải thích, không đưa phương án khác và không dùng nhiều khối mã Markdown."
    )


def prompt_contract_sha256() -> str:
    """Hash prompt logic, fixed terminology, and field-contract definitions."""
    contract_module = Path(__file__).with_name("field_contracts.py")
    material = "\n".join((
        inspect.getsource(schema_text),
        inspect.getsource(prompt_for),
        inspect.getsource(output_contract_for),
        json.dumps(FIELD_TERMINOLOGY, ensure_ascii=False, sort_keys=True),
        sha256_file(contract_module),
    ))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def run_demo_question(question, db_id, business_rules, glossary, model, *, temperature=0, max_tokens=1024, complete_fn=None, output_contract=None):
    """One explicit, injectable demo inference and read-only SQL execution."""
    if complete_fn is None:
        from bird_demo.llm import complete
        complete_fn=complete
    prompt=prompt_for(question,db_id,business_rules,glossary,output_contract=output_contract)
    started=time.monotonic()
    try:
        reply=complete_fn(prompt,model,temperature=temperature,max_tokens=max_tokens)
    except Exception as exc:
        return {"prompt":prompt,"elapsed_s":time.monotonic()-started,"error":str(exc),"sql":None,"reply":None,"execution":None}
    sql=extract_sql(reply)
    execution=read_only_query(db_id,sql) if sql else None
    return {"prompt":prompt,"elapsed_s":time.monotonic()-started,"error":None,"sql":sql,"reply":reply,"execution":execution}


def _export_execution(outcome):
    if isinstance(outcome, dict):
        result = outcome.get("result")
        return {
            "status": "success",
            "elapsed_seconds": outcome.get("elapsed_s"),
            "truncated": bool(outcome.get("truncated", False)),
            "display_limit": outcome.get("display_limit"),
            "columns": list(result.columns) if result is not None else [],
            "row_count": len(result.rows) if result is not None else 0,
            "rows": [list(row) for row in result.rows] if result is not None else [],
        }
    if isinstance(outcome, Timeout):
        return {"status": "timeout", "timeout_seconds": outcome.timeout_s}
    if isinstance(outcome, SqlError):
        return {"status": "sql_error", "error": outcome.message}
    return {"status": "not_executed", "rows": [], "columns": [], "row_count": None}


def export_demo_run(run_record: dict[str, Any]) -> str:
    """Serialize one interactive run, including prompts, returned reasoning and all result rows."""
    exported_questions = []
    for item in run_record.get("results", []):
        question = item.get("question", {})
        reply = item.get("reply")
        exported_questions.append({
            "question_id": question.get("question_id"),
            "variant_type": question.get("variant_type"),
            "question": question.get("question"),
            "prompt_sent": item.get("prompt"),
            "generated_sql": item.get("sql"),
            "llm_response": getattr(reply, "text", None),
            "reasoning_returned_by_provider": getattr(reply, "reasoning", None),
            "finish_reason": getattr(reply, "finish_reason", None),
            "llm_elapsed_seconds": item.get("elapsed"),
            "provider_error": item.get("error"),
            "execution": _export_execution(item.get("run_result")),
        })

    canonical_execution = run_record.get("canonical_execution")
    if isinstance(canonical_execution, dict):
        canonical_payload = _export_execution(canonical_execution)
    elif isinstance(canonical_execution, Timeout):
        canonical_payload = {"status": "timeout", "timeout_seconds": canonical_execution.timeout_s}
    elif isinstance(canonical_execution, SqlError):
        canonical_payload = {"status": "sql_error", "error": canonical_execution.message}
    else:
        canonical_payload = {"status": "not_executed"}

    payload = {
        "artifact_type": "bird_vn_interactive_demo_run",
        "run_at_unix_seconds": run_record.get("run_at"),
        "group_id": run_record.get("group_id"),
        "db_id": run_record.get("db_id"),
        "model": run_record.get("model"),
        "mode": run_record.get("mode"),
        "temperature": run_record.get("temperature"),
        "max_tokens": run_record.get("max_tokens"),
        "output_contract": run_record.get("output_contract"),
        "canonical_sql": run_record.get("canonical_sql"),
        "canonical_execution": canonical_payload,
        "metrics_diagnostic_only": run_record.get("score"),
        "questions": exported_questions,
        "notes": [
            "Reasoning is included only when the provider returned it.",
            "Interactive demo output is diagnostic and is not an official evaluation record.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def visible_run_artifact(artifact: dict[str,Any], registry: dict[str,Any], *, owner: bool) -> dict[str,Any]:
    """Return a detached payload with Final predictions/results removed for ordinary sessions."""
    payload=json.loads(json.dumps(artifact,ensure_ascii=False))
    if owner:return payload
    dev_groups={g["group_id"] for g in registry["groups"] if g.get("split")=="development"}
    dev_qids={q["question_id"] for q in registry["questions"] if q.get("split")=="development"}
    payload["question_records"]=[r for r in payload.get("question_records",[]) if r.get("question_id") in dev_qids or r.get("group_id") in dev_groups]
    payload["group_records"]={k:v for k,v in payload.get("group_records",{}).items() if k in dev_groups}
    if isinstance(payload.get("metrics_by_split"),dict):payload["metrics_by_split"]={k:v for k,v in payload["metrics_by_split"].items() if k=="development"}
    for key in ("metrics_by_group","group_metrics"):
        if isinstance(payload.get(key),dict):payload[key]={k:v for k,v in payload[key].items() if k in dev_groups}
    return payload


def compare_demo_q00_variants(results: list[dict[str,Any]], *, expected_variant_count: int | None=None, output_contract: dict[str, Any] | None=None) -> dict[str,Any]:
    """Compare Q00 and variants after aligning their columns to the Intent field contract."""
    def outcome(record):
        if record is None:return "NOT_RUN",None,None
        if record.get("error"):return "INFRA_ERROR",None,None
        if record.get("reply") is not None and not record.get("sql"):return "NO_SQL",None,None
        execution=record.get("run_result")
        if isinstance(execution,dict):
            if execution.get("truncated"):return "RESULT_TRUNCATED",None,None
            result=execution["result"]
            return "SUCCESS",result.rows,result.columns
        if isinstance(execution,Timeout):return "TIMEOUT",None,None
        if isinstance(execution,SqlError):return "SQL_ERROR",None,None
        if record.get("reply") is None:return "NOT_RUN",None,None
        return "NO_SQL",None,None

    by_index={r["question"].get("q_index"):r for r in results if r.get("question")}
    q0=by_index.get(0)
    total=expected_variant_count if expected_variant_count is not None else max(0,len([i for i in by_index if isinstance(i,int) and i>0]))
    if q0 is None:
        return {"rss_numerator":0,"rss_denominator":0,"rss_percent":None,"expected_pairs":total,"known_pairs":0,"pairs":[],"reason":"Q00 was not run"}
    q0_status,q0_rows,q0_columns=outcome(q0);pairs=[]
    expected_columns = (output_contract or {}).get("columns")
    aliases = (output_contract or {}).get("aliases", GROUP_COLUMN_ALIASES.get(q0["question"].get("group_id"), {}))
    q0_aligned = align_result(q0_rows or [],q0_columns,expected_columns,aliases) if expected_columns else None
    for index in range(1,total+1):
        variant=by_index.get(index);status,rows,columns=outcome(variant)
        known=q0_status not in {"INFRA_ERROR","NOT_RUN","RESULT_TRUNCATED"} and status not in {"INFRA_ERROR","NOT_RUN","RESULT_TRUNCATED"}
        aligned=align_result(rows or [],columns,expected_columns,aliases) if expected_columns else None
        if known and q0_status=="SUCCESS" and status=="SUCCESS":
            if expected_columns:
                stable=bool(q0_aligned and aligned and q0_aligned["valid"] and aligned["valid"] and result_equal(q0_aligned["rows"],aligned["rows"]))
            else:
                stable=result_equal(q0_rows or [],rows or [])
        else:
            stable=False if known else None
        q0_only=[];variant_only=[]
        if q0_status=="SUCCESS" and status=="SUCCESS":
            compare_q0=q0_aligned.get("rows") if q0_aligned and q0_aligned.get("valid") else q0_rows
            compare_variant=aligned.get("rows") if aligned and aligned.get("valid") else rows
            q0_set=set(map(tuple,compare_q0 or []));variant_set=set(map(tuple,compare_variant or []))
            q0_only=[list(row) for row in q0_set-variant_set][:50]
            variant_only=[list(row) for row in variant_set-q0_set][:50]
        pairs.append({"question_id":variant["question"]["question_id"] if variant else f"Q{index:02d}","q00_status":q0_status,"variant_status":status,"known":known,"stable":stable,
                      "q00_projection_status":q0_aligned.get("status") if q0_aligned else "legacy_rows_only",
                      "variant_projection_status":aligned.get("status") if aligned else "legacy_rows_only",
                      "q00_only_count":len(q0_only),"variant_only_count":len(variant_only),"q00_only_rows":q0_only,"variant_only_rows":variant_only})
    known_pairs=[p for p in pairs if p["known"]]
    numerator=sum(p["stable"] is True for p in known_pairs);denominator=len(known_pairs)
    return {"rss_numerator":numerator,"rss_denominator":denominator,"rss_percent":100*numerator/denominator if denominator else None,"expected_pairs":total,"known_pairs":denominator,"pairs":pairs,"reason":None if denominator else "No Q00?Qi pairs have known, complete execution results"}


def q00_pair_stability(results: list[dict[str,Any]], output_contract: dict[str, Any] | None=None) -> list[dict[str,Any]]:
    """Backward-compatible known Q00?Qi pair outcomes for analysis views."""
    comparison=compare_demo_q00_variants(results,output_contract=output_contract)
    q00_id=next((item.get("question",{}).get("question_id") for item in results
                 if item.get("question",{}).get("q_index")==0), "Q00")
    return [{"Pair":f"{q00_id} vs {p['question_id']}","Rows stable":p["stable"],"Q00 projection":p["q00_projection_status"],"Variant projection":p["variant_projection_status"]}
            for p in comparison["pairs"] if p["known"]]
