"""Validation & Repair framework for synthetic benchmark samples.

Architecture:
  Each validation rule checks a specific aspect of a BenchmarkSample.
  The ValidationEngine runs all rules, collects results, and can
  attempt auto-repair or flag failures for regeneration.

  Flow: BenchmarkSample → [rules] → ValidationReport → (repaired / flagged)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from synth_bench.canonical.models import BenchmarkSample, DifficultyLevel

# ── Validation Result ─────────────────────────────────────────────────────────


@dataclass
class ValidationResult:
    """Result of a single validation rule check."""

    rule_name: str
    passed: bool
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    auto_repaired: bool = False
    repair_description: str = ""


# ── Validation Report ─────────────────────────────────────────────────────────


@dataclass
class ValidationReport:
    """Complete report of all validation checks on a sample."""

    sample_id: str = ""
    results: list[ValidationResult] = field(default_factory=list)
    auto_repairs_applied: int = 0
    needs_regeneration: bool = False
    difficulty: DifficultyLevel = DifficultyLevel.EASY

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def n_passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def n_failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def n_repaired(self) -> int:
        return sum(1 for r in self.results if r.auto_repaired)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for dataset output."""
        return {
            "sample_id": self.sample_id,
            "all_passed": self.all_passed,
            "auto_repairs_applied": self.auto_repairs_applied,
            "needs_regeneration": self.needs_regeneration,
            "difficulty": self.difficulty.value
            if isinstance(self.difficulty, DifficultyLevel)
            else self.difficulty,
            "results": [
                {
                    "rule": r.rule_name,
                    "passed": r.passed,
                    "message": r.message,
                    "auto_repaired": r.auto_repaired,
                    "repair": r.repair_description if r.auto_repaired else None,
                }
                for r in self.results
            ],
        }


# ── BaseValidator ─────────────────────────────────────────────────────────────


class BaseValidator(ABC):
    """Abstract base for all validation rules.

    Each rule checks exactly one aspect of a BenchmarkSample.
    """

    name: str = "base"
    description: str = ""

    @abstractmethod
    def validate(self, sample: BenchmarkSample) -> ValidationResult:
        """Run this validation rule on a sample.

        Args:
            sample: The benchmark sample to validate.

        Returns:
            ValidationResult with pass/fail and details.
        """
        ...

    def auto_repair(self, sample: BenchmarkSample) -> tuple[BenchmarkSample, str]:
        """Attempt to auto-repair a sample that fails this rule.

        Default: no-op (returns sample unchanged).

        Args:
            sample: The sample to repair.

        Returns:
            (repaired_sample, repair_description)
        """
        return sample, ""


# ── ValidationEngine ──────────────────────────────────────────────────────────


class ValidationEngine:
    """Engine that chains validation rules and produces a ValidationReport.

    Supports:
      - Sequential rule execution
      - Auto-repair on failure (optional)
      - Regeneration flag for unrepairable samples
      - Difficulty scoring based on failures
    """

    def __init__(self, rules: list[BaseValidator] | None = None) -> None:
        self._rules: list[BaseValidator] = rules or []

    def add_rule(self, rule: BaseValidator) -> None:
        """Add a validation rule."""
        self._rules.append(rule)

    def validate(
        self,
        sample: BenchmarkSample,
        auto_repair: bool = True,
    ) -> tuple[BenchmarkSample, ValidationReport]:
        """Run all validation rules on a sample.

        Args:
            sample: The sample to validate.
            auto_repair: Whether to attempt auto-repair on failures.

        Returns:
            (validated_sample, report)
        """
        report = ValidationReport(sample_id=sample.metadata.sample_id)
        current_sample = sample

        for rule in self._rules:
            result = rule.validate(current_sample)

            # Attempt auto-repair if enabled and rule failed
            if not result.passed and auto_repair:
                repaired, repair_desc = rule.auto_repair(current_sample)
                if repair_desc:
                    current_sample = repaired
                    result.auto_repaired = True
                    result.repair_description = repair_desc
                    report.auto_repairs_applied += 1
                    result.passed = rule.validate(current_sample).passed

            report.results.append(result)

        report.needs_regeneration = not report.all_passed

        # Difficulty scoring based on failures
        if report.n_failed > 3:
            report.difficulty = DifficultyLevel.HARD
        elif report.n_failed > 1:
            report.difficulty = DifficultyLevel.MEDIUM
        else:
            report.difficulty = sample.metadata.difficulty

        return current_sample, report
