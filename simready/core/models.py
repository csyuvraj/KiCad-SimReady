"""Data models for KiCad schematic analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    """Check result severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class Pin:
    """A pin on a schematic symbol."""

    number: str
    name: str = ""
    uuid: str = ""
    connected: bool = False
    net_name: Optional[str] = None


@dataclass
class Component:
    """A schematic component (symbol instance)."""

    reference: str
    value: str = ""
    lib_id: str = ""
    footprint: str = ""
    uuid: str = ""
    properties: dict[str, str] = field(default_factory=dict)
    pins: list[Pin] = field(default_factory=list)

    @property
    def spice_model(self) -> str:
        """Return SPICE model from Sim.Device or SPICE_MODEL property."""
        return (
            self.properties.get("Sim.Device", "")
            or self.properties.get("SPICE_MODEL", "")
            or self.properties.get("SpiceModel", "")
        )

    @property
    def sim_pins(self) -> str:
        """Return simulation pin mapping."""
        return self.properties.get("Sim.Pins", "")

    @property
    def sim_params(self) -> str:
        """Return simulation parameters."""
        return self.properties.get("Sim.Params", "")

    @property
    def is_passive(self) -> bool:
        """Check if component is a passive (R, C, L)."""
        ref_prefix = self.reference.rstrip("0123456789")
        return ref_prefix in ("R", "C", "L")

    @property
    def is_ground(self) -> bool:
        """Check if component is a ground symbol."""
        return "GND" in self.lib_id.upper() or self.reference.upper().startswith("#PWR")


@dataclass
class Net:
    """An electrical net in the schematic."""

    name: str
    connected_pins: list[tuple[str, str]] = field(default_factory=list)

    def add_connection(self, component_ref: str, pin_number: str) -> None:
        """Record a pin connected to this net."""
        self.connected_pins.append((component_ref, pin_number))


@dataclass
class Schematic:
    """Parsed KiCad schematic representation."""

    filename: str
    project_name: str = ""
    components: list[Component] = field(default_factory=list)
    nets: list[Net] = field(default_factory=list)
    version: str = ""

    @property
    def net_map(self) -> dict[str, Net]:
        """Return nets indexed by name."""
        return {net.name: net for net in self.nets}

    def get_component(self, reference: str) -> Optional[Component]:
        """Find a component by reference designator."""
        for comp in self.components:
            if comp.reference == reference:
                return comp
        return None


@dataclass
class CheckResult:
    """Result of a single rule check."""

    rule_name: str
    passed: bool
    message: str
    severity: Severity = Severity.WARNING
    component_ref: Optional[str] = None
    recommendation: str = ""

    def to_dict(self) -> dict:
        """Serialize to dictionary for reporting."""
        return {
            "rule_name": self.rule_name,
            "passed": self.passed,
            "message": self.message,
            "severity": self.severity.value,
            "component_ref": self.component_ref,
            "recommendation": self.recommendation,
        }
