"""LiteLLM wrapper for multi-provider LLM access."""

import asyncio

# Appended to every system prompt so the council answers in the user's own
# language (the engine ships English prompts, but a user writing in Italian
# gets Italian back — at zero extra cost).
LANGUAGE_DIRECTIVE = "Respond in the same language as the input."


def _get_acompletion():
    """Lazy import of litellm to avoid 4s startup penalty."""
    from litellm import acompletion
    return acompletion


def _build_messages(
    messages: list[dict], system_prompt: str | None = None
) -> list[dict]:
    """Prepend system prompt to messages if provided, with the language directive."""
    full = []
    if system_prompt:
        content = system_prompt.rstrip()
        if LANGUAGE_DIRECTIVE not in content:
            content = f"{content}\n\n{LANGUAGE_DIRECTIVE}"
        full.append({"role": "system", "content": content})
    full.extend(messages)
    return full


def _response_cost(response) -> float:
    """Read the call cost, falling back to litellm's public helper.

    ``response._hidden_params["response_cost"]`` is the de-facto field but is a
    private API; if it's missing or zero we try ``litellm.completion_cost``.
    """
    cost = 0.0
    hidden = getattr(response, "_hidden_params", None)
    if isinstance(hidden, dict):
        cost = hidden.get("response_cost") or 0.0
    if not cost:
        try:
            from litellm import completion_cost

            cost = completion_cost(completion_response=response) or 0.0
        except Exception:
            cost = 0.0
    return cost


def _parse_response(response) -> dict:
    """Extract content, tokens, and cost from LiteLLM response."""
    content = response.choices[0].message.content
    return {
        "content": content,
        "cost": {
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "cost_usd": round(_response_cost(response), 6),
        },
    }


def _sanitize_error(model: str, exc: Exception) -> str:
    """Map a provider exception to a concise message without leaking raw detail.

    Raw litellm/httpx exceptions can carry endpoints, request ids or payload
    fragments; we surface the error *type* and model only.
    """
    name = type(exc).__name__
    lowered = f"{name} {exc}".lower()
    if "auth" in lowered or "api key" in lowered or "401" in lowered:
        reason = "authentication failed (check the API key)"
    elif "timeout" in lowered or "timed out" in lowered:
        reason = "request timed out"
    elif "rate limit" in lowered or "429" in lowered:
        reason = "rate limited"
    elif "not found" in lowered or "404" in lowered or "does not exist" in lowered:
        reason = "model not found"
    else:
        reason = name
    return f"{model}: {reason}"


async def query_model(
    model: str,
    messages: list[dict],
    system_prompt: str | None = None,
    temperature: float = 0.7,
    timeout: int = 60,
    max_output_tokens: int = 4096,
    response_format: dict | None = None,
) -> dict:
    """Call a single LLM via LiteLLM."""
    full_messages = _build_messages(messages, system_prompt)

    kwargs = {
        "model": model,
        "messages": full_messages,
        "temperature": temperature,
        "max_tokens": max_output_tokens,
        "num_retries": 2,
        "timeout": timeout,
        # gpt-5 / o-series are reasoning models: they reject temperature!=1 and
        # use max_completion_tokens. drop_params lets LiteLLM strip/translate
        # unsupported params per-model instead of erroring.
        "drop_params": True,
    }
    if response_format is not None:
        kwargs["response_format"] = response_format

    acompletion = _get_acompletion()
    response = await acompletion(**kwargs)

    return _parse_response(response)


async def query_parallel(
    models: list[str],
    messages_per_model: dict[str, list[dict]],
    system_prompts: dict[str, str],
    temperature: float = 0.7,
    timeout: int = 60,
    max_output_tokens: int = 4096,
) -> list[dict]:
    """Call N models in parallel with graceful degradation."""

    async def _call(model: str) -> dict:
        try:
            result = await query_model(
                model=model,
                messages=messages_per_model.get(model, messages_per_model["_default"]),
                system_prompt=system_prompts.get(model, system_prompts.get("_default")),
                temperature=temperature,
                timeout=timeout,
                max_output_tokens=max_output_tokens,
            )
            return {"model": model, "status": "ok", **result}
        except Exception as e:
            return {
                "model": model,
                "status": "error",
                "error": _sanitize_error(model, e),
                "content": None,
                "cost": {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0},
            }

    results = await asyncio.gather(*[_call(m) for m in models])
    return list(results)
