"""Protocol-constrained official prediction collector. Never invoked by the UI implicitly."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Any
import hashlib
import time
from openai import OpenAI, APIConnectionError, APITimeoutError, RateLimitError, InternalServerError
from bird_demo.llm import env
from bird_demo.runner import run, Rows, SqlError, Timeout
from bird_demo.benchmark.dashboard import output_contract_for, prompt_for

OFFICIAL_SQL_TIMEOUT_S=30.0
REPLICATE_IDS=(1,2,3)
MAX_TRANSIENT_ATTEMPTS=3  # initial attempt plus at most two retries


def make_bird_vn_prompt_builder(registry: dict) -> Callable[[dict], str]:
    """Build the same contract-aware prompt for every Q in a Semantic Group."""
    groups = {group["group_id"]: group for group in registry["groups"]}
    glossary = registry.get("semantic_glossary", {})

    def build(question: dict) -> str:
        group = groups.get(question.get("group_id"))
        if group is None:
            raise ValueError(f"Unknown Semantic Group for {question.get('question_id')!r}")
        if question.get("db_id") != group.get("db_id"):
            raise ValueError(f"Database mismatch for {question.get('question_id')!r}")
        contract = output_contract_for(group)
        return prompt_for(
            question["question"],
            question["db_id"],
            group["card_fields"]["business_rules"],
            glossary,
            output_contract=contract,
        )

    return build

class TransientInfrastructureError(RuntimeError): """Provider/network failure eligible for bounded retry."""
class PermanentProviderError(RuntimeError): """Bad request/auth/config failure; never retry."""

@dataclass(frozen=True)
class OfficialGate:
    registry_approved_and_frozen: bool
    prompt_model_config_frozen: bool
    collector_pipeline_tested: bool
    explicit_owner_confirmation: bool
    def ready(self):
        return all((self.registry_approved_and_frozen,self.prompt_model_config_frozen,self.collector_pipeline_tested,self.explicit_owner_confirmation))
    def blockers(self):
        names=("registry_approved_and_frozen","prompt_model_config_frozen","collector_pipeline_tested","explicit_owner_confirmation")
        return [name for name in names if not getattr(self,name)]

def collect_one(question: dict, prompt: str, model_id: str, config: dict, provider: Callable, *, sleep_fn: Callable=time.sleep):
    attempts=[]
    prompt_sha256=hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    for attempt in range(1,MAX_TRANSIENT_ATTEMPTS+1):
        try:
            text=provider(prompt,model_id,config)
            attempts.append({"attempt":attempt,"status":"RESPONSE_RECEIVED","error":None})
            return {"question_id":question["question_id"],"status":"RESPONSE_RECEIVED","response":text,"prompt_sha256":prompt_sha256,"attempts":attempts}
        except TransientInfrastructureError as exc:
            attempts.append({"attempt":attempt,"status":"TRANSIENT_INFRA_ERROR","error":str(exc)})
            if attempt==MAX_TRANSIENT_ATTEMPTS:
                return {"question_id":question["question_id"],"status":"UNKNOWN","response":None,"prompt_sha256":prompt_sha256,"attempts":attempts}
            sleep_fn(min(2 ** (attempt-1),4))
        except Exception as exc:
            attempts.append({"attempt":attempt,"status":"PERMANENT_OR_UNCLASSIFIED_ERROR","error":str(exc)})
            return {"question_id":question["question_id"],"status":"UNKNOWN","response":None,"prompt_sha256":prompt_sha256,"attempts":attempts}
    raise AssertionError("unreachable")

def openai_official_provider(prompt: str, model_id: str, config: dict) -> str:
    """OpenAI-compatible provider adapter with SDK retries disabled for D13 accounting."""
    timeout=float(config.get("provider_request_timeout_seconds",60))
    if timeout <= 0:
        raise ValueError("provider_request_timeout_seconds must be positive")
    client=OpenAI(base_url=env("LLM_BASE_URL"),api_key=env("LLM_API_KEY"),max_retries=0,timeout=timeout)
    try:
        response=client.chat.completions.create(model=model_id,messages=[{"role":"user","content":prompt}],temperature=config.get("temperature",0),max_tokens=config.get("max_tokens",1024))
    except (APIConnectionError,APITimeoutError,RateLimitError,InternalServerError) as exc:
        raise TransientInfrastructureError(str(exc)) from exc
    except Exception as exc:
        raise PermanentProviderError(str(exc)) from exc
    choice=response.choices[0]
    return choice.message.content or ""

def collect_three_replicates(questions: list[dict], model_id: str, config: dict, prompt_builder: Callable, provider: Callable, *, gate: OfficialGate):
    """Collect exactly three complete question passes, or refuse before contacting provider."""
    if not gate.ready():
        raise PermissionError("Official Evaluation blocked: "+", ".join(gate.blockers()))
    if not questions:raise ValueError("Official run requires a non-empty frozen question set")
    ids=[q.get("question_id") for q in questions]
    if any(not qid for qid in ids) or len(ids)!=len(set(ids)):raise ValueError("Question IDs must be present and unique")
    prompts = {question["question_id"]: prompt_builder(question) for question in questions}
    replicates=[]
    for replicate_id in REPLICATE_IDS:
        records=[]
        for question in questions:
            prompt=prompts[question["question_id"]]
            result=collect_one(question,prompt,model_id,config,provider)
            records.append({"replicate_id":replicate_id,**result})
        if [r["question_id"] for r in records]!=ids:raise RuntimeError("Incomplete replicate question coverage")
        replicates.append({"replicate_id":replicate_id,"question_count":len(records),"records":records})
    return {"model_id":model_id,"config":dict(config),"replicate_ids":list(REPLICATE_IDS),"timeout_s":OFFICIAL_SQL_TIMEOUT_S,"replicates":replicates}


def execute_official_sql(db_path, sql: str | None, *, runner: Callable=run):
    """Execute one saved prediction read-only with fixed D8 timeout; SQL outcomes are never retried."""
    if not sql or not sql.strip():return {"status":"no_sql","rows":None,"error":"no SQL supplied","timeout_s":OFFICIAL_SQL_TIMEOUT_S,"attempts":0}
    try:result=runner(db_path,sql,timeout_s=OFFICIAL_SQL_TIMEOUT_S)
    except Exception as exc:return {"status":"infra_error","rows":None,"error":str(exc),"timeout_s":OFFICIAL_SQL_TIMEOUT_S,"attempts":1}
    if isinstance(result,Rows):return {"status":"success","rows":result.rows,"columns":result.columns,"error":None,"timeout_s":OFFICIAL_SQL_TIMEOUT_S,"attempts":1}
    if isinstance(result,Timeout):return {"status":"timeout","rows":None,"error":f"query exceeded {result.timeout_s:g}s","timeout_s":OFFICIAL_SQL_TIMEOUT_S,"attempts":1}
    if isinstance(result,SqlError):return {"status":"sql_error","rows":None,"error":result.message,"timeout_s":OFFICIAL_SQL_TIMEOUT_S,"attempts":1}
    return {"status":"infra_error","rows":None,"error":"unknown SQL runner result","timeout_s":OFFICIAL_SQL_TIMEOUT_S,"attempts":1}
