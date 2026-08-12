# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Calls to `gpt-5.5`/`gpt-5.6` no longer fail with a 400. Those models accept
  only `temperature=1`, but LiteLLM still lists `temperature` as supported for
  them, so `drop_params` did not strip it; the call is now retried once on the
  provider default. Detection is by error shape, not a model allowlist.

### Changed
- Premium presets (`consensus`, `devil`, `panel`, `deep`, `arena`) now convene
  flagships — `openai/gpt-5.6`, `gemini/gemini-3.1-pro-preview`,
  `mistral/mistral-large-latest`. Cheap presets (`flash`, `nano`, `trio`,
  `code`, `copy`, `factcheck`, `redteam`) are unchanged.
- `timeout_per_model` raised from 60s to 120s: flagship reasoning models were
  timing out spuriously on an 8192-token budget.

### Added
- `test_configured_model_is_known_to_litellm` validates every model id in the
  shipped config against the LiteLLM registry, catching retired or misspelled
  ids (e.g. `gemini/gemini-3-pro`, which needs the `-preview` suffix) offline.
- MIT license, README, CONTRIBUTING, SECURITY policy and this changelog.
- GitHub Actions CI: tests, real entrypoint import, a build-and-install
  wheel smoke test, `ruff` (F, E9, I, UP) and `pip-audit`, across
  Linux/macOS/Windows × Python 3.11/3.12/3.13.
- Release workflow publishing to PyPI via Trusted Publishing on version tags.
- Bundled Claude Code skill in `skill/rasputin/` (chairman guidance + preset reference).
- Language directive so the council replies in the language of the input.
- Per-round prompts in `review`/`debate` presets are now honored.
- Safety limits: per-file text cap (`max_file_chars`) and a 50 MB pre-parse
  size cap, an LRU session cap (`max_sessions`), and an optional debate budget
  cap (`max_cost_usd`).
- `all_models_failed` status and a `budget_exceeded` flag in council results.
- `__version__` on the package; `total_cost` is now tracked per session.

### Fixed
- **Packaging:** the default config is bundled inside the package
  (`rasputin/data/rasputin.yaml`) and loaded via `importlib.resources`, so
  `uvx`/`pip install` no longer crash on startup with `FileNotFoundError`.
- `max_output_tokens` from the config is now propagated to every model call
  (was set in config but ignored, always running at the hardcoded 4096).
  Covered by a regression test.
- The `rounds:` blocks of multi-round presets were dead config; they now drive
  the per-round system prompts.
- Single-model tools (`rasputin_ask`/`rasputin_followup`) no longer leak raw
  stacktraces or provider error detail; errors go through `_sanitize_error`
  like the council path. Covered by a test.
- Claude/Anthropic models are now rejected in code, not just by documentation.
- Robust JSON extraction from model output (handles code fences and prose).

### Changed
- `pytest` moved from runtime dependencies to a `dev` dependency group; added
  `ruff` and `pip-audit` as dev tools.
- Dependencies now have upper bounds (e.g. `litellm>=1.89,<2`, `fastmcp>=3.4,<4`)
  for reproducible fresh installs.
- Minimum Python lowered to 3.11.
- Parsed documents are wrapped in untrusted-data delimiters (prompt-injection
  defense-in-depth).
- `ruff` ruleset extended to import sorting (`I`) and pyupgrade (`UP`).

## [0.1.0] — 2026

### Added
- Initial release: Rasputin multi-LLM council MCP server with `rasputin_ask`,
  `rasputin_council`, `rasputin_followup` and `rasputin_sessions` tools, 12
  presets (opinions / review / debate modes) and document parsing for pdf,
  docx, pptx, xlsx, csv and text formats.
