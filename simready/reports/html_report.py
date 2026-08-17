"""HTML report generator for simulation readiness analysis."""

from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from simready.core.analyzer import AnalysisReport
from simready.core.models import CheckResult, Severity


class HtmlReportGenerator:
    """Generate styled HTML reports from analysis results."""

    CSS = """
    :root {
        --bg: #0f172a;
        --surface: #1e293b;
        --border: #334155;
        --text: #e2e8f0;
        --muted: #94a3b8;
        --pass: #22c55e;
        --warn: #f59e0b;
        --error: #ef4444;
        --info: #3b82f6;
        --accent: #6366f1;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: var(--bg);
        color: var(--text);
        line-height: 1.6;
        padding: 2rem;
    }
    .container { max-width: 960px; margin: 0 auto; }
    header {
        border-bottom: 2px solid var(--accent);
        padding-bottom: 1.5rem;
        margin-bottom: 2rem;
    }
    header h1 { font-size: 1.75rem; font-weight: 700; }
    header .subtitle { color: var(--muted); margin-top: 0.25rem; }
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 600;
        margin-top: 0.75rem;
    }
    .badge-ready { background: rgba(34,197,94,0.15); color: var(--pass); }
    .badge-not-ready { background: rgba(239,68,68,0.15); color: var(--error); }
    .summary-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 1rem;
        margin-bottom: 2rem;
    }
    .stat-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        padding: 1rem;
        text-align: center;
    }
    .stat-card .value { font-size: 2rem; font-weight: 700; }
    .stat-card .label { color: var(--muted); font-size: 0.875rem; }
    .stat-pass .value { color: var(--pass); }
    .stat-fail .value { color: var(--error); }
    .stat-warn .value { color: var(--warn); }
    section { margin-bottom: 2rem; }
    section h2 {
        font-size: 1.25rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid var(--border);
    }
    .check-list { list-style: none; }
    .check-item {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 0.75rem;
    }
    .check-item .header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 0.5rem;
    }
    .severity {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        padding: 0.125rem 0.5rem;
        border-radius: 0.25rem;
    }
    .severity-error { background: rgba(239,68,68,0.15); color: var(--error); }
    .severity-warning { background: rgba(245,158,11,0.15); color: var(--warn); }
    .severity-info { background: rgba(59,130,246,0.15); color: var(--info); }
    .check-item.pass { border-left: 3px solid var(--pass); }
    .check-item.fail { border-left: 3px solid var(--error); }
    .check-item.fail.warning-only { border-left-color: var(--warn); }
    .rule-name { font-weight: 600; color: var(--muted); font-size: 0.875rem; }
    .message { font-size: 0.95rem; }
    .recommendation {
        margin-top: 0.5rem;
        padding: 0.5rem 0.75rem;
        background: rgba(99,102,241,0.1);
        border-radius: 0.25rem;
        font-size: 0.875rem;
        color: var(--muted);
    }
    .recommendation strong { color: var(--accent); }
    footer {
        margin-top: 3rem;
        padding-top: 1rem;
        border-top: 1px solid var(--border);
        color: var(--muted);
        font-size: 0.8rem;
        text-align: center;
    }
    """

    def generate(self, report: AnalysisReport) -> str:
        """Generate a complete HTML report string."""
        summary = report.summary()
        project = html.escape(summary["project_name"])
        ready = report.is_simulation_ready
        badge_class = "badge-ready" if ready else "badge-not-ready"
        badge_text = "Simulation Ready" if ready else "Not Simulation Ready"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        passed_html = self._render_checks(report.passed_checks, passed=True)
        failed_html = self._render_checks(report.failed_checks, passed=False)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SimReady Report — {project}</title>
    <style>{self.CSS}</style>
</head>
<body>
    <div class="container">
        <header>
            <h1>KiCad SimReady Report</h1>
            <p class="subtitle">Project: {project}</p>
            <span class="badge {badge_class}">{badge_text}</span>
        </header>

        <div class="summary-grid">
            <div class="stat-card">
                <div class="value">{summary['total_checks']}</div>
                <div class="label">Total Checks</div>
            </div>
            <div class="stat-card stat-pass">
                <div class="value">{summary['passed']}</div>
                <div class="label">Passed</div>
            </div>
            <div class="stat-card stat-fail">
                <div class="value">{summary['failed']}</div>
                <div class="label">Failed</div>
            </div>
            <div class="stat-card stat-warn">
                <div class="value">{summary['warnings']}</div>
                <div class="label">Warnings</div>
            </div>
        </div>

        <section>
            <h2>Failed Checks ({report.fail_count})</h2>
            {"<ul class='check-list'>" + failed_html + "</ul>" if failed_html else "<p style='color:var(--pass)'>All checks passed!</p>"}
        </section>

        <section>
            <h2>Passed Checks ({report.pass_count})</h2>
            {"<ul class='check-list'>" + passed_html + "</ul>" if passed_html else "<p style='color:var(--muted)'>No passed checks recorded.</p>"}
        </section>

        <footer>
            Generated by KiCad SimReady v1.0.0 &mdash; {timestamp}
        </footer>
    </div>
</body>
</html>"""

    def generate_file(
        self, report: AnalysisReport, output_path: str | Path
    ) -> Path:
        """Write HTML report to a file and return the path."""
        path = Path(output_path)
        path.write_text(self.generate(report), encoding="utf-8")
        return path

    def _render_checks(
        self, checks: list[CheckResult], passed: bool
    ) -> str:
        items: list[str] = []
        for check in checks:
            items.append(self._render_check_item(check, passed))
        return "\n".join(items)

    def _render_check_item(self, check: CheckResult, passed: bool) -> str:
        sev_class = f"severity-{check.severity.value}"
        item_class = "pass" if passed else "fail"
        if not passed and check.severity == Severity.WARNING:
            item_class += " warning-only"

        ref = (
            f' <span class="rule-name">[{html.escape(check.component_ref)}]</span>'
            if check.component_ref
            else ""
        )
        rec = ""
        if check.recommendation and not passed:
            rec = (
                f'<div class="recommendation">'
                f"<strong>Recommendation:</strong> "
                f"{html.escape(check.recommendation)}"
                f"</div>"
            )

        return f"""<li class="check-item {item_class}">
            <div class="header">
                <span class="severity {sev_class}">{html.escape(check.severity.value)}</span>
                <span class="rule-name">{html.escape(check.rule_name)}</span>{ref}
            </div>
            <p class="message">{html.escape(check.message)}</p>
            {rec}
        </li>"""
