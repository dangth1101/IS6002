from pathlib import Path
from bird_demo.benchmark import dashboard
from bird_demo.benchmark.dashboard import read_registry, visible_groups, read_only_query, run_demo_question, load_audit, load_similarity, visible_run_artifact, q00_pair_stability
from bird_demo.llm import Reply
from bird_demo.runner import Rows, SqlError, Timeout

def test_registry_scope_and_question_counts():
    registry=read_registry()
    assert len(registry["groups"])==50 and len(registry["questions"])==550
    assert len(visible_groups(registry))==10
    assert sum(len([q for q in registry["questions"] if q["group_id"]==g["group_id"]]) for g in visible_groups(registry))==110
    assert all(len([q for q in registry["questions"] if q["group_id"]==g["group_id"]])==11 for g in visible_groups(registry))

def test_sbert_artifact_has_current_lineage_and_real_pairs():
    summary,status=load_audit()
    assert status=="CURRENT"
    assert summary["q00_variant_pairs_computed"]==500
    rows=load_similarity()
    assert len(rows)==500
    assert all(0<=float(row["cosine_similarity"])<=1.00001 for row in rows)

def test_final_is_excluded_from_default_explorer():
    registry=read_registry()
    assert {g["split"] for g in visible_groups(registry)}=={"development"}
    assert len(visible_groups(registry,include_final=True))==50

def test_sql_runner_is_read_only_and_rejects_multiple_statements():
    db="erp_sales"
    before=read_only_query(db,"SELECT count(*) AS n FROM SALES_ORDERS")["result"].rows[0][0]
    denied=read_only_query(db,"DELETE FROM SALES_ORDERS")
    assert isinstance(denied,SqlError)
    cte=read_only_query(db,"WITH x AS (SELECT 1) DELETE FROM SALES_ORDERS")
    assert isinstance(cte,SqlError)
    multi=read_only_query(db,"SELECT 1; SELECT 2")
    assert isinstance(multi,SqlError)
    after=read_only_query(db,"SELECT count(*) AS n FROM SALES_ORDERS")["result"].rows[0][0]
    assert before==after

def test_sql_runner_caps_rows_and_times_out():
    capped=read_only_query("erp_sales","SELECT order_id FROM SALES_ORDERS",max_rows=2)
    assert capped["truncated"] and len(capped["result"].rows)==2
    timed=read_only_query("erp_sales","WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<10000000) SELECT max(x) FROM n",timeout_s=0.001)
    assert isinstance(timed,Timeout)

def test_mock_provider_success_and_failure_do_not_need_api(monkeypatch):
    registry=read_registry();group=next(g for g in registry["groups"] if g["split"]=="development")
    question=next(q for q in registry["questions"] if q["group_id"]==group["group_id"])
    def success(prompt,model,**kwargs):
        assert "CREATE TABLE" in prompt
        assert kwargs=={"temperature":0.2,"max_tokens":42}
        return Reply("```sql\nSELECT 1 AS demo\n```","stop")
    ok=run_demo_question(question["question"],group["db_id"],group["card_fields"]["business_rules"],registry["semantic_glossary"],"mock/model",temperature=.2,max_tokens=42,complete_fn=success)
    assert ok["sql"]=="SELECT 1 AS demo" and isinstance(ok["execution"]["result"],Rows)
    bad=run_demo_question(question["question"],group["db_id"],group["card_fields"]["business_rules"],registry["semantic_glossary"],"mock/model",complete_fn=lambda *a,**k: (_ for _ in ()).throw(RuntimeError("mock offline failure")))
    assert "mock offline failure" in bad["error"] and bad["execution"] is None

def test_owner_access_requires_server_token(monkeypatch):
    monkeypatch.delenv("BIRD_VN_OWNER_TOKEN",raising=False)
    assert not dashboard.owner_access_granted("anything")
    monkeypatch.setenv("BIRD_VN_OWNER_TOKEN","owner-secret")
    assert dashboard.owner_access_granted("owner-secret")
    assert not dashboard.owner_access_granted("wrong")

def test_existing_llm_client_receives_demo_generation_controls(monkeypatch):
    from bird_demo import llm
    class Choice:
        message=type("Message",(),{"content":"SELECT 1"})()
        finish_reason="stop"
    class FakeCompletions:
        def create(self,**kwargs):
            captured.update(kwargs)
            return type("Response",(),{"choices":[Choice()]})()
    class FakeClient:
        chat=type("Chat",(),{"completions":FakeCompletions()})()
    captured={};monkeypatch.setattr(llm,"client",lambda:FakeClient())
    reply=llm.complete("prompt","mock/model",temperature=0.4,max_tokens=77)
    assert reply.text=="SELECT 1" and captured["temperature"]==0.4 and captured["max_tokens"]==77

def test_run_artifact_hides_final_records_without_owner():
    import json
    registry=read_registry()
    artifact=json.loads((Path("benchmark_data/runs/offline_smoke.json")).read_text(encoding="utf-8"))
    filtered=visible_run_artifact(artifact,registry,owner=False)
    assert len(filtered["question_records"])==110
    assert all(record["split"]=="development" for record in filtered["question_records"])
    assert len(filtered["group_records"])==10 and set(filtered["metrics_by_split"])=={"development"}
    assert len(artifact["question_records"])==550  # source artifact remains untouched
    assert len(visible_run_artifact(artifact,registry,owner=True)["question_records"])==550

def test_demo_stability_uses_q00_variant_pairs_only():
    def result(qid,index,rows):return {"question":{"question_id":qid,"q_index":index},"sql":"SELECT 1","run_result":{"result":type("Rows",(),{"rows":rows})()}}
    rows=[result("G-Q00",0,[(1,)]),result("G-Q01",1,[(1,)]),result("G-Q02",2,[(2,)]) ]
    pairs=q00_pair_stability(rows)
    assert pairs==[{"Pair":"G-Q00 vs G-Q01","Rows stable":True},{"Pair":"G-Q00 vs G-Q02","Rows stable":False}]
    assert q00_pair_stability(rows[1:])==[]


def test_pinned_hash_ignores_line_endings_but_not_content(tmp_path):
    import hashlib
    from bird_demo.benchmark.registry import file_matches_sha256
    sha = lambda b: hashlib.sha256(b).hexdigest()
    text = tmp_path / "artifact.json"
    text.write_bytes(b'{\n  "a": 1\n}\n')
    assert file_matches_sha256(text, sha(b'{\n  "a": 1\n}\n'))
    assert file_matches_sha256(text, sha(b'{\r\n  "a": 1\r\n}\r\n'))  # pinned on a Windows checkout
    assert not file_matches_sha256(text, sha(b'{\n  "a": 2\n}\n'))
    assert not file_matches_sha256(tmp_path / "missing.json", sha(b""))
    binary = tmp_path / "db.sqlite"
    binary.write_bytes(b"\0\r\n")
    assert not file_matches_sha256(binary, sha(b"\0\n"))
