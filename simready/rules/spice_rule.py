"""Rule: Detect missing SPICE models on components."""

from __future__ import annotations

from simready.core.models import CheckResult, Component, Schematic, Severity
from simready.rules.base_rule import BaseRule

# Components that typically need SPICE models for simulation
SPICE_REQUIRED_PREFIXES = ("Q", "U", "D", "M", "J", "X")
SPICE_REQUIRED_LIB_PATTERNS = (
    "transistor",
    "mosfet",
    "diode",
    "opamp",
    "amplifier",
    "regulator",
)


class SpiceModelRule(BaseRule):
    """Detect components missing SPICE simulation models."""

    name = "SpiceModelRule"
    description = "Checks that active components have SPICE model assignments."

    def check(self, schematic: Schematic) -> list[CheckResult]:
        """Report SPICE model coverage for active components.

        Args:
            schematic: Schematic to inspect.

        Returns:
            One CheckResult per active component, or a single informational
            result when the schematic contains none.
        """
        results: list[CheckResult] = []

        for comp in schematic.components:
            if comp.is_power or comp.reference.startswith("#"):
                continue

            if not self._needs_spice_model(comp):
                continue

            if comp.spice_model:
                results.append(
                    CheckResult(
                        rule_name=self.name,
                        passed=True,
                        message=f"{comp.reference} has SPICE model '{comp.spice_model}'.",
                        severity=Severity.INFO,
                        component_ref=comp.reference,
                    )
                )
            else:
                results.append(
                    CheckResult(
                        rule_name=self.name,
                        passed=False,
                        message=f"{comp.reference} ({comp.lib_id}) is missing a SPICE model.",
                        severity=Severity.ERROR,
                        component_ref=comp.reference,
                        recommendation=(
                            f"Add Sim.Device property or SPICE model to {comp.reference}. "
                            "Use KiCad's Simulation Model Editor or set Sim.Device manually."
                        ),
                    )
                )

        if not results:
            results.append(
                CheckResult(
                    rule_name=self.name,
                    passed=True,
                    message="No active components requiring SPICE models found.",
                    severity=Severity.INFO,
                )
            )

        return results

    @staticmethod
    def _needs_spice_model(comp: Component) -> bool:
        """Return True when the component is an active device needing a model."""
        lib_id = comp.lib_id.lower()
        return comp.ref_prefix in SPICE_REQUIRED_PREFIXES or any(
            pattern in lib_id for pattern in SPICE_REQUIRED_LIB_PATTERNS
        )
