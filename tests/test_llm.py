import json

import pytest

from bird_demo import llm
from bird_demo.llm import Reply, cached_complete


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
    }
    assert cached_complete("prompt", "openai/gpt-4.1").text == "SELECT 2"


def test_a_different_model_is_a_different_cache_entry(calls):
    cached_complete("prompt", "openai/gpt-4.1")
    cached_complete("prompt", "openai/gpt-3.5-turbo")

    assert len(calls) == 2
