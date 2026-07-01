"""Output guardrails: hallucination, advice, and language quality."""

from __future__ import annotations

import re
from typing import Any

from src.guardrails.report import GuardrailCheck, GuardrailReport
from src.messages.templates import MESSAGE_TEMPLATES

# Regulated / inappropriate financial advice patterns (not in approved templates)
FORBIDDEN_ADVICE_PATTERNS = [
    r"\binvest\b",
    r"\bguaranteed\b",
    r"\bget rich\b",
    r"\bfinancial advice\b",
    r"\byou must\b",
    r"\blegal action\b",
    r"\bsue\b",
    r"\bbankruptcy\b",
]

FORBIDDEN_LANGUAGE_PATTERNS = [
    r"\bidiot\b",
    r"\bstupid\b",
    r"\bscam\b",
    r"!!!+",
    r"\bURGENT\b",
]

ADVICE_RE = re.compile("|".join(FORBIDDEN_ADVICE_PATTERNS), re.IGNORECASE)
LANGUAGE_RE = re.compile("|".join(FORBIDDEN_LANGUAGE_PATTERNS), re.IGNORECASE)

ALLOWED_NUDGE_TYPES = {
    "reminder",
    "warning",
    "motivational",
    "reward_led",
    "direct_debit_setup",
    "none",
}

ALLOWED_TONES = {"professional_friendly", "casual_energetic", "supportive_clear"}

MAX_MESSAGE_LENGTH = 500


def _all_template_fragments() -> set[str]:
    """Collect substrings that appear in approved templates (anti-hallucination baseline)."""
    fragments: set[str] = set()
    for tone_templates in MESSAGE_TEMPLATES.values():
        for nudge_templates in tone_templates.values():
            for text in nudge_templates.values():
                for word in re.findall(r"[A-Za-z]{4,}", text):
                    fragments.add(word.lower())
    return fragments


TEMPLATE_VOCAB = _all_template_fragments()


def apply_output_guardrails(
    message: str,
    nudge_type: str,
    tone: str,
    report: GuardrailReport,
) -> str:
    """Validate and sanitize final message before returning to UI."""
    safe_message = message

    # Hallucination: message must use approved template vocabulary (no LLM free text)
    unknown_tokens = [
        t
        for t in re.findall(r"[A-Za-z]{5,}", message)
        if t.lower() not in TEMPLATE_VOCAB and t.lower() not in {"lloyds", "credit"}
    ]
    hallucination_risk = len(unknown_tokens) > 8
    if hallucination_risk:
        safe_message = (
            "A friendly reminder about your upcoming payment. "
            "Please check your app for the amount and due date."
        )
        report.add(
            GuardrailCheck(
                name="hallucination_template_drift",
                category="hallucination",
                passed=False,
                action="replaced_with_safe_fallback_message",
                detail=f"Message contained non-template vocabulary: {unknown_tokens[:5]}",
            )
        )
    else:
        report.add(
            GuardrailCheck(
                name="hallucination_template_only",
                category="hallucination",
                passed=True,
                detail="Message composed from approved templates only",
            )
        )

    # Advice guardrail
    if ADVICE_RE.search(safe_message):
        safe_message = re.sub(ADVICE_RE, "", safe_message).strip()
        report.add(
            GuardrailCheck(
                name="regulated_advice",
                category="advice",
                passed=False,
                action="stripped_regulated_advice_phrases",
                detail="Removed language that could constitute financial advice",
            )
        )
    else:
        report.add(
            GuardrailCheck(
                name="regulated_advice",
                category="advice",
                passed=True,
                detail="No regulated advice phrases detected",
            )
        )

    # Proper language
    language_issue = bool(LANGUAGE_RE.search(safe_message))
    if language_issue:
        safe_message = LANGUAGE_RE.sub("", safe_message).strip()
        report.add(
            GuardrailCheck(
                name="proper_language",
                category="proper_language",
                passed=False,
                action="sanitized_inappropriate_language",
                detail="Removed harsh or inappropriate phrasing",
            )
        )
    else:
        report.add(
            GuardrailCheck(
                name="proper_language",
                category="proper_language",
                passed=True,
                detail="Tone and language within brand guidelines",
            )
        )

    if nudge_type not in ALLOWED_NUDGE_TYPES:
        report.add(
            GuardrailCheck(
                name="output_nudge_enum",
                category="misalignment",
                passed=False,
                action="invalid_nudge_type",
                detail=f"Unknown nudge type: {nudge_type}",
            )
        )

    if tone not in ALLOWED_TONES:
        report.add(
            GuardrailCheck(
                name="output_tone_enum",
                category="misalignment",
                passed=False,
                action="invalid_tone",
                detail=f"Unknown tone: {tone}",
            )
        )

    if len(safe_message) > MAX_MESSAGE_LENGTH:
        safe_message = safe_message[: MAX_MESSAGE_LENGTH - 3] + "..."
        report.add(
            GuardrailCheck(
                name="message_length",
                category="proper_language",
                passed=False,
                action="truncated_message",
                detail=f"Message exceeded {MAX_MESSAGE_LENGTH} characters",
            )
        )

    return safe_message
