# Guardrails

Safety and policy controls applied before and after ML inference.

## Categories

| Category | Module | Purpose |
|----------|--------|---------|
| **Input validation** | `input_safety.py` | Data cleaning (existing pipeline) |
| **Prompt injection** | `input_safety.py` | Strip override/injection patterns from string fields |
| **Bias** | `policy.py` | Vulnerable customers → supportive tone, no harsh warning |
| **Goal misalignment** | `policy.py` | Reward-led only when eligible; no nudge if account closed |
| **Misalignment** | `alignment.py` | Nudge severity matches payment risk / segment |
| **Hallucination** | `output_safety.py` | Template-only messages; fallback if drift detected |
| **Advice** | `output_safety.py` | Block regulated financial advice phrases |
| **Proper language** | `output_safety.py` | No harsh/abusive language; length limits |

## Note on LLM guardrails

This platform does **not** use an LLM. Guardrails are adapted for:

- **Hallucination** → template-only messaging (no free-form generation)
- **Prompt injection** → sanitise malicious strings in account JSON fields

## Usage

Guardrails run automatically in `NudgeRecommender.recommend()`.

Response includes:

```json
"guardrails": {
  "passed": true,
  "actions_taken": [],
  "checks": [...]
}
```

## Files

| File | Role |
|------|------|
| `pipeline.py` | Orchestrates input + output guardrails |
| `input_safety.py` | Cleaning + injection defence |
| `policy.py` | Business policy + bias (vulnerability) |
| `alignment.py` | Risk/nudge alignment |
| `output_safety.py` | Message validation |
| `report.py` | Check results dataclass |
