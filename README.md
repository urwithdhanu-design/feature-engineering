# Credit Card Missing Payments — Nudge & Risk ML Platform

Python-based feature engineering and machine learning platform for credit card payment nudges. Predicts which nudge to show in the UI based on payment patterns, £20 reward eligibility, and direct debit status.

## Capabilities

| Module | Purpose |
|--------|---------|
| **Nudge selection** | Predict nudge type: reminder, warning, motivational, reward-led, direct debit setup |
| **Tone selection** | Age-group messaging: Ethan (23), Jordan (19), Sarah (38) |
| **Payment risk** | Probability of late, missed, or minimum-only payment next cycle |
| **Reward eligibility** | £20 reward rules engine |

## Payment history encoding

Three-cycle history string (oldest → newest):

| Code | Meaning |
|------|---------|
| M | Paid on time |
| D | Paid early |
| L | Paid late |
| X | Missed payment |
| N | Never paid |

## Personas

| Persona | Age | Tone | Segment |
|---------|-----|------|---------|
| Ethan | 23 | professional_friendly | Working Singles & Couples |
| Jordan | 19 | casual_energetic | Young Starters |
| Sarah | 38 | supportive_clear | Established Families |

## Quick start

See **[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)** for full install → train → `input/` / `output/` run steps.  
See **[docs/AI_TEAM_BRIEFING.md](docs/AI_TEAM_BRIEFING.md)** §7 for training data & model architecture (meeting talking points).

```bash
pip install -r requirements.txt
python main.py generate-synthetic
python main.py train
python main.py run
python main.py serve   # API at http://127.0.0.1:8000/docs
```

Legacy persona matrix (177 scenarios):

```bash
python main.py generate    # 177 scenario JSON files (59 × 3 personas)
python main.py demo --persona ethan --scenario MMM
```

## Project structure

```
data/
  personas/          # ethan, sarah, jordan configs
  scenarios/         # 59 JSON files per persona
src/
  features/          # Payment history → ML features
  rules/             # Reward eligibility, nudge rules
  models/            # Training pipeline
  messages/          # Tone-specific templates
  inference/         # End-to-end recommender
models/              # Trained model artifacts
schemas/             # Output JSON schema
```

## £20 reward criteria

- 3 contractual minimum payments on time within 6 months of account opening
- Account active with balance generating minimum payment due
- No missed or late payments
- Good standing: no arrears, no over-limit at payment due

## Output example

```json
{
  "nudge_type": "reward_led",
  "tone": "professional_friendly",
  "message": "Congratulations — you've made 3 on-time payments...",
  "payment_risk": {
    "risk_missed_payment": 0.06,
    "risk_late_payment": 0.10,
    "risk_minimum_only_payment": 0.20
  },
  "reward_eligibility": { "eligible": true, "payments_needed": 0 }
}
```
