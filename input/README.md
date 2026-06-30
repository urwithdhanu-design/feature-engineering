# Input folder

Place **one customer per JSON file** here. The `run` command reads every `*.json` file and writes results to `../output/`.

## Required fields

| Field | Example |
|-------|---------|
| `customerId` | `"CUST12345"` |
| `payment_history_string` | `"MM"`, `"ML"`, `"M"` (oldest → newest) |
| `payment_current_due_amount` | `25.0` |
| `payment_due_date` | `"2026-08-09"` |
| `current_balance_amount` | `1200.0` |
| `account_credit_limit_amount` | `5000.0` |
| `minimum_payment_schedule_amount` | `25.0` |
| `direct_debit_active_indicator` | `0` or `1` |
| `months_on_book_counter` | `2` |
| `age` | `26` (for message tone) |
| `account_status_open_indicator` | `1` |

## Payment history codes

| Code | Meaning |
|------|---------|
| M | Paid on time |
| D | Paid early |
| L | Paid late |
| X | Missed |
| N | Never paid |

## Run

```powershell
python main.py run
```
