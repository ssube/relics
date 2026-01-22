"""Tests for relics.persistence module."""

import json
import tempfile
from pathlib import Path

import pytest
from pydantic.dataclasses import dataclass

from relics import (
    Component,
    World,
    list_relics,
    load,
    load_relic,
    save,
    save_relic,
)


@dataclass
class Position(Component):
    """Test component for position."""

    x: float
    y: float


@dataclass
class Health(Component):
    """Test component for health."""

    current: int
    maximum: int


@dataclass
class Team(Component):
    """Test component for team."""

    id: str


class TestJsonPersistence:
    """Tests for JSON save/load."""

    def test_save_basic(self) -> None:
        """Test basic save functionality."""
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Health: Health(current=100, maximum=100)},
        )
        world.spawn("player", {Position: Position(x=10, y=20)})
        world.spawn("player", {Position: Position(x=30, y=40)})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            save(world, temp_path)

            # Verify file structure
            with open(temp_path) as f:
                data = json.load(f)

            assert "metadata" in data
            assert "prefabs" in data
            assert "entities" in data
            assert "components" in data

            assert data["metadata"]["version"] == "1.0"
            assert len(data["entities"]) == 2
            assert "Position" in data["components"]
            assert len(data["components"]["Position"]) == 2
        finally:
            Path(temp_path).unlink()

    def test_load_basic(self) -> None:
        """Test basic load functionality."""
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0)},
        )

        # Register component types
        world.register_component_type(Position)
        world.register_component_type(Health)

        entity = world.spawn("player", {Position: Position(x=10, y=20)})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            save(world, temp_path)

            # Load into new world
            world2 = World()
            component_registry = {"Position": Position, "Health": Health}
            load(world2, temp_path, component_registry)

            assert len(world2._entities) == 1

            # Get the entity
            loaded_entity = world2.get_entity(entity.id)
            pos = loaded_entity.get_component(Position)
            assert pos.x == 10
            assert pos.y == 20
        finally:
            Path(temp_path).unlink()

    def test_round_trip(self) -> None:
        """Test save/load round-trip preserves data."""
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Health: Health(current=100, maximum=100)},
        )

        entity1 = world.spawn("player", {Position: Position(x=10, y=20)})
        entity2 = world.spawn(
            "player",
            {Position: Position(x=30, y=40), Health: Health(current=50, maximum=100)},
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            save(world, temp_path)

            # Load into new world
            world2 = World()
            component_registry = {"Position": Position, "Health": Health}
            load(world2, temp_path, component_registry)

            # Verify entities
            assert world2.has_entity(entity1.id)
            assert world2.has_entity(entity2.id)

            # Verify components
            e1 = world2.get_entity(entity1.id)
            e2 = world2.get_entity(entity2.id)

            assert e1.get_component(Position).x == 10
            assert e2.get_component(Position).x == 30
            assert e2.get_component(Health).current == 50
        finally:
            Path(temp_path).unlink()

    def test_epoch_preserved(self) -> None:
        """Test that epoch is preserved on load."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")

        # Advance epoch
        for _ in range(10):
            world.tick(0.016)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            save(world, temp_path)

            world2 = World()
            load(world2, temp_path, {"Position": Position})

            assert world2.epoch == 10
        finally:
            Path(temp_path).unlink()


class TestRelics:
    """Tests for named relic snapshots."""

    def test_save_relic(self) -> None:
        """Test saving a named relic."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")

        with tempfile.TemporaryDirectory() as temp_dir:
            save_relic(world, "test_save", temp_dir)

            # Verify relic file exists
            relic_path = Path(temp_dir) / "test_save.json"
            assert relic_path.exists()

            # Verify metadata file
            metadata_path = Path(temp_dir) / "_relics.json"
            assert metadata_path.exists()

    def test_load_relic(self) -> None:
        """Test loading a named relic."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        entity = world.spawn("player", {Position: Position(x=10, y=20)})

        with tempfile.TemporaryDirectory() as temp_dir:
            save_relic(world, "test_load", temp_dir)

            # Load into new world
            world2 = World()
            load_relic(world2, "test_load", temp_dir, {"Position": Position})

            assert world2.has_entity(entity.id)
            e = world2.get_entity(entity.id)
            assert e.get_component(Position).x == 10

    def test_list_relics(self) -> None:
        """Test listing available relics."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")

        with tempfile.TemporaryDirectory() as temp_dir:
            save_relic(world, "relic1", temp_dir)
            save_relic(world, "relic2", temp_dir)
            save_relic(world, "relic3", temp_dir)

            relics = list_relics(temp_dir)
            names = [r.name for r in relics]

            assert "relic1" in names
            assert "relic2" in names
            assert "relic3" in names

    def test_list_relics_empty(self) -> None:
        """Test listing relics when none exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            relics = list_relics(temp_dir)
            assert relics == []

    def test_overwrite_relic(self) -> None:
        """Test overwriting an existing relic."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player", {Position: Position(x=10, y=10)})

        with tempfile.TemporaryDirectory() as temp_dir:
            save_relic(world, "test_overwrite", temp_dir)

            # Modify world
            world.spawn("player", {Position: Position(x=20, y=20)})

            # Should fail without overwrite
            with pytest.raises(FileExistsError):
                save_relic(world, "test_overwrite", temp_dir)

            # Should succeed with overwrite
            save_relic(world, "test_overwrite", temp_dir, overwrite=True)

            # Verify it was updated
            world2 = World()
            load_relic(world2, "test_overwrite", temp_dir, {"Position": Position})
            assert len(world2._entities) == 2

    def test_load_nonexistent_relic(self) -> None:
        """Test loading non-existent relic raises error."""
        world = World()

        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(FileNotFoundError):
                load_relic(world, "nonexistent", temp_dir)

    def test_relic_info_fields(self) -> None:
        """Test RelicInfo contains correct fields."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")

        # Advance epoch
        for _ in range(5):
            world.tick(0.016)

        with tempfile.TemporaryDirectory() as temp_dir:
            save_relic(world, "test_info", temp_dir)

            relics = list_relics(temp_dir)
            assert len(relics) == 1

            info = relics[0]
            assert info.name == "test_info"
            assert info.epoch == 5
            assert info.created_at is not None
