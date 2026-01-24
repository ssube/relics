"""Tests for SQLite persistence driver."""

import sqlite3
import tempfile
from pathlib import Path
from typing import List, Optional

import pytest
from pydantic.dataclasses import dataclass

from relics import Component, Edge, World
from relics.persistence import SQLitePersistenceDriver


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
class Inventory(Component):
    """Test component with complex types."""

    items: List[str]
    capacity: int


@dataclass
class Flags(Component):
    """Test component with boolean field."""

    active: bool
    visible: bool


@dataclass
class Config(Component):
    """Test component with optional field."""

    name: str
    value: Optional[int] = None


@dataclass
class AllyTo(Edge):
    """Test edge type for ally relationships."""

    trust_level: float = 1.0


@dataclass
class OwnsItem(Edge):
    """Test edge type with string field."""

    item_name: str


class TestSQLitePersistenceDriver:
    """Tests for SQLitePersistenceDriver class."""

    def test_driver_save_basic(self) -> None:
        """Test basic save functionality with driver instance."""
        driver = SQLitePersistenceDriver()
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Health: Health(current=100, maximum=100)},
        )
        world.spawn("player", {Position: Position(x=10, y=20)})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            driver.save(world, temp_path)

            # Verify database structure
            conn = sqlite3.connect(temp_path)
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor}
            conn.close()

            assert "metadata" in tables
            assert "prefabs" in tables
            assert "entities" in tables
            assert "component_Position" in tables
            assert "component_Health" in tables
        finally:
            Path(temp_path).unlink()

    def test_driver_load_basic(self) -> None:
        """Test basic load functionality with driver instance."""
        driver = SQLitePersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        entity = world.spawn("player", {Position: Position(x=10, y=20)})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            driver.save(world, temp_path)

            world2 = World()
            driver.load(world2, temp_path, {"Position": Position, "Health": Health})

            assert len(world2._entities) == 1
            loaded_entity = world2.get_entity(entity.id)
            assert loaded_entity.get_component(Position).x == 10
            assert loaded_entity.get_component(Position).y == 20
        finally:
            Path(temp_path).unlink()

    def test_driver_round_trip(self) -> None:
        """Test save/load round-trip preserves data."""
        driver = SQLitePersistenceDriver()
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

        with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            driver.save(world, temp_path)

            world2 = World()
            component_registry = {"Position": Position, "Health": Health}
            driver.load(world2, temp_path, component_registry)

            assert world2.has_entity(entity1.id)
            assert world2.has_entity(entity2.id)

            e1 = world2.get_entity(entity1.id)
            e2 = world2.get_entity(entity2.id)

            assert e1.get_component(Position).x == 10
            assert e2.get_component(Position).x == 30
            assert e2.get_component(Health).current == 50
        finally:
            Path(temp_path).unlink()

    def test_driver_round_trip_with_relationships(self) -> None:
        """Test save/load round-trip with relationships."""
        driver = SQLitePersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player", {Position: Position(x=10, y=20)})
        p2 = world.spawn("player", {Position: Position(x=30, y=40)})
        p1.add_relationship(AllyTo(trust_level=0.9), p2.id)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            driver.save(world, temp_path)

            # Verify edge table exists
            conn = sqlite3.connect(temp_path)
            sql = "SELECT name FROM sqlite_master "
            sql += "WHERE type='table' AND name='edge_AllyTo'"
            cursor = conn.execute(sql)
            assert cursor.fetchone() is not None
            conn.close()

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

    def test_driver_complex_types(self) -> None:
        """Test saving/loading components with complex types (lists)."""
        driver = SQLitePersistenceDriver()
        world = World()
        world.register_prefab(
            "player",
            {Inventory: Inventory(items=[], capacity=10)},
        )
        entity = world.spawn(
            "player",
            {Inventory: Inventory(items=["sword", "shield", "potion"], capacity=20)},
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            driver.save(world, temp_path)

            world2 = World()
            driver.load(world2, temp_path, {"Inventory": Inventory})

            loaded = world2.get_entity(entity.id)
            inv = loaded.get_component(Inventory)
            assert inv.items == ["sword", "shield", "potion"]
            assert inv.capacity == 20
        finally:
            Path(temp_path).unlink()

    def test_driver_boolean_types(self) -> None:
        """Test saving/loading components with boolean fields."""
        driver = SQLitePersistenceDriver()
        world = World()
        world.register_prefab(
            "player",
            {Flags: Flags(active=False, visible=True)},
        )
        entity = world.spawn(
            "player",
            {Flags: Flags(active=True, visible=False)},
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            driver.save(world, temp_path)

            world2 = World()
            driver.load(world2, temp_path, {"Flags": Flags})

            loaded = world2.get_entity(entity.id)
            flags = loaded.get_component(Flags)
            assert flags.active is True
            assert flags.visible is False
        finally:
            Path(temp_path).unlink()

    def test_driver_optional_types(self) -> None:
        """Test saving/loading components with optional fields."""
        driver = SQLitePersistenceDriver()
        world = World()
        world.register_prefab(
            "player",
            {Config: Config(name="default")},
        )
        e1 = world.spawn("player", {Config: Config(name="config1", value=42)})
        e2 = world.spawn("player", {Config: Config(name="config2", value=None)})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            driver.save(world, temp_path)

            world2 = World()
            driver.load(world2, temp_path, {"Config": Config})

            c1 = world2.get_entity(e1.id).get_component(Config)
            c2 = world2.get_entity(e2.id).get_component(Config)

            assert c1.name == "config1"
            assert c1.value == 42
            assert c2.name == "config2"
            assert c2.value is None
        finally:
            Path(temp_path).unlink()

    def test_driver_epoch_preserved(self) -> None:
        """Test that epoch is preserved on load."""
        driver = SQLitePersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")

        for _ in range(10):
            world.tick(0.016)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            driver.save(world, temp_path)

            world2 = World()
            driver.load(world2, temp_path, {"Position": Position})

            assert world2.epoch == 10
        finally:
            Path(temp_path).unlink()

    def test_driver_save_relic(self) -> None:
        """Test saving a named relic with driver."""
        driver = SQLitePersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")

        with tempfile.TemporaryDirectory() as temp_dir:
            driver.save_relic(world, "test_relic", temp_dir)

            relic_path = Path(temp_dir) / "test_relic.db"
            assert relic_path.exists()

            # Verify metadata
            conn = sqlite3.connect(str(relic_path))
            cursor = conn.execute("SELECT value FROM metadata WHERE key='relic_name'")
            result = cursor.fetchone()
            conn.close()
            assert result[0] == "test_relic"

    def test_driver_load_relic(self) -> None:
        """Test loading a named relic with driver."""
        driver = SQLitePersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        entity = world.spawn("player", {Position: Position(x=10, y=20)})

        with tempfile.TemporaryDirectory() as temp_dir:
            driver.save_relic(world, "test_load", temp_dir)

            world2 = World()
            driver.load_relic(world2, "test_load", temp_dir, {"Position": Position})

            assert world2.has_entity(entity.id)
            loaded = world2.get_entity(entity.id)
            assert loaded.get_component(Position).x == 10

    def test_driver_list_relics(self) -> None:
        """Test listing relics with driver."""
        driver = SQLitePersistenceDriver()
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
        driver = SQLitePersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")

        with tempfile.TemporaryDirectory() as temp_dir:
            driver.save_relic(world, "test_relic", temp_dir)

            with pytest.raises(FileExistsError):
                driver.save_relic(world, "test_relic", temp_dir)

    def test_driver_overwrite_relic_succeeds(self) -> None:
        """Test that overwrite=True allows overwriting."""
        driver = SQLitePersistenceDriver()
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
        driver = SQLitePersistenceDriver()
        world = World()

        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(FileNotFoundError):
                driver.load_relic(world, "nonexistent", temp_dir)

    def test_driver_load_file_not_found(self) -> None:
        """Test loading non-existent file raises error."""
        driver = SQLitePersistenceDriver()
        world = World()

        with pytest.raises(FileNotFoundError):
            driver.load(world, "/nonexistent/path/world.db")

    def test_driver_list_relics_empty_dir(self) -> None:
        """Test listing relics in empty directory."""
        driver = SQLitePersistenceDriver()

        with tempfile.TemporaryDirectory() as temp_dir:
            relics = driver.list_relics(temp_dir)
            assert relics == []

    def test_driver_list_relics_nonexistent_dir(self) -> None:
        """Test listing relics in nonexistent directory."""
        driver = SQLitePersistenceDriver()
        relics = driver.list_relics("/nonexistent/path")
        assert relics == []

    def test_driver_skip_unknown_components(self) -> None:
        """Test that load skips unknown component tables."""
        driver = SQLitePersistenceDriver()
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Health: Health(current=100, maximum=100)},
        )
        entity = world.spawn("player")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            driver.save(world, temp_path)

            # Load with only Position in registry
            world2 = World()
            driver.load(world2, temp_path, {"Position": Position})

            loaded = world2.get_entity(entity.id)
            assert loaded.has_component(Position)
            assert not loaded.has_component(Health)
        finally:
            Path(temp_path).unlink()

    def test_driver_skip_unknown_edge_types(self) -> None:
        """Test that load skips unknown edge tables."""
        driver = SQLitePersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")
        p1.add_relationship(AllyTo(trust_level=0.5), p2.id)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            driver.save(world, temp_path)

            # Load without edge registry
            world2 = World()
            driver.load(world2, temp_path, {"Position": Position}, {})

            loaded_p1 = world2.get_entity(p1.id)
            # Should have no relationships since AllyTo wasn't registered
            assert not loaded_p1.has_relationship(AllyTo)
        finally:
            Path(temp_path).unlink()

    def test_driver_overwrite_existing_db(self) -> None:
        """Test that save overwrites existing database file."""
        driver = SQLitePersistenceDriver()
        world1 = World()
        world1.register_prefab("player", {Position: Position(x=0, y=0)})
        world1.spawn("player", {Position: Position(x=1, y=1)})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            driver.save(world1, temp_path)

            # Save different world to same path
            world2 = World()
            world2.register_prefab("player", {Position: Position(x=0, y=0)})
            world2.spawn("player", {Position: Position(x=99, y=99)})
            driver.save(world2, temp_path)

            # Load and verify it's the second world
            world3 = World()
            driver.load(world3, temp_path, {"Position": Position})

            entities = list(world3._entities.keys())
            assert len(entities) == 1
            pos = world3.get_entity(entities[0]).get_component(Position)
            assert pos.x == 99
            assert pos.y == 99
        finally:
            Path(temp_path).unlink()

    def test_driver_multiple_relationship_types(self) -> None:
        """Test saving/loading with multiple relationship types."""
        driver = SQLitePersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")

        p1.add_relationship(AllyTo(trust_level=0.8), p2.id)
        p1.add_relationship(OwnsItem(item_name="sword"), p2.id)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            driver.save(world, temp_path)

            world2 = World()
            driver.load(
                world2,
                temp_path,
                {"Position": Position},
                {"AllyTo": AllyTo, "OwnsItem": OwnsItem},
            )

            loaded = world2.get_entity(p1.id)
            assert loaded.has_relationship(AllyTo, p2.id)
            assert loaded.has_relationship(OwnsItem, p2.id)

            ally_rels = loaded.get_relationships(AllyTo)
            assert ally_rels[0][0].trust_level == 0.8

            owns_rels = loaded.get_relationships(OwnsItem)
            assert owns_rels[0][0].item_name == "sword"
        finally:
            Path(temp_path).unlink()

    def test_driver_relic_info_fields(self) -> None:
        """Test RelicInfo contains correct fields."""
        driver = SQLitePersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")

        for _ in range(5):
            world.tick(0.016)

        with tempfile.TemporaryDirectory() as temp_dir:
            driver.save_relic(world, "test_info", temp_dir)

            relics = driver.list_relics(temp_dir)
            assert len(relics) == 1

            info = relics[0]
            assert info.name == "test_info"
            assert info.epoch == 5
            assert info.created_at is not None
            assert len(info.created_at) > 0


class TestSQLiteEdgeCases:
    """Tests for edge cases in SQLite loading - orphaned data and corrupted files."""

    def test_load_skips_orphaned_source_relationships(self) -> None:
        """Test loading with relationships pointing to missing source entities."""
        driver = SQLitePersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")
        p1.add_relationship(AllyTo(trust_level=0.9), p2.id)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            driver.save(world, temp_path)

            # Manually corrupt by deleting source entity from database
            conn = sqlite3.connect(temp_path)
            conn.execute(f"DELETE FROM entities WHERE entity_id = '{p1.id}'")
            conn.execute(f"DELETE FROM component_Position WHERE entity_id = '{p1.id}'")
            conn.commit()
            conn.close()

            world2 = World()
            driver.load(world2, temp_path, {"Position": Position}, {"AllyTo": AllyTo})

            # Only p2 should exist
            assert not world2.has_entity(p1.id)
            assert world2.has_entity(p2.id)
        finally:
            Path(temp_path).unlink()

    def test_load_skips_orphaned_target_relationships(self) -> None:
        """Test loading with relationships pointing to missing target entities."""
        driver = SQLitePersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")
        p1.add_relationship(AllyTo(trust_level=0.9), p2.id)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            driver.save(world, temp_path)

            # Manually corrupt by deleting target entity from database
            conn = sqlite3.connect(temp_path)
            conn.execute(f"DELETE FROM entities WHERE entity_id = '{p2.id}'")
            conn.execute(f"DELETE FROM component_Position WHERE entity_id = '{p2.id}'")
            conn.commit()
            conn.close()

            world2 = World()
            driver.load(world2, temp_path, {"Position": Position}, {"AllyTo": AllyTo})

            # p1 should exist but have no relationships
            assert world2.has_entity(p1.id)
            assert not world2.has_entity(p2.id)
            loaded_p1 = world2.get_entity(p1.id)
            assert not loaded_p1.has_relationship(AllyTo)
        finally:
            Path(temp_path).unlink()

    def test_load_skips_orphaned_components(self) -> None:
        """Test loading with components for non-existent entities."""
        driver = SQLitePersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        entity = world.spawn("player")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            driver.save(world, temp_path)

            # Manually corrupt by deleting entity but keeping component
            conn = sqlite3.connect(temp_path)
            conn.execute(f"DELETE FROM entities WHERE entity_id = '{entity.id}'")
            conn.commit()
            conn.close()

            world2 = World()
            driver.load(world2, temp_path, {"Position": Position})

            # Should have no entities (component is orphaned)
            assert len(world2._entities) == 0
        finally:
            Path(temp_path).unlink()

    def test_list_relics_skips_corrupted_files(self) -> None:
        """Test list_relics handles corrupted database files gracefully."""
        driver = SQLitePersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Save a valid relic
            driver.save_relic(world, "valid_relic", temp_dir)

            # Create a corrupted .db file
            corrupted_path = Path(temp_dir) / "corrupted.db"
            corrupted_path.write_text("not a valid sqlite database")

            # Create another corrupted file with valid SQLite but no metadata table
            no_metadata_path = Path(temp_dir) / "no_metadata.db"
            conn = sqlite3.connect(str(no_metadata_path))
            conn.execute("CREATE TABLE other (id INTEGER)")
            conn.commit()
            conn.close()

            # List should skip corrupted files and return only valid relic
            relics = driver.list_relics(temp_dir)

            names = [r.name for r in relics]
            assert "valid_relic" in names
            assert "corrupted" not in names
            assert "no_metadata" not in names

    def test_deserialize_malformed_json_raises_validation_error(self) -> None:
        """Test that malformed JSON in complex fields raises validation error.

        The JSONDecodeError is caught and the raw string is returned,
        but Pydantic validation then fails because it expects a list.
        """
        import pydantic

        driver = SQLitePersistenceDriver()
        world = World()
        world.register_prefab("player", {Inventory: Inventory(items=[], capacity=10)})
        entity = world.spawn("player")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            driver.save(world, temp_path)

            # Corrupt the JSON in the items column
            conn = sqlite3.connect(temp_path)
            conn.execute(
                f"UPDATE component_Inventory SET items = 'not-valid-json[' "
                f"WHERE entity_id = '{entity.id}'"
            )
            conn.commit()
            conn.close()

            world2 = World()
            # The JSON decode error is caught and returns string as-is,
            # but Pydantic validation then fails because items should be a list
            with pytest.raises(pydantic.ValidationError):
                driver.load(world2, temp_path, {"Inventory": Inventory})
        finally:
            Path(temp_path).unlink()


class TestSQLiteSchemaDetails:
    """Tests for SQLite schema details."""

    def test_component_table_schema(self) -> None:
        """Test that component tables have correct schema."""
        driver = SQLitePersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player", {Position: Position(x=1.5, y=2.5)})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            driver.save(world, temp_path)

            conn = sqlite3.connect(temp_path)
            cursor = conn.execute("PRAGMA table_info(component_Position)")
            columns = {row[1]: row[2] for row in cursor}
            conn.close()

            assert "entity_id" in columns
            assert columns["entity_id"] == "TEXT"
            assert "x" in columns
            assert columns["x"] == "REAL"
            assert "y" in columns
            assert columns["y"] == "REAL"
        finally:
            Path(temp_path).unlink()

    def test_edge_table_schema(self) -> None:
        """Test that edge tables have correct schema."""
        driver = SQLitePersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")
        p1.add_relationship(AllyTo(trust_level=0.5), p2.id)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            driver.save(world, temp_path)

            conn = sqlite3.connect(temp_path)
            cursor = conn.execute("PRAGMA table_info(edge_AllyTo)")
            columns = {row[1]: row[2] for row in cursor}
            conn.close()

            assert "source_id" in columns
            assert columns["source_id"] == "TEXT"
            assert "target_id" in columns
            assert columns["target_id"] == "TEXT"
            assert "trust_level" in columns
            assert columns["trust_level"] == "REAL"
        finally:
            Path(temp_path).unlink()

    def test_integer_type_mapping(self) -> None:
        """Test that int fields map to INTEGER."""
        driver = SQLitePersistenceDriver()
        world = World()
        world.register_prefab("player", {Health: Health(current=100, maximum=100)})
        world.spawn("player")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            driver.save(world, temp_path)

            conn = sqlite3.connect(temp_path)
            cursor = conn.execute("PRAGMA table_info(component_Health)")
            columns = {row[1]: row[2] for row in cursor}
            conn.close()

            assert columns["current"] == "INTEGER"
            assert columns["maximum"] == "INTEGER"
        finally:
            Path(temp_path).unlink()
