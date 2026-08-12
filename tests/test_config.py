import litellm
import pytest

from rasputin.config import load_config


def _configured_models() -> list[tuple[str, str]]:
    """Every (preset, model_id) pair the shipped config can dispatch to."""
    config = load_config()
    aliases = config.get("aliases", {})
    pairs = [
        (name, model["id"])
        for name, preset in config["presets"].items()
        if name not in aliases
        for model in preset.get("models", [])
    ]
    pairs.append(("council.consensus_model", config["council"]["consensus_model"]))
    return pairs


@pytest.mark.parametrize(("preset", "model_id"), _configured_models())
def test_configured_model_is_known_to_litellm(preset, model_id):
    """Catch typos and retired ids before a live call does.

    A bare ``gemini/gemini-3-pro`` (no ``-preview`` suffix) fails here the way
    it would fail at runtime, without spending a request to find out.
    """
    assert litellm.get_model_info(model_id)["litellm_provider"] == model_id.split("/")[0]


def test_load_config_returns_dict():
    config = load_config()
    assert isinstance(config, dict)
    assert "defaults" in config
    assert "presets" in config
    assert "council" in config


def test_config_defaults():
    config = load_config()
    assert config["defaults"]["temperature"] == 0.7
    assert config["defaults"]["timeout_per_model"] == 120
    assert config["defaults"]["max_output_tokens"] == 8192


def test_config_has_trio_preset():
    config = load_config()
    trio = config["presets"]["trio"]
    assert trio["mode"] == "opinions"
    assert len(trio["models"]) == 3


def test_config_has_all_12_presets():
    config = load_config()
    expected = {"flash", "nano", "trio", "code", "copy", "factcheck",
                "redteam", "consensus", "devil", "panel", "deep", "arena"}
    actual = {k for k in config["presets"] if k not in config.get("aliases", {})}
    assert expected == actual


def test_config_aliases_resolve():
    config = load_config()
    assert "default" in config["presets"]
    assert config["presets"]["default"] == config["presets"]["trio"]
    assert config["presets"]["quick"] == config["presets"]["flash"]
    assert config["presets"]["fight"] == config["presets"]["arena"]
