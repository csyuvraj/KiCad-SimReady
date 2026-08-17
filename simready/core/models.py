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


class ReadinessLevel(str, Enum):
    """Overall schematic simulation readiness level.
    
    Attributes:
        READY: All error-severity checks passed; schematic is ready to simulate.
        NOT_READY: One or more error-severity checks failed; issues must be resolved.
    """

    READY = "ready"
    NOT_READY = "not_ready"


@dataclass
class Pin:
    """A pin on a schematic symbol.
    
    Attributes:
        number: Pin identifier (e.g., "1", "2", "A1").
        name: Human-readable pin name (e.g., "VCC", "GND", "NC").
        uuid: KiCad unique identifier for the pin.
        connected: Boolean flag indicating if pin has net connection.
        net_name: Name of the net this pin is connected to, if any.
    """

    number: str
    name: str = ""
    uuid: str = ""
    connected: bool = False
    net_name: Optional[str] = None


@dataclass
class Component:
    """A schematic component (symbol instance).
    
    Attributes:
        reference: Reference designator (e.g., "R1", "U1", "Q1").
        value: Component value (e.g., "10k", "100n", "2N3904").
        lib_id: Library identifier from KiCad (e.g., "Device:R").
        footprint: PCB footprint assignment (e.g., "Resistor_SMD:R_0805").
        uuid: KiCad unique identifier.
        properties: Dictionary of custom properties (includes Sim.Device, Sim.Pins, etc).
        pins: List of Pin objects belonging to this component.
    """

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
        """Return simulation pin mapping from Sim.Pins property."""
        return self.properties.get("Sim.Pins", "")

    @property
    def sim_params(self) -> str:
        """Return simulation parameters from Sim.Params property."""
        return self.properties.get("Sim.Params", "")

    @property
    def is_passive(self) -> bool:
        """Check if component is a passive device (R, C, L).
        
        Returns:
            True if reference prefix is R, C, or L.
        """
        ref_prefix = self.reference.rstrip("0123456789")
        return ref_prefix in ("R", "C", "L")

    @property
    def is_ground(self) -> bool:
        """Check if component is a ground symbol.
        
        Returns:
            True if lib_id contains "GND" or reference starts with "#PWR".
        """
        return "GND" in self.lib_id.upper() or self.reference.upper().startswith("#PWR")


@dataclass
class Net:
    """An electrical net in the schematic.
    
    Attributes:
        name: Net name (e.g., "GND", "VCC", "VOUT").
        connected_pins: List of (component_ref, pin_number) tuples connected to this net.
    """

    name: str
    connected_pins: list[tuple[str, str]] = field(default_factory=list)

    def add_connection(self, component_ref: str, pin_number: str) -> None:
        """Record a pin connected to this net.
        
        Args:
            component_ref: Reference designator of the component.
            pin_number: Pin number on the component.
        """
        self.connected_pins.append((component_ref, pin_number))


@dataclass
class Schematic:
    """Parsed KiCad schematic representation.
    
    Attributes:
        filename: Path to the .kicad_sch file.
        project_name: Project name (extracted from filename).
        components: List of Component objects in the schematic.
        nets: List of Net objects representing electrical connections.
        version: KiCad file format version (e.g., "20250114").
    """

    filename: str
    project_name: str = ""
    components: list[Component] = field(default_factory=list)
    nets: list[Net] = field(default_factory=list)
    version: str = ""

    @property
    def net_map(self) -> dict[str, Net]:
        """Return nets indexed by name for quick lookup.
        
        Returns:
            Dictionary mapping net name to Net object.
        """
        return {net.name: net for net in self.nets}

    def get_component(self, reference: str) -> Optional[Component]:
        """Find a component by reference designator.
        
        Args:
            reference: Reference designator to search for.
            
        Returns:
            Component object if found, None otherwise.
        """
        for comp in self.components:
            if comp.reference == reference:
                return comp
        return None


@dataclass
class CheckResult:
    """Result of a single rule check.
    
    Attributes:
        rule_name: Name of the rule that produced this result.
        passed: True if the check passed, False if it failed.
        message: Human-readable message describing the check result.
        severity: Severity level (INFO, WARNING, ERROR).
        component_ref: Reference designator of affected component, if applicable.
        recommendation: Actionable recommendation to fix the issue.
    """

    rule_name: str
    passed: bool
    message: str
    severity: Severity = Severity.WARNING
    component_ref: Optional[str] = None
    recommendation: str = ""

    def to_dict(self) -> dict:
        """Serialize to dictionary for reporting.
        
        Returns:
            Dictionary representation with string severity value.
        """
        return {
            "rule_name": self.rule_name,
            "passed": self.passed,
            "message": self.message,
            "severity": self.severity.value,
            "component_ref": self.component_ref,
            "recommendation": self.recommendation,
        }
