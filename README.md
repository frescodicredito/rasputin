# Rasputin 🧙

[![CI](https://github.com/frescodicredito/rasputin/actions/workflows/ci.yml/badge.svg)](https://github.com/frescodicredito/rasputin/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-server-purple.svg)](https://modelcontextprotocol.io)

**A multi-LLM council for Claude Code.** Rasputin convenes external models — Gemini, GPT and Mistral — to give Claude independent second opinions on your work. Claude stays the chairman: Rasputin returns the raw opinions and a cross-model consensus, Claude synthesizes the decision.

Why a council instead of a single model? Asking one model to grade work biases toward its own family. Three independent providers, queried in parallel and cross-checked, surface disagreements a single reviewer would hide — at a few cents per run.

## What it does

- **Parallel council** — query 3 model families at once and get a structured consensus (agreements / disagreements / verdict).
- **12 presets** — from a 1¢ sanity check to a full 3-round adversarial debate. Pick by intent (`code`, `redteam`, `factcheck`, `panel`, `deep`, `arena`…), not by model name.
- **Reads your documents** — pass file paths and Rasputin parses `pdf`, `docx`, `pptx`, `xlsx`, `csv`, `md`, `txt` and source files into the prompt automatically.
- **Iterative dialogue** — keep a session open and follow up with the whole council or a single model.
- **Graceful degradation** — if one provider is down, the others still answer; you never lose the whole run.
- **Speaks your language** — prompts ship in English, but the council replies in the language you wrote in.

## Install

Requires Python 3.11+ and [`uv`](https://docs.astral.sh/uv/). You need API keys for the providers you want to use: `OPENAI_API_KEY` and `MISTRAL_API_KEY` are required, `GEMINI_API_KEY` is optional.

### Recommended: run directly from GitHub with `uvx`

No clone, no path to manage. Add this to your Claude Code MCP config (`.mcp.json` or your Claude config):

```json
{
  "mcpServers": {
    "rasputin": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/frescodicredito/rasputin", "rasputin"],
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "MISTRAL_API_KEY": "...",
        "GEMINI_API_KEY": "..."
      }
    }
  }
}
```

`uvx` fetches, builds and runs the server in an isolated environment. To pin a version, append `@v0.1.0` to the URL.

> Prefer setting the API keys as real environment variables (or your OS keychain) over inlining them in `.mcp.json`; the `env` block above is shown for clarity, but inline secrets are easy to leak into dotfiles and backups.

### Alternative: clone for local development

```bash
git clone https://github.com/frescodicredito/rasputin.git
cd rasputin
uv sync
```

```json
{
  "mcpServers": {
    "rasputin": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/rasputin", "python", "-m", "rasputin"],
      "env": { "OPENAI_API_KEY": "sk-...", "MISTRAL_API_KEY": "...", "GEMINI_API_KEY": "..." }
    }
  }
}
```

## Skill (optional but recommended)

The repo ships a Claude Code skill in [`skill/rasputin/`](skill/rasputin/) that teaches Claude how to act as chairman: which preset to pick, how to build context, and how to present the council's verdict. Install it by copying it into your skills directory:

```bash
cp -r skill/rasputin ~/.claude/skills/rasputin
```

With the skill installed, prompts like "convoca il consiglio", "give me a second opinion" or "red team this" route to Rasputin automatically.

## Example

Ask Claude Code something like:

> Convene the council on my landing-page copy — is the hook strong enough?
> `files: ["draft.md"]`, preset `copy`

Claude calls the `rasputin_council` tool, which fans the request out to three models and returns:

```jsonc
{
  "preset": "copy",
  "mode": "opinions",
  "models_consulted": [
    "mistral/mistral-large-latest",
    "openai/gpt-5-mini",
    "gemini/gemini-flash-latest"
  ],
  "opinions": [
    {
      "model": "mistral/mistral-large-latest",
      "response": "Hook buries the benefit in the second line. Lead with the outcome, cut the adjective stack. CTA is generic — make it specific.",
      "cost": { "input_tokens": 612, "output_tokens": 158, "cost_usd": 0.000543 }
    },
    {
      "model": "openai/gpt-5-mini",
      "response": "Clear value prop but the hook reads like a feature list. Tighten to one promise. Drop the third paragraph entirely.",
      "cost": { "input_tokens": 612, "output_tokens": 141, "cost_usd": 0.000389 }
    },
    {
      "model": "gemini/gemini-flash-latest",
      "response": "Strong tone, weak first sentence. The reader doesn't know what they get in 3 seconds. CTA: replace 'Learn more' with the actual action.",
      "cost": { "input_tokens": 612, "output_tokens": 137, "cost_usd": 0.000091 }
    }
  ],
  "consensus_analysis": {
    "agreements": [
      "The hook hides the benefit and must lead with the outcome",
      "The call-to-action is too generic and should name the concrete action"
    ],
    "disagreements": [
      "Mistral wants to keep paragraph 3; GPT wants it cut entirely"
    ],
    "summary": "Solid copy weakened by a slow hook and a vague CTA — both fixable in one pass."
  },
  "total_cost": { "input_tokens": 1836, "output_tokens": 436, "cost_usd": 0.00112 }
}
```

Claude then synthesizes this for you: *"All three flag the same two problems — the hook and the CTA — so fix those first; they split on paragraph 3, so that one's your call."*

## Tools

| Tool | Purpose |
|------|---------|
| `rasputin_council` | Convene a council with a preset (parallel opinions, peer review, or debate). |
| `rasputin_ask` | Single external model, with iterative dialogue via `session_id`. |
| `rasputin_followup` | Continue a session — the whole council or one target model. |
| `rasputin_sessions` | List, inspect, or close active sessions. |

Examples for each tool:

```python
# One quick opinion from a single model (starts a session you can continue)
rasputin_ask(
    message="Is this API design RESTful? Any red flags?",
    model="gemini/gemini-flash-latest",
    context="Internal microservice, Python/FastAPI",
    files=["openapi.yaml"],
)

# Continue that dialogue (single model) or push a question to the whole council
rasputin_followup(session_id="ask-1a2b3c4d", message="And how would you version it?")
rasputin_followup(session_id="council-9f8e7d6c", message="Now focus on security only.")

# Manage sessions
rasputin_sessions(action="list")
rasputin_sessions(action="get", session_id="council-9f8e7d6c")
rasputin_sessions(action="close", session_id="council-9f8e7d6c")
```

Claude/Anthropic model ids are rejected by design — the chairman must stay outside the panel.

## Presets

| Preset | Models | Mode | ~Cost (30K ctx) | Use case |
|--------|--------|------|-----------------|----------|
| `flash` | 1 (Gemini Flash) | opinions | $0.01 | Quick sanity check |
| `nano` | 2 (GPT Nano + Mistral Small) | opinions | $0.01 | Batch / CI |
| `trio` *(default)* | 3 (Gemini + GPT + Mistral) | opinions | $0.10 | General review |
| `code` | 3 (GPT + Gemini + Mistral) | opinions | $0.10 | Code / PR review |
| `copy` | 3 (Mistral + GPT + Gemini) | opinions | $0.04 | Content critique |
| `factcheck` | 3 premium | opinions | $0.18 | Verify claims |
| `redteam` | 3 premium | opinions | $0.18 | Find flaws / attack vectors |
| `consensus` | 3 budget | review (2 rounds) | $0.08 | Go / no-go decisions |
| `devil` | 3 (Mistral-led) | debate (2 rounds) | $0.25 | Stress-test a position |
| `panel` | 3 premium + personas | opinions | $0.18 | Strategic review |
| `deep` | 3 premium | review (peer review) | $0.35 | Critical decisions |
| `arena` | 3 (Pro / Contra / Arbiter) | debate (3 rounds) | $0.80 | Full structured debate |

Aliases: `default→trio`, `quick→flash`, `cheap→nano`, `secure→redteam`, `strategy→panel`, `decide→consensus`, `fight→arena`.

Models and presets are defined in [`rasputin/data/rasputin.yaml`](rasputin/data/rasputin.yaml) — copy it, edit any preset, and point `RASPUTIN_CONFIG` at your file to override the bundled defaults.

## Configuration

| Env var | Purpose |
|---------|---------|
| `OPENAI_API_KEY` | Required for GPT models. |
| `MISTRAL_API_KEY` | Required for Mistral models. |
| `GEMINI_API_KEY` | Optional, enables Gemini models. |
| `RASPUTIN_CONFIG` | Optional path to a custom config YAML. |

Config-file keys worth knowing (under `defaults` / `council`): `max_output_tokens`, `max_file_chars` (per-file text cap), `timeout_per_model`, `max_sessions` (LRU cap on in-memory sessions), `max_cost_usd` (debate budget cap, `0` = off), `session_ttl_minutes`.

## Security

Rasputin sends the content of any file path you pass it to the configured external LLM providers, and reviews of attacker-controlled documents are subject to prompt injection. Treat file inputs as untrusted and run with least privilege — see [SECURITY.md](SECURITY.md).

## Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| `Preset 'X' not found` | Typo in the preset name; see the Presets table or aliases. |
| All opinions return errors / `status: all_models_failed` | Missing or invalid API keys, or no network. Check the `*_API_KEY` env vars; the server logs which keys it sees on startup (stderr). |
| `Model '...' rejected` | You passed a Claude/Anthropic model. The council excludes them by design. |
| Empty or truncated answers | Raise `max_output_tokens`, or the document hit `max_file_chars` — increase it in your config. |
| `File too large` | The file exceeds the 50 MB pre-parse cap. Split it or extract the relevant part. |
| Server runs old code after an edit | Restart Claude Code — the MCP server process is long-lived. |

## Development

```bash
uv sync
uv run pytest          # run the test suite
uv run ruff check .    # lint (F, E9, I, UP)
```

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE) © Francesco Di Credico
