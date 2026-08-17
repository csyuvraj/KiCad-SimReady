"""Rule: Detect missing component values."""

from __future__ import annotations

import re

from simready.core.models import CheckResult, Schematic, Severity
from simready.rules.base_rule import BaseRule

VALUE_REQUIRED_PREFIXES = ("R", "C", "L")
PLACEHOLDER_VALUES = {"", "~", "?", "TBD", "VALUE", "VAL"}


class ComponentValueRule(BaseRule):
    """Detect passive components with missing or placeholder values."""

    name = "ComponentValueRule"
    description = "Checks that resistors, capacitors, and inductors have valid values."

    def check(self, schematic: Schematic) -> list[CheckResult]:
        results: list[CheckResult] = []

        for comp in schematic.components:
            ref_prefix = comp.reference.rstrip("0123456789")
            if ref_prefix not in VALUE_REQUIRED_PREFIXES:
                continue

            value = comp.value.strip()
            if self._is_valid_value(value, ref_prefix):
                results.append(
                    CheckResult(
                        rule_name=self.name,
                        passed=True,
                        message=f"{comp.reference} has value '{value}'.",
                        severity=Severity.INFO,
                        component_ref=comp.reference,
                    )
                )
            else:
                unit_hint = {"R": "Ω", "C": "F", "L": "H"}.get(ref_prefix, "")
                results.append(
                    CheckResult(
                        rule_name=self.name,
                        passed=False,
                        message=f"{comp.reference} has missing or invalid value '{value}'.",
                        severity=Severity.ERROR,
                        component_ref=comp.reference,
                        recommendation=(
                            f"Set a valid value for {comp.reference} "
                            f"(e.g., 10k for resistor, 100n for capacitor). "
                            f"Unit: {unit_hint}"
                        ),
                    )
                )

        return results

    @staticmethod
    def _is_valid_value(value: str, prefix: str) -> bool:
        if value.upper() in PLACEHOLDER_VALUES:
            return False
        patterns = {
            "R": r"^\d+(\.\d+)?[kKmMμu]?$|^\d+(\.\d+)?[ΩOhm]*$",
            "C": r"^\d+(\.\d+)?[pPnNμu]?F?$",
            "L": r"^\d+(\.\d+)?[pPnNμu]?H?$",
        }
        pattern = patterns.get(prefix, r".+")
        return bool(re.match(pattern, value, re.IGNORECASE))
