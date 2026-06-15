---
name: rasputin
description: >
  Multi-LLM council (Gemini, GPT, Mistral) with 12 presets for external review of
  documents. Supports file input (pdf, docx, pptx, xlsx) and iterative dialogue.
  Use when external opinion, parere esterno, second opinion, red team, convoca il
  consiglio, chiedi a Rasputin, opinione esterna, verifica esterna. Do NOT use for
  generating content, writing code, or tasks without external LLM need.
---

# Rasputin — Multi-LLM Council

External LLM opinions for Claude Code. You send the document + context, Rasputin queries
Gemini + GPT + Mistral in parallel, you synthesize the results for the user.

**You are the chairman.** Rasputin returns raw opinions. You synthesize.

> The examples below are partly in Italian on purpose: Rasputin replies in the
> language of the input, so a prompt written in Italian gets Italian opinions back.

## Quick Start

1. User asks for review/opinion on a document
2. Choose preset (default: `trio`)
3. Build context string (brief, target, objectives)
4. Call `rasputin_council(message=..., preset="trio", context=..., files=[...])`
5. Receive opinions from 3 LLMs + consensus analysis
6. Synthesize for user using the chairman output format below

## Rules

1. **Never include Claude models** in the council (intra-family bias since you synthesize). Rasputin enforces this and will reject Claude/Anthropic model ids.
2. **Always provide context** — don't just send the document, include brief/target/objectives
3. **Present individual opinions** before your synthesis — transparency matters
4. **Highlight disagreements** — when models diverge, that's the most valuable signal

## Examples

### Example 1: Review a presentation

**User**: "Dammi un parere esterno su questa presentazione" (Give me an external opinion on this presentation)

**Process**:
1. Identify document: `/path/to/pitch.pptx`
2. Build context from conversation: "Pitch for early-stage VC investors, seed round 2M"
3. Choose preset: `trio` (standard review)

**Call**:
```
rasputin_council(
    message="Analizza questa presentazione: struttura argomentativa, coerenza dei dati, punti deboli, cosa manca.",
    preset="trio",
    context="Pitch deck for early-stage VC investors. Goal: 2M EUR seed round. Target: Italian tech funds.",
    files=["/path/to/pitch.pptx"]
)
```

**Output to user**:
```markdown
## External Opinions (3 models — preset: trio)

### Consensus
- The value proposition is clear but TAM/SAM/SOM lacks sources
- The team slide is the strongest point

### Disagreements
- **Gemini**: the financial plan is too optimistic (10x growth in 12 months with no basis)
- **GPT**: the financial plan is aggressive but acceptable for seed stage
- **Mistral**: a competition slide is missing entirely

### My synthesis
The unanimous call on TAM sources should be acted on immediately. On the financial
plan, I lean toward Gemini — for this audience, prudence pays. The competition slide
flagged by Mistral is indeed absent and should be added.

**Cost**: $0.05 | Models: Gemini Flash, GPT-5 Mini, Mistral Large
```

### Example 2: Red team a strategy document

**User**: "Trova tutti i problemi in questa strategia" (Find every problem in this strategy)

**Call**:
```
rasputin_council(
    message="Red team this strategy. Find every flaw, risk, and logical gap.",
    preset="redteam",
    context="Q2 social media strategy for a luxury fashion brand. Budget 50K. Target Gen Z Italy.",
    files=["/path/to/strategy.docx"]
)
```

### Example 3: Quick check on copy

**User**: "Does this LinkedIn post work?"

**Call**:
```
rasputin_ask(
    message="Critique this LinkedIn post: hook, clarity, tone, CTA. Be direct.",
    model="gemini/gemini-flash-latest",
    context="Personal LinkedIn post about AI and marketing. Tone: direct, provocative."
)
```

## Preset Selection Guide

| User needs | Preset | Why |
|------------|--------|-----|
| Quick check, "does this make sense?" | `flash` | 1 model, $0.01, 3 sec |
| Standard review (DEFAULT) | `trio` | 3 families, balanced |
| Code review | `code` | Models tuned for bugs/security |
| Copy/content critique | `copy` | Creative critique focus |
| Verify facts and data | `factcheck` | Claim-by-claim verification |
| Find flaws and risks | `redteam` | Adversarial, severity-rated |
| Stress-test an argument | `devil` | 2 rounds, all contrarian |
| Strategic review (multi-perspective) | `panel` | 3 personas: strategist, engineer, skeptic |
| Go/no-go decision | `consensus` | 2 rounds, convergence-seeking |
| Critical/irreversible decision | `deep` | Premium + anonymous peer review |
| Full debate, see both sides | `arena` | PRO vs CONTRA vs ARBITER, 3 rounds |
| Batch/CI, ultra-cheap | `nano` | 2 budget models, $0.01 |

**Default**: `trio` unless user specifies otherwise or context suggests a specific preset.

## How to Build Context

Before calling Rasputin, assemble the right context for the external LLMs.

| Document type | Include as `context` parameter |
|---------------|-------------------------------|
| Presentation/pitch | Brief, target audience, objectives, market context |
| Strategy document | Brief, constraints, competitive context, decisions made |
| Data analysis/report | Research question, methodology, sources, known limits |
| Copy/social content | Brand guidelines, tone, channel, target, desired CTA |
| Code/architecture | Requirements, technical constraints, architectural decisions, stack |

Pass file paths via the `files` parameter. Rasputin parses pdf, docx, pptx, xlsx, csv, txt.

## Chairman Output Format

When presenting council results to the user:

```markdown
## External Opinions ({N} models — preset: {preset})

### Consensus
[Points where all models agree — strong signals]

### Disagreements
[Where models disagree — specify each position. Most valuable part]

### My synthesis
[Your assessment integrating external opinions with context
the external models didn't have. What's actionable, what to ignore.]

**Cost**: ${total_cost} | Models: {model_list}
```

Don't just parrot opinions. Add value by connecting them to context only you have.

## References

- `references/presets.md` — Full preset details (models, prompts, costs, latency)
