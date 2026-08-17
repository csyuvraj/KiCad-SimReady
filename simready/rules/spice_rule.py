"""Rule: Detect missing SPICE models on components."""

from __future__ import annotations

from simready.core.models import CheckResult, Schematic, Severity
from simready.rules.base_rule import BaseRule

# Components that typically need SPICE models for simulation
SPICE_REQUIRED_PREFIXES = ("Q", "U", "D", "M", "J", "X")
SPICE_REQUIRED_LIB_PATTERNS = ("Transistor", "MOSFET", "Diode", "OpAmp", "Regulator")


class SpiceModelRule(BaseRule):
    """Detect components missing SPICE simulation models."""

    name = "SpiceModelRule"
    description = "Checks that active components have SPICE model assignments."

    def check(self, schematic: Schematic) -> list[CheckResult]:
        results: list[CheckResult] = []

        for comp in schematic.components:
            if comp.is_ground or comp.reference.startswith("#"):
                continue

            ref_prefix = comp.reference.rstrip("0123456789")
            needs_spice = ref_prefix in SPICE_REQUIRED_PREFIXES or any(
                pat in comp.lib_id for pat in SPICE_REQUIRED_LIB_PATTERNS
            )

            if not needs_spice:
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

        if not any(r.component_ref for r in results):
            results.append(
                CheckResult(
                    rule_name=self.name,
                    passed=True,
                    message="No active components requiring SPICE models found.",
                    severity=Severity.INFO,
                )
            )

        return results
