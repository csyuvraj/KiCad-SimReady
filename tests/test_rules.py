"""Tests for simulation readiness rules."""

import pytest

from simready.core.models import Component, Net, Pin, Schematic, Severity
from simready.rules.floating_pin_rule import FloatingPinRule
from simready.rules.footprint_rule import FootprintRule
from simready.rules.ground_rule import GroundReferenceRule
from simready.rules.simulation_rule import SimulationParameterRule
from simready.rules.spice_rule import SpiceModelRule
from simready.rules.value_rule import ComponentValueRule


def _schematic(*components, nets=None):
    return Schematic(
        filename="test.kicad_sch",
        components=list(components),
        nets=nets or [],
    )


class TestGroundReferenceRule:
    def test_pass_with_ground_net(self):
        sch = _schematic(nets=[Net(name="GND")])
        results = GroundReferenceRule().check(sch)
        assert any(r.passed for r in results)

    def test_fail_without_ground(self):
        sch = _schematic(nets=[Net(name="VCC")])
        results = GroundReferenceRule().check(sch)
        assert any(not r.passed for r in results)
        assert results[0].severity == Severity.ERROR


class TestComponentValueRule:
    def test_pass_valid_resistor(self):
        sch = _schematic(Component(reference="R1", value="10k"))
        results = ComponentValueRule().check(sch)
        assert all(r.passed for r in results)

    def test_fail_missing_value(self):
        sch = _schematic(Component(reference="R1", value="~"))
        results = ComponentValueRule().check(sch)
        assert any(not r.passed for r in results)

    def test_pass_valid_capacitor(self):
        sch = _schematic(Component(reference="C1", value="100n"))
        results = ComponentValueRule().check(sch)
        assert all(r.passed for r in results)

    def test_ignores_non_passive(self):
        sch = _schematic(Component(reference="U1", value=""))
        results = ComponentValueRule().check(sch)
        assert len(results) == 0


class TestSpiceModelRule:
    def test_fail_missing_spice_on_transistor(self):
        sch = _schematic(
            Component(reference="Q1", lib_id="Simulation_SPICE:NPN")
        )
        results = SpiceModelRule().check(sch)
        assert any(not r.passed for r in results)

    def test_pass_with_spice_model(self):
        sch = _schematic(
            Component(
                reference="Q1",
                lib_id="Simulation_SPICE:NPN",
                properties={"Sim.Device": "NPN"},
            )
        )
        results = SpiceModelRule().check(sch)
        assert any(r.passed for r in results)


class TestFootprintRule:
    def test_fail_missing_footprint(self):
        sch = _schematic(Component(reference="R1", footprint=""))
        results = FootprintRule().check(sch)
        assert any(not r.passed for r in results)

    def test_pass_with_footprint(self):
        sch = _schematic(
            Component(reference="R1", footprint="Resistor_SMD:R_0805")
        )
        results = FootprintRule().check(sch)
        assert all(r.passed for r in results)


class TestFloatingPinRule:
    def test_detect_unconnected_pin(self):
        comp = Component(
            reference="R1",
            pins=[Pin(number="1"), Pin(number="2")],
        )
        sch = _schematic(comp)
        results = FloatingPinRule().check(sch)
        assert any(not r.passed for r in results)

    def test_pass_connected_pin(self):
        comp = Component(
            reference="R1",
            pins=[
                Pin(number="1", connected=True, net_name="VCC"),
                Pin(number="2", connected=True, net_name="GND"),
            ],
        )
        sch = _schematic(comp, nets=[Net(name="VCC"), Net(name="GND")])
        results = FloatingPinRule().check(sch)
        assert all(r.passed for r in results)


class TestSimulationParameterRule:
    def test_fail_missing_sim_properties(self):
        sch = _schematic(Component(reference="R1", value="10k"))
        results = SimulationParameterRule().check(sch)
        assert any(not r.passed for r in results)

    def test_pass_complete_sim_metadata(self):
        sch = _schematic(
            Component(
                reference="R1",
                value="10k",
                properties={
                    "Sim.Device": "R",
                    "Sim.Pins": "1=passive 2=passive",
                },
            )
        )
        results = SimulationParameterRule().check(sch)
        assert all(r.passed for r in results)


class TestComponentValueFormats:
    @pytest.mark.parametrize(
        "value", ["10k", "4.7uF", "100n", "1meg", "2k2", "0R", "1e-9", "220 nF", "10"]
    )
    def test_accepts_spice_values(self, value):
        sch = _schematic(Component(reference="R1", value=value))
        assert all(r.passed for r in ComponentValueRule().check(sch))

    @pytest.mark.parametrize("value", ["", "~", "TBD", "value", "abc", "10 kilo ohms"])
    def test_rejects_placeholders(self, value):
        sch = _schematic(Component(reference="C1", value=value))
        assert all(not r.passed for r in ComponentValueRule().check(sch))


class TestPowerSymbolHandling:
    def _power(self):
        return Component(
            reference="#PWR01",
            lib_id="power:GND",
            pins=[Pin(number="1")],
        )

    def test_footprint_rule_skips_power(self):
        assert FootprintRule().check(_schematic(self._power())) == []

    def test_floating_pin_rule_skips_power(self):
        assert FloatingPinRule().check(_schematic(self._power())) == []

    def test_simulation_rule_skips_power(self):
        assert SimulationParameterRule().check(_schematic(self._power())) == []


class TestFloatingPinNoConnect:
    def test_no_connect_pin_passes(self):
        comp = Component(reference="Q1", pins=[Pin(number="3", no_connect=True)])
        assert all(r.passed for r in FloatingPinRule().check(_schematic(comp)))


class TestSpiceModelDetection:
    def test_lib_id_pattern_requires_model(self):
        sch = _schematic(Component(reference="X1", lib_id="Amplifier_Operational:OpAmp"))
        assert any(not r.passed for r in SpiceModelRule().check(sch))

    def test_passives_do_not_require_model(self):
        sch = _schematic(Component(reference="R1", lib_id="Device:R", value="10k"))
        results = SpiceModelRule().check(sch)
        assert all(r.passed for r in results)
        assert all(r.component_ref is None for r in results)


class TestSimulationSources:
    def test_source_requires_sim_params(self):
        sch = _schematic(Component(reference="V1", properties={"Sim.Device": "DC"}))
        results = SimulationParameterRule().check(sch)
        assert any("Sim.Params" in r.message for r in results if not r.passed)
