"""Reads the rules in data/logic.json and turns them into Rule Builder rules.

The notation:
    A & B         both
    A | B         either
    Bomb×3        three copies of a progressive item (Progressive Pressure Bomb)
    Cogs(4)       four Upgrade Cogs
    SkyAssailant  a cog mod, which stands for the tool copies that unlock it (here Bomb×4)
    Rosie         an event, by name
    —             nothing

The rules name today's items. A seed's tool options turn them into its own: with the Pressure Bomb main item,
Bomb×3 is the Pressure Bomb and two Progressive Pressure Bombs; with the Progressive Hook Shot, Grappler is two copies
of it.
"""
import re
from collections.abc import Iterator
from dataclasses import dataclass

from rule_builder.rules import And, Has, Or, Rule, True_

from .data import COG_MODS, ITEMS, ItemData

TOKEN = re.compile(r"\(|\)|&|\||[^()&|]+")

# A rule's name for an item -> the item. Artifacts are counted as a group instead
ITEM_OF_ATOM = {item.logic: item.name for item in ITEMS if item.logic and item.logic != "Artifacts"}


@dataclass(frozen=True)
class Atom:
    """An item, a number of cogs, a cog mod or an event."""
    name: str
    count: int = 1


@dataclass(frozen=True)
class AllOf:
    parts: tuple


@dataclass(frozen=True)
class AnyOf:
    parts: tuple


@dataclass(frozen=True)
class Nothing:
    pass


Tree = Atom | AllOf | AnyOf | Nothing


def parse(text: str) -> Tree:
    """Parses one rule into a tree."""
    text = re.sub(r"Cogs\((\d+)\)", r"Cogs×\1", text)
    tokens = [token.strip() for token in TOKEN.findall(text) if token.strip()]

    try:
        tree = _parse_any(tokens)
    except (IndexError, ValueError):
        raise ValueError(f"can't read the rule {text!r}") from None

    if tokens:
        raise ValueError(f"unexpected {tokens[0]!r} in the rule {text!r}")

    return tree


def _parse_any(tokens: list[str]) -> Tree:
    parts = [_parse_all(tokens)]
    while tokens and tokens[0] == "|":
        tokens.pop(0)
        parts.append(_parse_all(tokens))

    return parts[0] if len(parts) == 1 else AnyOf(tuple(parts))


def _parse_all(tokens: list[str]) -> Tree:
    parts = [_parse_one(tokens)]
    while tokens and tokens[0] == "&":
        tokens.pop(0)
        parts.append(_parse_one(tokens))

    return parts[0] if len(parts) == 1 else AllOf(tuple(parts))


def _parse_one(tokens: list[str]) -> Tree:
    token = tokens.pop(0)

    if token == "(":
        inner = _parse_any(tokens)
        if tokens.pop(0) != ")":
            raise ValueError("unbalanced parentheses")
        return inner

    if token == "—":
        return Nothing()

    name, _, count = token.partition("×")
    return Atom(name.strip(), int(count) if count else 1)


def atom_items(name: str, count: int, tool_items: list[ItemData]) -> list[tuple[str, int]] | None:
    """The items and number of copies an atom asks for in a seed with these tool items, or None for an event."""
    if name in COG_MODS:
        mod = COG_MODS[name]
        return seed_items(ITEM_OF_ATOM[mod.needs], mod.count, tool_items)

    if name in ITEM_OF_ATOM:
        return seed_items(ITEM_OF_ATOM[name], count, tool_items)

    return None


def seed_items(item: str, copies: int, tool_items: list[ItemData]) -> list[tuple[str, int]]:
    """Turns copies of an item the rules name into the items of a seed with these tool items."""
    for tool_item in tool_items:
        grant = tool_item.grant

        # The main item is the first copy
        if grant.kind == "main" and grant.progressive == item:
            if copies == 1:
                return [(tool_item.name, 1)]
            return [(tool_item.name, 1), (item, copies - 1)]

        if grant.kind == "progressive" and item in grant.items:
            return [(tool_item.name, grant.items.index(item) + 1)]

    return [(item, copies)]


def atoms(tree: Tree) -> Iterator[str]:
    """Every atom name in a tree."""
    if isinstance(tree, Atom):
        yield tree.name
    elif isinstance(tree, (AllOf, AnyOf)):
        for part in tree.parts:
            yield from atoms(part)


def needed_counts(tree: Tree, counts: dict[str, int], tool_items: list[ItemData]) -> None:
    """Raises counts[item] to the most copies of each item the tree asks for anywhere."""
    if isinstance(tree, Atom):
        for item, copies in atom_items(tree.name, tree.count, tool_items) or []:
            counts[item] = max(counts.get(item, 0), copies)

    elif isinstance(tree, (AllOf, AnyOf)):
        for part in tree.parts:
            needed_counts(part, counts, tool_items)


def to_rule(tree: Tree, events: set[str], tool_items: list[ItemData]) -> Rule:
    """Turns a tree into a Rule Builder rule."""
    if isinstance(tree, Nothing):
        return True_()

    if isinstance(tree, Atom):
        if tree.name in events:
            return Has(tree.name)

        need = atom_items(tree.name, tree.count, tool_items)
        if need is None:
            raise ValueError(f"unknown name {tree.name!r} in a rule")

        rules = [Has(item, copies) for item, copies in need]
        return rules[0] if len(rules) == 1 else And(*rules)

    rules = [to_rule(part, events, tool_items) for part in tree.parts]
    return And(*rules) if isinstance(tree, AllOf) else Or(*rules)
