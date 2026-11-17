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
    reasoning: str = ""  # reasoning tokens, when the model/provider returns them


def env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is not set. Copy .env.example to .env and fill it in.")
    return value


def default_model() -> str:
    """The model from LLM_MODEL. The app uses it; the batch's --model overrides it."""
    return env("LLM_MODEL")


# OpenRouter vendor/model ids offered in the app's model dropdowns (checked against
# https://openrouter.ai/api/v1/models on 2026-11-17). Any other id can still be typed in.
MODEL_CHOICES = (
    "openai/gpt-6-sol",
    "openai/gpt-5.5",
    "openai/gpt-5.4-mini",
    "openai/gpt-4.1",
    "openai/gpt-4o-mini",
    "google/gemini-3.5-flash",
    "google/gemini-3.1-pro-preview",
    "google/gemini-3.1-flash-lite-preview",
    "google/gemini-2.5-pro",
    "google/gemini-2.5-flash",
)


def model_choices() -> list[str]:
    """Dropdown options: LLM_MODEL first (the default selection), then MODEL_CHOICES."""
    configured = os.environ.get("LLM_MODEL")
    return list(dict.fromkeys([configured, *MODEL_CHOICES] if configured else MODEL_CHOICES))


@cache
def client() -> OpenAI:
    # Built on first use, so importing this module needs no .env (tests stub complete).
    return OpenAI(base_url=env("LLM_BASE_URL"), api_key=env("LLM_API_KEY"), max_retries=3)


def complete(prompt: str, model: str, *, temperature: float = 0, max_tokens: int = MAX_TOKENS) -> Reply:
    """One live chat call. Optional generation controls preserve legacy defaults."""
    response = client().chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],  # no system message
        temperature=temperature,  # always sent; OpenRouter drops it for models that don't take it
        max_tokens=max_tokens,
    )
    choice = response.choices[0]
    return Reply(
        text=choice.message.content or "",
        finish_reason=choice.finish_reason or "",
        reasoning=reasoning_of(choice.message),
    )


def reasoning_of(message: object) -> str:
    """Reasoning tokens from a chat message: OpenRouter's `reasoning`, or `reasoning_content`."""
    for field in ("reasoning", "reasoning_content"):
        value = getattr(message, field, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def cached_complete(prompt: str, model: str, refresh: bool = False) -> Reply:
    """`complete` with one file per reply on disk. `refresh=True` skips the read but still writes."""
    path = CACHE_DIR / f"{hashlib.sha256((model + prompt).encode()).hexdigest()}.json"
    if not refresh and path.exists():
        cached = json.loads(path.read_text(encoding="utf-8"))
        return Reply(text=cached["text"], finish_reason=cached["finish_reason"], reasoning=cached.get("reasoning", ""))

    reply = complete(prompt, model)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"model": model, "prompt": prompt, **asdict(reply)}, indent=2), encoding="utf-8")
    tmp.replace(path)  # a crash mid-write never leaves a half file behind
    return reply
