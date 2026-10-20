"""Helpers for the script graphs in the level files (.le, XML)"""
import xml.etree.ElementTree as ET

FIRST_ID = 990000101
ENTITY_TAGS = ("CustomEntity", "ScriptEntity", "ShapeEntity", "TextureEntity")


def sub(parent: ET.Element, tag: str, text: str | None = None) -> ET.Element:
    element = ET.SubElement(parent, tag)
    if text is not None:
        element.text = text

    return element


def prop(node: ET.Element, name: str, type_name: str, value: str) -> None:
    element = sub(node, "Property")
    sub(element, "Name", name)
    sub(element, "Type", type_name)
    sub(element, "Value", value)


def get_prop(node: ET.Element, name: str) -> ET.Element:
    return next(element for element in node.findall("Property") if element.findtext("Name") == name)


def set_prop(node: ET.Element, name: str, value: str, expect: str) -> None:
    """Sets a property's value"""
    element = get_prop(node, name).find("Value")
    if element.text != expect:
        raise ValueError(f"node {node.findtext('Id')} {name}: expected {expect!r}, found {element.text!r}")

    element.text = value


def connections(node: ET.Element) -> ET.Element:
    element = node.find("Connections")
    if element is None:
        element = sub(node, "Connections")

    return element


def connect(source: ET.Element, target: ET.Element) -> None:
    connection = sub(connections(source), "Connection")
    sub(connection, "SourceContact", "out")
    sub(connection, "TargetContact", "in")
    sub(connection, "TargetId", target.findtext("Id"))


def bind(node: ET.Element, entity_id: int) -> None:
    connection = sub(connections(node), "Connection")
    sub(connection, "SourceContact", "entity")
    sub(connection, "TargetContact", "")
    sub(connection, "TargetId", str(entity_id))


def drop_connection(node: ET.Element, target_id: int) -> None:
    all_connections = connections(node)
    matches = [element for element in all_connections if element.findtext("TargetId") == str(target_id)]
    if len(matches) != 1:
        raise ValueError(f"node {node.findtext('Id')}: {len(matches)} connections to {target_id}")

    all_connections.remove(matches[0])


class Level:
    def __init__(self, text: str, path: str):
        self.path = path
        self.root = ET.fromstring(text)

        areas = self.root.findall("./Areas/Area")
        if len(areas) != 1:
            raise ValueError(f"{path}: {len(areas)} areas, expected 1")

        self.layers = {layer.findtext("Name"): layer for layer in areas[0].findall("Layers/*")}
        self.scripts = self.layers["Foreground"].find("Entities")  # the script nodes are in the Foreground layer

        self.by_id = {}
        for element in self.root.iter():
            if element.tag in ENTITY_TAGS:
                self.by_id.setdefault(element.findtext("Id"), []).append(element)

        self.next_id = FIRST_ID

    def entity(self, entity_id: int | str, layer: str | None = None) -> ET.Element:
        matches = self.by_id.get(str(entity_id), [])
        if layer is not None:
            in_layer = list(self.layers[layer].find("Entities"))
            matches = [element for element in matches if element in in_layer]

        if len(matches) != 1:
            raise ValueError(f"{self.path}: {len(matches)} entities with id {entity_id}")

        return matches[0]

    def node(self, node_id: int, definition: str | None = None) -> ET.Element:
        """The script node with this id"""
        element = self.entity(node_id)
        if element.tag != "ScriptEntity":
            raise ValueError(f"{self.path}: {node_id} is a {element.tag}, not a script node")

        if definition is not None and element.findtext("Definition") != definition:
            raise ValueError(f"{self.path}: node {node_id} is {element.findtext('Definition')}, expected {definition}")

        return element

    def add_node(self, definition: str, name: str, props: list[tuple[str, str, str]] = ()) -> ET.Element:
        """Adds a script node"""
        node_id = self.next_id
        self.next_id += 1

        node = sub(self.scripts, "ScriptEntity")
        sub(node, "Id", str(node_id))
        sub(node, "Name", name)
        sub(node, "Position", "0, 0")
        sub(node, "Definition", definition)
        sub(node, "Area", "0, 0, 150, 63")
        sub(node, "Connections")
        for prop_name, type_name, value in props:
            prop(node, prop_name, type_name, value)

        self.by_id.setdefault(str(node_id), []).append(node)
        return node

    def set_upgrade(self, upgrade: str, name: str | None = None) -> ET.Element:
        return self.add_node("SetUpgrade", name or f"AP_Set_{upgrade}", [
            ("UpgradeId", "String", upgrade),
            ("Tier", "Int32", "1"),
            ("HideNewMarker", "Boolean", "True"),
        ])

    def watch(self, definition: str, entity_id: str, target: ET.Element, name: str) -> None:
        watcher = self.add_node(definition, name)
        connect(watcher, target)
        bind(watcher, entity_id)

    def serialize(self) -> bytes:
        return ET.tostring(self.root, encoding="utf-8", xml_declaration=True)
