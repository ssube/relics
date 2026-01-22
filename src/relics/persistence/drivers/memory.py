"""In-memory persistence driver for testing and temporary snapshots."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, cast

from relics.persistence.base import PersistenceDriver, RelicInfo
from relics.persistence.serialization import _component_to_dict, _dict_to_component
from relics.prefab import prefab_to_dict
from relics.types import Component, Edge, EntityId

if TYPE_CHECKING:
    from relics.world import World


class InMemoryPersistenceDriver(PersistenceDriver):
    """In-memory persistence driver.

    Stores world snapshots in memory using a dictionary. Useful for:
    - Testing without disk I/O
    - Undo/redo systems
    - Temporary checkpoints
    - Fast snapshot/restore cycles

    The path parameter is used as a dictionary key, so any string works.

    Example:
        driver = InMemoryPersistenceDriver()
        driver.save(world, "checkpoint_1")
        driver.save(world, "checkpoint_2")
        driver.load(world, "checkpoint_1")  # Restore to checkpoint_1

    Note:
        Data is stored as deep copies to prevent reference issues.
        All data is lost when the driver instance is garbage collected.
    """

    def __init__(self) -> None:
        """Initialize the in-memory storage."""
        self._storage: Dict[str, Dict[str, Any]] = {}
        self._relics: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def clear(self) -> None:
        """Clear all stored snapshots and relics.

        Useful for resetting state between tests.
        """
        self._storage.clear()
        self._relics.clear()

    def _world_to_data(
        self, world: "World", relic_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convert world state to a serializable dictionary.

        Args:
            world: The World to serialize.
            relic_name: Optional name for this relic snapshot.

        Returns:
            Dictionary containing all world state.
        """
        # Build metadata
        metadata: Dict[str, Any] = {
            "version": "1.0",
            "epoch": world.epoch,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "world_id": world.id,
        }
        if relic_name is not None:
            metadata["relic_name"] = relic_name

        # Build prefabs section
        prefabs_data: Dict[str, Dict[str, Any]] = {}
        for prefab_name, components in world._prefabs.items():
            prefabs_data[prefab_name] = prefab_to_dict(prefab_name, components)

        # Build entities section
        entities_data: Dict[str, Dict[str, Any]] = {}
        for entity_id in world._entities:
            entities_data[str(entity_id)] = {
                "prefab": entity_id.prefab,
                "created_epoch": 0,
            }

        # Build components section (type-grouped)
        components_data: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for entity_id, components in world._entities.items():
            for comp_type, comp_instance in components.items():
                type_name = comp_type.__name__
                if type_name not in components_data:
                    components_data[type_name] = {}
                components_data[type_name][str(entity_id)] = _component_to_dict(
                    comp_instance
                )

        # Build relationships section (type-grouped)
        relationships_data: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        for source_id, edge_types in world._relationships.items():
            for edge_type, edges in edge_types.items():
                type_name = edge_type.__name__
                if type_name not in relationships_data:
                    relationships_data[type_name] = {}
                source_key = str(source_id)
                if source_key not in relationships_data[type_name]:
                    relationships_data[type_name][source_key] = []
                for target_id, edge in edges.items():
                    relationships_data[type_name][source_key].append(
                        {
                            "target": str(target_id),
                            "edge": _component_to_dict(edge),
                        }
                    )

        return {
            "metadata": metadata,
            "prefabs": prefabs_data,
            "entities": entities_data,
            "components": components_data,
            "relationships": relationships_data,
        }

    def _data_to_world(
        self,
        world: "World",
        data: Dict[str, Any],
        component_registry: Optional[Dict[str, Type[Component]]] = None,
        edge_registry: Optional[Dict[str, Type[Edge]]] = None,
    ) -> None:
        """Load world state from a dictionary.

        Args:
            world: The World to load into.
            data: The data dictionary.
            component_registry: Optional mapping of component names to types.
            edge_registry: Optional mapping of edge names to types.
        """
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

        # Load metadata
        metadata = data.get("metadata", {})
        world._epoch = metadata.get("epoch", 0)

        # Load prefabs
        prefabs_data = data.get("prefabs", {})
        for prefab_name, prefab_info in prefabs_data.items():
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
        entities_data = data.get("entities", {})
        components_data = data.get("components", {})

        for entity_id_str, entity_info in entities_data.items():
            entity_id = EntityId.parse(entity_id_str)
            prefab = entity_info.get("prefab", entity_id.prefab)

            world._entities[entity_id] = {}

            if prefab not in world._prefab_index:
                world._prefab_index[prefab] = set()
            world._prefab_index[prefab].add(entity_id)

        # Load components
        for comp_name, entities_components in components_data.items():
            if comp_name not in component_registry:
                continue

            comp_type = component_registry[comp_name]

            for entity_id_str, comp_fields in entities_components.items():
                entity_id = EntityId.parse(entity_id_str)
                if entity_id in world._entities:
                    component = cast(
                        Component, _dict_to_component(comp_type, comp_fields)
                    )
                    world._entities[entity_id][comp_type] = component

                    if comp_type not in world._component_index:
                        world._component_index[comp_type] = set()
                    world._component_index[comp_type].add(entity_id)

        # Load relationships
        relationships_data = data.get("relationships", {})
        for edge_name, sources in relationships_data.items():
            if edge_name not in edge_registry:
                continue

            edge_type = edge_registry[edge_name]

            for source_id_str, edges in sources.items():
                source_id = EntityId.parse(source_id_str)
                if source_id not in world._entities:
                    continue

                for edge_info in edges:
                    target_id = EntityId.parse(edge_info["target"])
                    if target_id not in world._entities:
                        continue

                    edge = cast(Edge, _dict_to_component(edge_type, edge_info["edge"]))

                    if source_id not in world._relationships:
                        world._relationships[source_id] = {}
                    if edge_type not in world._relationships[source_id]:
                        world._relationships[source_id][edge_type] = {}
                    world._relationships[source_id][edge_type][target_id] = edge

                    if target_id not in world._incoming_relationships:
                        world._incoming_relationships[target_id] = {}
                    if edge_type not in world._incoming_relationships[target_id]:
                        world._incoming_relationships[target_id][edge_type] = {}
                    world._incoming_relationships[target_id][edge_type][
                        source_id
                    ] = edge

    def save(
        self,
        world: "World",
        path: str | Path,
        relic_name: Optional[str] = None,
    ) -> None:
        """Save world state to memory.

        Args:
            world: The World to save.
            path: Key to store the snapshot under.
            relic_name: Optional name for this relic snapshot.
        """
        key = str(path)
        data = self._world_to_data(world, relic_name)
        # Deep copy to prevent reference issues
        self._storage[key] = copy.deepcopy(data)

    def load(
        self,
        world: "World",
        path: str | Path,
        component_registry: Optional[Dict[str, Type[Component]]] = None,
        edge_registry: Optional[Dict[str, Type[Edge]]] = None,
    ) -> None:
        """Load world state from memory.

        Args:
            world: The World to load into.
            path: Key of the stored snapshot.
            component_registry: Optional mapping of component names to types.
            edge_registry: Optional mapping of edge names to types.

        Raises:
            FileNotFoundError: If no snapshot exists with the given key.
        """
        key = str(path)
        if key not in self._storage:
            raise FileNotFoundError(f"Snapshot '{key}' not found")

        # Deep copy to prevent reference issues
        data = copy.deepcopy(self._storage[key])
        self._data_to_world(world, data, component_registry, edge_registry)

    def save_relic(
        self,
        world: "World",
        name: str,
        relics_dir: str | Path,
        overwrite: bool = False,
    ) -> None:
        """Save a named snapshot (relic) to memory.

        Args:
            world: The World to save.
            name: The relic name.
            relics_dir: Directory key for organizing relics.
            overwrite: If True, overwrite existing relic with same name.

        Raises:
            FileExistsError: If relic exists and overwrite is False.
        """
        dir_key = str(relics_dir)
        if dir_key not in self._relics:
            self._relics[dir_key] = {}

        if name in self._relics[dir_key] and not overwrite:
            raise FileExistsError(f"Relic '{name}' already exists")

        data = self._world_to_data(world, relic_name=name)
        self._relics[dir_key][name] = copy.deepcopy(data)

    def load_relic(
        self,
        world: "World",
        name: str,
        relics_dir: str | Path,
        component_registry: Optional[Dict[str, Type[Component]]] = None,
        edge_registry: Optional[Dict[str, Type[Edge]]] = None,
    ) -> None:
        """Load a named relic from memory.

        Args:
            world: The World to load into.
            name: The relic name.
            relics_dir: Directory key containing relics.
            component_registry: Optional mapping of component names to types.
            edge_registry: Optional mapping of edge names to types.

        Raises:
            FileNotFoundError: If the relic doesn't exist.
        """
        dir_key = str(relics_dir)
        if dir_key not in self._relics or name not in self._relics[dir_key]:
            raise FileNotFoundError(f"Relic '{name}' not found")

        data = copy.deepcopy(self._relics[dir_key][name])
        self._data_to_world(world, data, component_registry, edge_registry)

    def list_relics(self, relics_dir: str | Path) -> List[RelicInfo]:
        """List all available relics in a directory.

        Args:
            relics_dir: Directory key containing relics.

        Returns:
            List of RelicInfo objects.
        """
        dir_key = str(relics_dir)
        if dir_key not in self._relics:
            return []

        relics: List[RelicInfo] = []
        for name, data in self._relics[dir_key].items():
            metadata = data.get("metadata", {})
            relics.append(
                RelicInfo(
                    name=metadata.get("relic_name", name),
                    epoch=metadata.get("epoch", 0),
                    created_at=metadata.get("created_at", ""),
                )
            )

        # Sort by creation time (newest first)
        relics.sort(key=lambda r: r.created_at, reverse=True)
        return relics

    def has_snapshot(self, path: str | Path) -> bool:
        """Check if a snapshot exists.

        Args:
            path: Key to check.

        Returns:
            True if snapshot exists.
        """
        return str(path) in self._storage

    def delete_snapshot(self, path: str | Path) -> bool:
        """Delete a snapshot.

        Args:
            path: Key of snapshot to delete.

        Returns:
            True if snapshot was deleted, False if it didn't exist.
        """
        key = str(path)
        if key in self._storage:
            del self._storage[key]
            return True
        return False

    def list_snapshots(self) -> List[str]:
        """List all stored snapshot keys.

        Returns:
            List of snapshot keys.
        """
        return list(self._storage.keys())
