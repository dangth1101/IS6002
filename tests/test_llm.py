import json

import pytest

from bird_demo import llm
from bird_demo.llm import MODEL_CHOICES, Reply, cached_complete, model_choices


@pytest.fixture
def calls(tmp_path, monkeypatch):
    """Stub out the live call; each call returns a new reply so a rewrite is visible."""
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path / "llm")
    made = []

    def fake_complete(prompt, model):
        made.append((prompt, model))
        return Reply(text=f"SELECT {len(made)}", finish_reason="stop")

    monkeypatch.setattr(llm, "complete", fake_complete)
    return made


def test_second_identical_call_is_served_from_the_cache(calls):
    first = cached_complete("prompt", "openai/gpt-4.1")
    second = cached_complete("prompt", "openai/gpt-4.1")

    assert first == second == Reply(text="SELECT 1", finish_reason="stop")
    assert len(calls) == 1


def test_refresh_calls_again_and_rewrites_the_file(calls, tmp_path):
    cached_complete("prompt", "openai/gpt-4.1")
    fresh = cached_complete("prompt", "openai/gpt-4.1", refresh=True)

    assert fresh.text == "SELECT 2"
    assert len(calls) == 2
    [cache_file] = (tmp_path / "llm").iterdir()
    assert json.loads(cache_file.read_text()) == {
        "model": "openai/gpt-4.1",
        "prompt": "prompt",
        "text": "SELECT 2",
        "finish_reason": "stop",
        "reasoning": "",
    }
    assert cached_complete("prompt", "openai/gpt-4.1").text == "SELECT 2"


def test_a_different_model_is_a_different_cache_entry(calls):
    cached_complete("prompt", "openai/gpt-4.1")
    cached_complete("prompt", "openai/gpt-3.5-turbo")

    assert len(calls) == 2



def test_configured_model_is_first_and_not_duplicated(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "google/gemini-2.5-flash")
    choices = model_choices()
    assert choices[0] == "google/gemini-2.5-flash"
    assert len(choices) == len(set(choices)) == len(MODEL_CHOICES)


def test_unlisted_configured_model_is_still_offered(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "local/my-model")
    assert model_choices() == ["local/my-model", *MODEL_CHOICES]


def test_without_llm_model_lists_gpt_and_gemini(monkeypatch):
    monkeypatch.delenv("LLM_MODEL", raising=False)
    choices = model_choices()
    assert choices == list(MODEL_CHOICES)
    assert any(c.startswith("openai/gpt-") for c in choices) and any(c.startswith("google/gemini-") for c in choices)


def test_complete_keeps_reasoning_tokens_from_the_provider(monkeypatch):
    from types import SimpleNamespace

    message = SimpleNamespace(content="```sql\nSELECT 1\n```", reasoning="  Count the rows first.  ")
    response = SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason="stop")])
    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_: response)))
    monkeypatch.setattr(llm, "client", lambda: fake_client)

    reply = llm.complete("prompt", "google/gemini-2.5-pro")

    assert reply == Reply(text="```sql\nSELECT 1\n```", finish_reason="stop", reasoning="Count the rows first.")


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ({"reasoning": "via OpenRouter"}, "via OpenRouter"),
        ({"reasoning_content": "via reasoning_content"}, "via reasoning_content"),
        ({"reasoning": None, "reasoning_content": "fallback"}, "fallback"),
        ({"reasoning": "   "}, ""),
        ({}, ""),
    ],
)
def test_reasoning_of_reads_known_fields(fields, expected):
    from types import SimpleNamespace

    assert llm.reasoning_of(SimpleNamespace(**fields)) == expected


def test_cache_keeps_reasoning_and_reads_old_files_without_it(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path / "llm")
    monkeypatch.setattr(llm, "complete", lambda prompt, model: Reply("SELECT 1", "stop", "think"))
    assert cached_complete("p", "m") == cached_complete("p", "m") == Reply("SELECT 1", "stop", "think")

    [cache_file] = (tmp_path / "llm").iterdir()
    old = json.loads(cache_file.read_text())
    del old["reasoning"]
    cache_file.write_text(json.dumps(old))
    assert cached_complete("p", "m") == Reply("SELECT 1", "stop")
