import pytest
from bird_demo.benchmark.official import (OfficialGate,TransientInfrastructureError, PermanentProviderError, collect_one, collect_three_replicates, execute_official_sql, OFFICIAL_SQL_TIMEOUT_S)
import hashlib
import json
from pathlib import Path
from bird_demo.benchmark.release import release_readiness

ROOT = Path(__file__).resolve().parents[1]

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


def test_frozen_final_release_binds_three_replicate_offline_integration():
    base = ROOT / "benchmark_data/official"
    frozen = json.loads((base / "frozen_registry_manifest.json").read_text(encoding="utf-8"))
    config = json.loads((base / "frozen_config.json").read_text(encoding="utf-8"))
    smoke = json.loads((base / "implementation_validation.json").read_text(encoding="utf-8"))
    assert frozen["status"] == "FROZEN_FOR_FINAL_EVALUATION"
    readiness = release_readiness(ROOT)
    assert readiness["registry_ready"] and readiness["config_ready"] and readiness["freeze_integrity_ready"]
    assert readiness["d8_ready"] and readiness["d9_ready"] and readiness["d13_ready"]
    assert readiness["official_run_authorized"] is False
    assert readiness["ready_for_official_run"] is False
    assert frozen["official_api_calls_authorized"] is False
    assert config["evaluation_split"] == "final" and config["replicates"] == 3
    assert config["official_api_calls_authorized"] is False
    assert smoke["validation_type"] == "OFFLINE_MOCK_IMPLEMENTATION_SMOKE"
    assert smoke["empirical_result"] is False and smoke["api_called"] is False
    assert smoke["replicate_count"] == 3
    assert smoke["questions_per_replicate"] == 440
    assert smoke["prediction_records_total"] == 1320
    assert all(run["execution_records"] == 440 and run["all_results_match_canonical"]
               and (ROOT / run["artifact_path"]).is_file()
               and hashlib.sha256((ROOT / run["artifact_path"]).read_bytes()).hexdigest() == run["artifact_sha256"]
               for run in smoke["runs"])
    for relative_path, expected_hash in frozen["integrity_files_sha256"].items():
        actual_hash = hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
        assert actual_hash == expected_hash, relative_path
