"""Tests for S-expression and schematic parser."""

import pytest
from pathlib import Path

from simready.core.parser import SExpressionParser, SchematicParser

SAMPLE_SCH = Path(__file__).parent.parent / "examples" / "sample.kicad_sch"

MINIMAL_SCH = """(kicad_sch
  (version 20250114)
  (generator "eeschema")
  (symbol
    (lib_id "Device:R")
    (uuid "abc-123")
    (property "Reference" "R1")
    (property "Value" "10k")
    (property "Footprint" "Resistor_SMD:R_0805")
    (property "Sim.Device" "R")
    (property "Sim.Pins" "1=passive 2=passive")
    (pin "1" (uuid "p1") (at 100 80 0))
    (pin "2" (uuid "p2") (at 140 80 0))
  )
  (global_label "GND" (at 160 140 0))
)"""


class TestSExpressionParser:
    def test_parse_simple_list(self):
        parser = SExpressionParser('(hello "world" 42)')
        result = parser.parse()
        assert result == ["hello", "world", "42"]

    def test_parse_nested(self):
        parser = SExpressionParser('(outer (inner "value"))')
        result = parser.parse()
        assert result[0] == "outer"
        assert result[1] == ["inner", "value"]

    def test_parse_quoted_string_with_spaces(self):
        parser = SExpressionParser('(prop "Reference" "R1")')
        result = parser.parse()
        assert result[2] == "R1"


class TestSchematicParser:
    def test_parse_minimal_schematic(self):
        parser = SchematicParser()
        sch = parser.parse_text(MINIMAL_SCH, filename="test.kicad_sch")
        assert sch.project_name == "test"
        assert len(sch.components) == 1
        assert sch.components[0].reference == "R1"
        assert sch.components[0].value == "10k"

    def test_parse_sample_schematic(self):
        if not SAMPLE_SCH.exists():
            pytest.skip("Sample schematic not found")
        parser = SchematicParser()
        sch = parser.parse_file(SAMPLE_SCH)
        assert sch.project_name == "sample"
        assert len(sch.components) >= 3
        refs = {c.reference for c in sch.components}
        assert "R1" in refs
        assert "C1" in refs

    def test_component_properties(self):
        parser = SchematicParser()
        sch = parser.parse_text(MINIMAL_SCH)
        r1 = sch.components[0]
        assert r1.spice_model == "R"
        assert r1.sim_pins == "1=passive 2=passive"
        assert r1.footprint == "Resistor_SMD:R_0805"

    def test_pins_extracted(self):
        parser = SchematicParser()
        sch = parser.parse_text(MINIMAL_SCH)
        r1 = sch.components[0]
        assert len(r1.pins) == 2
        assert r1.pins[0].number == "1"
        assert r1.pins[1].number == "2"

    def test_ground_net_detected(self):
        parser = SchematicParser()
        sch = parser.parse_text(MINIMAL_SCH)
        net_names = {n.name for n in sch.nets}
        assert "GND" in net_names


LIB_SYMBOL_SCH = """(kicad_sch
  (version 20250114)
  (lib_symbols
    (symbol "Device:R"
      (property "Reference" "R")
      (property "Value" "R")
      (symbol "R_0_1"
        (pin passive line (at 0 3.81 270) (name "~") (number "1"))
        (pin passive line (at 0 -3.81 90) (name "~") (number "2"))
      )
    )
  )
  (symbol
    (lib_id "Device:R")
    (at 100 80 0)
    (uuid "r1")
    (property "Reference" "R1")
    (property "Value" "10k")
  )
  (wire (pts (xy 100 76.19) (xy 120 76.19)))
  (wire (pts (xy 120 76.19) (xy 120 60)))
  (label "VIN" (at 120 60 0))
  (no_connect (at 100 83.81))
)"""


class TestLibrarySymbols:
    def _parse(self):
        return SchematicParser().parse_text(LIB_SYMBOL_SCH, filename="lib.kicad_sch")

    def test_lib_symbol_definitions_are_not_components(self):
        sch = self._parse()
        assert [c.reference for c in sch.components] == ["R1"]

    def test_pin_geometry_from_library_symbol(self):
        sch = self._parse()
        positions = {p.number: p.position for p in sch.components[0].pins}
        assert positions["1"] == (100.0, 76.19)
        assert positions["2"] == (100.0, 83.81)

    def test_wire_t_junction_joins_label_to_pin(self):
        sch = self._parse()
        pin1 = sch.components[0].pins[0]
        assert pin1.connected is True
        assert pin1.net_name == "VIN"

    def test_no_connect_marker_applied(self):
        sch = self._parse()
        pin2 = sch.components[0].pins[1]
        assert pin2.no_connect is True
