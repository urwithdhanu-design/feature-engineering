"""Data cleaning pipeline applied before feature engineering and training."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

VALID_HISTORY_PATTERN = re.compile(r"^[MDLXN]+$")
VALID_CODES = set("MDLXN")


@dataclass
class CleaningReport:
    """Summary of records removed or corrected during cleaning."""

    input_count: int = 0
    output_count: int = 0
    duplicates_removed: int = 0
    invalid_removed: int = 0
    records_corrected: int = 0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_count": self.input_count,
            "output_count": self.output_count,
            "duplicates_removed": self.duplicates_removed,
            "invalid_removed": self.invalid_removed,
            "records_corrected": self.records_corrected,
            "warnings": self.warnings[:20],
        }


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _sanitize_history(raw: str | None) -> str | None:
    if raw is None or not str(raw).strip():
        return None
    cleaned = "".join(c for c in str(raw).upper() if c in VALID_CODES)
    if not cleaned or not VALID_HISTORY_PATTERN.match(cleaned):
        return None
    return cleaned


def clean_account(account: dict[str, Any], report: CleaningReport | None = None) -> dict[str, Any] | None:
    """
    Clean and validate a single account record.

    Returns None if the record should be dropped from training.
    """
    corrected = False
    acc = {**account}

    history = _sanitize_history(acc.get("payment_history_string"))
    if history is None:
        return None
    if history != acc.get("payment_history_string"):
        acc["payment_history_string"] = history
        corrected = True

    age = acc.get("age")
    if age is None:
        acc["age"] = 30
        corrected = True
    else:
        clamped = int(_clamp(float(age), 18, 100))
        if clamped != int(age):
            acc["age"] = clamped
            corrected = True

    limit = float(acc.get("account_credit_limit_amount", 0) or 0)
    balance = float(acc.get("current_balance_amount", 0) or 0)
    if limit <= 0:
        acc["account_credit_limit_amount"] = 1000.0
        limit = 1000.0
        corrected = True
    if balance < 0:
        acc["current_balance_amount"] = 0.0
        balance = 0.0
        corrected = True

    for key in (
        "payment_current_due_amount",
        "payment_total_due_amount",
        "payment_total_past_due_amount",
        "minimum_payment_schedule_amount",
    ):
        val = float(acc.get(key, 0) or 0)
        if val < 0:
            acc[key] = 0.0
            corrected = True

    dd = acc.get("direct_debit_active_indicator")
    if dd not in (0, 1, "0", "1"):
        acc["direct_debit_active_indicator"] = 0
        corrected = True
    else:
        acc["direct_debit_active_indicator"] = int(dd)

    mob = acc.get("months_on_book_counter")
    if mob is None or int(mob) < 0:
        acc["months_on_book_counter"] = len(history)
        corrected = True

    if acc.get("account_status_open_indicator") not in (0, 1, "0", "1"):
        acc["account_status_open_indicator"] = 1
        corrected = True

    if report and corrected:
        report.records_corrected += 1

    return acc


def clean_accounts(accounts: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], CleaningReport]:
    """
    Deduplicate, validate, and normalize a list of account records.

    - Drops duplicate customerId (keeps first occurrence)
    - Drops records with invalid payment_history_string
    - Clamps/fixes out-of-range numeric values
    """
    report = CleaningReport(input_count=len(accounts))
    seen_ids: set[str] = set()
    cleaned: list[dict[str, Any]] = []

    for account in accounts:
        customer_id = str(account.get("customerId", "")).strip()
        if customer_id:
            if customer_id in seen_ids:
                report.duplicates_removed += 1
                continue
            seen_ids.add(customer_id)

        result = clean_account(account, report=report)
        if result is None:
            report.invalid_removed += 1
            continue
        cleaned.append(result)

    report.output_count = len(cleaned)
    if report.duplicates_removed:
        report.warnings.append(f"Removed {report.duplicates_removed} duplicate customerId(s)")
    if report.invalid_removed:
        report.warnings.append(f"Removed {report.invalid_removed} record(s) with invalid payment history")
    if report.records_corrected:
        report.warnings.append(f"Corrected {report.records_corrected} field value(s) across records")

    return cleaned, report


def clean_account_for_inference(account: dict[str, Any]) -> dict[str, Any]:
    """Clean a single account for inference; applies fixes instead of dropping."""
    report = CleaningReport()
    result = clean_account(account, report=report)
    if result is None:
        fallback = {**account}
        fallback["payment_history_string"] = "M"
        return clean_account(fallback, report=report) or fallback
    return result
