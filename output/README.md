# Output folder

Nudge recommendations are written here by `python main.py run`.

Each input file `input/<name>.json` produces:

| File | Contents |
|------|----------|
| `output/<name>_recommendation.json` | Nudge type, message, risk scores, reward eligibility |
| `output/<name>_summary.txt` | Human-readable summary for UI review |

Example: `input/sample_customer_55001.json` → `output/sample_customer_55001_recommendation.json`
