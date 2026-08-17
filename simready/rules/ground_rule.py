"""Rule: Detect missing ground reference."""

from __future__ import annotations

from simready.core.models import CheckResult, Schematic, Severity
from simready.rules.base_rule import BaseRule

GND_NAMES = {"GND", "GRO", "GROUND", "0", "VSS", "AGND", "DGND"}


class GroundReferenceRule(BaseRule):
    """Detect schematics missing a ground reference net."""

    name = "GroundReferenceRule"
    description = "Checks that the schematic has at least one ground reference."

    def check(self, schematic: Schematic) -> list[CheckResult]:
        results: list[CheckResult] = []

        has_ground_net = any(
            net.name.upper() in GND_NAMES for net in schematic.nets
        )
        has_ground_symbol = any(comp.is_ground for comp in schematic.components)

        if has_ground_net or has_ground_symbol:
            results.append(
                CheckResult(
                    rule_name=self.name,
                    passed=True,
                    message="Ground reference detected in schematic.",
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
