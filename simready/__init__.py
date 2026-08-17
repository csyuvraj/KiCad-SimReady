"""KiCad SimReady - Simulation Readiness Analyzer.

A KiCad 9 Eeschema Action Plugin that analyzes schematics for SPICE simulation readiness.
"""

from simready.core.analyzer import Analyzer, AnalysisReport
from simready.core.models import (
    CheckResult,
    Component,
    Net,
    Pin,
    ReadinessLevel,
    Schematic,
    Severity,
)
from simready.core.parser import SchematicParser

__version__ = "1.0.0"
__all__ = [
    "Analyzer",
    "AnalysisReport",
    "CheckResult",
    "Component",
    "Net",
    "Pin",
    "ReadinessLevel",
    "Schematic",
    "Severity",
    "SchematicParser",
]
