"""Input guardrails: data cleaning and prompt-injection defence."""

from __future__ import annotations

import re
from typing import Any

from src.data.cleaning import clean_account_for_inference
from src.guardrails.report import GuardrailCheck, GuardrailReport

# Patterns suggesting injection or instruction override in free-text fields
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above)\s+instructions",
    r"disregard\s+(the\s+)?(system|policy|rules)",
    r"you\s+are\s+now",
    r"<\s*script",
    r"\{\{.*\}\}",
    r"system\s*:",
    r"assistant\s*:",
    r"jailbreak",
]

INJECTION_RE = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)
MAX_STRING_FIELD_LEN = 256

STRING_FIELDS = (
    "customerId",
    "productId",
    "persona_scenario_name",
    "brand_name",
    "employment_status",
    "fresco_segment",
    "direct_debit_type",
)


def _strip_injection(value: str) -> tuple[str, bool]:
    original = value
    cleaned = INJECTION_RE.sub("", value)
    cleaned = cleaned.strip()
    if len(cleaned) > MAX_STRING_FIELD_LEN:
        cleaned = cleaned[:MAX_STRING_FIELD_LEN]
    return cleaned, cleaned != original


def sanitize_account_input(account: dict[str, Any], report: GuardrailReport) -> dict[str, Any]:
    """Apply data cleaning plus prompt-injection sanitisation on string fields."""
    acc = clean_account_for_inference(account)
    injection_found = False

    for key in STRING_FIELDS:
        raw = acc.get(key)
        if raw is None or not isinstance(raw, str):
            continue
        cleaned, changed = _strip_injection(raw)
        if changed:
            injection_found = True
            acc[key] = cleaned

    report.add(
        GuardrailCheck(
            name="prompt_injection",
            category="prompt_injection",
            passed=not injection_found,
            action="sanitized_input_strings" if injection_found else None,
            detail="Removed suspicious override patterns from input fields"
            if injection_found
            else "No injection patterns detected",
        )
    )

    report.add(
        GuardrailCheck(
            name="input_data_cleaning",
            category="input_validation",
            passed=True,
            detail="Account validated and normalized via data cleaning pipeline",
        )
    )

    return acc
