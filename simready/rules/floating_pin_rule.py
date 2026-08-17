"""Rule: Detect floating (unconnected) pins."""

from __future__ import annotations

from simready.core.models import CheckResult, Schematic, Severity
from simready.rules.base_rule import BaseRule

# Pin types that are acceptable to leave unconnected
OPTIONAL_PIN_NAMES = {"NC", "NOCONNECT", "N/C", "DNC", "UNUSED"}


class FloatingPinRule(BaseRule):
    """Detect pins that appear to be unconnected."""

    name = "FloatingPinRule"
    description = "Checks for pins that are not connected to any net."

    def check(self, schematic: Schematic) -> list[CheckResult]:
        results: list[CheckResult] = []

        connected_set: set[tuple[str, str]] = set()
        for net in schematic.nets:
            for ref, pin_num in net.connected_pins:
                connected_set.add((ref, pin_num))

        for comp in schematic.components:
            if comp.is_ground or comp.reference.startswith("#"):
                continue

            for pin in comp.pins:
                if pin.name.upper() in OPTIONAL_PIN_NAMES:
                    continue

                is_connected = pin.connected or (comp.reference, pin.number) in connected_set

                if is_connected:
                    results.append(
                        CheckResult(
                            rule_name=self.name,
                            passed=True,
                            message=f"{comp.reference} pin {pin.number} is connected.",
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
                                f"{comp.reference} pin {pin.number}"
                                + (f" ({pin.name})" if pin.name else "")
                                + " appears unconnected."
                            ),
                            severity=Severity.WARNING,
                            component_ref=comp.reference,
                            recommendation=(
                                f"Connect {comp.reference} pin {pin.number} to the "
                                "appropriate net, or mark it as No Connect (NC) if intentional."
                            ),
                        )
                    )

        return results
