"""Rule: Detect missing footprints."""

from __future__ import annotations

from simready.core.models import CheckResult, Schematic, Severity
from simready.rules.base_rule import BaseRule

PLACEHOLDER_FOOTPRINTS = {"", "~", "?", "TBD", "Footprint"}


class FootprintRule(BaseRule):
    """Detect components with missing or placeholder footprints."""

    name = "FootprintRule"
    description = "Checks that components have assigned PCB footprints."

    def check(self, schematic: Schematic) -> list[CheckResult]:
        """Report footprint assignment for every non-power component.

        Args:
            schematic: Schematic to inspect.

        Returns:
            One CheckResult per component.
        """
        results: list[CheckResult] = []

        for comp in schematic.components:
            if comp.is_power or comp.reference.startswith("#"):
                continue

            footprint = comp.footprint.strip()
            if footprint and footprint not in PLACEHOLDER_FOOTPRINTS:
                results.append(
                    CheckResult(
                        rule_name=self.name,
                        passed=True,
                        message=f"{comp.reference} has footprint '{footprint}'.",
                        severity=Severity.INFO,
                        component_ref=comp.reference,
                    )
                )
            else:
                results.append(
                    CheckResult(
                        rule_name=self.name,
                        passed=False,
                        message=f"{comp.reference} is missing a footprint assignment.",
                        severity=Severity.WARNING,
                        component_ref=comp.reference,
                        recommendation=(
                            f"Assign a PCB footprint to {comp.reference} via "
                            "Properties → Footprint, or use CvPcb to map footprints."
                        ),
                    )
                )

        return results
