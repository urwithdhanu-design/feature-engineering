# Getting Started — Run Guide

Step-by-step instructions to install, train, and run the credit card nudge platform using the **input/** and **output/** folders.

---

## Folder layout

```
feature-engineering-account-builder-missing-payments/
├── input/          ← Place customer JSON files here (one customer per file)
├── output/         ← Nudge results written here after you run
├── data/training/  ← Synthetic training data (5000 customers)
├── models/         ← Trained ML models
└── main.py         ← Main entry point
```

| Folder | Purpose |
|--------|---------|
| **input/** | Customer account JSON you want scored |
| **output/** | `_recommendation.json` + `_summary.txt` per customer |
| **data/training/** | `synthetic_5000_2mo.jsonl` used to train models |
| **models/** | `model_bundle.pkl` + `training_metrics.json` |

See also: `input/README.md` and `output/README.md` for field details.

---

## Step 1 — Open terminal in project folder

```powershell
cd C:\projects\feature-engineering-account-builder-missing-payments
```

---

## Step 2 — Install dependencies (one time)

```powershell
pip install -r requirements.txt
```

Requires **Python 3.10+**. If `python` is not found, use `py` instead (e.g. `py main.py run`).

---

## Step 3 — Generate training data (one time)

Creates **5,000 synthetic customers** with **2 months** of payment history each.

```powershell
python main.py generate-synthetic
```

Output file: `data\training\synthetic_5000_2mo.jsonl`

---

## Step 4 — Train models (one time, or after regenerating data)

Training runs **three pre-processing steps** before fitting models:

1. **Data cleaning** — dedupe, validate payment history, fix out-of-range values  
2. **Feature engineering** — derive payment stats, utilization, cycle codes  
3. **K-Means segmentation** — assign each customer to 1 of 3 behavioural clusters  

```powershell
python main.py train
```

Optional: change number of clusters (default 3):

```powershell
python main.py train --clusters 3
```

Saves:
- `models\model_bundle.pkl` (models + K-Means segmenter)
- `models\training_metrics.json` (includes cleaning report)
- `models\segment_profiles.json` (cluster summaries)

Verify training:

```powershell
type models\training_metrics.json
```

Expect `"training_samples": 5000`.

---

## Step 5 — Run automated tests (optional)

```powershell
python -m pytest tests/ -v
```

Expect **11 passed**.

---

## Step 6 — Add a customer to input/

Create a JSON file in `input\`, for example `input\my_customer.json`.

**Minimum required fields:**

| Field | Example |
|-------|---------|
| `customerId` | `"CUST12345"` |
| `payment_history_string` | `"MM"`, `"ML"`, `"M"` |
| `payment_current_due_amount` | `25.0` |
| `payment_due_date` | `"2026-08-09"` |
| `current_balance_amount` | `1200.0` |
| `account_credit_limit_amount` | `5000.0` |
| `minimum_payment_schedule_amount` | `25.0` |
| `direct_debit_active_indicator` | `0` or `1` |
| `months_on_book_counter` | `1` or `2` |
| `age` | `26` |
| `account_status_open_indicator` | `1` |

**Payment history codes** (oldest month → newest):

| Code | Meaning |
|------|---------|
| M | Paid on time |
| D | Paid early |
| L | Paid late |
| X | Missed payment |
| N | Never paid |

A sample file is already included: `input\sample_customer_55001.json`  
(Payment history `MX` = on time, then missed.)

---

## Step 7 — Run the program

Process **all** JSON files in `input\` and write results to `output\`:

```powershell
python main.py run
```

Example output:

```
OK  sample_customer_55001.json  ->  sample_customer_55001_recommendation.json, sample_customer_55001_summary.txt

Processed 1 customer(s). Output folder: ...\output
```

### Output files per customer

| File | Contents |
|------|----------|
| `output\<name>_recommendation.json` | Full result for UI/API (nudge, message, risk, reward) |
| `output\<name>_summary.txt` | Human-readable summary |

---

## Quick copy-paste — full flow

```powershell
cd C:\projects\feature-engineering-account-builder-missing-payments
pip install -r requirements.txt
python main.py generate-synthetic
python main.py train
python -m pytest tests/ -v
python main.py run
type output\sample_customer_55001_summary.txt
```

---

## Other useful commands

| Command | Description |
|---------|-------------|
| `python main.py run` | Process all `input/*.json` → `output/` |
| `python main.py recommend input\my_customer.json` | Single customer, print to terminal |
| `python main.py recommend-random --from-training` | Test with random training record |
| `python main.py demo --persona ethan --scenario MMM` | Demo using persona matrix |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError` | `pip install -r requirements.txt` |
| `Model not found. Run first: python main.py train` | Run `python main.py train` |
| Training file missing | Run `python main.py generate-synthetic` |
| No JSON files in input | Add a `.json` file to `input\` |
| `python` not found | Use `py main.py run` |

---

## What happens before training? (Data cleaning & clustering)

### Short answer

| Step | Included today? |
|------|-----------------|
| **Data cleaning** | **Yes** — `src/data/cleaning.py` |
| **Feature engineering** | **Yes** — `src/features/engineer.py` |
| **K-Means segmentation** | **Yes** — `src/data/segmentation.py` |
| **Model training** | **Yes** — runs after the above |

---

### Training pipeline (current)

```
Load JSONL (5000 records)
        ↓
1. Data cleaning (dedupe, validate, clamp values)
        ↓
2. Feature engineering (payment stats, utilization, cycle codes)
        ↓
3. K-Means segmentation (3 clusters default, StandardScaler + KMeans)
        ↓
4. Label encoding + train/test split (80% / 20%)
        ↓
5. Train Gradient Boosting models (17 features incl. customer_segment)
        ↓
Save model_bundle.pkl + segment_profiles.json
```

**Data cleaning** — removes duplicates, drops invalid payment history, fixes negative amounts, clamps age 18–100.

**K-Means** — groups customers by payment behaviour; adds `customer_segment` (0/1/2) as a model feature. Profiles saved to `models/segment_profiles.json`.

**Inference** — `python main.py run` applies the same cleaning + segment assignment before predicting.

---

## Further reading

- `docs/AI_TEAM_BRIEFING.md` — Meeting talking points for core AI team
- `docs/PLATFORM_GUIDE.md` — How the platform works, LLM, feature engineering FAQ
- `README.md` — Project overview and capabilities
