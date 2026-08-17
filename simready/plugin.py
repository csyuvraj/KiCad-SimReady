"""
KiCad SimReady — Eeschema Action Plugin

Entry point for the KiCad 9 Action Plugin system. When run inside KiCad,
this plugin analyzes the active schematic for simulation readiness and
generates an HTML report.

Installation:
    Copy the simready/ directory and this file into:
        ~/.local/share/kicad/9.0/scripting/plugins/simready/
    Or on macOS:
        ~/Library/Preferences/kicad/9.0/scripting/plugins/simready/
"""

from __future__ import annotations

import os
import sys
import webbrowser
from pathlib import Path

# Ensure the plugin directory is on sys.path for imports
_PLUGIN_DIR = Path(__file__).resolve().parent
if str(_PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_DIR.parent))

from simready.core.analyzer import Analyzer
from simready.core.parser import SchematicParser
from simready.reports.html_report import HtmlReportGenerator
from simready.rules.floating_pin_rule import FloatingPinRule
from simready.rules.footprint_rule import FootprintRule
from simready.rules.ground_rule import GroundReferenceRule
from simready.rules.simulation_rule import SimulationParameterRule
from simready.rules.spice_rule import SpiceModelRule
from simready.rules.value_rule import ComponentValueRule


def create_analyzer() -> Analyzer:
    """Build an analyzer with all default rules."""
    analyzer = Analyzer()
    analyzer.set_rules([
        SpiceModelRule(),
        GroundReferenceRule(),
        ComponentValueRule(),
        FootprintRule(),
        FloatingPinRule(),
        SimulationParameterRule(),
    ])
    return analyzer


def run_analysis(schematic_path: str, output_dir: str | None = None) -> Path:
    """
    Run simulation readiness analysis on a schematic file.

    Args:
        schematic_path: Path to .kicad_sch file.
        output_dir: Directory for HTML report (defaults to schematic directory).

    Returns:
        Path to the generated HTML report.
    """
    parser = SchematicParser()
    schematic = parser.parse_file(schematic_path)

    analyzer = create_analyzer()
    report = analyzer.analyze(schematic)

    out_dir = Path(output_dir) if output_dir else Path(schematic_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / f"{schematic.project_name}_simready_report.html"

    generator = HtmlReportGenerator()
    generator.generate_file(report, report_path)

    return report_path


def _get_schematic_path() -> str | None:
    """Try to get the active schematic path from KiCad."""
    try:
        import eeschema  # noqa: F401 — KiCad bundled module
        # KiCad 9 API: use GetBoard or schematic frame
        from pcbnew import GetBoard  # type: ignore
        board = GetBoard()
        if board:
            project = board.GetFileName()
            if project:
                sch = Path(project).with_suffix(".kicad_sch")
                if sch.exists():
                    return str(sch)
    except ImportError:
        pass

    try:
        import pcbnew  # type: ignore
        board = pcbnew.GetBoard()
        if board and board.GetFileName():
            sch = Path(board.GetFileName()).with_suffix(".kicad_sch")
            if sch.exists():
                return str(sch)
    except (ImportError, AttributeError):
        pass

    return None


class SimReadyPlugin:
    """KiCad Action Plugin wrapper with graceful fallback."""

    def defaults(self):
        """Set plugin metadata (KiCad ActionPlugin interface)."""
        self.name = "KiCad SimReady"
        self.category = "Analyze Schematic"
        self.description = "Check schematic simulation readiness and generate HTML report"
        self.show_toolbar_button = True

    def Run(self):
        """Execute the plugin (KiCad ActionPlugin interface)."""
        sch_path = _get_schematic_path()

        if not sch_path:
            self._show_message(
                "Could not determine schematic path.\n"
                "Please save your project and try again."
            )
            return

        try:
            report_path = run_analysis(sch_path)
            summary = _build_summary(report_path, sch_path)
            self._show_message(summary)
            webbrowser.open(f"file://{report_path}")
        except Exception as exc:
            self._show_message(f"SimReady analysis failed:\n{exc}")

    def _show_message(self, message: str) -> None:
        """Display a message dialog if wx is available, else print."""
        try:
            import wx  # KiCad bundles wxPython
            dlg = wx.MessageDialog(None, message, "KiCad SimReady", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
        except ImportError:
            print(f"[KiCad SimReady] {message}")


def _build_summary(report_path: Path, sch_path: str) -> str:
    """Build a short summary message for the dialog."""
    parser = SchematicParser()
    schematic = parser.parse_file(sch_path)
    analyzer = create_analyzer()
    report = analyzer.analyze(schematic)
    summary = report.summary()

    status = "READY" if summary["simulation_ready"] else "NOT READY"
    return (
        f"Simulation Readiness: {status}\n\n"
        f"Passed: {summary['passed']}  |  "
        f"Failed: {summary['failed']}  |  "
        f"Warnings: {summary['warnings']}\n\n"
        f"Report saved to:\n{report_path}"
    )


# ── KiCad plugin registration ──────────────────────────────────────────
try:
    import pcbnew  # type: ignore

    class SimReadyActionPlugin(SimReadyPlugin, pcbnew.ActionPlugin):
        """Registered KiCad Action Plugin."""

        def defaults(self):
            super().defaults()
            self.plugin_name = "SimReadyActionPlugin"

    SimReadyActionPlugin().register()

except ImportError:
    # Running outside KiCad — plugin registration skipped
    pass


# ── CLI entry point ──────────────────────────────────────────────────────
def main():
    """Command-line interface for standalone usage."""
    import argparse

    arg_parser = argparse.ArgumentParser(
        description="KiCad SimReady — Simulation Readiness Checker"
    )
    arg_parser.add_argument(
        "schematic",
        help="Path to .kicad_sch schematic file",
    )
    arg_parser.add_argument(
        "-o", "--output",
        help="Output directory for HTML report",
        default=None,
    )
    arg_parser.add_argument(
        "--open",
        action="store_true",
        help="Open report in browser after generation",
    )
    args = arg_parser.parse_args()

    sch_path = args.schematic
    if not Path(sch_path).exists():
        print(f"Error: Schematic not found: {sch_path}")
        sys.exit(1)

    report_path = run_analysis(sch_path, args.output)

    parser = SchematicParser()
    schematic = parser.parse_file(sch_path)
    analyzer = create_analyzer()
    report = analyzer.analyze(schematic)
    summary = report.summary()

    status = "READY" if summary["simulation_ready"] else "NOT READY"
    print(f"\nKiCad SimReady — {schematic.project_name}")
    print(f"Status: {status}")
    print(f"Passed: {summary['passed']}  Failed: {summary['failed']}  Warnings: {summary['warnings']}")
    print(f"Report: {report_path}")

    if args.open:
        webbrowser.open(f"file://{report_path}")


if __name__ == "__main__":
    main()
