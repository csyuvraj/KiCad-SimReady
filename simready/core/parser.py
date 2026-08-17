"""Parser for KiCad .kicad_sch schematic files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional, Union

from simready.core.models import Component, Net, Pin, Schematic


class SExpressionParser:
    """Minimal S-expression parser for KiCad schematic files."""

    def __init__(self, text: str):
        self._text = text
        self._pos = 0
        self._length = len(text)

    def parse(self) -> list:
        """Parse the entire S-expression document."""
        self._skip_whitespace()
        if self._pos >= self._length:
            return []
        return self._parse_list()

    def _parse_list(self) -> list:
        if self._text[self._pos] != "(":
            raise ValueError(f"Expected '(' at position {self._pos}")
        self._pos += 1
        result: list[Any] = []
        while self._pos < self._length:
            self._skip_whitespace()
            if self._pos >= self._length:
                break
            if self._text[self._pos] == ")":
                self._pos += 1
                return result
            token = self._parse_token()
            result.append(token)
        return result

    def _parse_token(self) -> Union[str, list]:
        self._skip_whitespace()
        if self._pos >= self._length:
            return ""
        if self._text[self._pos] == "(":
            return self._parse_list()
        return self._parse_atom()

    def _parse_atom(self) -> str:
        self._skip_whitespace()
        if self._pos >= self._length:
            return ""
        if self._text[self._pos] == '"':
            return self._parse_quoted_string()
        return self._parse_bare_atom()

    def _parse_quoted_string(self) -> str:
        self._pos += 1  # skip opening quote
        start = self._pos
        while self._pos < self._length and self._text[self._pos] != '"':
            if self._text[self._pos] == "\\":
                self._pos += 2
            else:
                self._pos += 1
        result = self._text[start : self._pos]
        if self._pos < self._length:
            self._pos += 1  # skip closing quote
        return result

    def _parse_bare_atom(self) -> str:
        start = self._pos
        while self._pos < self._length and self._text[self._pos] not in " \t\n\r()":
            self._pos += 1
        return self._text[start : self._pos]

    def _skip_whitespace(self) -> None:
        while self._pos < self._length and self._text[self._pos] in " \t\n\r":
            self._pos += 1


def _find_elements(tree: list, tag: str) -> list[list]:
    """Recursively find all sub-lists starting with tag."""
    results: list[list] = []
    if not isinstance(tree, list) or len(tree) == 0:
        return results
    if tree[0] == tag:
        results.append(tree)
    for item in tree:
        if isinstance(item, list):
            results.extend(_find_elements(item, tag))
    return results


def _get_property(symbol: list, prop_name: str) -> str:
    """Extract a property value from a symbol S-expression."""
    for item in symbol:
        if isinstance(item, list) and len(item) >= 3 and item[0] == "property":
            if item[1] == prop_name:
                return str(item[2])
    return ""


def _parse_symbol(symbol: list) -> Component:
    """Parse a symbol element into a Component."""
    lib_id = ""
    uuid = ""
    pins: list[Pin] = []

    for item in symbol:
        if not isinstance(item, list):
            continue
        tag = item[0] if item else ""
        if tag == "lib_id" and len(item) >= 2:
            lib_id = str(item[1])
        elif tag == "uuid" and len(item) >= 2:
            uuid = str(item[1])
        elif tag == "pin" and len(item) >= 2:
            pin_num = str(item[1])
            pin_uuid = ""
            pin_name = ""
            for sub in item[2:]:
                if isinstance(sub, list):
                    if sub[0] == "uuid" and len(sub) >= 2:
                        pin_uuid = str(sub[1])
                    elif sub[0] == "name" and len(sub) >= 2:
                        pin_name = str(sub[1])
            pins.append(Pin(number=pin_num, name=pin_name, uuid=pin_uuid))

    return Component(
        reference=_get_property(symbol, "Reference"),
        value=_get_property(symbol, "Value"),
        lib_id=lib_id,
        footprint=_get_property(symbol, "Footprint"),
        uuid=uuid,
        properties=_extract_all_properties(symbol),
        pins=pins,
    )


def _extract_all_properties(symbol: list) -> dict[str, str]:
    """Extract all property key-value pairs from a symbol."""
    props: dict[str, str] = {}
    for item in symbol:
        if isinstance(item, list) and len(item) >= 3 and item[0] == "property":
            props[str(item[1])] = str(item[2])
    return props


def _parse_labels(tree: list) -> dict[str, list[tuple[float, float]]]:
    """Extract label positions keyed by net name."""
    labels: dict[str, list[tuple[float, float]]] = {}
    for label_type in ("label", "global_label", "hierarchical_label", "power"):
        for elem in _find_elements(tree, label_type):
            name = ""
            x, y = 0.0, 0.0
            for item in elem:
                if isinstance(item, str) and item not in (
                    "label",
                    "global_label",
                    "hierarchical_label",
                    "power",
                ):
                    if not name:
                        name = item
                elif isinstance(item, list) and item[0] == "at" and len(item) >= 3:
                    try:
                        x = float(item[1])
                        y = float(item[2])
                    except (ValueError, TypeError):
                        pass
            if name:
                labels.setdefault(name, []).append((x, y))
    return labels


def _parse_wires(tree: list) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Extract wire segments as coordinate pairs."""
    wires: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for wire in _find_elements(tree, "wire"):
        pts = None
        for item in wire:
            if isinstance(item, list) and item[0] == "pts":
                pts = item
                break
        if pts:
            coordinates: list[tuple[float, float]] = []
            for pt in pts[1:]:
                if isinstance(pt, list) and pt[0] == "xy" and len(pt) >= 3:
                    try:
                        coordinates.append((float(pt[1]), float(pt[2])))
                    except (ValueError, TypeError):
                        pass
            for i in range(len(coordinates) - 1):
                wires.append((coordinates[i], coordinates[i + 1]))
    return wires


class SchematicParser:
    """Parse KiCad .kicad_sch files into Schematic models."""

    def parse_file(self, filepath: str | Path) -> Schematic:
        """Parse a schematic file from disk."""
        path = Path(filepath)
        text = path.read_text(encoding="utf-8")
        return self.parse_text(text, filename=str(path))

    def parse_text(self, text: str, filename: str = "unknown.kicad_sch") -> Schematic:
        """Parse schematic text content."""
        parser = SExpressionParser(text)
        tree = parser.parse()

        project_name = Path(filename).stem
        version = ""
        if isinstance(tree, list) and len(tree) >= 2:
            for item in tree[1:]:
                if isinstance(item, list) and item[0] == "version" and len(item) >= 2:
                    version = str(item[1])

        components: list[Component] = []
        for symbol in _find_elements(tree, "symbol"):
            comp = _parse_symbol(symbol)
            if comp.reference:
                components.append(comp)

        nets = self._build_nets(tree, components)

        return Schematic(
            filename=filename,
            project_name=project_name,
            components=components,
            nets=nets,
            version=version,
        )

    def _build_nets(
        self, tree: list, components: list[Component]
    ) -> list[Net]:
        """Build net connectivity from labels, wires, and pin positions."""
        labels = _parse_labels(tree)
        wires = _parse_wires(tree)

        # Collect pin positions from symbols
        pin_positions: dict[tuple[float, float], tuple[str, str]] = {}
        for symbol in _find_elements(tree, "symbol"):
            ref = _get_property(symbol, "Reference")
            if not ref:
                continue
            for item in symbol:
                if isinstance(item, list) and item[0] == "pin" and len(item) >= 2:
                    pin_num = str(item[1])
                    for sub in item[2:]:
                        if isinstance(sub, list) and sub[0] == "at" and len(sub) >= 3:
                            try:
                                x, y = float(sub[1]), float(sub[2])
                                pin_positions[(x, y)] = (ref, pin_num)
                            except (ValueError, TypeError):
                                pass

        # Map label names to connected pins via wire proximity
        net_connections: dict[str, list[tuple[str, str]]] = {}
        tolerance = 0.01

        def points_close(
            p1: tuple[float, float], p2: tuple[float, float]
        ) -> bool:
            return abs(p1[0] - p2[0]) < tolerance and abs(p1[1] - p2[1]) < tolerance

        def find_connected_points(
            start: tuple[float, float], visited: set[tuple[float, float]]
        ) -> set[tuple[float, float]]:
            """Flood-fill wire connectivity from a starting point."""
            connected = {start}
            visited.add(start)
            changed = True
            while changed:
                changed = False
                for (w1, w2) in wires:
                    for pt in (w1, w2):
                        if pt in connected:
                            other = w2 if pt == w1 else w1
                            if other not in connected:
                                connected.add(other)
                                changed = True
            return connected

        for net_name, label_positions in labels.items():
            connections: list[tuple[str, str]] = []
            for label_pos in label_positions:
                wire_points = find_connected_points(label_pos, set())
                for pin_pos, (ref, pin_num) in pin_positions.items():
                    for wp in wire_points:
                        if points_close(pin_pos, wp):
                            connections.append((ref, pin_num))
                            break
            net_connections[net_name] = connections

        # Also detect GND from power symbols
        for comp in components:
            if comp.is_ground:
                for pin in comp.pins:
                    net_connections.setdefault("GND", []).append(
                        (comp.reference, pin.number)
                    )

        nets: list[Net] = []
        for name, connections in net_connections.items():
            net = Net(name=name)
            for ref, pin_num in connections:
                net.add_connection(ref, pin_num)
            nets.append(net)

        # Mark pins as connected
        for net in nets:
            for ref, pin_num in net.connected_pins:
                comp = next((c for c in components if c.reference == ref), None)
                if comp:
                    for pin in comp.pins:
                        if pin.number == pin_num:
                            pin.connected = True
                            pin.net_name = net.name

        return nets
