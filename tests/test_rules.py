"""Tests for simulation readiness rules."""

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
