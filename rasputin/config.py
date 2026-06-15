"""Configuration loader for Rasputin."""

import os
from importlib import resources
from pathlib import Path

import yaml


def _default_config_path() -> Path:
    """Locate the bundled default config, working from a wheel or a checkout."""
    return Path(str(resources.files("rasputin") / "data" / "rasputin.yaml"))


def load_config() -> dict:
    """Load configuration from YAML + apply defaults.

    Resolution order:
    1. ``RASPUTIN_CONFIG`` environment variable, if set (user override).
    2. The default config bundled inside the package (``rasputin/data``).
    """
    config_path = os.environ.get("RASPUTIN_CONFIG") or _default_config_path()

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Defaults
    config.setdefault("defaults", {})
    config["defaults"].setdefault("temperature", 0.7)
    config["defaults"].setdefault("max_output_tokens", 4096)
    config["defaults"].setdefault("timeout_per_model", 60)
    config["defaults"].setdefault("max_file_chars", 200_000)

    config.setdefault("council", {})
    config["council"].setdefault("consensus_model", "gemini/gemini-flash-latest")
    config["council"].setdefault("max_debate_rounds", 3)
    config["council"].setdefault("session_ttl_minutes", 120)
    config["council"].setdefault("max_sessions", 100)
    config["council"].setdefault("max_cost_usd", 0.0)  # 0 = no budget cap

    # Resolve aliases
    aliases = config.get("aliases", {})
    presets = config.get("presets", {})
    for alias, target in aliases.items():
        if alias not in presets and target in presets:
            presets[alias] = presets[target]

    return config
