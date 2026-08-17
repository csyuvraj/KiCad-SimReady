"""Analysis engine that orchestrates rule execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from simready.core.models import CheckResult, Schematic, Severity
from simready.rules.base_rule import BaseRule


@dataclass
class AnalysisReport:
    """Aggregated results from running all rules."""

    schematic: Schematic
    results: list[CheckResult] = field(default_factory=list)

    @property
    def passed_checks(self) -> list[CheckResult]:
        return [r for r in self.results if r.passed]

    @property
    def failed_checks(self) -> list[CheckResult]:
        return [r for r in self.results if not r.passed]

    @property
    def errors(self) -> list[CheckResult]:
        return [r for r in self.failed_checks if r.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[CheckResult]:
        return [r for r in self.failed_checks if r.severity == Severity.WARNING]

    @property
    def total_checks(self) -> int:
        return len(self.results)

    @property
    def pass_count(self) -> int:
        return len(self.passed_checks)

    @property
    def fail_count(self) -> int:
        return len(self.failed_checks)

    @property
    def is_simulation_ready(self) -> bool:
        """True when no error-severity failures exist."""
        return len(self.errors) == 0

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
        }


class Analyzer:
    """Run simulation readiness rules against a schematic."""

    def __init__(self, rules: Optional[list[BaseRule]] = None):
        self._rules: list[BaseRule] = rules or []

    def add_rule(self, rule: BaseRule) -> None:
        """Register a rule with the analyzer."""
        self._rules.append(rule)

    def set_rules(self, rules: list[BaseRule]) -> None:
        """Replace all registered rules."""
        self._rules = list(rules)

    @property
    def rules(self) -> list[BaseRule]:
        return list(self._rules)

    def analyze(self, schematic: Schematic) -> AnalysisReport:
        """Run all rules and return an aggregated report."""
        results: list[CheckResult] = []
        for rule in self._rules:
            try:
                rule_results = rule.check(schematic)
                results.extend(rule_results)
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
