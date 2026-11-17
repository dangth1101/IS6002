"""Read-only BIRD-VN dashboard data and safe interactive SQL helpers."""
from __future__ import annotations
import csv, hashlib, hmac, json, os, re, sqlite3, time
from pathlib import Path
from typing import Any
from bird_demo.data import ROOT
from bird_demo.benchmark.registry import file_matches_sha256, load_registry, sha256_file
from bird_demo.runner import Rows, SqlError, Timeout
from bird_demo.benchmark.metrics import result_equal
from bird_demo.benchmark.metrics import INFRA_FAILURE, Observation, metric_summary
from bird_demo.prompt import extract_sql
from bird_demo.llm import Reply

REGISTRY_PATH = ROOT / "benchmark_data/authoring/dataset.json"
AUDIT_DIR = ROOT / "docs/benchmark/review/full_semantic_validation_sbert"
PHYSICAL_DIR = ROOT / "benchmark_data/physical"
MAX_DISPLAY_ROWS = 500
DEMO_TIMEOUT_S = 30

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


def score_demo_results(questions: list[dict[str, Any]], results: list[dict[str, Any]], canonical_rows: list[list[Any]], canonical_columns: list[str] | None = None) -> dict[str, Any]:
    """Score one interactive run against canonical rows and report output-schema differences."""
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
            observations[qid] = Observation(status, rows, correct=result_equal(rows, canonical_rows))
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
        predicted_set = set(map(tuple, rows)) if rows is not None else set()
        canonical_only = list(canonical_set - predicted_set) if rows is not None else []
        prediction_only = list(predicted_set - canonical_set) if rows is not None else []
        column_differences = []
        if columns is not None:
            for index in range(max(len(canonical_columns), len(columns))):
                gold_name = canonical_columns[index] if index < len(canonical_columns) else None
                generated_name = columns[index] if index < len(columns) else None
                if gold_name != generated_name:
                    column_differences.append({"position": index + 1, "canonical": gold_name, "generated": generated_name})
        details.append({"question_id": qid, "variant_type": question["variant_type"],
                        "status": run_status.get(qid, "not_run"), "known": observation.outcome_known,
                        "correct": observation.is_correct,
                        "row_count": len(rows) if rows is not None else None,
                        "canonical_row_count": len(canonical_rows),
                        "columns_match": columns == canonical_columns if columns is not None else None,
                        "canonical_columns": canonical_columns,
                        "generated_columns": columns,
                        "column_differences": column_differences,
                        "canonical_only_rows": [list(row) for row in canonical_only[:50]],
                        "prediction_only_rows": [list(row) for row in prediction_only[:50]],
                        "canonical_only_count": len(canonical_only),
                        "prediction_only_count": len(prediction_only)})
    return {"metrics": summary, "questions": details, "canonical_row_count": len(canonical_rows),
            "canonical_columns": canonical_columns,
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

def prompt_for(question, db_id, business_rules, glossary):
    if isinstance(glossary,dict): terms="\n".join(f"- {k}: {v}" for k,v in glossary.items())
    else: terms="\n".join(f"- {item.get('vi')}: {item.get('technical')}" for item in glossary)
    return f"{schema_text(db_id)}\n\nBusiness rules (synthetic): {business_rules}\n\nGlossary:\n{terms}\n\nQuestion (Vietnamese): {question}\nUse valid SQLite. Return one SELECT or WITH query only."


def run_demo_question(question, db_id, business_rules, glossary, model, *, temperature=0, max_tokens=1024, complete_fn=None):
    """One explicit, injectable demo inference and read-only SQL execution."""
    if complete_fn is None:
        from bird_demo.llm import complete
        complete_fn=complete
    prompt=prompt_for(question,db_id,business_rules,glossary)
    started=time.monotonic()
    try:
        reply=complete_fn(prompt,model,temperature=temperature,max_tokens=max_tokens)
    except Exception as exc:
        return {"prompt":prompt,"elapsed_s":time.monotonic()-started,"error":str(exc),"sql":None,"reply":None,"execution":None}
    sql=extract_sql(reply)
    execution=read_only_query(db_id,sql) if sql else None
    return {"prompt":prompt,"elapsed_s":time.monotonic()-started,"error":None,"sql":sql,"reply":reply,"execution":execution}


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


def compare_demo_q00_variants(results: list[dict[str,Any]], *, expected_variant_count: int | None=None) -> dict[str,Any]:
    """Compare executed variant rows with Q00; failed/truncated pairs are not scored as stable."""
    def outcome(record):
        if record is None:return "NOT_RUN",None
        if record.get("error"):return "INFRA_ERROR",None
        if record.get("reply") is not None and not record.get("sql"):return "NO_SQL",None
        execution=record.get("run_result")
        if isinstance(execution,dict):
            if execution.get("truncated"):return "RESULT_TRUNCATED",None
            return "SUCCESS",execution["result"].rows
        if isinstance(execution,Timeout):return "TIMEOUT",None
        if isinstance(execution,SqlError):return "SQL_ERROR",None
        if record.get("reply") is None:return "NOT_RUN",None
        return "NO_SQL",None

    by_index={r["question"].get("q_index"):r for r in results if r.get("question")}
    q0=by_index.get(0)
    total=expected_variant_count if expected_variant_count is not None else max(0,len([i for i in by_index if isinstance(i,int) and i>0]))
    if q0 is None:
        return {"rss_numerator":0,"rss_denominator":0,"rss_percent":None,"expected_pairs":total,"known_pairs":0,"pairs":[],"reason":"Q00 was not run"}
    q0_status,q0_rows=outcome(q0);pairs=[]
    for index in range(1,total+1):
        variant=by_index.get(index);status,rows=outcome(variant)
        known=q0_status not in {"INFRA_ERROR","NOT_RUN","RESULT_TRUNCATED"} and status not in {"INFRA_ERROR","NOT_RUN","RESULT_TRUNCATED"}
        stable=bool(q0_status=="SUCCESS" and status=="SUCCESS" and result_equal(q0_rows or [],rows or [])) if known else None
        q0_only=[];variant_only=[]
        if q0_status=="SUCCESS" and status=="SUCCESS":
            q0_set=set(map(tuple,q0_rows or []));variant_set=set(map(tuple,rows or []))
            q0_only=[list(row) for row in q0_set-variant_set][:50]
            variant_only=[list(row) for row in variant_set-q0_set][:50]
        pairs.append({"question_id":variant["question"]["question_id"] if variant else f"Q{index:02d}","q00_status":q0_status,"variant_status":status,"known":known,"stable":stable,"q00_only_count":len(q0_only),"variant_only_count":len(variant_only),"q00_only_rows":q0_only,"variant_only_rows":variant_only})
    known_pairs=[p for p in pairs if p["known"]]
    numerator=sum(p["stable"] is True for p in known_pairs);denominator=len(known_pairs)
    return {"rss_numerator":numerator,"rss_denominator":denominator,"rss_percent":100*numerator/denominator if denominator else None,"expected_pairs":total,"known_pairs":denominator,"pairs":pairs,"reason":None if denominator else "No Q00?Qi pairs have known, complete execution results"}


def q00_pair_stability(results: list[dict[str,Any]]) -> list[dict[str,Any]]:
    """Backward-compatible known Q00?Qi pair outcomes for analysis views."""
    comparison=compare_demo_q00_variants(results)
    q00_id=next((item.get("question",{}).get("question_id") for item in results
                 if item.get("question",{}).get("q_index")==0), "Q00")
    return [{"Pair":f"{q00_id} vs {p['question_id']}","Rows stable":p["stable"]}
            for p in comparison["pairs"] if p["known"]]
