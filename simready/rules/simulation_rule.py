"""Rule: Detect missing simulation metadata."""

from __future__ import annotations

from simready.core.models import CheckResult, Schematic, Severity
from simready.rules.base_rule import BaseRule

SIMULATION_PROPERTIES = ("Sim.Device", "Sim.Pins", "Sim.Params", "Sim.Type")
PASSIVE_PREFIXES = ("R", "C", "L")
ACTIVE_PREFIXES = ("Q", "U", "D", "M", "J", "X")


class SimulationParameterRule(BaseRule):
    """Detect components missing simulation metadata fields."""

    name = "SimulationParameterRule"
    description = "Checks that simulatable components have required Sim.* properties."

    def check(self, schematic: Schematic) -> list[CheckResult]:
        results: list[CheckResult] = []

        for comp in schematic.components:
            if comp.is_ground or comp.reference.startswith("#"):
                continue

            ref_prefix = comp.reference.rstrip("0123456789")
            if ref_prefix not in PASSIVE_PREFIXES + ACTIVE_PREFIXES:
                continue

            missing = self._missing_sim_properties(comp, ref_prefix)

            if not missing:
                results.append(
                    CheckResult(
                        rule_name=self.name,
                        passed=True,
                        message=f"{comp.reference} has complete simulation metadata.",
                        severity=Severity.INFO,
                        component_ref=comp.reference,
                    )
                )
            else:
                results.append(
                    CheckResult(
                        rule_name=self.name,
                        passed=False,
                        message=(
                            f"{comp.reference} is missing simulation properties: "
                            f"{', '.join(missing)}."
                        ),
                        severity=Severity.WARNING,
                        component_ref=comp.reference,
                        recommendation=(
                            f"Open Simulation Model Editor for {comp.reference} and "
                            "configure Sim.Device, Sim.Pins, and Sim.Params as needed."
                        ),
                    )
                )

        return results

    @staticmethod
    def _missing_sim_properties(comp, ref_prefix: str) -> list[str]:
        missing: list[str] = []
        if ref_prefix in PASSIVE_PREFIXES:
            if not comp.properties.get("Sim.Device") and not comp.properties.get("Sim.Type"):
                missing.append("Sim.Device")
            if not comp.properties.get("Sim.Pins"):
                missing.append("Sim.Pins")
        elif ref_prefix in ACTIVE_PREFIXES:
            if not comp.spice_model:
                missing.append("Sim.Device")
            if not comp.sim_pins:
                missing.append("Sim.Pins")
        return missing
