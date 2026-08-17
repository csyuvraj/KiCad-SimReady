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

import sys
import webbrowser
from pathlib import Path

# Ensure the package parent directory is importable when KiCad loads this
# file directly from its plugins folder.
_PLUGIN_DIR = Path(__file__).resolve().parent
if str(_PLUGIN_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_DIR.parent))

from simready.core.analyzer import Analyzer, AnalysisReport
from simready.core.parser import SchematicParser
from simready.reports.html_report import HtmlReportGenerator
from simready.rules.floating_pin_rule import FloatingPinRule
from simready.rules.footprint_rule import FootprintRule
from simready.rules.ground_rule import GroundReferenceRule
from simready.rules.simulation_rule import SimulationParameterRule
from simready.rules.spice_rule import SpiceModelRule
from simready.rules.value_rule import ComponentValueRule


def create_analyzer() -> Analyzer:
    """Build an analyzer with all default simulation readiness rules.

    Returns:
        Analyzer preloaded with the six built-in rules.
    """
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


def analyze_schematic(schematic_path: str | Path) -> AnalysisReport:
    """Parse a schematic and run every default rule against it.

    Args:
        schematic_path: Path to a ``.kicad_sch`` file.

    Returns:
        Analysis report for the schematic.
    """
    schematic = SchematicParser().parse_file(schematic_path)
    return create_analyzer().analyze(schematic)


def run_analysis(
    schematic_path: str | Path, output_dir: str | Path | None = None
) -> Path:
    """Analyze a schematic and write its HTML report.

    Args:
        schematic_path: Path to .kicad_sch file.
        output_dir: Directory for HTML report (defaults to schematic directory).

    Returns:
        Path to the generated HTML report.
    """
    report = analyze_schematic(schematic_path)
    return write_report(report, schematic_path, output_dir)


def write_report(
    report: AnalysisReport,
    schematic_path: str | Path,
    output_dir: str | Path | None = None,
) -> Path:
    """Write an analysis report to an HTML file.

    Args:
        report: Analysis results to render.
        schematic_path: Source schematic, used for the default output directory.
        output_dir: Directory for the HTML report.

    Returns:
        Path to the generated HTML report.
    """
    out_dir = Path(output_dir) if output_dir else Path(schematic_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / f"{report.schematic.project_name}_simready_report.html"
    return HtmlReportGenerator().generate_file(report, report_path)


def _get_schematic_path() -> str | None:
    """Try to get the active schematic path from KiCad.

    KiCad exposes the open board through ``pcbnew``; the schematic of the
    same project is derived from its filename.

    Returns:
        Path to the active schematic, or None when it cannot be determined.
    """
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
            report = analyze_schematic(sch_path)
            report_path = write_report(report, sch_path)
            self._show_message(_build_summary(report, report_path))
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


def _build_summary(report: AnalysisReport, report_path: Path) -> str:
    """Build a short summary message for the KiCad dialog.

    Args:
        report: Analysis results.
        report_path: Location of the generated HTML report.

    Returns:
        Multi-line summary text.
    """
    summary = report.summary()
    return (
        f"Simulation Readiness: {report.readiness_level.label}\n"
        f"Score: {summary['readiness_score']}/100\n\n"
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
def main() -> None:
    """Command-line entry point.

    Exits with status 0 unless ``--strict`` is given and the schematic is
    not simulation ready, so the CLI can gate CI pipelines.
    """
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
        "--strict",
        action="store_true",
        help="Exit with status 1 when the schematic is not simulation ready",
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

    report = analyze_schematic(sch_path)
    report_path = write_report(report, sch_path, args.output)
    summary = report.summary()

    print(f"\nKiCad SimReady — {summary['project_name']}")
    print(f"Status: {report.readiness_level.label}")
    print(f"Readiness score: {summary['readiness_score']}/100")
    print(
        f"Passed: {summary['passed']}  "
        f"Failed: {summary['failed']}  "
        f"Warnings: {summary['warnings']}"
    )
    print(f"Report: {report_path}")

    if args.open:
        webbrowser.open(f"file://{report_path}")

    if args.strict and not report.is_simulation_ready:
        sys.exit(1)


if __name__ == "__main__":
    main()
