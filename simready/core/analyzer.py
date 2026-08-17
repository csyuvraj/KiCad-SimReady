"""Analysis engine that orchestrates rule execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from simready.core.models import CheckResult, ReadinessLevel, Schematic, Severity
from simready.rules.base_rule import BaseRule


@dataclass
class AnalysisReport:
    """Aggregated results from running all rules against a schematic.

    Attributes:
        schematic: The analyzed schematic.
        results: Every CheckResult produced by the rules, in execution order.
    """

    schematic: Schematic
    results: list[CheckResult] = field(default_factory=list)

    @property
    def passed_checks(self) -> list[CheckResult]:
        """Return the checks that passed."""
        return [r for r in self.results if r.passed]

    @property
    def failed_checks(self) -> list[CheckResult]:
        """Return the checks that failed."""
        return [r for r in self.results if not r.passed]

    @property
    def errors(self) -> list[CheckResult]:
        """Return failed checks with ERROR severity."""
        return [r for r in self.failed_checks if r.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[CheckResult]:
        """Return failed checks with WARNING severity."""
        return [r for r in self.failed_checks if r.severity == Severity.WARNING]

    @property
    def recommendations(self) -> list[CheckResult]:
        """Return failed checks that carry an actionable recommendation.

        Results are ordered by descending severity so the most important
        fixes appear first in reports.
        """
        with_recommendation = [r for r in self.failed_checks if r.recommendation]
        return sorted(
            with_recommendation, key=lambda r: r.severity.weight, reverse=True
        )

    @property
    def total_checks(self) -> int:
        """Return the total number of checks performed."""
        return len(self.results)

    @property
    def pass_count(self) -> int:
        """Return the number of passed checks."""
        return len(self.passed_checks)

    @property
    def fail_count(self) -> int:
        """Return the number of failed checks."""
        return len(self.failed_checks)

    @property
    def is_simulation_ready(self) -> bool:
        """True when no error-severity failures exist."""
        return len(self.errors) == 0

    @property
    def readiness_level(self) -> ReadinessLevel:
        """Classify the schematic as READY, NEEDS_REVIEW, or NOT_READY."""
        if self.errors:
            return ReadinessLevel.NOT_READY
        if self.failed_checks:
            return ReadinessLevel.NEEDS_REVIEW
        return ReadinessLevel.READY

    @property
    def readiness_score(self) -> int:
        """Return a 0-100 simulation readiness score.

        Each check contributes its severity weight (ERROR 3, WARNING 2,
        INFO 1) to the maximum attainable score; failed checks forfeit their
        weight. Errors therefore cost three times as much as informational
        findings. An empty report scores 100.
        """
        total_weight = sum(r.severity.weight for r in self.results)
        if total_weight == 0:
            return 100
        earned = sum(r.severity.weight for r in self.passed_checks)
        return round(100 * earned / total_weight)

    def summary(self) -> dict:
        """Return a summary dictionary for reporting."""
        return {
            "project_name": self.schematic.project_name,
            "total_checks": self.total_checks,
            "passed": self.pass_count,
            "failed": self.fail_count,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "simulation_ready": self.is_simulation_ready,
            "readiness_level": self.readiness_level.value,
            "readiness_score": self.readiness_score,
        }


class Analyzer:
    """Run simulation readiness rules against a schematic.

    Rules are executed in registration order and isolated from each other:
    a rule that raises is reported as a failed check instead of aborting
    the analysis.
    """

    def __init__(self, rules: Optional[list[BaseRule]] = None):
        self._rules: list[BaseRule] = list(rules) if rules else []

    def add_rule(self, rule: BaseRule) -> None:
        """Register a rule with the analyzer."""
        self._rules.append(rule)

    def set_rules(self, rules: list[BaseRule]) -> None:
        """Replace all registered rules."""
        self._rules = list(rules)

    @property
    def rules(self) -> list[BaseRule]:
        """Return a copy of the registered rules."""
        return list(self._rules)

    def analyze(self, schematic: Schematic) -> AnalysisReport:
        """Run all rules and return an aggregated report.

        Args:
            schematic: Parsed schematic to analyze.

        Returns:
            AnalysisReport containing every CheckResult produced.
        """
        results: list[CheckResult] = []
        for rule in self._rules:
            try:
                results.extend(rule.check(schematic))
            except Exception as exc:
                results.append(
                    CheckResult(
                        rule_name=rule.name,
                        passed=False,
                        message=f"Rule execution failed: {exc}",
                        severity=Severity.ERROR,
                        recommendation="Check schematic file integrity.",
                    )
                )
        return AnalysisReport(schematic=schematic, results=results)
