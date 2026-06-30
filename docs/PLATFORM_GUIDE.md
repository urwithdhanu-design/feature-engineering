# Credit Card Nudge Platform — Understanding Guide

This document answers the key questions about how the platform works, what technology it uses, and how it handles real customers day to day.

---

## Table of contents

1. [What does this platform do?](#1-what-does-this-platform-do)
2. [How does it work end to end?](#2-how-does-it-work-end-to-end)
3. [Will it work for a new customer tomorrow?](#3-will-it-work-for-a-new-customer-tomorrow)
4. [Is an LLM used?](#4-is-an-llm-used)
5. [Is feature engineering applied?](#5-is-feature-engineering-applied)
6. [Quick reference](#6-quick-reference)

---

## 1. What does this platform do?

Given a customer's **credit card account data** (payment history, balances, direct debit status, age, etc.), the platform returns:

| Output | Description |
|--------|-------------|
| **Nudge type** | Which intervention to show: reminder, warning, motivational, reward-led, or direct debit setup |
| **Tone** | How to phrase the message (based on age group / persona) |
| **Message** | Ready-to-display text for the UI |
| **Payment risk** | Probability of missed, late, or minimum-only payment next cycle |
| **Reward eligibility** | Whether the customer qualifies for the £20 reward |

**Goal:** Show the right nudge at the right time so customers pay on time, set up direct debit, or earn the £20 reward.

---

## 2. How does it work end to end?

```
Live account data (JSON)
        ↓
Feature engineering (derive stats + numeric features)
        ↓
ML models (nudge, tone, risk predictions)
        ↓
Business rules (reward eligibility + safety overrides)
        ↓
Message templates (tone-specific wording)
        ↓
UI-ready JSON response
```

### Step-by-step

**Step 1 — Enrich the account**  
From `payment_history_string` (e.g. `"MMM"`, `"MML"`, `"XXX"`) the system calculates:
- Missing and on-time payment counts
- Past-due amounts per cycle
- Arrears flags

**Step 2 — Build ML features**  
Raw and derived fields become a numeric feature vector (16 features): age, utilization, direct debit status, cycle codes, etc.

**Step 3 — Run three ML models**

| Model | Output |
|-------|--------|
| Nudge model | reminder / warning / motivational / reward_led / direct_debit_setup |
| Tone model | professional_friendly / casual_energetic / supportive_clear |
| Risk model | risk_missed_payment, risk_late_payment, risk_minimum_only_payment |

**Step 4 — Apply business rules**  
Rules can override the ML output. Example: if the customer qualifies for the £20 reward, nudge is always `reward_led`.

**Step 5 — Format the message**  
Pre-approved templates are filled with amount, due date, and reward progress. No free-form text generation.

**Step 6 — Return JSON to the UI**

Example response:

```json
{
  "nudge_type": "reward_led",
  "tone": "professional_friendly",
  "message": "Congratulations — you've made 3 on-time payments and earned your £20 reward!",
  "payment_risk": {
    "risk_missed_payment": 0.06,
    "risk_late_payment": 0.10,
    "risk_minimum_only_payment": 0.20
  },
  "reward_eligibility": {
    "eligible": true,
    "payments_needed": 0
  },
  "show_nudge": true
}
```

### What are the 177 scenario JSON files for?

They are **not** a customer database and are **not** looked up per customer at runtime.

They are used to:
- **Train** the ML models (`python main.py train`)
- **Test** behaviour across payment patterns
- **Demo** specific cases (`python main.py demo --persona ethan --scenario XXX`)

Real customers go through the same inference pipeline with live JSON — no pre-built file needed.

---

## 3. Will it work for a new customer tomorrow?

**Yes.** You do not need to create a new JSON file for each customer.

Pass their live account data into the recommender:

```bash
python main.py recommend path/to/customer_account.json
```

Or in Python:

```python
from src.inference.recommender import recommend_for_account

result = recommend_for_account({
    "customerId": "CUST9999",
    "age": 27,
    "payment_history_string": "MM",
    "direct_debit_active_indicator": 0,
    "payment_current_due_amount": 45.00,
    "payment_due_date": "2026-07-09",
    "months_on_book_counter": 2,
    "current_balance_amount": 450.00,
    "account_credit_limit_amount": 3000.00,
    "minimum_payment_schedule_amount": 25.0,
    "account_status_open_indicator": 1
})
```

### What your backend must send

**Essential fields**

| Field | Why |
|-------|-----|
| `payment_history_string` | Main signal — last 3–6 cycles encoded as M/D/L/X/N |
| `payment_current_due_amount` | Shown in the message |
| `payment_due_date` | Shown in the message |
| `direct_debit_active_indicator` | Direct debit nudge logic |
| `months_on_book_counter` | £20 reward window (6 months from opening) |
| `current_balance_amount` | Reward eligibility and utilization |
| `minimum_payment_schedule_amount` | Past-due and reward calculations |

**For correct tone (one of these)**

| Option | How tone is chosen |
|--------|-------------------|
| `persona_id` | `ethan`, `jordan`, or `sarah` → fixed tone per persona |
| `age` | Inferred: ≤22 → casual, 23–30 → professional, 31+ → supportive |

If neither is provided, age defaults to 30 (supportive tone).

### Payment history codes

| Code | Meaning |
|------|---------|
| **M** | Paid on time |
| **D** | Paid early |
| **L** | Paid late |
| **X** | Missed payment |
| **N** | Never paid |

String is ordered **oldest → newest**. Example: `"MML"` = on time, on time, then late.

### Personas and tones (training / demo)

| Persona | Age | Tone | Segment |
|---------|-----|------|---------|
| Ethan | 23 | professional_friendly | Working Singles & Couples |
| Jordan | 19 | casual_energetic | Young Starters |
| Sarah | 38 | supportive_clear | Established Families |

### £20 reward criteria (rule-based)

A customer qualifies when **all** of the following are true:

- 3 contractual minimum payments **on time** within 6 months of account opening (not necessarily consecutive)
- Account is active and has a balance so a minimum payment is due
- No missed or late payments
- Good standing: no arrears, not over-limit when payment is due

### Current limitations (production awareness)

| Aspect | Today | Recommendation for production |
|--------|--------|-------------------------------|
| Training data | 177 synthetic scenarios | Retrain on real customer outcomes |
| Model accuracy | Very high on holdout | Validate on live A/B tests |
| Reward logic | Deterministic rules | Works for any customer today |
| Retraining | Manual (`python main.py train`) | Schedule periodic retraining |

---

## 4. Is an LLM used?

**No. There is no Large Language Model (LLM) in this platform.**

No OpenAI, Anthropic, LangChain, or similar — the codebase uses classical ML and fixed templates only.

### What is used instead

| Component | Technology |
|-----------|------------|
| Nudge selection | Gradient Boosting Classifier (scikit-learn) |
| Tone selection | Gradient Boosting Classifier (scikit-learn) |
| Payment risk | Gradient Boosting Regressor (scikit-learn) |
| £20 reward eligibility | Deterministic business rules |
| Message text | Pre-written templates with placeholders |

### How messages are created

Messages are **not generated** by AI. They come from approved templates in `src/messages/templates.py`, for example:

- **Ethan (23):** *"Your payment of £{amount} is due on {due_date}. You're on track — keep it up."*
- **Jordan (19):** *"Heads up — £{amount} due {due_date}. You're doing great!"*
- **Sarah (38):** *"A friendly reminder that £{amount} is due on {due_date}."*

The model chooses **which** nudge and **which** tone; the template supplies the **exact wording**.

### Why no LLM?

- **Predictable** — same input gives the same message (important in regulated banking)
- **Fast and cheap** — runs locally, no API calls
- **Auditable** — every message is from an approved template
- **Structured output** — nudge type and risk scores fit tree-based models well

An LLM could be added later as an optional layer (e.g. light personalization) while keeping nudge type from the ML model. That is **not** implemented today.

---

## 5. Is feature engineering applied?

**Yes. Feature engineering runs on every account at training time and at inference time.** It is not optional and cannot be skipped.

There are **two stages**.

### Stage 1: `enrich_account()` — derive fields from raw data

**File:** `src/features/engineer.py`  
**Also uses:** `src/features/payment_history.py`

Input: raw account JSON with at least `payment_history_string`.

Output: same record plus computed fields, for example:

| Derived field | Source |
|---------------|--------|
| `missing_payments_last_6_cycles` | Count of X and N in history |
| `on_time_payments_last_6_cycles` | Count of M and D in history |
| `payment_total_past_due_amount` | Simulated from L/X/N cycles |
| `_late_payments`, `_never_paid_cycles` | Per-code counts |
| `has_arrears` | Whether past due > 0 |

**Important:** Even if your backend sends `missing_payments_last_6_cycles`, the platform **recomputes** it from `payment_history_string`. That string is the source of truth.

Example: `"MML"` → 0 missing, 1 late, past due £12.50.

### Stage 2: `account_to_features()` — ML feature vector

**File:** `src/features/engineer.py`

Turns the enriched account into **16 numeric features** used by the models:

| Input | Engineered feature |
|-------|-------------------|
| Balance ÷ credit limit | `utilization` |
| `"MML"` per cycle | `cycle_1_code=0`, `cycle_2_code=0`, `cycle_3_code=2` |
| Payment stats | `missing_payments_last_6_cycles`, `has_arrears`, etc. |
| Account fields | `age`, `months_on_book_counter`, `direct_debit_active_indicator`, … |

Full list (`FEATURE_COLUMNS`):

1. age  
2. months_on_book_counter  
3. utilization  
4. payment_total_due_amount  
5. payment_current_due_amount  
6. payment_total_past_due_amount  
7. missing_payments_last_6_cycles  
8. on_time_payments_last_6_cycles  
9. _late_payments  
10. _never_paid_cycles  
11. direct_debit_active_indicator  
12. reward_qualifying_on_time_count  
13. has_arrears  
14. cycle_1_code  
15. cycle_2_code  
16. cycle_3_code  

Cycle codes: M=0, D=1, L=2, X=3, N=4.

### When it runs

**Training** (`python main.py train`):

```
Raw scenario JSON → enrich_account() → account_to_features() → DataFrame → ML fit
```

**Inference** (`python main.py recommend`):

```
Live customer JSON → enrich_account() → account_to_features() → DataFrame → ML predict
```

The ML models **never** see raw JSON — only the 16 engineered features.

### What is not included

This is **domain-specific** feature engineering in Python, not a heavy sklearn pipeline:

| Not used | Used instead |
|----------|--------------|
| LLM embeddings | Numeric cycle codes |
| StandardScaler | Tree models on raw feature values |
| PCA / polynomial features | Hand-picked payment behaviour features |

That is standard practice for gradient boosting on tabular banking data.

### Minimum input for feature engineering

| Priority | Fields |
|----------|--------|
| **Must have** | `payment_history_string`, `minimum_payment_schedule_amount`, `current_balance_amount`, `account_credit_limit_amount` |
| **Should have** | `age`, `months_on_book_counter`, `direct_debit_active_indicator`, payment amounts |

If `payment_history_string` is missing, it defaults to `"MMM"` — avoid this in production.

---

## 6. Quick reference

### Commands

```bash
pip install -r requirements.txt
python main.py generate    # Create 177 training scenario files
python main.py train         # Train models (uses feature engineering)
python main.py demo --persona ethan --scenario MMM
python main.py recommend path/to/customer.json
```

### Key files

| Path | Purpose |
|------|---------|
| `src/features/payment_history.py` | Parse payment history string |
| `src/features/engineer.py` | Feature engineering pipeline |
| `src/rules/reward_eligibility.py` | £20 reward rules |
| `src/rules/nudge_rules.py` | Nudge labels and risk heuristics |
| `src/models/train.py` | Train gradient boosting models |
| `src/inference/recommender.py` | End-to-end recommendation |
| `src/messages/templates.py` | Tone-specific message templates |
| `data/scenarios/` | Training fixtures (59 × 3 personas) |
| `models/model_bundle.pkl` | Saved trained models |

### FAQ summary

| Question | Answer |
|----------|--------|
| How does it work? | JSON in → feature engineering → ML + rules → message out |
| New customer tomorrow? | **Yes** — pass live JSON to `recommend` |
| Need a scenario file per customer? | **No** |
| LLM used? | **No** — scikit-learn + templates |
| Feature engineering applied? | **Yes** — always, train and inference |
| Models see raw JSON? | **No** — only 16 engineered features |

---

*Last updated: June 2026 — aligned with the feature-engineering-account-builder-missing-payments codebase.*
