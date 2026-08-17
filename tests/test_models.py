"""Tests for data models."""

from simready.core.models import (
    CheckResult,
    Component,
    Net,
    Pin,
    ReadinessLevel,
    Schematic,
    Severity,
)


class TestComponent:
    def test_spice_model_from_sim_device(self):
        comp = Component(
            reference="Q1",
            properties={"Sim.Device": "NPN"},
        )
        assert comp.spice_model == "NPN"

    def test_spice_model_fallback(self):
        comp = Component(
            reference="Q1",
            properties={"SPICE_MODEL": "2N3904"},
        )
        assert comp.spice_model == "2N3904"

    def test_is_passive(self):
        assert Component(reference="R1").is_passive is True
        assert Component(reference="C1").is_passive is True
        assert Component(reference="L1").is_passive is True
        assert Component(reference="U1").is_passive is False

    def test_is_ground(self):
        assert Component(reference="#PWR01", lib_id="power:GND").is_ground is True
        assert Component(reference="R1", lib_id="Device:R").is_ground is False


class TestNet:
    def test_add_connection(self):
        net = Net(name="VCC")
        net.add_connection("R1", "1")
        assert ("R1", "1") in net.connected_pins


class TestCheckResult:
    def test_to_dict(self):
        result = CheckResult(
            rule_name="TestRule",
            passed=False,
            message="Something failed",
            severity=Severity.ERROR,
            component_ref="R1",
            recommendation="Fix it",
        )
        d = result.to_dict()
        assert d["rule_name"] == "TestRule"
        assert d["passed"] is False
        assert d["severity"] == "error"


class TestSchematic:
    def test_get_component(self):
        sch = Schematic(
            filename="test.kicad_sch",
            components=[
                Component(reference="R1"),
                Component(reference="C1"),
            ],
        )
        assert sch.get_component("R1") is not None
        assert sch.get_component("X9") is None

    def test_net_map(self):
        sch = Schematic(
            filename="test.kicad_sch",
            nets=[Net(name="GND"), Net(name="VCC")],
        )
        assert "GND" in sch.net_map
        assert sch.net_map["VCC"].name == "VCC"


class TestSeverity:
    def test_weights_ordered(self):
        assert Severity.ERROR.weight > Severity.WARNING.weight > Severity.INFO.weight


class TestReadinessLevel:
    def test_labels(self):
        assert ReadinessLevel.READY.label == "Simulation Ready"
        assert ReadinessLevel.NEEDS_REVIEW.label == "Needs Review"
        assert ReadinessLevel.NOT_READY.label == "Not Simulation Ready"


class TestComponentHelpers:
    def test_ref_prefix(self):
        assert Component(reference="R12").ref_prefix == "R"
        assert Component(reference="#PWR01").ref_prefix == "#PWR"

    def test_is_power(self):
        assert Component(reference="#PWR01", lib_id="power:VCC").is_power is True
        assert Component(reference="R1", lib_id="Device:R").is_power is False


class TestPin:
    def test_no_connect_defaults_false(self):
        assert Pin(number="1").no_connect is False
