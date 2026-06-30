# AI Team Briefing — Credit Card Nudge Platform

A short guide for explaining this project in meetings with the core AI / ML team.

---

## 1. Elevator pitch (30 seconds)

> We built a **Python ML pipeline** that takes a credit card customer’s **payment history and account state**, and returns a **personalised nudge** for the UI: which message type to show, what tone to use, payment risk scores, and £20 reward eligibility.  
> It uses **feature engineering**, **data cleaning**, **K-Means segmentation**, and **gradient boosting models** — not an LLM. Messages come from **approved templates**.

---

## 2. What problem does it solve?

| Business need | Platform output |
|---------------|-----------------|
| Reduce missed payments | `warning` / `motivational` nudges |
| Promote direct debit | `direct_debit_setup` nudge |
| Drive £20 reward uptake | `reward_led` nudge + eligibility rules |
| Right message for age group | Tone: professional / casual / supportive |
| Prioritise risky accounts | Payment risk probabilities + `high_risk` segment |

---

## 3. End-to-end architecture

```
input/customer.json
        ↓
Data cleaning (validate, dedupe, fix values)
        ↓
Feature engineering (payment stats, utilization, cycle codes)
        ↓
K-Means → behavioural segment (reliable / at_risk / high_risk)
        ↓
ML models → nudge type, tone, risk scores
        ↓
Business rules → reward eligibility, overrides
        ↓
Message templates → final UI text
        ↓
output/customer_recommendation.json
```

---

## 4. What does “training a model” mean?

**Training** = showing an algorithm many **examples** so it learns patterns to **predict outcomes for new customers**.

### Analogy

Like teaching someone to sort mail:
1. You give them **5,000 labelled letters** (training data)
2. They learn: *“This shape of address usually means urgent”*
3. Tomorrow, a **new letter** arrives — they classify it **without** having seen that exact letter before

### In this project

| Step | What happens |
|------|----------------|
| **Training data** | 5,000 synthetic customers (`synthetic_5000_2mo.jsonl`) |
| **Features (inputs)** | 17 numbers per customer (age, utilization, missed payments, segment, …) |
| **Labels (targets)** | What nudge to show, tone, risk scores (from rules + heuristics) |
| **Training** | Algorithm adjusts internal rules to minimise prediction error |
| **Saved artifact** | `models/model_bundle.pkl` — reused at inference |
| **Inference** | New customer JSON → same pipeline → prediction (no retraining) |

**Important:** Training is **offline** (batch). Inference is **online** (per customer, milliseconds).

---

## 5. Libraries we use

| Library | Role in this project |
|---------|----------------------|
| **Python 3.10+** | Runtime |
| **pandas** | Tables / DataFrames for features |
| **numpy** | Numeric arrays |
| **scikit-learn** | ML algorithms and preprocessing |
| ↳ `GradientBoostingClassifier` | Nudge + tone prediction |
| ↳ `GradientBoostingRegressor` | Payment risk (3 targets) |
| ↳ `KMeans` | Customer segmentation |
| ↳ `StandardScaler` | Scale features before K-Means |
| ↳ `LabelEncoder` | Encode nudge/tone categories |
| ↳ `train_test_split` | 80/20 train/holdout evaluation |
| **pytest** | Automated tests |

**Not used:** TensorFlow, PyTorch, OpenAI, LangChain, LLMs.

---

## 6. Models we train (3 capabilities)

| Model | Type | Input | Output |
|-------|------|-------|--------|
| **Nudge model** | Classifier | 17 features | `reminder`, `warning`, `motivational`, `reward_led`, `direct_debit_setup` |
| **Tone model** | Classifier | 17 features | `professional_friendly`, `casual_energetic`, `supportive_clear` |
| **Risk models** | Regressor ×3 | 17 features | Probability of missed / late / minimum-only payment |

All are **Gradient Boosting** — ensemble of decision trees, strong on tabular banking data.

---

## 7. Feature engineering (16 + 1 features)

Raw JSON → numeric vector:

| Feature | Source |
|---------|--------|
| `utilization` | balance ÷ credit limit |
| `missing_payments_last_6_cycles` | From `payment_history_string` |
| `cycle_1/2/3_code` | M/D/L/X/N encoded as 0–5 |
| `customer_segment` | K-Means cluster id (0, 1, 2) |
| … | age, direct debit, arrears, etc. |

Payment history codes: **M** on time, **D** early, **L** late, **X** missed, **N** never paid.

---

## 8. Data cleaning (before training)

`src/data/cleaning.py`

- Remove duplicate `customerId`
- Drop invalid payment history
- Clamp age 18–100, fix negative amounts
- Normalise flags (direct debit, account open)

Same cleaning runs at **inference** for consistency.

---

## 9. K-Means clusters (behavioural, not age)

**3 clusters by default** — named by **payment risk** after fitting:

| Name | Meaning |
|------|---------|
| `reliable` | Low risk — on-time payers, no arrears |
| `at_risk` | Medium risk — some misses/late, may have arrears |
| `high_risk` | High risk — frequent misses, arrears |

**Not the same as personas:**

| Personas (tone) | Clusters (behaviour) |
|-----------------|----------------------|
| Jordan 18–22, Ethan 23–30, Sarah 31+ | Split by payment patterns |
| Controls **wording** | Extra **ML feature** + UI label |

Cluster profiles: `models/segment_profiles.json`

---

## 11. Rules vs ML (hybrid design)

| Component | Approach | Why |
|-----------|----------|-----|
| £20 reward eligibility | **Rules** | Regulatory clarity, auditable |
| Critical nudge override (reward earned) | **Rules** | Business policy |
| Nudge / tone / risk | **ML** | Learns complex patterns |
| Message text | **Templates** | Controlled, compliant copy |

---

## 12. Training data (be honest in meetings)

| Question | Answer |
|----------|--------|
| How many records? | **5,000** synthetic customers |
| Real customer data? | **No** — proof of concept |
| Labels from? | Business rules + heuristics (not historical outcomes) |
| Holdout accuracy? | ~99.9% nudge accuracy (expected — labels from same rules) |

**Production path:** retrain on real labelled data (who paid late, who responded to nudges).

---

## 13. Demo commands for meetings

```powershell
pip install -r requirements.txt
python main.py generate-synthetic
python main.py train --clusters 3
python main.py run
type output\sample_customer_55001_summary.txt
type models\segment_profiles.json
```

---

## 14. Likely questions from core AI team

**Q: Why not an LLM?**  
A: Banking needs predictable, auditable messages. Templates + classical ML are faster, cheaper, and compliant.

**Q: Why gradient boosting vs deep learning?**  
A: Small tabular dataset, interpretable features, no need for neural nets on this scale.

**Q: Why K-Means with k=3?**  
A: Default for 3 risk tiers; configurable via `--clusters`. Names assigned by risk score post-hoc.

**Q: Data leakage?**  
A: Train/test split on customers; segmenter fit on full set before split — in production, fit segmenter on train only only (improvement for v2).

**Q: How do you evaluate?**  
A: Holdout accuracy/MAE today; production needs A/B tests on payment outcomes.

**Q: MLOps / deployment?**  
A: Today: CLI + pickle file. Production: wrap `recommend_for_account()` in an API, version models, monitor drift.

---

## 15. Key files to reference

| File | Purpose |
|------|---------|
| `src/data/cleaning.py` | Data cleaning |
| `src/data/segmentation.py` | K-Means + segment names |
| `src/features/engineer.py` | Feature engineering |
| `src/models/train.py` | Training pipeline |
| `src/inference/recommender.py` | Inference / UI output |
| `models/model_bundle.pkl` | Trained models |
| `docs/GETTING_STARTED.md` | Run instructions |

---

*Use this doc as talking points — adapt depth to your audience.*
