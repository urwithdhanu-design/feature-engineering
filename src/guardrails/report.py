"""Guardrail check results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GuardrailCheck:
    name: str
    category: str
    passed: bool
    action: str | None = None
    detail: str | None = None


@dataclass
class GuardrailReport:
    """Outcome of all guardrail checks for one recommendation."""

    passed: bool = True
    checks: list[GuardrailCheck] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list)

    def add(self, check: GuardrailCheck) -> None:
        self.checks.append(check)
        if not check.passed:
            self.passed = False
        if check.action:
            self.actions_taken.append(check.action)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "actions_taken": self.actions_taken,
            "checks": [
                {
                    "name": c.name,
                    "category": c.category,
                    "passed": c.passed,
                    "action": c.action,
                    "detail": c.detail,
                }
                for c in self.checks
            ],
        }
