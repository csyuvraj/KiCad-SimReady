"""Rule: Detect missing simulation metadata."""

from __future__ import annotations

from simready.core.models import CheckResult, Component, Schematic, Severity
from simready.rules.base_rule import BaseRule

PASSIVE_PREFIXES = ("R", "C", "L")
ACTIVE_PREFIXES = ("Q", "U", "D", "M", "J", "X")
# Independent sources are only simulatable once their waveform is described.
SOURCE_PREFIXES = ("V", "I")


class SimulationParameterRule(BaseRule):
    """Detect components missing simulation metadata fields."""

    name = "SimulationParameterRule"
    description = "Checks that simulatable components have required Sim.* properties."

    def check(self, schematic: Schematic) -> list[CheckResult]:
        """Report missing ``Sim.*`` metadata for simulatable components.

        Args:
            schematic: Schematic to inspect.

        Returns:
            One CheckResult per simulatable component.
        """
        results: list[CheckResult] = []

        for comp in schematic.components:
            if comp.is_power or comp.reference.startswith("#"):
                continue

            if comp.ref_prefix not in PASSIVE_PREFIXES + ACTIVE_PREFIXES + SOURCE_PREFIXES:
                continue

            missing = self._missing_sim_properties(comp)

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
    def _missing_sim_properties(comp: Component) -> list[str]:
        """Return the ``Sim.*`` properties the component still needs.

        Args:
            comp: Component under evaluation.

        Returns:
            Names of the missing simulation properties, in report order.
        """
        missing: list[str] = []
        prefix = comp.ref_prefix

        if prefix in PASSIVE_PREFIXES:
            if not comp.spice_model and not comp.properties.get("Sim.Type"):
                missing.append("Sim.Device")
            if not comp.sim_pins:
                missing.append("Sim.Pins")
        elif prefix in ACTIVE_PREFIXES:
            if not comp.spice_model:
                missing.append("Sim.Device")
            if not comp.sim_pins:
                missing.append("Sim.Pins")
        elif prefix in SOURCE_PREFIXES:
            if not comp.spice_model:
                missing.append("Sim.Device")
            if not comp.sim_params:
                missing.append("Sim.Params")

        return missing
