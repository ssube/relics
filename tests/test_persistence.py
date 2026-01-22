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


class TestComponentSerializationFormats:
    """Tests for different component serialization formats in persistence."""

    def test_serialize_pydantic_base_model(self) -> None:
        """Test saving/loading Pydantic BaseModel components."""
        from pydantic import BaseModel

        class CustomData(BaseModel, Component):
            name: str
            score: int

        world = World()
        world.register_prefab("test", {CustomData: CustomData(name="test", score=100)})
        world.register_component_type(CustomData)

        entity = world.spawn("test", {CustomData: CustomData(name="loaded", score=50)})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            save(world, temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            # Verify serialization
            assert "CustomData" in data["components"]
            assert data["components"]["CustomData"][str(entity.id)]["name"] == "loaded"
            assert data["components"]["CustomData"][str(entity.id)]["score"] == 50

            # Test load
            world2 = World()
            load(world2, temp_path, {"CustomData": CustomData})

            e = world2.get_entity(entity.id)
            comp = e.get_component(CustomData)
            assert comp.name == "loaded"
            assert comp.score == 50
        finally:
            Path(temp_path).unlink()

    def test_serialize_plain_class_component(self) -> None:
        """Test saving/loading plain class components with __dict__."""

        class PlainData(Component):
            def __init__(self, tag: str, count: int):
                self.tag = tag
                self.count = count

        world = World()
        world.register_prefab("test", {PlainData: PlainData(tag="init", count=0)})
        world.register_component_type(PlainData)

        entity = world.spawn("test", {PlainData: PlainData(tag="custom", count=42)})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            save(world, temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            # Verify serialization
            assert "PlainData" in data["components"]
            assert data["components"]["PlainData"][str(entity.id)]["tag"] == "custom"
            assert data["components"]["PlainData"][str(entity.id)]["count"] == 42

            # Test load
            world2 = World()
            load(world2, temp_path, {"PlainData": PlainData})

            e = world2.get_entity(entity.id)
            comp = e.get_component(PlainData)
            assert comp.tag == "custom"
            assert comp.count == 42
        finally:
            Path(temp_path).unlink()

    def test_skip_private_fields(self) -> None:
        """Test that private fields are excluded from serialization."""

        class DataWithPrivate(Component):
            def __init__(self, value: int):
                self.value = value
                self._internal = "secret"

        world = World()
        world.register_prefab("test", {DataWithPrivate: DataWithPrivate(value=10)})
        world.register_component_type(DataWithPrivate)

        entity = world.spawn("test")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            save(world, temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            # Private field should not be serialized
            comp_data = data["components"]["DataWithPrivate"][str(entity.id)]
            assert "value" in comp_data
            assert "_internal" not in comp_data
        finally:
            Path(temp_path).unlink()


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


class TestRelationshipPersistence:
    """Tests for saving and loading relationships."""

    def test_save_relationships(self) -> None:
        """Test that relationships are saved to JSON."""
        from relics import Edge

        @dataclass
        class AllyTo(Edge):
            trust_level: float = 1.0

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player", {Position: Position(x=10, y=20)})
        p2 = world.spawn("player", {Position: Position(x=30, y=40)})

        p1.add_relationship(AllyTo(trust_level=0.9), p2.id)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            save(world, temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            assert "relationships" in data
            assert "AllyTo" in data["relationships"]
            assert str(p1.id) in data["relationships"]["AllyTo"]
            rels = data["relationships"]["AllyTo"][str(p1.id)]
            assert len(rels) == 1
            assert rels[0]["target"] == str(p2.id)
            assert rels[0]["edge"]["trust_level"] == 0.9
        finally:
            Path(temp_path).unlink()

    def test_load_relationships(self) -> None:
        """Test that relationships are loaded from JSON."""
        from relics import Edge

        @dataclass
        class AllyTo(Edge):
            trust_level: float = 1.0

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player", {Position: Position(x=10, y=20)})
        p2 = world.spawn("player", {Position: Position(x=30, y=40)})

        p1.add_relationship(AllyTo(trust_level=0.8), p2.id)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            save(world, temp_path)

            # Load into new world
            world2 = World()
            component_registry = {"Position": Position}
            edge_registry = {"AllyTo": AllyTo}
            load(world2, temp_path, component_registry, edge_registry)

            # Check relationships loaded
            loaded_p1 = world2.get_entity(p1.id)
            assert loaded_p1.has_relationship(AllyTo, p2.id)

            relationships = loaded_p1.get_relationships(AllyTo)
            assert len(relationships) == 1
            edge, target_id = relationships[0]
            assert target_id == p2.id
            assert edge.trust_level == 0.8

            # Check incoming relationship
            loaded_p2 = world2.get_entity(p2.id)
            assert loaded_p2.has_incoming_relationship(AllyTo, p1.id)
        finally:
            Path(temp_path).unlink()

    def test_skip_unknown_edge_types(self) -> None:
        """Test that unknown edge types are skipped during load."""
        from relics import Edge

        @dataclass
        class AllyTo(Edge):
            trust_level: float = 1.0

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")

        p1.add_relationship(AllyTo(), p2.id)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            save(world, temp_path)

            # Load without edge registry - should skip relationships
            world2 = World()
            load(world2, temp_path, {"Position": Position}, {})

            loaded_p1 = world2.get_entity(p1.id)
            # Should have no relationships since AllyTo wasn't registered
            assert not loaded_p1.has_relationship(AllyTo)
        finally:
            Path(temp_path).unlink()

    def test_skip_missing_entities_in_relationships(self) -> None:
        """Test that relationships with missing entities are skipped."""
        # Create a JSON file with a relationship pointing to non-existent entity
        data = {
            "metadata": {"version": "1.0", "epoch": 0},
            "prefabs": {},
            "entities": {"player_1": {"prefab": "player"}},
            "components": {"Position": {"player_1": {"x": 0, "y": 0}}},
            "relationships": {
                "AllyTo": {
                    "player_1": [{"target": "player_999", "edge": {"trust_level": 1.0}}]
                }
            },
        }

        from relics import Edge

        @dataclass
        class AllyTo(Edge):
            trust_level: float = 1.0

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            world = World()
            world.register_component_type(Position)
            load(world, temp_path, {"Position": Position}, {"AllyTo": AllyTo})

            # Should load the entity but skip the relationship
            assert world.has_entity(world.query().execute_ids().__next__())
        finally:
            Path(temp_path).unlink()

    def test_skip_missing_source_in_relationships(self) -> None:
        """Test that relationships from missing source entities are skipped."""
        # Create a JSON file with a relationship from non-existent entity
        data = {
            "metadata": {"version": "1.0", "epoch": 0},
            "prefabs": {},
            "entities": {"player_1": {"prefab": "player"}},
            "components": {"Position": {"player_1": {"x": 0, "y": 0}}},
            "relationships": {
                "AllyTo": {
                    "player_999": [{"target": "player_1", "edge": {"trust_level": 1.0}}]
                }
            },
        }

        from relics import Edge

        @dataclass
        class AllyTo(Edge):
            trust_level: float = 1.0

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            world = World()
            world.register_component_type(Position)
            load(world, temp_path, {"Position": Position}, {"AllyTo": AllyTo})

            # Should load the entity but skip the relationship
            entity_id = next(world.query().execute_ids())
            loaded_entity = world.get_entity(entity_id)
            # No incoming relationships since source doesn't exist
            assert not loaded_entity.has_incoming_relationship(AllyTo)
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

            # Verify metadata contains relic name (self-contained)
            import json
            with relic_path.open("r") as f:
                data = json.load(f)
            assert data["metadata"]["relic_name"] == "test_save"

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
