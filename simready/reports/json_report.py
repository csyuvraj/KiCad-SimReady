"""JSON report generator for simulation readiness analysis."""

from __future__ import annotations

import json
from pathlib import Path

from simready import __version__
from simready.core.analyzer import AnalysisReport


class JsonReportGenerator:
    """Generate machine-readable JSON reports from analysis results."""

    def generate(self, report: AnalysisReport) -> str:
        """Return a formatted JSON report string."""
        payload = self.build_dict(report)
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def build_dict(self, report: AnalysisReport) -> dict[str, object]:
        """Build the report payload as a dictionary."""
        summary = report.summary()
        return {
            "generator": "KiCad SimReady",
            "version": __version__,
            "summary": summary,
            "passed_checks": [r.to_dict() for r in report.passed_checks],
            "failed_checks": [r.to_dict() for r in report.failed_checks],
            "issues_by_severity": {
                "critical": [r.to_dict() for r in report.critical_issues],
                "error": [r.to_dict() for r in report.errors],
                "warning": [r.to_dict() for r in report.warnings],
            },
        }

    def generate_file(self, report: AnalysisReport, output_path: str | Path) -> Path:
        """Write JSON report to disk and return the path."""
        path = Path(output_path)
        path.write_text(self.generate(report), encoding="utf-8")
        return path
