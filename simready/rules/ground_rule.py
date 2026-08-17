"""Rule: Detect missing ground reference."""

from __future__ import annotations

from simready.core.models import CheckResult, Schematic, Severity
from simready.rules.base_rule import BaseRule

GND_NAMES = {"GND", "GROUND", "EARTH", "0", "VSS", "AGND", "DGND", "GNDA", "GNDD"}


class GroundReferenceRule(BaseRule):
    """Detect schematics missing a ground reference net."""

    name = "GroundReferenceRule"
    description = "Checks that the schematic has at least one ground reference."

    def check(self, schematic: Schematic) -> list[CheckResult]:
        """Report whether the schematic provides a SPICE ground reference.

        Args:
            schematic: Schematic to inspect.

        Returns:
            A single CheckResult describing the ground reference status.
        """
        results: list[CheckResult] = []

        ground_nets = [net.name for net in schematic.nets if net.name.upper() in GND_NAMES]
        ground_symbols = [comp.reference for comp in schematic.components if comp.is_ground]

        if ground_nets or ground_symbols:
            detected = ", ".join(ground_nets or ground_symbols)
            results.append(
                CheckResult(
                    rule_name=self.name,
                    passed=True,
                    message=f"Ground reference detected in schematic ({detected}).",
                    severity=Severity.INFO,
                )
            )
        else:
            results.append(
                CheckResult(
                    rule_name=self.name,
                    passed=False,
                    message="No ground reference (GND) found in schematic.",
                    severity=Severity.ERROR,
                    recommendation=(
                        "Add a GND power symbol and connect it to your circuit ground net. "
                        "SPICE simulation requires a global ground reference (node 0)."
                    ),
                )
            )

        return results
