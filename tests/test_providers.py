import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch


def test_build_messages_with_system_prompt():
    from rasputin.providers import _build_messages

    msgs = [{"role": "user", "content": "hello"}]
    result = _build_messages(msgs, system_prompt="You are helpful.")
    assert len(result) == 2
    assert result[0]["role"] == "system"
    assert result[1]["role"] == "user"


def test_build_messages_without_system_prompt():
    from rasputin.providers import _build_messages

    msgs = [{"role": "user", "content": "hello"}]
    result = _build_messages(msgs, system_prompt=None)
    assert len(result) == 1


def test_build_messages_appends_language_directive():
    from rasputin.providers import LANGUAGE_DIRECTIVE, _build_messages

    msgs = [{"role": "user", "content": "ciao"}]
    result = _build_messages(msgs, system_prompt="You are a reviewer.")
    assert result[0]["role"] == "system"
    assert LANGUAGE_DIRECTIVE in result[0]["content"]


def test_build_messages_does_not_duplicate_directive():
    from rasputin.providers import LANGUAGE_DIRECTIVE, _build_messages

    sp = f"You are a reviewer.\n\n{LANGUAGE_DIRECTIVE}"
    result = _build_messages([{"role": "user", "content": "x"}], system_prompt=sp)
    assert result[0]["content"].count(LANGUAGE_DIRECTIVE) == 1


def test_parse_cost_from_response():
    from rasputin.providers import _parse_response

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test response"
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_response._hidden_params = {"response_cost": 0.001234}

    result = _parse_response(mock_response)
    assert result["content"] == "Test response"
    assert result["cost"]["input_tokens"] == 100
    assert result["cost"]["output_tokens"] == 50
    assert result["cost"]["cost_usd"] == 0.001234


@patch("rasputin.providers._get_acompletion")
def test_query_parallel_handles_failures(mock_get_acompletion):
    from rasputin.providers import query_parallel

    async def _run():
        ok_response = MagicMock()
        ok_response.choices = [MagicMock()]
        ok_response.choices[0].message.content = "OK"
        ok_response.usage.prompt_tokens = 10
        ok_response.usage.completion_tokens = 5
        ok_response._hidden_params = {"response_cost": 0.0001}

        # litellm.acompletion is imported lazily via _get_acompletion();
        # patch the accessor to return an AsyncMock with per-call behavior.
        mock_get_acompletion.return_value = AsyncMock(
            side_effect=[ok_response, Exception("API down")]
        )

        results = await query_parallel(
            models=["model-a", "model-b"],
            messages_per_model={"_default": [{"role": "user", "content": "test"}]},
            system_prompts={"_default": "Be helpful."},
        )

        assert len(results) == 2
        assert results[0]["status"] == "ok"
        assert results[1]["status"] == "error"
        # Error is sanitized: it names the model but does not leak the raw
        # exception text.
        assert "model-b" in results[1]["error"]
        assert "API down" not in results[1]["error"]

    asyncio.run(_run())


def test_sanitize_error_maps_known_types():
    from rasputin.providers import _sanitize_error

    assert "authentication" in _sanitize_error(
        "openai/gpt-5", Exception("Error 401 invalid api key")
    )
    assert "timed out" in _sanitize_error("m", TimeoutError("request timed out"))
    assert "rate limited" in _sanitize_error("m", Exception("429 Too Many Requests"))
    assert "m:" in _sanitize_error("m", Exception("weird boom"))


class BadRequestError(Exception):
    """Stand-in for litellm.BadRequestError (matched by class name)."""


def test_is_temperature_rejection_only_fires_on_temperature():
    from rasputin.providers import _is_temperature_rejection

    real = BadRequestError(
        "litellm.BadRequestError: OpenAIException - Unsupported value: "
        "'temperature' does not support 0.7 with this model."
    )
    assert _is_temperature_rejection(real)

    # A different bad request must not be retried into a second billed call.
    assert not _is_temperature_rejection(BadRequestError("context length exceeded"))
    # Nor must an unrelated exception type that happens to mention temperature.
    assert not _is_temperature_rejection(Exception("unsupported temperature"))


def test_query_model_retries_without_temperature(monkeypatch):
    import asyncio

    from rasputin import providers

    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        if "temperature" in kwargs:
            raise BadRequestError("Unsupported value: 'temperature' does not support 0.7")
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
            _hidden_params={"response_cost": 0.0},
        )

    monkeypatch.setattr(providers, "_get_acompletion", lambda: fake_acompletion)

    result = asyncio.run(
        providers.query_model(
            model="openai/gpt-5.6",
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.7,
        )
    )

    assert result["content"] == "ok"
    assert len(calls) == 2
    assert "temperature" in calls[0] and "temperature" not in calls[1]
