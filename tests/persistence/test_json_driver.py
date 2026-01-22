"""Tests for JSON persistence driver."""

import json
import tempfile
from pathlib import Path

import pytest
from pydantic.dataclasses import dataclass

from relics import Component, Edge, World
from relics.persistence import JSONPersistenceDriver, RelicInfo


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
class AllyTo(Edge):
    """Test edge type for ally relationships."""

    trust_level: float = 1.0


class TestJSONPersistenceDriver:
    """Tests for JSONPersistenceDriver class."""

    def test_driver_save_basic(self) -> None:
        """Test basic save functionality with driver instance."""
        driver = JSONPersistenceDriver()
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Health: Health(current=100, maximum=100)},
        )
        world.spawn("player", {Position: Position(x=10, y=20)})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            driver.save(world, temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            assert "metadata" in data
            assert "prefabs" in data
            assert "entities" in data
            assert "components" in data
            assert data["metadata"]["version"] == "1.0"
        finally:
            Path(temp_path).unlink()

    def test_driver_load_basic(self) -> None:
        """Test basic load functionality with driver instance."""
        driver = JSONPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        entity = world.spawn("player", {Position: Position(x=10, y=20)})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            driver.save(world, temp_path)

            world2 = World()
            driver.load(world2, temp_path, {"Position": Position, "Health": Health})

            assert len(world2._entities) == 1
            loaded_entity = world2.get_entity(entity.id)
            assert loaded_entity.get_component(Position).x == 10
        finally:
            Path(temp_path).unlink()

    def test_driver_round_trip_with_relationships(self) -> None:
        """Test save/load round-trip with relationships."""
        driver = JSONPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player", {Position: Position(x=10, y=20)})
        p2 = world.spawn("player", {Position: Position(x=30, y=40)})
        p1.add_relationship(AllyTo(trust_level=0.9), p2.id)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            driver.save(world, temp_path)

            world2 = World()
            driver.load(world2, temp_path, {"Position": Position}, {"AllyTo": AllyTo})

            loaded_p1 = world2.get_entity(p1.id)
            assert loaded_p1.has_relationship(AllyTo, p2.id)

            relationships = loaded_p1.get_relationships(AllyTo)
            assert len(relationships) == 1
            edge, target_id = relationships[0]
            assert edge.trust_level == 0.9
        finally:
            Path(temp_path).unlink()

    def test_driver_save_relic(self) -> None:
        """Test saving a named relic with driver."""
        driver = JSONPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")

        with tempfile.TemporaryDirectory() as temp_dir:
            driver.save_relic(world, "test_relic", temp_dir)

            relic_path = Path(temp_dir) / "test_relic.json"
            assert relic_path.exists()

            with relic_path.open("r") as f:
                data = json.load(f)
            assert data["metadata"]["relic_name"] == "test_relic"

    def test_driver_load_relic(self) -> None:
        """Test loading a named relic with driver."""
        driver = JSONPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        entity = world.spawn("player", {Position: Position(x=10, y=20)})

        with tempfile.TemporaryDirectory() as temp_dir:
            driver.save_relic(world, "test_load", temp_dir)

            world2 = World()
            driver.load_relic(world2, "test_load", temp_dir, {"Position": Position})

            assert world2.has_entity(entity.id)

    def test_driver_list_relics(self) -> None:
        """Test listing relics with driver."""
        driver = JSONPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")

        with tempfile.TemporaryDirectory() as temp_dir:
            driver.save_relic(world, "relic1", temp_dir)
            driver.save_relic(world, "relic2", temp_dir)

            relics = driver.list_relics(temp_dir)
            names = [r.name for r in relics]

            assert "relic1" in names
            assert "relic2" in names

    def test_driver_overwrite_relic_fails(self) -> None:
        """Test that overwrite=False raises error on existing relic."""
        driver = JSONPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")

        with tempfile.TemporaryDirectory() as temp_dir:
            driver.save_relic(world, "test_relic", temp_dir)

            with pytest.raises(FileExistsError):
                driver.save_relic(world, "test_relic", temp_dir)

    def test_driver_overwrite_relic_succeeds(self) -> None:
        """Test that overwrite=True allows overwriting."""
        driver = JSONPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")

        with tempfile.TemporaryDirectory() as temp_dir:
            driver.save_relic(world, "test_relic", temp_dir)
            driver.save_relic(world, "test_relic", temp_dir, overwrite=True)

            relics = driver.list_relics(temp_dir)
            assert len(relics) == 1

    def test_driver_load_nonexistent_relic(self) -> None:
        """Test loading non-existent relic raises error."""
        driver = JSONPersistenceDriver()
        world = World()

        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(FileNotFoundError):
                driver.load_relic(world, "nonexistent", temp_dir)

    def test_driver_load_file_not_found(self) -> None:
        """Test loading non-existent file raises error."""
        driver = JSONPersistenceDriver()
        world = World()

        with pytest.raises(FileNotFoundError):
            driver.load(world, "/nonexistent/path/world.json")

    def test_driver_list_relics_empty_dir(self) -> None:
        """Test listing relics in empty directory."""
        driver = JSONPersistenceDriver()

        with tempfile.TemporaryDirectory() as temp_dir:
            relics = driver.list_relics(temp_dir)
            assert relics == []

    def test_driver_list_relics_nonexistent_dir(self) -> None:
        """Test listing relics in nonexistent directory."""
        driver = JSONPersistenceDriver()
        relics = driver.list_relics("/nonexistent/path")
        assert relics == []

    def test_driver_save_with_relic_name_in_metadata(self) -> None:
        """Test that save includes relic_name in metadata when provided."""
        driver = JSONPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            driver.save(world, temp_path, relic_name="my_relic")

            with open(temp_path) as f:
                data = json.load(f)

            assert data["metadata"]["relic_name"] == "my_relic"
        finally:
            Path(temp_path).unlink()
