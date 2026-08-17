"""Integration tests for the plugin CLI and end-to-end workflow."""

from pathlib import Path

import pytest

from simready.core.analyzer import Analyzer
from simready.core.parser import SchematicParser
from simready.plugin import create_analyzer, run_analysis
from simready.reports.html_report import HtmlReportGenerator

SAMPLE_SCH = Path(__file__).parent.parent / "examples" / "sample.kicad_sch"


@pytest.fixture
def sample_schematic():
    if not SAMPLE_SCH.exists():
        pytest.skip("Sample schematic not found")
    return SAMPLE_SCH


class TestEndToEnd:
    def test_full_analysis_pipeline(self, sample_schematic, tmp_path):
        parser = SchematicParser()
        schematic = parser.parse_file(sample_schematic)

        analyzer = create_analyzer()
        report = analyzer.analyze(schematic)

        assert report.total_checks > 0
        assert report.summary()["project_name"] == "sample"

    def test_run_analysis_generates_report(self, sample_schematic, tmp_path):
        report_path = run_analysis(str(sample_schematic), str(tmp_path))
        assert report_path.exists()
        content = report_path.read_text()
        assert "KiCad SimReady Report" in content

    def test_sample_has_expected_issues(self, sample_schematic):
        parser = SchematicParser()
        schematic = parser.parse_file(sample_schematic)
        analyzer = create_analyzer()
        report = analyzer.analyze(schematic)

        failed_rules = {r.rule_name for r in report.failed_checks}
        # R2 has missing value and footprint; Q1 missing SPICE model
        assert "ComponentValueRule" in failed_rules
        assert "SpiceModelRule" in failed_rules

    def test_create_analyzer_has_all_rules(self):
        analyzer = create_analyzer()
        rule_names = {r.name for r in analyzer.rules}
        expected = {
            "SpiceModelRule",
            "GroundReferenceRule",
            "ComponentValueRule",
            "FootprintRule",
            "FloatingPinRule",
            "SimulationParameterRule",
        }
        assert expected == rule_names
