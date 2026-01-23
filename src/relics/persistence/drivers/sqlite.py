"""SQLite persistence driver for saving and loading world state."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Set,
    Type,
    Union,
    cast,
    get_args,
    get_origin,
)

from relics.persistence.base import PersistenceDriver, RelicInfo
from relics.persistence.serialization import _component_to_dict, _dict_to_component
from relics.prefab import prefab_to_dict
from relics.types import Component, Edge, EntityId

if TYPE_CHECKING:
    from relics.world import World


class SQLitePersistenceDriver(PersistenceDriver):
    """SQLite database persistence driver.

    Saves and loads world state to/from SQLite databases with:
    - Fixed tables for metadata, prefabs, and entities
    - Dynamic tables for each component and edge type
    - Efficient type mapping for primitive types
    """

    def _python_type_to_sqlite(self, python_type: Any) -> str:
        """Map Python types to SQLite column types.

        Args:
            python_type: The Python type annotation.

        Returns:
            SQLite column type string.
        """
        # Handle Optional types
        origin = get_origin(python_type)
        if origin is Union:
            args = get_args(python_type)
            # Filter out NoneType for Optional
            non_none_args = [a for a in args if a is not type(None)]
            if len(non_none_args) == 1:
                return self._python_type_to_sqlite(non_none_args[0])

        # Handle basic types
        if python_type is int:
            return "INTEGER"
        elif python_type is float:
            return "REAL"
        elif python_type is str:
            return "TEXT"
        elif python_type is bool:
            return "INTEGER"  # SQLite stores bools as 0/1
        else:
            # Complex types (list, dict, etc.) serialize to JSON text
            return "TEXT"

    def _get_type_hints(self, cls: Type) -> Dict[str, Any]:
        """Get type hints for a class, handling various component formats.

        Args:
            cls: The class to get type hints for.

        Returns:
            Dictionary of field names to types.
        """
        hints: Dict[str, Any] = {}

        if hasattr(cls, "__dataclass_fields__"):
            for name, field in cls.__dataclass_fields__.items():
                if not name.startswith("_"):
                    hints[name] = field.type
        elif hasattr(cls, "__pydantic_fields__"):
            for name, field in cls.__pydantic_fields__.items():
                if not name.startswith("_"):
                    hints[name] = field.annotation
        elif hasattr(cls, "model_fields"):
            for name, field in cls.model_fields.items():
                if not name.startswith("_"):
                    hints[name] = field.annotation
        elif hasattr(cls, "__annotations__"):
            hints = {
                k: v for k, v in cls.__annotations__.items() if not k.startswith("_")
            }

        return hints

    def _create_component_table(
        self,
        conn: sqlite3.Connection,
        comp_type: Type[Component],
    ) -> str:
        """Create a table for a component type.

        Args:
            conn: SQLite connection.
            comp_type: The component type.

        Returns:
            The table name.
        """
        table_name = f"component_{comp_type.__name__}"
        hints = self._get_type_hints(comp_type)

        columns = ["entity_id TEXT PRIMARY KEY"]
        for field_name, field_type in hints.items():
            sqlite_type = self._python_type_to_sqlite(field_type)
            columns.append(f"{field_name} {sqlite_type}")

        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})"
        conn.execute(sql)
        return table_name

    def _create_edge_table(
        self,
        conn: sqlite3.Connection,
        edge_type: Type[Edge],
    ) -> str:
        """Create a table for an edge type.

        Args:
            conn: SQLite connection.
            edge_type: The edge type.

        Returns:
            The table name.
        """
        table_name = f"edge_{edge_type.__name__}"
        hints = self._get_type_hints(edge_type)

        columns = [
            "source_id TEXT NOT NULL",
            "target_id TEXT NOT NULL",
        ]
        for field_name, field_type in hints.items():
            sqlite_type = self._python_type_to_sqlite(field_type)
            columns.append(f"{field_name} {sqlite_type}")

        columns.append("PRIMARY KEY (source_id, target_id)")

        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})"
        conn.execute(sql)
        return table_name

    def _serialize_value(self, value: Any, field_type: Any) -> Any:
        """Serialize a value for SQLite storage.

        Args:
            value: The value to serialize.
            field_type: The expected type.

        Returns:
            Serialized value suitable for SQLite.
        """
        if value is None:
            return None
        elif isinstance(value, bool):
            return 1 if value else 0
        elif isinstance(value, (int, float, str)):
            return value
        else:
            # Complex types serialize to JSON
            return json.dumps(value)

    def _deserialize_value(self, value: Any, field_type: Any) -> Any:
        """Deserialize a value from SQLite storage.

        Args:
            value: The stored value.
            field_type: The expected type.

        Returns:
            Deserialized Python value.
        """
        if value is None:
            return None

        # Handle Optional types
        origin = get_origin(field_type)
        if origin is Union:
            args = get_args(field_type)
            non_none_args = [a for a in args if a is not type(None)]
            if len(non_none_args) == 1:
                field_type = non_none_args[0]

        if field_type is bool:
            return bool(value)
        elif field_type is int:
            return int(value)
        elif field_type is float:
            return float(value)
        elif field_type is str:
            return str(value)
        else:
            # Complex types were JSON serialized
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return value

    def save(
        self,
        world: "World",
        path: str | Path,
        relic_name: Optional[str] = None,
    ) -> None:
        """Save world state to a SQLite database.

        Args:
            world: The World to save.
            path: Path to write the database file.
            relic_name: Optional name for this relic snapshot.
        """
        path = Path(path)

        # Remove existing file if it exists
        if path.exists():
            path.unlink()

        conn = sqlite3.connect(str(path))
        try:
            # Create fixed tables
            conn.execute("""
                CREATE TABLE metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE prefabs (
                    name TEXT PRIMARY KEY,
                    definition TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE entities (
                    entity_id TEXT PRIMARY KEY,
                    prefab TEXT NOT NULL,
                    created_epoch INTEGER DEFAULT 0
                )
            """)

            # Store metadata
            metadata = {
                "version": "1.0",
                "epoch": str(world.epoch),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "world_id": world.id,
            }
            if relic_name is not None:
                metadata["relic_name"] = relic_name

            for key, value in metadata.items():
                conn.execute(
                    "INSERT INTO metadata (key, value) VALUES (?, ?)",
                    (key, value),
                )

            # Store prefabs
            for prefab_name, components in world._prefabs.items():
                definition = json.dumps(prefab_to_dict(prefab_name, components))
                conn.execute(
                    "INSERT INTO prefabs (name, definition) VALUES (?, ?)",
                    (prefab_name, definition),
                )

            # Store entities
            for entity_id in world._entities:
                sql = "INSERT INTO entities (entity_id, prefab, created_epoch) "
                sql += "VALUES (?, ?, ?)"
                conn.execute(sql, (str(entity_id), entity_id.prefab, 0))

            # Create component tables and store data
            component_types_seen: Set[Type[Component]] = set()
            for entity_id, components in world._entities.items():
                for comp_type, comp_instance in components.items():
                    if comp_type not in component_types_seen:
                        self._create_component_table(conn, comp_type)
                        component_types_seen.add(comp_type)

                    # Get field data
                    data = _component_to_dict(comp_instance)
                    hints = self._get_type_hints(comp_type)

                    # Build insert statement
                    fields = ["entity_id"] + list(data.keys())
                    placeholders = ["?"] * len(fields)
                    values = [str(entity_id)] + [
                        self._serialize_value(data[f], hints.get(f))
                        for f in data.keys()
                    ]

                    table_name = f"component_{comp_type.__name__}"
                    fields_str = ", ".join(fields)
                    placeholders_str = ", ".join(placeholders)
                    sql = (
                        f"INSERT INTO {table_name} ({fields_str}) "
                        f"VALUES ({placeholders_str})"
                    )
                    conn.execute(sql, values)

            # Create edge tables and store relationships
            edge_types_seen: Set[Type[Edge]] = set()
            for source_id, edge_types in world._relationships.items():
                for edge_type, edges in edge_types.items():
                    if edge_type not in edge_types_seen:
                        self._create_edge_table(conn, edge_type)
                        edge_types_seen.add(edge_type)

                    for target_id, edge in edges.items():
                        data = _component_to_dict(edge)
                        hints = self._get_type_hints(edge_type)

                        fields = ["source_id", "target_id"] + list(data.keys())
                        placeholders = ["?"] * len(fields)
                        values = [str(source_id), str(target_id)] + [
                            self._serialize_value(data[f], hints.get(f))
                            for f in data.keys()
                        ]

                        table_name = f"edge_{edge_type.__name__}"
                        fields_str = ", ".join(fields)
                        placeholders_str = ", ".join(placeholders)
                        sql = (
                            f"INSERT INTO {table_name} ({fields_str}) "
                            f"VALUES ({placeholders_str})"
                        )
                        conn.execute(sql, values)

            conn.commit()
        finally:
            conn.close()

    def load(
        self,
        world: "World",
        path: str | Path,
        component_registry: Optional[Dict[str, Type[Component]]] = None,
        edge_registry: Optional[Dict[str, Type[Edge]]] = None,
    ) -> None:
        """Load world state from a SQLite database.

        Args:
            world: The World to load into (will be cleared first).
            path: Path to the database file.
            component_registry: Optional mapping of component names to types.
                If not provided, uses the world's registered component types.
            edge_registry: Optional mapping of edge names to types.
                If not provided, uses the world's registered edge types.

        Raises:
            FileNotFoundError: If the database doesn't exist.
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Database '{path}' not found")

        # Use provided registry or world's registry
        if component_registry is None:
            component_registry = world._component_types
        if edge_registry is None:
            edge_registry = world._edge_types

        # Clear existing state
        world._entities.clear()
        world._prefab_index.clear()
        world._relationships.clear()
        world._incoming_relationships.clear()
        world._component_index.clear()

        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        try:
            # Load metadata
            cursor = conn.execute("SELECT key, value FROM metadata")
            metadata = {row["key"]: row["value"] for row in cursor}
            world._epoch = int(metadata.get("epoch", 0))

            # Load prefabs
            cursor = conn.execute("SELECT name, definition FROM prefabs")
            for row in cursor:
                prefab_name = row["name"]
                prefab_info = json.loads(row["definition"])
                components_info = prefab_info.get("components", {})
                components: Dict[Type[Component], Component] = {}

                for comp_name, comp_fields in components_info.items():
                    if comp_name not in component_registry:
                        continue
                    comp_type = component_registry[comp_name]
                    components[comp_type] = cast(
                        Component, _dict_to_component(comp_type, comp_fields)
                    )

                world._prefabs[prefab_name] = components

            # Load entities
            cursor = conn.execute("SELECT entity_id, prefab FROM entities")
            for row in cursor:
                entity_id = EntityId.parse(row["entity_id"])
                prefab = row["prefab"]

                world._entities[entity_id] = {}

                if prefab not in world._prefab_index:
                    world._prefab_index[prefab] = set()
                world._prefab_index[prefab].add(entity_id)

            # Find and load component tables
            sql = "SELECT name FROM sqlite_master "
            sql += "WHERE type='table' AND name LIKE 'component_%'"
            cursor = conn.execute(sql)
            component_tables = [row["name"] for row in cursor]

            for table_name in component_tables:
                comp_name = table_name[len("component_") :]
                if comp_name not in component_registry:
                    continue

                comp_type = component_registry[comp_name]
                hints = self._get_type_hints(comp_type)

                cursor = conn.execute(f"SELECT * FROM {table_name}")
                for row in cursor:
                    entity_id = EntityId.parse(row["entity_id"])
                    if entity_id not in world._entities:
                        continue

                    # Build component data
                    comp_data: Dict[str, Any] = {}
                    for field_name in hints.keys():
                        if field_name in row.keys():
                            comp_data[field_name] = self._deserialize_value(
                                row[field_name], hints[field_name]
                            )

                    component = cast(
                        Component, _dict_to_component(comp_type, comp_data)
                    )
                    world._entities[entity_id][comp_type] = component

                    if comp_type not in world._component_index:
                        world._component_index[comp_type] = set()
                    world._component_index[comp_type].add(entity_id)

            # Find and load edge tables
            sql = "SELECT name FROM sqlite_master "
            sql += "WHERE type='table' AND name LIKE 'edge_%'"
            cursor = conn.execute(sql)
            edge_tables = [row["name"] for row in cursor]

            for table_name in edge_tables:
                edge_name = table_name[len("edge_") :]
                if edge_name not in edge_registry:
                    continue

                edge_type = edge_registry[edge_name]
                hints = self._get_type_hints(edge_type)

                cursor = conn.execute(f"SELECT * FROM {table_name}")
                for row in cursor:
                    source_id = EntityId.parse(row["source_id"])
                    target_id = EntityId.parse(row["target_id"])

                    if source_id not in world._entities:
                        continue
                    if target_id not in world._entities:
                        continue

                    # Build edge data
                    edge_data: Dict[str, Any] = {}
                    for field_name in hints.keys():
                        if field_name in row.keys():
                            edge_data[field_name] = self._deserialize_value(
                                row[field_name], hints[field_name]
                            )

                    edge = cast(Edge, _dict_to_component(edge_type, edge_data))

                    # Add to outgoing
                    if source_id not in world._relationships:
                        world._relationships[source_id] = {}
                    if edge_type not in world._relationships[source_id]:
                        world._relationships[source_id][edge_type] = {}
                    world._relationships[source_id][edge_type][target_id] = edge

                    # Add to incoming
                    if target_id not in world._incoming_relationships:
                        world._incoming_relationships[target_id] = {}
                    if edge_type not in world._incoming_relationships[target_id]:
                        world._incoming_relationships[target_id][edge_type] = {}
                    world._incoming_relationships[target_id][edge_type][
                        source_id
                    ] = edge

        finally:
            conn.close()

    def save_relic(
        self,
        world: "World",
        name: str,
        relics_dir: str | Path,
        overwrite: bool = False,
    ) -> None:
        """Save a named snapshot (relic) of the world.

        Relics are saved as complete database file copies.

        Args:
            world: The World to save.
            name: The relic name.
            relics_dir: Directory to store relics.
            overwrite: If True, overwrite existing relic with same name.

        Raises:
            FileExistsError: If relic exists and overwrite is False.
        """
        relics_dir = Path(relics_dir)
        relics_dir.mkdir(parents=True, exist_ok=True)

        relic_path = relics_dir / f"{name}.db"
        if relic_path.exists() and not overwrite:
            raise FileExistsError(f"Relic '{name}' already exists")

        self.save(world, relic_path, relic_name=name)

    def load_relic(
        self,
        world: "World",
        name: str,
        relics_dir: str | Path,
        component_registry: Optional[Dict[str, Type[Component]]] = None,
        edge_registry: Optional[Dict[str, Type[Edge]]] = None,
    ) -> None:
        """Load a named relic into the world.

        Args:
            world: The World to load into.
            name: The relic name.
            relics_dir: Directory containing relics.
            component_registry: Optional mapping of component names to types.
            edge_registry: Optional mapping of edge names to types.

        Raises:
            FileNotFoundError: If the relic doesn't exist.
        """
        relics_dir = Path(relics_dir)
        relic_path = relics_dir / f"{name}.db"

        if not relic_path.exists():
            raise FileNotFoundError(f"Relic '{name}' not found")

        self.load(world, relic_path, component_registry, edge_registry)

    def list_relics(self, relics_dir: str | Path) -> List[RelicInfo]:
        """List all available relics.

        Scans the directory for .db files and reads metadata from each.

        Args:
            relics_dir: Directory containing relics.

        Returns:
            List of RelicInfo objects.
        """
        relics_dir = Path(relics_dir)

        if not relics_dir.exists():
            return []

        relics: List[RelicInfo] = []

        for db_file in relics_dir.glob("*.db"):
            try:
                conn = sqlite3.connect(str(db_file))
                conn.row_factory = sqlite3.Row
                try:
                    cursor = conn.execute("SELECT key, value FROM metadata")
                    metadata = {row["key"]: row["value"] for row in cursor}

                    name = metadata.get("relic_name", db_file.stem)

                    relics.append(
                        RelicInfo(
                            name=name,
                            epoch=int(metadata.get("epoch", 0)),
                            created_at=metadata.get("created_at", ""),
                        )
                    )
                finally:
                    conn.close()
            except (sqlite3.Error, KeyError):
                # Skip invalid files
                continue

        # Sort by creation time (newest first)
        relics.sort(key=lambda r: r.created_at, reverse=True)
        return relics
