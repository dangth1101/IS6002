"""The LLM seam: raw prompt in, raw reply out.

No prompt building and no SQL extraction here; that's prompt.py. Any
OpenAI-compatible endpoint works; switching provider is a .env change only.
"""

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from functools import cache

from dotenv import load_dotenv
from openai import OpenAI

from bird_demo.data import ROOT

load_dotenv(ROOT / ".env")

CACHE_DIR = ROOT / ".cache" / "llm"
MAX_TOKENS = 1024


@dataclass(frozen=True)
class Reply:
    text: str
    finish_reason: str  # "stop", "length", ...


def env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is not set. Copy .env.example to .env and fill it in.")
    return value


def default_model() -> str:
    """The model from LLM_MODEL. The app uses it; the batch's --model overrides it."""
    return env("LLM_MODEL")


@cache
def client() -> OpenAI:
    # Built on first use, so importing this module needs no .env (tests stub complete).
    return OpenAI(base_url=env("LLM_BASE_URL"), api_key=env("LLM_API_KEY"), max_retries=3)


def complete(prompt: str, model: str) -> Reply:
    """One live chat call. Raises if it still fails after the client's retries."""
    response = client().chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],  # no system message
        temperature=0,  # always sent; OpenRouter drops it for models that don't take it
        max_tokens=MAX_TOKENS,
    )
    choice = response.choices[0]
    return Reply(text=choice.message.content or "", finish_reason=choice.finish_reason or "")


def cached_complete(prompt: str, model: str, refresh: bool = False) -> Reply:
    """`complete` with one file per reply on disk. `refresh=True` skips the read but still writes."""
    path = CACHE_DIR / f"{hashlib.sha256((model + prompt).encode()).hexdigest()}.json"
    if not refresh and path.exists():
        cached = json.loads(path.read_text(encoding="utf-8"))
        return Reply(text=cached["text"], finish_reason=cached["finish_reason"])

    reply = complete(prompt, model)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"model": model, "prompt": prompt, **asdict(reply)}, indent=2), encoding="utf-8")
    tmp.replace(path)  # a crash mid-write never leaves a half file behind
    return reply
