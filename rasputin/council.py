"""Council orchestration — opinions, review, debate modes."""

import json
import re

from rasputin.providers import query_model, query_parallel
from rasputin.sessions import Session


def _sum_costs(results: list[dict]) -> dict:
    """Aggregate token and USD cost across a list of model results."""
    return {
        "input_tokens": sum(r["cost"]["input_tokens"] for r in results),
        "output_tokens": sum(r["cost"]["output_tokens"] for r in results),
        "cost_usd": round(sum(r["cost"]["cost_usd"] for r in results), 6),
    }


def _round_prompt(rounds: dict | None, n: int, fallback: str | None) -> str | None:
    """Return the configured ``system_prompt`` for round ``n`` of a preset.

    YAML round keys may be parsed as ints or strings, so both are tried.
    """
    if rounds:
        rc = rounds.get(n) or rounds.get(str(n))
        if isinstance(rc, dict) and rc.get("system_prompt"):
            return rc["system_prompt"]
    return fallback


def _extract_json(text: str) -> dict | None:
    """Best-effort JSON extraction from an LLM response.

    Handles markdown code fences and surrounding prose. Returns ``None`` if no
    valid JSON object can be parsed (callers fall back gracefully).
    """
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else None
    if candidate is None:
        start, end = text.find("{"), text.rfind("}") + 1
        candidate = text[start:end] if start >= 0 and end > start else None
    if not candidate:
        return None
    try:
        return json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        return None


def _max_tokens(config: dict) -> int:
    return config["defaults"].get("max_output_tokens", 4096)


async def run_council(
    mode: str,
    models_config: list[dict],
    resolved_models: list[str],
    message: str,
    system_prompt: str | None,
    config: dict,
    session: Session,
    rounds: dict | None = None,
) -> dict:
    """Dispatch a council run based on ``mode`` (opinions / review / debate)."""
    if mode == "opinions":
        return await _run_opinions(
            models_config, resolved_models, message, system_prompt, config, session
        )
    elif mode == "review":
        return await _run_review(
            models_config, resolved_models, message, system_prompt, config,
            session, rounds,
        )
    elif mode == "debate":
        return await _run_debate(
            models_config, resolved_models, message, system_prompt, config,
            session, rounds,
        )
    else:
        raise ValueError(f"Unknown mode: {mode}")


async def _run_opinions(
    models_config: list[dict],
    resolved_models: list[str],
    message: str,
    system_prompt: str | None,
    config: dict,
    session: Session,
) -> dict:
    """Parallel independent opinions + consensus extraction."""
    system_prompts = {}
    for mc in models_config:
        sp = mc.get("system_prompt") or system_prompt or ""
        system_prompts[mc["id"]] = sp
    system_prompts["_default"] = system_prompt or ""

    messages_per_model = {"_default": [{"role": "user", "content": message}]}

    results = await query_parallel(
        models=resolved_models,
        messages_per_model=messages_per_model,
        system_prompts=system_prompts,
        temperature=config["defaults"]["temperature"],
        timeout=config["defaults"]["timeout_per_model"],
        max_output_tokens=_max_tokens(config),
    )

    for r in results:
        if r["status"] == "ok":
            session.add_user_message(message, model=r["model"])
            session.add_assistant_message(r["model"], r["content"])

    consensus = await _extract_consensus(results, config)

    total_cost = _sum_costs(results)
    total_cost["cost_usd"] = round(
        total_cost["cost_usd"] + consensus.get("_cost", 0), 6
    )

    opinions = [
        {"model": r["model"], "response": r["content"], "cost": r["cost"]}
        for r in results
        if r["status"] == "ok"
    ]
    errors = [
        {"model": r["model"], "error": r["error"]}
        for r in results
        if r["status"] == "error"
    ]

    result = {
        "opinions": opinions,
        "errors": errors if errors else None,
        "consensus_analysis": {
            k: v for k, v in consensus.items() if k != "_cost"
        },
        "total_cost": total_cost,
    }
    # Make total failure unambiguous to the chairman: an empty opinion list
    # must not read as "council ran, found nothing".
    if not opinions:
        result["status"] = "all_models_failed"
    return result


async def _run_review(
    models_config: list[dict],
    resolved_models: list[str],
    message: str,
    system_prompt: str | None,
    config: dict,
    session: Session,
    rounds: dict | None = None,
) -> dict:
    """Opinions + anonymous peer review."""
    round1 = await _run_opinions(
        models_config,
        resolved_models,
        message,
        _round_prompt(rounds, 1, system_prompt),
        config,
        session,
    )

    opinions = round1["opinions"]
    if len(opinions) < 2:
        round1["peer_review"] = None
        return round1

    labels = [chr(65 + i) for i in range(len(opinions))]
    label_map = {label: op["model"] for label, op in zip(labels, opinions)}

    anon_text = "\n\n".join(
        f"=== Response {label} ===\n{op['response']}"
        for label, op in zip(labels, opinions)
    )

    review_prompt = (
        f"You have seen multiple responses to this question:\n\n"
        f"ORIGINAL QUESTION:\n{message}\n\n"
        f"RESPONSES:\n{anon_text}\n\n"
        f"Evaluate each response. Then provide a FINAL RANKING as JSON:\n"
        f'{{"ranking": ["Response X", ...], "best": "Response X", "reasoning": "..."}}'
    )

    r2_system = _round_prompt(
        rounds,
        2,
        "You are evaluating responses from other reviewers. "
        "Be objective and thorough.",
    )

    r2_messages = {"_default": [{"role": "user", "content": review_prompt}]}
    r2_sys = {m: r2_system for m in resolved_models}
    r2_sys["_default"] = r2_system

    round2_results = await query_parallel(
        models=resolved_models,
        messages_per_model=r2_messages,
        system_prompts=r2_sys,
        temperature=config["defaults"]["temperature"],
        timeout=config["defaults"]["timeout_per_model"],
        max_output_tokens=_max_tokens(config),
    )

    peer_reviews = [
        {"model": r["model"], "evaluation": r["content"], "cost": r["cost"]}
        for r in round2_results
        if r["status"] == "ok"
    ]

    r2_cost = _sum_costs(round2_results)
    round1["total_cost"]["cost_usd"] = round(
        round1["total_cost"]["cost_usd"] + r2_cost["cost_usd"], 6
    )
    round1["total_cost"]["input_tokens"] += r2_cost["input_tokens"]
    round1["total_cost"]["output_tokens"] += r2_cost["output_tokens"]

    round1["peer_review"] = {
        "evaluations": peer_reviews,
        "label_map": label_map,
    }

    return round1


async def _run_debate(
    models_config: list[dict],
    resolved_models: list[str],
    message: str,
    system_prompt: str | None,
    config: dict,
    session: Session,
    rounds: dict | None = None,
) -> dict:
    """Multi-round debate with convergence check and an optional budget cap."""
    max_rounds = config["council"].get("max_debate_rounds", 3)

    # Check preset-specific max_rounds
    for mc in models_config:
        if isinstance(mc, dict) and "max_rounds" in mc:
            max_rounds = mc["max_rounds"]

    max_cost = config["council"].get("max_cost_usd", 0) or 0
    debate_rounds = []

    r1 = await _run_opinions(
        models_config,
        resolved_models,
        message,
        _round_prompt(rounds, 1, system_prompt),
        config,
        session,
    )
    debate_rounds.append({"round": 1, "opinions": r1["opinions"]})

    convergence = {"converged": False}
    budget_exceeded = False
    for round_num in range(2, max_rounds + 1):
        if max_cost and _debate_cost(debate_rounds) >= max_cost:
            budget_exceeded = True
            break

        prev_responses = "\n\n".join(
            f"=== {op['model']} ===\n{op['response']}"
            for op in debate_rounds[-1]["opinions"]
        )

        round_message = (
            f"Previous round of discussion:\n\n{prev_responses}\n\n"
            f"Original question: {message}\n\n"
            f"Consider the other participants' arguments. Respond to their points, "
            f"refine your position, or change your mind if convinced."
        )

        r_n = await _run_opinions(
            models_config,
            resolved_models,
            round_message,
            _round_prompt(rounds, round_num, system_prompt),
            config,
            session,
        )
        debate_rounds.append({"round": round_num, "opinions": r_n["opinions"]})

        convergence = await _check_convergence(debate_rounds, config)
        if convergence.get("converged"):
            break

    total_cost = {
        "input_tokens": sum(
            sum(op["cost"]["input_tokens"] for op in r["opinions"])
            for r in debate_rounds
        ),
        "output_tokens": sum(
            sum(op["cost"]["output_tokens"] for op in r["opinions"])
            for r in debate_rounds
        ),
        "cost_usd": round(_debate_cost(debate_rounds), 6),
    }

    return {
        "debate_rounds": debate_rounds,
        "num_rounds": len(debate_rounds),
        "convergence": convergence,
        "budget_exceeded": budget_exceeded,
        "total_cost": total_cost,
    }


def _debate_cost(debate_rounds: list[dict]) -> float:
    """Cumulative USD cost across all debate rounds so far."""
    return sum(
        sum(op["cost"]["cost_usd"] for op in r["opinions"]) for r in debate_rounds
    )


async def _extract_consensus(results: list[dict], config: dict) -> dict:
    """Use a cheap model to extract agreements and disagreements."""
    successful = [r for r in results if r["status"] == "ok"]
    if len(successful) < 2:
        return {
            "agreements": [],
            "disagreements": [],
            "summary": "Only one response available."
            if successful
            else "No responses available.",
            "_cost": 0,
        }

    responses_text = "\n\n".join(
        f"=== {r['model']} ===\n{r['content']}" for r in successful
    )

    consensus_prompt = (
        f"Analyze these {len(successful)} independent reviews and extract:\n"
        f"1. AGREEMENTS: points where all reviewers agree\n"
        f"2. DISAGREEMENTS: points where reviewers diverge (specify who says what)\n"
        f"3. SUMMARY: one-sentence overall assessment\n\n"
        f'Respond in JSON: {{"agreements": [...], "disagreements": [...], "summary": "..."}}'
    )

    consensus_model = config["council"].get(
        "consensus_model", "gemini/gemini-flash-latest"
    )

    try:
        result = await query_model(
            model=consensus_model,
            messages=[
                {
                    "role": "user",
                    "content": f"{responses_text}\n\n{consensus_prompt}",
                }
            ],
            system_prompt="Extract consensus and disagreements. Return valid JSON only.",
            temperature=0.2,
            timeout=30,
            max_output_tokens=_max_tokens(config),
            response_format={"type": "json_object"},
        )
        parsed = _extract_json(result["content"])
        if isinstance(parsed, dict):
            parsed.setdefault("agreements", [])
            parsed.setdefault("disagreements", [])
            parsed.setdefault("summary", "")
            parsed["_cost"] = result["cost"]["cost_usd"]
            return parsed
    except Exception:
        pass

    return {
        "agreements": [],
        "disagreements": [],
        "summary": "Consensus extraction failed.",
        "_cost": 0,
    }


async def _check_convergence(debate_rounds: list[dict], config: dict) -> dict:
    """Check if debate positions are converging."""
    if len(debate_rounds) < 2:
        return {"converged": False}

    latest = debate_rounds[-1]["opinions"]
    if len(latest) < 2:
        return {"converged": False, "reason": "Too few active participants"}

    consensus_model = config["council"].get(
        "consensus_model", "gemini/gemini-flash-latest"
    )

    text = "\n\n".join(
        f"{op['model']}: {op['response'][:500]}" for op in latest
    )

    try:
        result = await query_model(
            model=consensus_model,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Are these positions converging or still diverging?\n\n"
                        f"{text}\n\n"
                        f'Respond JSON: {{"converged": true/false, "reason": "..."}}'
                    ),
                }
            ],
            system_prompt="Return valid JSON only.",
            temperature=0.1,
            timeout=15,
            max_output_tokens=_max_tokens(config),
            response_format={"type": "json_object"},
        )
        parsed = _extract_json(result["content"])
        if isinstance(parsed, dict) and "converged" in parsed:
            return parsed
    except Exception:
        pass

    return {"converged": False, "reason": "Check failed"}
