"""Tests for HTML report generation."""

from simready.core.analyzer import AnalysisReport
from simready.core.models import CheckResult, Schematic, Severity
from simready.reports.html_report import HtmlReportGenerator


class TestHtmlReportGenerator:
    def _sample_report(self):
        sch = Schematic(filename="test.kicad_sch", project_name="test")
        results = [
            CheckResult(
                rule_name="GroundReferenceRule",
                passed=True,
                message="Ground reference detected.",
                severity=Severity.INFO,
            ),
            CheckResult(
                rule_name="ComponentValueRule",
                passed=False,
                message="R2 has missing value.",
                severity=Severity.ERROR,
                component_ref="R2",
                recommendation="Set a valid value for R2.",
            ),
            CheckResult(
                rule_name="FootprintRule",
                passed=False,
                message="R2 missing footprint.",
                severity=Severity.WARNING,
                component_ref="R2",
                recommendation="Assign a footprint.",
            ),
        ]
        return AnalysisReport(schematic=sch, results=results)

    def test_generate_returns_html(self):
        gen = HtmlReportGenerator()
        html = gen.generate(self._sample_report())
        assert "<!DOCTYPE html>" in html
        assert "KiCad SimReady Report" in html
        assert "test" in html

    def test_contains_failed_checks(self):
        gen = HtmlReportGenerator()
        html = gen.generate(self._sample_report())
        assert "R2 has missing value" in html
        assert "Recommendation" in html

    def test_contains_summary_stats(self):
        gen = HtmlReportGenerator()
        html = gen.generate(self._sample_report())
        assert "Total Checks" in html
        assert "Not Simulation Ready" in html

    def test_generate_file(self, tmp_path):
        gen = HtmlReportGenerator()
        out = tmp_path / "report.html"
        gen.generate_file(self._sample_report(), out)
        assert out.exists()
        content = out.read_text()
        assert "KiCad SimReady Report" in content

    def test_passed_checks_rendered(self):
        gen = HtmlReportGenerator()
        html = gen.generate(self._sample_report())
        assert "Ground reference detected" in html

    def test_html_escaping(self):
        sch = Schematic(filename="test.kicad_sch")
        results = [
            CheckResult(
                rule_name="Test",
                passed=False,
                message='Value contains <script>alert("xss")</script>',
                severity=Severity.ERROR,
            )
        ]
        report = AnalysisReport(schematic=sch, results=results)
        html = HtmlReportGenerator().generate(report)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


class TestReadinessRendering:
    def _report(self, results):
        sch = Schematic(filename="test.kicad_sch", project_name="demo")
        return AnalysisReport(schematic=sch, results=results)

    def test_score_and_level_rendered(self):
        report = self._report(
            [
                CheckResult(rule_name="A", passed=True, message="ok", severity=Severity.INFO),
                CheckResult(
                    rule_name="B",
                    passed=False,
                    message="warn",
                    severity=Severity.WARNING,
                    recommendation="Fix the warning",
                ),
            ]
        )
        html = HtmlReportGenerator().generate(report)
        assert "demo" in html
        assert "Needs Review" in html
        assert f">{report.readiness_score}<" in html

    def test_recommendations_section(self):
        report = self._report(
            [
                CheckResult(
                    rule_name="ComponentValueRule",
                    passed=False,
                    message="R2 invalid",
                    severity=Severity.ERROR,
                    component_ref="R2",
                    recommendation="Set a valid value for R2",
                )
            ]
        )
        html = HtmlReportGenerator().generate(report)
        assert "Recommendations (1)" in html
        assert "Set a valid value for R2" in html

    def test_no_recommendations_note(self):
        report = self._report(
            [CheckResult(rule_name="A", passed=True, message="ok", severity=Severity.INFO)]
        )
        html = HtmlReportGenerator().generate(report)
        assert "No action required." in html
        assert "Simulation Ready" in html
