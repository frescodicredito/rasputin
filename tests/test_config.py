from rasputin.config import load_config


def test_load_config_returns_dict():
    config = load_config()
    assert isinstance(config, dict)
    assert "defaults" in config
    assert "presets" in config
    assert "council" in config


def test_config_defaults():
    config = load_config()
    assert config["defaults"]["temperature"] == 0.7
    assert config["defaults"]["timeout_per_model"] == 60
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
