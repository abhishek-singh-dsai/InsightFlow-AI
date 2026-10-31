import json

import asyncio

from insightflow.ai import _context, enabled, describe_dataset, answer_question


def test_gemini_opt_in(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert not enabled()
    monkeypatch.setenv("GOOGLE_API_KEY", "replace_me")
    assert not enabled()
    monkeypatch.setenv("GOOGLE_API_KEY", "test_fake_key")
    assert enabled()


def test_context_serializable_and_bounded():
    p = {"data": "x" * 30_000}
    assert len(_context(p)) == 18_000
    assert isinstance(json.loads(_context({"value": 2})), dict)


def test_no_api_key_falls_back(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert "optional" in asyncio.run(describe_dataset({})).lower()
    assert "without AI" in asyncio.run(answer_question("what?", {}))
