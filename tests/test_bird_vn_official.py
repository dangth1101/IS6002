import pytest
from bird_demo.benchmark.official import (OfficialGate,TransientInfrastructureError, PermanentProviderError, collect_one, collect_three_replicates, execute_official_sql, OFFICIAL_SQL_TIMEOUT_S)

def ready_gate(): return OfficialGate(True,True,True,True)
def test_official_gate_blocks_before_provider_call():
    called=[]
    with pytest.raises(PermissionError):collect_three_replicates([],"m",{},lambda q:"",lambda *a:called.append(1),gate=OfficialGate(False,False,False,False))
    assert not called

def test_protocol_runs_exactly_three_complete_replicates():
    questions=[{"question_id":f"Q{i}"} for i in range(2)];calls=[]
    result=collect_three_replicates(questions,"mock/model",{"temperature":0},lambda q:q["question_id"],lambda prompt,model,config:(calls.append((prompt,model,config)) or "SELECT 1"),gate=ready_gate())
    assert result["replicate_ids"]==[1,2,3] and [r["question_count"] for r in result["replicates"]]==[2,2,2]
    assert len(calls)==6 and result["timeout_s"]==30
    assert [r["replicate_id"] for r in result["replicates"][2]["records"]]==[3,3]

def test_only_transient_infrastructure_errors_retry_twice():
    attempts=[]
    def transient(*args):
        attempts.append(1)
        if len(attempts)<3:raise TransientInfrastructureError("network")
        return "response"
    waits=[]
    out=collect_one({"question_id":"Q"},"prompt","m",{},transient,sleep_fn=waits.append)
    assert out["status"]=="RESPONSE_RECEIVED" and len(out["attempts"])==3 and waits==[1,2]
    attempts.clear()
    def permanent(*args):attempts.append(1);raise PermanentProviderError("invalid request")
    out=collect_one({"question_id":"Q"},"prompt","m",{},permanent)
    assert out["status"]=="UNKNOWN" and len(attempts)==1 and len(out["attempts"])==1
    assert OFFICIAL_SQL_TIMEOUT_S==30

def test_official_sql_timeout_is_fixed_and_never_retried():
    calls=[]
    def fake_runner(path,sql,*,timeout_s):calls.append(timeout_s);return __import__("bird_demo.runner",fromlist=["Timeout"]).Timeout(timeout_s)
    from pathlib import Path
    out=execute_official_sql(Path("db.sqlite"),"SELECT 1",runner=fake_runner)
    assert out["status"]=="timeout" and calls==[30.0] and out["attempts"]==1
    empty=execute_official_sql(Path("db.sqlite"),None,runner=fake_runner)
    assert empty["status"]=="no_sql" and len(calls)==1
