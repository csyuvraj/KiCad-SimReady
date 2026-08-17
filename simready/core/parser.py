"""Parser for KiCad .kicad_sch schematic files.

The parser is deliberately split into three layers:

1. :class:`SExpressionParser` turns raw file text into nested Python lists.
2. Module-level helpers extract symbols, labels, wires, and no-connect flags
   from that tree.
3. :class:`SchematicParser` assembles the extracted data into the
   :mod:`simready.core.models` dataclasses, including net connectivity.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Optional, Union

from simready.core.models import Component, Net, Pin, Schematic

# Coordinates are compared after rounding to this many decimals (mm).
_COORD_DECIMALS = 3
_TOLERANCE = 0.01

Point = tuple[float, float]


class SExpressionParser:
    """Minimal S-expression parser for KiCad schematic files."""

    def __init__(self, text: str):
        self._text = text
        self._pos = 0
        self._length = len(text)

    def parse(self) -> list:
        """Parse the entire S-expression document.

        Returns:
            Nested list representing the document, or an empty list for
            empty input.
        """
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
            result.append(self._parse_token())
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
        chars: list[str] = []
        while self._pos < self._length and self._text[self._pos] != '"':
            if self._text[self._pos] == "\\" and self._pos + 1 < self._length:
                chars.append(self._text[self._pos + 1])
                self._pos += 2
            else:
                chars.append(self._text[self._pos])
                self._pos += 1
        if self._pos < self._length:
            self._pos += 1  # skip closing quote
        return "".join(chars)

    def _parse_bare_atom(self) -> str:
        start = self._pos
        while self._pos < self._length and self._text[self._pos] not in " \t\n\r()":
            self._pos += 1
        return self._text[start : self._pos]

    def _skip_whitespace(self) -> None:
        while self._pos < self._length and self._text[self._pos] in " \t\n\r":
            self._pos += 1


def _tag(element: Any) -> str:
    """Return the leading tag of an S-expression element, or an empty string."""
    if isinstance(element, list) and element and isinstance(element[0], str):
        return element[0]
    return ""


def _find_elements(tree: Any, tag: str, skip_tags: tuple[str, ...] = ()) -> list[list]:
    """Recursively find all sub-lists starting with ``tag``.

    Args:
        tree: S-expression node to search.
        tag: Tag to match (e.g. ``"symbol"``).
        skip_tags: Tags whose subtrees are not searched (e.g. ``"lib_symbols"``).

    Returns:
        List of matching S-expression elements.
    """
    results: list[list] = []
    if not isinstance(tree, list) or not tree:
        return results
    if _tag(tree) in skip_tags:
        return results
    if tree[0] == tag:
        results.append(tree)
    for item in tree:
        if isinstance(item, list):
            results.extend(_find_elements(item, tag, skip_tags))
    return results


def _get_child(element: list, tag: str) -> Optional[list]:
    """Return the first direct child element with the given tag."""
    for item in element:
        if _tag(item) == tag:
            return item
    return None


def _get_property(symbol: list, prop_name: str) -> str:
    """Extract a property value from a symbol S-expression."""
    return _extract_all_properties(symbol).get(prop_name, "")


def _extract_all_properties(symbol: list) -> dict[str, str]:
    """Extract all property key-value pairs from a symbol."""
    props: dict[str, str] = {}
    for item in symbol:
        if _tag(item) == "property" and len(item) >= 3:
            props[str(item[1])] = str(item[2])
    return props


def _parse_at(element: list) -> Optional[tuple[float, float, float]]:
    """Parse an ``(at x y [angle])`` child into a coordinate triple."""
    at = _get_child(element, "at")
    if at is None or len(at) < 3:
        return None
    try:
        angle = float(at[3]) if len(at) >= 4 else 0.0
        return float(at[1]), float(at[2]), angle
    except (TypeError, ValueError):
        return None


def _round_point(point: Point) -> Point:
    """Quantize a coordinate pair so equal positions compare equal."""
    return (round(point[0], _COORD_DECIMALS), round(point[1], _COORD_DECIMALS))


def find_symbol_instances(tree: list) -> list[list]:
    """Return placed symbol instances, excluding ``lib_symbols`` definitions.

    KiCad stores symbol *definitions* inside ``(lib_symbols ...)``; those
    carry template properties such as ``(property "Reference" "R")`` and must
    not be mistaken for placed components.
    """
    instances: list[list] = []
    for element in _find_elements(tree, "symbol", skip_tags=("lib_symbols",)):
        if _get_property(element, "Reference"):
            instances.append(element)
    return instances


def _library_pin_geometry(tree: list) -> dict[str, dict[str, tuple[Point, str]]]:
    """Map ``lib_id`` to per-pin library coordinates and names.

    Placed symbols in modern KiCad files do not repeat pin coordinates, so pin
    positions are recovered from the library definition and transformed by the
    instance placement.
    """
    geometry: dict[str, dict[str, tuple[Point, str]]] = {}
    lib_symbols = _get_child(tree, "lib_symbols")
    if lib_symbols is None:
        return geometry

    for definition in lib_symbols[1:]:
        if _tag(definition) != "symbol" or len(definition) < 2:
            continue
        lib_id = str(definition[1])
        pins: dict[str, tuple[Point, str]] = {}
        for pin in _find_elements(definition, "pin"):
            at = _parse_at(pin)
            number_elem = _get_child(pin, "number")
            if at is None or number_elem is None or len(number_elem) < 2:
                continue
            name_elem = _get_child(pin, "name")
            name = str(name_elem[1]) if name_elem and len(name_elem) >= 2 else ""
            pins[str(number_elem[1])] = ((at[0], at[1]), name)
        if pins:
            geometry[lib_id] = pins
    return geometry


def _transform_pin(
    pin_xy: Point,
    origin: tuple[float, float, float],
    mirror: str,
) -> Point:
    """Map library pin coordinates into absolute sheet coordinates.

    Library symbols use a Y-up coordinate system while the sheet uses Y-down,
    so the pin's Y offset is negated before the placement rotation is applied.

    Args:
        pin_xy: Pin coordinates in library space.
        origin: Instance placement as ``(x, y, angle_degrees)``.
        mirror: KiCad mirror axis (``"x"``, ``"y"``, or ``""``).

    Returns:
        Absolute ``(x, y)`` position of the pin on the sheet.
    """
    px, py = pin_xy[0], -pin_xy[1]
    if mirror == "y":
        px = -px
    elif mirror == "x":
        py = -py

    angle = math.radians(origin[2])
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    rotated_x = px * cos_a + py * sin_a
    rotated_y = -px * sin_a + py * cos_a
    return _round_point((origin[0] + rotated_x, origin[1] + rotated_y))


def _parse_symbol(
    symbol: list,
    library_geometry: Optional[dict[str, dict[str, tuple[Point, str]]]] = None,
) -> Component:
    """Parse a placed symbol element into a Component.

    Args:
        symbol: Symbol instance S-expression.
        library_geometry: Optional pin geometry from ``lib_symbols``, used to
            resolve pin positions and names when the instance omits them.

    Returns:
        Populated Component including its pins.
    """
    lib_id_elem = _get_child(symbol, "lib_id")
    lib_id = str(lib_id_elem[1]) if lib_id_elem and len(lib_id_elem) >= 2 else ""
    uuid_elem = _get_child(symbol, "uuid")
    uuid = str(uuid_elem[1]) if uuid_elem and len(uuid_elem) >= 2 else ""

    origin = _parse_at(symbol)
    mirror_elem = _get_child(symbol, "mirror")
    mirror = str(mirror_elem[1]) if mirror_elem and len(mirror_elem) >= 2 else ""
    lib_pins = (library_geometry or {}).get(lib_id, {})

    pins: list[Pin] = []
    for item in symbol:
        if _tag(item) != "pin" or len(item) < 2:
            continue
        number = str(item[1])
        pin_uuid_elem = _get_child(item, "uuid")
        name_elem = _get_child(item, "name")
        name = str(name_elem[1]) if name_elem and len(name_elem) >= 2 else ""

        at = _parse_at(item)
        position = _round_point((at[0], at[1])) if at else None
        if position is None and number in lib_pins and origin is not None:
            position = _transform_pin(lib_pins[number][0], origin, mirror)
        if not name and number in lib_pins:
            name = lib_pins[number][1]

        pins.append(
            Pin(
                number=number,
                name=name,
                uuid=str(pin_uuid_elem[1]) if pin_uuid_elem and len(pin_uuid_elem) >= 2 else "",
                position=position,
            )
        )

    if not pins and lib_pins and origin is not None:
        # Some writers omit per-instance pins entirely; fall back to the
        # library definition so connectivity can still be resolved.
        pins = [
            Pin(
                number=number,
                name=name,
                position=_transform_pin(pin_xy, origin, mirror),
            )
            for number, (pin_xy, name) in lib_pins.items()
        ]

    return Component(
        reference=_get_property(symbol, "Reference"),
        value=_get_property(symbol, "Value"),
        lib_id=lib_id,
        footprint=_get_property(symbol, "Footprint"),
        uuid=uuid,
        properties=_extract_all_properties(symbol),
        pins=pins,
    )


def _parse_labels(tree: list) -> dict[str, list[Point]]:
    """Extract label positions keyed by net name."""
    labels: dict[str, list[Point]] = {}
    for label_type in ("label", "global_label", "hierarchical_label"):
        for elem in _find_elements(tree, label_type, skip_tags=("lib_symbols",)):
            if len(elem) < 2 or not isinstance(elem[1], str) or not elem[1]:
                continue
            at = _parse_at(elem)
            if at is None:
                continue
            labels.setdefault(elem[1], []).append(_round_point((at[0], at[1])))
    return labels


def _parse_wires(tree: list) -> list[tuple[Point, Point]]:
    """Extract wire segments as coordinate pairs."""
    wires: list[tuple[Point, Point]] = []
    for wire in _find_elements(tree, "wire", skip_tags=("lib_symbols",)):
        pts = _get_child(wire, "pts")
        if pts is None:
            continue
        coordinates: list[Point] = []
        for pt in pts[1:]:
            if _tag(pt) == "xy" and len(pt) >= 3:
                try:
                    coordinates.append(_round_point((float(pt[1]), float(pt[2]))))
                except (TypeError, ValueError):
                    continue
        for start, end in zip(coordinates, coordinates[1:]):
            wires.append((start, end))
    return wires


def _parse_no_connects(tree: list) -> set[Point]:
    """Extract positions flagged with a no-connect marker."""
    positions: set[Point] = set()
    for elem in _find_elements(tree, "no_connect", skip_tags=("lib_symbols",)):
        at = _parse_at(elem)
        if at is not None:
            positions.add(_round_point((at[0], at[1])))
    return positions


def _point_on_segment(point: Point, start: Point, end: Point) -> bool:
    """Return True when ``point`` lies on the wire segment ``start``-``end``.

    This makes T-junctions connect even when the touching wire ends in the
    middle of another segment.
    """
    seg_x, seg_y = end[0] - start[0], end[1] - start[1]
    rel_x, rel_y = point[0] - start[0], point[1] - start[1]
    length_sq = seg_x * seg_x + seg_y * seg_y
    if length_sq == 0:
        return abs(rel_x) < _TOLERANCE and abs(rel_y) < _TOLERANCE
    cross = abs(seg_x * rel_y - seg_y * rel_x) / math.sqrt(length_sq)
    if cross > _TOLERANCE:
        return False
    projection = (rel_x * seg_x + rel_y * seg_y) / length_sq
    return -_TOLERANCE <= projection <= 1 + _TOLERANCE


class _UnionFind:
    """Minimal union-find used to group electrically connected points."""

    def __init__(self) -> None:
        self._parent: dict[Point, Point] = {}

    def add(self, item: Point) -> None:
        """Add a point as its own group if not already known."""
        self._parent.setdefault(item, item)

    def find(self, item: Point) -> Point:
        """Return the representative point of the group containing ``item``."""
        self.add(item)
        root = item
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[item] != root:
            self._parent[item], item = root, self._parent[item]
        return root

    def union(self, first: Point, second: Point) -> None:
        """Merge the groups containing the two points."""
        root_a, root_b = self.find(first), self.find(second)
        if root_a != root_b:
            self._parent[root_b] = root_a


class SchematicParser:
    """Parse KiCad ``.kicad_sch`` files into :class:`Schematic` models."""

    def parse_file(self, filepath: str | Path) -> Schematic:
        """Parse a schematic file from disk.

        Args:
            filepath: Path to a ``.kicad_sch`` file.

        Returns:
            Parsed Schematic model.
        """
        path = Path(filepath)
        return self.parse_text(path.read_text(encoding="utf-8"), filename=str(path))

    def parse_text(self, text: str, filename: str = "unknown.kicad_sch") -> Schematic:
        """Parse schematic text content.

        Args:
            text: Contents of a ``.kicad_sch`` file.
            filename: Path used to derive the project name.

        Returns:
            Parsed Schematic model.
        """
        tree = SExpressionParser(text).parse()

        version = ""
        version_elem = _get_child(tree, "version") if isinstance(tree, list) else None
        if version_elem and len(version_elem) >= 2:
            version = str(version_elem[1])

        library_geometry = _library_pin_geometry(tree) if isinstance(tree, list) else {}
        components = [
            _parse_symbol(symbol, library_geometry)
            for symbol in find_symbol_instances(tree)
        ]

        self._apply_no_connects(components, _parse_no_connects(tree))
        nets = self._build_nets(tree, components)

        return Schematic(
            filename=filename,
            project_name=Path(filename).stem,
            components=components,
            nets=nets,
            version=version,
        )

    @staticmethod
    def _apply_no_connects(
        components: list[Component], no_connects: set[Point]
    ) -> None:
        """Flag pins covered by a no-connect marker."""
        if not no_connects:
            return
        for comp in components:
            for pin in comp.pins:
                if pin.position is not None and pin.position in no_connects:
                    pin.no_connect = True

    def _build_nets(self, tree: list, components: list[Component]) -> list[Net]:
        """Build net connectivity from labels, wires, power symbols, and pins.

        Points are grouped with a union-find over wire segments; a group is
        named after any label attached to it, after the value of a power
        symbol pin it contains, or with a generated ``Net-n`` name.

        Args:
            tree: Parsed S-expression tree.
            components: Components already extracted from the tree.

        Returns:
            List of nets with pin connections resolved.
        """
        labels = _parse_labels(tree)
        wires = _parse_wires(tree)

        groups = _UnionFind()
        pin_points: dict[Point, list[tuple[str, str]]] = {}
        for comp in components:
            for pin in comp.pins:
                if pin.position is not None:
                    pin_points.setdefault(pin.position, []).append(
                        (comp.reference, pin.number)
                    )
                    groups.add(pin.position)

        label_points: dict[Point, list[str]] = {}
        for name, positions in labels.items():
            for position in positions:
                label_points.setdefault(position, []).append(name)
                groups.add(position)

        for start, end in wires:
            groups.add(start)
            groups.add(end)
            groups.union(start, end)

        # Attach pins and labels that sit anywhere along a wire segment.
        for point in list(pin_points) + list(label_points):
            for start, end in wires:
                if _point_on_segment(point, start, end):
                    groups.union(point, start)

        # A power symbol names the net attached to its pin (e.g. "GND").
        power_names: dict[Point, str] = {}
        for comp in components:
            if not comp.is_power:
                continue
            net_name = comp.value.strip() or ("GND" if comp.is_ground else "")
            if not net_name:
                continue
            for pin in comp.pins:
                if pin.position is not None:
                    power_names[pin.position] = net_name

        net_connections: dict[str, list[tuple[str, str]]] = {
            name: [] for name in labels
        }
        grouped_pins: dict[Point, list[tuple[str, str]]] = {}
        group_names: dict[Point, str] = {}

        for point, connections in pin_points.items():
            grouped_pins.setdefault(groups.find(point), []).extend(connections)
        for point, names in label_points.items():
            group_names.setdefault(groups.find(point), names[0])
        for point, name in power_names.items():
            group_names[groups.find(point)] = name

        unnamed_index = 0
        for root, connections in grouped_pins.items():
            name = group_names.get(root)
            if name is None:
                if len(connections) < 2:
                    continue
                unnamed_index += 1
                name = f"Net-{unnamed_index}"
            net_connections.setdefault(name, []).extend(connections)

        # Ground symbols without resolvable geometry still imply a GND net.
        for comp in components:
            if comp.is_ground and any(pin.position is None for pin in comp.pins):
                for pin in comp.pins:
                    if pin.position is None:
                        net_connections.setdefault("GND", []).append(
                            (comp.reference, pin.number)
                        )

        nets: list[Net] = []
        for name, connections in net_connections.items():
            net = Net(name=name)
            for ref, pin_number in dict.fromkeys(connections):
                net.add_connection(ref, pin_number)
            nets.append(net)

        self._mark_connected_pins(nets, components)
        return nets

    @staticmethod
    def _mark_connected_pins(nets: list[Net], components: list[Component]) -> None:
        """Set ``connected`` and ``net_name`` on pins that belong to a net."""
        by_reference = {comp.reference: comp for comp in components}
        for net in nets:
            for ref, pin_number in net.connected_pins:
                comp = by_reference.get(ref)
                if comp is None:
                    continue
                for pin in comp.pins:
                    if pin.number == pin_number:
                        pin.connected = True
                        pin.net_name = net.name
