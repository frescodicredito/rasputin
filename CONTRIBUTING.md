# Contributing to Rasputin

Thanks for your interest in improving Rasputin! This is a small project, so the process is light.

## Getting started

```bash
git clone https://github.com/frescodicredito/rasputin.git
cd rasputin
uv sync
```

## Development workflow

- **Run the tests** before opening a PR:
  ```bash
  uv run pytest
  ```
- **Lint** (pyflakes, syntax, import order, pyupgrade):
  ```bash
  uv run ruff check .
  ```
- **Add a test for every behavior change.** Bug fixes should come with a regression test that fails before the fix and passes after it.
- Keep changes focused and the diff small. The whole engine is a handful of modules:
  - `rasputin/server.py` — MCP tools and entrypoint
  - `rasputin/council.py` — orchestration (opinions / review / debate)
  - `rasputin/providers.py` — LiteLLM wrapper
  - `rasputin/files.py` — document parsing
  - `rasputin/sessions.py` — session state
  - `rasputin/config.py` — config loading
  - `rasputin/data/rasputin.yaml` — presets and models (bundled in the wheel)

## Adding or changing presets

Presets live in `rasputin/data/rasputin.yaml`. Keep prompts in English (the engine appends a directive so the council answers in the user's language). Never add a Claude/Anthropic model to a council — the chairman (Claude Code) must stay outside the panel to avoid intra-family bias (the server enforces this).

## Pull requests

- Describe the change and why it's needed.
- Make sure CI is green (tests + lint + `pip-audit`) across the OS/Python matrix.
- Update `CHANGELOG.md` under an `## [Unreleased]` heading.

## Code of conduct

Be respectful and constructive. Assume good faith.
