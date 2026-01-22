"""Component definitions for the character sheet demo."""

from pydantic.dataclasses import dataclass

from relics.types import Component


@dataclass
class Identity(Component):
    """Character identity information."""

    name: str
    title: str = ""


@dataclass
class CharacterClass(Component):
    """Character race and class information."""

    race: str
    cls: str


@dataclass
class Appearance(Component):
    """Physical appearance of a character."""

    hair_color: str
    eye_color: str
    height_cm: int
    weight_kg: float


@dataclass
class Equipment(Component):
    """Equipment item information."""

    name: str
    item_type: str  # "weapon", "armor", "clothing"
    material: str = ""
    quality: str = "common"


@dataclass
class WeaponStats(Component):
    """Combat statistics for weapons."""

    damage: int
    damage_type: str  # "slashing", "piercing", "bludgeoning"
    two_handed: bool = False


@dataclass
class ArmorStats(Component):
    """Defensive statistics for armor."""

    defense: int
    armor_type: str  # "light", "medium", "heavy"
