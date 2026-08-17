"""Tests for the analysis engine."""

from simready.core.analyzer import Analyzer, AnalysisReport
from simready.core.models import CheckResult, Component, Schematic, Severity
from simready.rules.base_rule import BaseRule


class AlwaysPassRule(BaseRule):
    name = "AlwaysPass"

    def check(self, schematic):
        return [CheckResult(rule_name=self.name, passed=True, message="OK")]


class AlwaysFailRule(BaseRule):
    name = "AlwaysFail"

    def check(self, schematic):
        return [
            CheckResult(
                rule_name=self.name,
                passed=False,
                message="Failed",
                severity=Severity.ERROR,
            )
        ]


class TestAnalyzer:
    def _empty_schematic(self):
        return Schematic(filename="test.kicad_sch")

    def test_run_single_rule(self):
        analyzer = Analyzer([AlwaysPassRule()])
        report = analyzer.analyze(self._empty_schematic())
        assert report.pass_count == 1
        assert report.fail_count == 0

    def test_run_multiple_rules(self):
        analyzer = Analyzer([AlwaysPassRule(), AlwaysFailRule()])
        report = analyzer.analyze(self._empty_schematic())
        assert report.total_checks == 2
        assert report.pass_count == 1
        assert report.fail_count == 1

    def test_simulation_ready_no_errors(self):
        analyzer = Analyzer([AlwaysPassRule()])
        report = analyzer.analyze(self._empty_schematic())
        assert report.is_simulation_ready is True

    def test_not_simulation_ready_with_errors(self):
        analyzer = Analyzer([AlwaysFailRule()])
        report = analyzer.analyze(self._empty_schematic())
        assert report.is_simulation_ready is False

    def test_add_rule(self):
        analyzer = Analyzer()
        analyzer.add_rule(AlwaysPassRule())
        report = analyzer.analyze(self._empty_schematic())
        assert report.total_checks == 1

    def test_summary(self):
        analyzer = Analyzer([AlwaysPassRule(), AlwaysFailRule()])
        report = analyzer.analyze(self._empty_schematic())
        summary = report.summary()
        assert summary["total_checks"] == 2
        assert summary["passed"] == 1
        assert summary["failed"] == 1
        assert summary["simulation_ready"] is False

    def test_rule_exception_handled(self):
        class BrokenRule(BaseRule):
            name = "Broken"

            def check(self, schematic):
                raise RuntimeError("boom")

        analyzer = Analyzer([BrokenRule()])
        report = analyzer.analyze(self._empty_schematic())
        assert report.fail_count == 1
        assert "boom" in report.failed_checks[0].message
