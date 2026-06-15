# Rasputin Presets — Reference

> Models are picked at the capability/cost sweet spot: OpenAI `gpt-5` family
> (same price as the older `gpt-4.1`, a generation ahead), Gemini
> `gemini-flash-latest` for cheap tiers and `gemini-3.1-pro-preview` on premium
> presets, Mistral via `-latest` (already optimal at very low cost). Costs are
> estimates for a ~30K-token document.

## Preset Details

### flash — Quick Sanity Check
- **Models**: gemini/gemini-flash-latest
- **Mode**: opinions (1 model)
- **Cost**: ~$0.01 per 30K doc
- **Latency**: 2-4 sec
- **Prompt**: "Be direct, flag issues only if significant. Skip praise."

### nano — Ultra-Budget
- **Models**: openai/gpt-5-nano + mistral/mistral-small-latest
- **Mode**: opinions
- **Cost**: ~$0.01
- **Latency**: 2-5 sec
- **Prompt**: "Top 3 issues only. Max 100 words."

### trio — Standard Council (DEFAULT)
- **Models**: gemini/gemini-flash-latest + openai/gpt-5-mini + mistral/mistral-large-latest
- **Mode**: opinions
- **Cost**: ~$0.05
- **Latency**: 4-8 sec
- **Prompt**: "Review council. Structure: Key issues, Suggestions, Verdict."
- **When**: 70% of reviews. The go-to preset.

### code — Code Review
- **Models**: openai/gpt-5 + gemini/gemini-flash-latest + mistral/mistral-large-latest
- **Mode**: opinions
- **Cost**: ~$0.12
- **Latency**: 6-12 sec (gpt-5 reasoning)
- **Prompt**: "PR review. Bugs, security, performance, edge cases. Severity: BLOCKER/MAJOR/MINOR."

### copy — Creative Critique
- **Models**: mistral/mistral-large-latest + openai/gpt-5-mini + gemini/gemini-flash-latest
- **Mode**: opinions
- **Cost**: ~$0.05
- **Latency**: 5-10 sec
- **Prompt**: "Copywriter critique: hook, clarity, tone, CTA, cut list."
- **Note**: Mistral first — strong on tone and Romance languages.

### factcheck — Claim Verification
- **Models**: gemini/gemini-3.1-pro-preview + openai/gpt-5 + mistral/mistral-large-latest
- **Mode**: opinions
- **Cost**: ~$0.25
- **Latency**: 8-15 sec
- **Prompt**: "Each claim: VERIFIED/UNVERIFIED/DISPUTED/FALSE. Confidence: high/medium/low."

### redteam — Adversarial
- **Models**: openai/gpt-5 + gemini/gemini-3.1-pro-preview + mistral/mistral-large-latest
- **Mode**: opinions
- **Cost**: ~$0.25
- **Latency**: 8-15 sec
- **Prompt**: "ONLY find flaws. No strengths. Severity: CRITICAL/HIGH/MEDIUM/LOW."

### consensus — Go/No-Go
- **Models**: gemini/gemini-flash-latest + openai/gpt-5-mini + mistral/mistral-small-latest
- **Mode**: review (2 rounds)
- **Cost**: ~$0.10
- **Latency**: 10-15 sec
- **Round 1**: Independent assessment + RECOMMENDATION
- **Round 2**: See all opinions, state AGREEMENT/DISAGREEMENT, final recommendation

### devil — Devil's Advocate
- **Models**: mistral/mistral-large-latest + openai/gpt-5 + gemini/gemini-3.1-pro-preview
- **Mode**: debate (2 rounds)
- **Cost**: ~$0.35
- **Latency**: 15-25 sec
- **Round 1**: "Argue AGAINST. Strongest counterarguments."
- **Round 2**: "Find weaknesses in the defense."
- **Note**: Mistral leads — naturally contrarian.

### panel — Expert Panel
- **Models**: gemini/gemini-3.1-pro-preview (STRATEGIST) + openai/gpt-5 (ENGINEER) + mistral/mistral-large-latest (SKEPTIC)
- **Mode**: opinions (persona-driven)
- **Cost**: ~$0.25
- **Latency**: 10-18 sec
- **Each model has a different persona and prompt.**

### deep — Premium + Peer Review
- **Models**: gemini/gemini-3.1-pro-preview + openai/gpt-5 + mistral/mistral-large-latest
- **Mode**: review (2 rounds with anonymous peer review)
- **Cost**: ~$0.45
- **Latency**: 15-30 sec
- **Round 1**: Thorough analysis
- **Round 2**: Review other opinions anonymously, identify agreements/disagreements

### arena — Structured Debate
- **Models**: openai/gpt-5 (PRO) + mistral/mistral-large-latest (CONTRA) + gemini/gemini-3.1-pro-preview (ARBITER)
- **Mode**: debate (max 3 rounds)
- **Cost**: ~$1.00
- **Latency**: 30-50 sec
- **PRO**: Build strongest case in favor
- **CONTRA**: Dismantle, propose alternatives
- **ARBITER**: Summarize each round, declare winner at end

## Model Pricing Reference (USD per 1M tokens)

| Model | Input | Output |
|---------|------:|-------:|
| gpt-5 | 1.25 | 10.00 |
| gpt-5-mini | 0.25 | 2.00 |
| gpt-5-nano | 0.05 | 0.40 |
| gemini-3.1-pro-preview | 2.00 | 12.00 |
| gemini-flash-latest | 0.30 | 2.50 |
| mistral-large-latest | 0.50 | 1.50 |
| mistral-small-latest | 0.06 | 0.18 |

## Aliases

| Alias | Maps to |
|-------|---------|
| default | trio |
| quick | flash |
| cheap | nano |
| review | trio |
| secure | redteam |
| strategy | panel |
| decide | consensus |
| fight | arena |

## Privacy Notes

- **Gemini**: US servers. API data NOT used for training (paid tier).
- **OpenAI**: US servers. API data NOT used for training.
- **Mistral**: EU servers (Paris). GDPR native. API data NOT used for training.
- For sensitive data, Mistral is the safest option (EU jurisdiction).

Always verify the current data-retention and training policy with each provider.
