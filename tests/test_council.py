import asyncio
from unittest.mock import patch

from rasputin.sessions import SessionManager


def _make_mock_result(model, content):
    return {
        "model": model,
        "status": "ok",
        "content": content,
        "cost": {"input_tokens": 100, "output_tokens": 50, "cost_usd": 0.001},
    }


@patch("rasputin.council.query_parallel")
@patch("rasputin.council._extract_consensus")
def test_run_opinions(mock_consensus, mock_parallel):
    from rasputin.council import run_council

    mock_parallel.return_value = [
        _make_mock_result("model-a", "Opinion A"),
        _make_mock_result("model-b", "Opinion B"),
    ]
    mock_consensus.return_value = {
        "agreements": ["Both agree on X"],
        "disagreements": [],
        "summary": "Aligned.",
        "_cost": 0,
    }

    config = {
        "defaults": {"temperature": 0.7, "timeout_per_model": 30},
        "council": {"consensus_model": "gemini/gemini-2.5-flash"},
        "presets": {"trio": {"system_prompt": "Review."}},
    }
    models_config = [
        {"id": "model-a", "role": "reviewer"},
        {"id": "model-b", "role": "reviewer"},
    ]
    session = SessionManager(ttl_minutes=60).get_or_create(
        None, type="council", models=["model-a", "model-b"]
    )

    result = asyncio.run(
        run_council(
            mode="opinions",
            models_config=models_config,
            resolved_models=["model-a", "model-b"],
            message="Review this.",
            system_prompt=None,
            config=config,
            session=session,
        )
    )

    assert len(result["opinions"]) == 2
    assert result["opinions"][0]["model"] == "model-a"
    assert result["consensus_analysis"]["agreements"] == ["Both agree on X"]
    assert result["total_cost"]["cost_usd"] > 0


@patch("rasputin.council.query_parallel")
@patch("rasputin.council._extract_consensus")
def test_max_output_tokens_propagated_to_query_parallel(mock_consensus, mock_parallel):
    """Regression: the council must forward config max_output_tokens to query_parallel.

    Guards against the bug where config/rasputin.yaml set max_output_tokens but
    providers kept their hardcoded 4096 default because nothing passed the value
    through — silently truncating long answers from reasoning models.
    """
    from rasputin.council import run_council

    mock_parallel.return_value = []
    mock_consensus.return_value = {"_cost": 0}

    config = {
        "defaults": {
            "temperature": 0.7,
            "timeout_per_model": 30,
            "max_output_tokens": 9999,
        },
        "council": {"consensus_model": "gemini/gemini-2.5-flash"},
    }
    session = SessionManager(ttl_minutes=60).get_or_create(
        None, type="council", models=["model-a"]
    )

    asyncio.run(
        run_council(
            mode="opinions",
            models_config=[{"id": "model-a", "role": "reviewer"}],
            resolved_models=["model-a"],
            message="Review this.",
            system_prompt=None,
            config=config,
            session=session,
        )
    )

    assert mock_parallel.call_args.kwargs["max_output_tokens"] == 9999


def test_extract_json_handles_fences_and_prose():
    from rasputin.council import _extract_json

    assert _extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert _extract_json('prose before {"b": 2} prose after') == {"b": 2}
    assert _extract_json("no json at all") is None
    assert _extract_json("") is None


def test_round_prompt_reads_int_and_str_keys():
    from rasputin.council import _round_prompt

    rounds = {1: {"system_prompt": "one"}, "2": {"system_prompt": "two"}}
    assert _round_prompt(rounds, 1, "fb") == "one"
    assert _round_prompt(rounds, 2, "fb") == "two"
    assert _round_prompt(rounds, 3, "fb") == "fb"
    assert _round_prompt(None, 1, "fb") == "fb"


def _base_config(**council):
    cfg = {
        "defaults": {
            "temperature": 0.7,
            "timeout_per_model": 30,
            "max_output_tokens": 4096,
        },
        "council": {"consensus_model": "gemini/gemini-flash-latest"},
    }
    cfg["council"].update(council)
    return cfg


@patch("rasputin.council.query_parallel")
@patch("rasputin.council._extract_consensus")
def test_run_opinions_flags_total_failure(mock_consensus, mock_parallel):
    from rasputin.council import run_council

    mock_parallel.return_value = [
        {
            "model": "m1",
            "status": "error",
            "error": "m1: timed out",
            "content": None,
            "cost": {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0},
        }
    ]
    mock_consensus.return_value = {"_cost": 0}
    session = SessionManager(ttl_minutes=60).get_or_create(None, "council", ["m1"])

    result = asyncio.run(
        run_council(
            mode="opinions",
            models_config=[{"id": "m1"}],
            resolved_models=["m1"],
            message="q",
            system_prompt=None,
            config=_base_config(),
            session=session,
        )
    )
    assert result["opinions"] == []
    assert result["status"] == "all_models_failed"
    assert result["errors"]


@patch("rasputin.council.query_parallel")
@patch("rasputin.council._extract_consensus")
def test_run_review_adds_peer_review_with_round_prompts(mock_consensus, mock_parallel):
    from rasputin.council import run_council

    mock_parallel.side_effect = [
        [_make_mock_result("m1", "op1"), _make_mock_result("m2", "op2")],
        [_make_mock_result("m1", "rank1"), _make_mock_result("m2", "rank2")],
    ]
    mock_consensus.return_value = {
        "agreements": [],
        "disagreements": [],
        "summary": "s",
        "_cost": 0,
    }
    session = SessionManager(ttl_minutes=60).get_or_create(
        None, "council", ["m1", "m2"]
    )

    result = asyncio.run(
        run_council(
            mode="review",
            models_config=[{"id": "m1"}, {"id": "m2"}],
            resolved_models=["m1", "m2"],
            message="q",
            system_prompt=None,
            config=_base_config(),
            session=session,
            rounds={1: {"system_prompt": "r1"}, 2: {"system_prompt": "r2"}},
        )
    )
    assert result["peer_review"] is not None
    assert len(result["peer_review"]["evaluations"]) == 2
    assert result["peer_review"]["label_map"] == {"A": "m1", "B": "m2"}
    # round-2 system prompt from the preset must reach query_parallel
    assert mock_parallel.call_args_list[1].kwargs["system_prompts"]["m1"] == "r2"


@patch("rasputin.council._check_convergence")
@patch("rasputin.council.query_parallel")
@patch("rasputin.council._extract_consensus")
def test_run_debate_runs_multiple_rounds(mock_consensus, mock_parallel, mock_conv):
    from rasputin.council import run_council

    mock_parallel.return_value = [
        _make_mock_result("m1", "x"),
        _make_mock_result("m2", "y"),
    ]
    mock_consensus.return_value = {"_cost": 0}
    mock_conv.return_value = {"converged": False}
    session = SessionManager(ttl_minutes=60).get_or_create(
        None, "council", ["m1", "m2"]
    )

    result = asyncio.run(
        run_council(
            mode="debate",
            models_config=[{"id": "m1"}, {"id": "m2"}],
            resolved_models=["m1", "m2"],
            message="q",
            system_prompt=None,
            config=_base_config(max_debate_rounds=2),
            session=session,
        )
    )
    assert result["num_rounds"] == 2
    assert result["budget_exceeded"] is False
    assert len(result["debate_rounds"]) == 2


@patch("rasputin.council._check_convergence")
@patch("rasputin.council.query_parallel")
@patch("rasputin.council._extract_consensus")
def test_run_debate_honors_budget_cap(mock_consensus, mock_parallel, mock_conv):
    from rasputin.council import run_council

    expensive = {
        "model": "m1",
        "status": "ok",
        "content": "x",
        "cost": {"input_tokens": 1, "output_tokens": 1, "cost_usd": 1.0},
    }
    mock_parallel.return_value = [expensive]
    mock_consensus.return_value = {"_cost": 0}
    mock_conv.return_value = {"converged": False}
    session = SessionManager(ttl_minutes=60).get_or_create(None, "council", ["m1"])

    result = asyncio.run(
        run_council(
            mode="debate",
            models_config=[{"id": "m1"}],
            resolved_models=["m1"],
            message="q",
            system_prompt=None,
            config=_base_config(max_debate_rounds=4, max_cost_usd=0.5),
            session=session,
        )
    )
    # round 1 already costs 1.0 USD > 0.5 cap → no further rounds
    assert result["num_rounds"] == 1
    assert result["budget_exceeded"] is True
