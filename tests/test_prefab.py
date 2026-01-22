"""Tests for relics.prefab module."""

import json
import tempfile
from pathlib import Path

import pytest
from pydantic.dataclasses import dataclass

from relics import (
    Component,
    PrefabNotFoundError,
    World,
    get_prefab,
    list_prefabs,
    load_prefabs_from_json,
    save_prefabs_to_json,
)


@dataclass
class Position(Component):
    """Test component for position."""

    x: float
    y: float
    z: float = 0.0


@dataclass
class Health(Component):
    """Test component for health."""

    current: int
    maximum: int


@dataclass
class Team(Component):
    """Test component for team."""

    id: str
    name: str


class TestPrefabRegistry:
    """Tests for prefab registration and spawning."""

    def test_register_prefab(self) -> None:
        """Test registering a prefab."""
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Health: Health(current=100, maximum=100)},
        )

        prefab = get_prefab(world, "player")
        assert Position in prefab
        assert Health in prefab

    def test_get_prefab_not_found(self) -> None:
        """Test getting non-existent prefab raises error."""
        world = World()
        with pytest.raises(PrefabNotFoundError):
            get_prefab(world, "unknown")

    def test_list_prefabs(self) -> None:
        """Test listing all prefabs."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_prefab("enemy", {Position: Position(x=0, y=0)})

        prefabs = list_prefabs(world)
        assert "player" in prefabs
        assert "enemy" in prefabs
        assert len(prefabs) == 2

    def test_list_prefabs_empty(self) -> None:
        """Test listing prefabs when none registered."""
        world = World()
        prefabs = list_prefabs(world)
        assert prefabs == []


class TestPrefabJson:
    """Tests for JSON prefab loading and saving."""

    def test_load_prefabs_from_json(self) -> None:
        """Test loading prefabs from JSON file."""
        world = World()

        # Create a temp JSON file
        prefab_data = {
            "player": {
                "components": {
                    "Position": {"x": 0, "y": 0, "z": 0},
                    "Health": {"current": 100, "maximum": 100},
                }
            },
            "enemy": {
                "components": {
                    "Position": {"x": 10, "y": 20, "z": 0},
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(prefab_data, f)
            temp_path = f.name

        try:
            component_registry = {
                "Position": Position,
                "Health": Health,
            }

            load_prefabs_from_json(world, temp_path, component_registry)

            # Check prefabs were loaded
            prefabs = list_prefabs(world)
            assert "player" in prefabs
            assert "enemy" in prefabs

            # Check component values
            player_prefab = get_prefab(world, "player")
            assert Position in player_prefab
            assert Health in player_prefab
            assert player_prefab[Position].x == 0
            assert player_prefab[Health].current == 100

            enemy_prefab = get_prefab(world, "enemy")
            assert Position in enemy_prefab
            assert enemy_prefab[Position].x == 10
        finally:
            Path(temp_path).unlink()

    def test_load_prefabs_unknown_component(self) -> None:
        """Test loading prefabs with unknown component raises error."""
        world = World()

        prefab_data = {
            "player": {
                "components": {
                    "UnknownComponent": {"field": "value"},
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(prefab_data, f)
            temp_path = f.name

        try:
            component_registry = {"Position": Position}

            with pytest.raises(ValueError, match="Unknown component type"):
                load_prefabs_from_json(world, temp_path, component_registry)
        finally:
            Path(temp_path).unlink()

    def test_save_prefabs_to_json(self) -> None:
        """Test saving prefabs to JSON file."""
        world = World()
        world.register_prefab(
            "player",
            {
                Position: Position(x=5, y=10, z=0),
                Health: Health(current=80, maximum=100),
            },
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            save_prefabs_to_json(world, temp_path)

            # Read back and verify
            with open(temp_path) as f:
                data = json.load(f)

            assert "player" in data
            assert "components" in data["player"]
            assert "Position" in data["player"]["components"]
            assert data["player"]["components"]["Position"]["x"] == 5
            assert data["player"]["components"]["Health"]["current"] == 80
        finally:
            Path(temp_path).unlink()

    def test_round_trip(self) -> None:
        """Test saving and loading prefabs round-trips correctly."""
        world1 = World()
        world1.register_prefab(
            "player",
            {
                Position: Position(x=5, y=10, z=0),
                Team: Team(id="blue", name="Blue Team"),
            },
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            save_prefabs_to_json(world1, temp_path)

            # Load into new world
            world2 = World()
            component_registry = {"Position": Position, "Team": Team}
            load_prefabs_from_json(world2, temp_path, component_registry)

            # Verify
            prefab = get_prefab(world2, "player")
            assert prefab[Position].x == 5
            assert prefab[Position].y == 10
            assert prefab[Team].id == "blue"
            assert prefab[Team].name == "Blue Team"
        finally:
            Path(temp_path).unlink()


class TestComponentSerialization:
    """Tests for different component serialization formats."""

    def test_serialize_pydantic_base_model(self) -> None:
        """Test serializing Pydantic BaseModel components."""
        from pydantic import BaseModel

        class CustomComponent(BaseModel, Component):
            name: str
            value: int

        world = World()
        comp = CustomComponent(name="a", value=1)
        world.register_prefab("test", {CustomComponent: comp})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            save_prefabs_to_json(world, temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            assert "CustomComponent" in data["test"]["components"]
            assert data["test"]["components"]["CustomComponent"]["name"] == "a"
            assert data["test"]["components"]["CustomComponent"]["value"] == 1
        finally:
            Path(temp_path).unlink()

    def test_serialize_plain_class_component(self) -> None:
        """Test serializing plain class components with __dict__."""

        class PlainComponent(Component):
            def __init__(self, name: str, value: int):
                self.name = name
                self.value = value

        world = World()
        comp = PlainComponent(name="b", value=2)
        world.register_prefab("test", {PlainComponent: comp})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            save_prefabs_to_json(world, temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            assert "PlainComponent" in data["test"]["components"]
            assert data["test"]["components"]["PlainComponent"]["name"] == "b"
            assert data["test"]["components"]["PlainComponent"]["value"] == 2
        finally:
            Path(temp_path).unlink()
