"""Rule: Detect missing component values."""

from __future__ import annotations

import re

from simready.core.models import CheckResult, Schematic, Severity
from simready.rules.base_rule import BaseRule

VALUE_REQUIRED_PREFIXES = ("R", "C", "L")
PLACEHOLDER_VALUES = {"", "~", "?", "TBD", "VALUE", "VAL", "DNP"}
UNIT_HINTS = {"R": "Ω", "C": "F", "L": "H"}

# SI prefixes accepted by ngspice / KiCad value fields.
_PREFIX = r"(?:meg|mil|[pnumkKMGTμµ])"
_UNIT = r"(?:ohms?|Ω|R|F|H)?"
# Matches "10k", "4.7uF", "2k2", "1meg", "100 nF", "1e-9", "0R".
VALUE_PATTERN = re.compile(
    rf"^\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\s*(?:{_PREFIX}\s*\d*)?\s*{_UNIT}$",
    re.IGNORECASE,
)


class ComponentValueRule(BaseRule):
    """Detect passive components with missing or placeholder values."""

    name = "ComponentValueRule"
    description = "Checks that resistors, capacitors, and inductors have valid values."

    def check(self, schematic: Schematic) -> list[CheckResult]:
        """Validate the value field of every R/C/L component.

        Args:
            schematic: Schematic to inspect.

        Returns:
            One CheckResult per passive component.
        """
        results: list[CheckResult] = []

        for comp in schematic.components:
            if comp.ref_prefix not in VALUE_REQUIRED_PREFIXES:
                continue

            value = comp.value.strip()
            if self._is_valid_value(value):
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
                unit_hint = UNIT_HINTS.get(comp.ref_prefix, "")
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
    def _is_valid_value(value: str) -> bool:
        """Return True when the value parses as a SPICE-compatible quantity.

        Accepts plain numbers, SI prefixes (including ngspice's ``meg``),
        optional units, and the ``2k2``/``4u7`` engineering notation.

        Args:
            value: Raw component value field.

        Returns:
            True if the value is usable by a simulator.
        """
        value = value.strip()
        if value.upper() in PLACEHOLDER_VALUES:
            return False
        return bool(VALUE_PATTERN.match(value))
