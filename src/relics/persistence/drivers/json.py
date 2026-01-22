"""JSON persistence driver for saving and loading world state."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, cast

from relics.persistence.base import PersistenceDriver, RelicInfo
from relics.persistence.serialization import _component_to_dict, _dict_to_component
from relics.prefab import prefab_to_dict
from relics.types import Component, Edge, EntityId

if TYPE_CHECKING:
    from relics.world import World


class JSONPersistenceDriver(PersistenceDriver):
    """JSON file persistence driver.

    Saves and loads world state to/from JSON files using the type-grouped
    format from SPEC.md.
    """

    def save(
        self,
        world: "World",
        path: str | Path,
        relic_name: Optional[str] = None,
    ) -> None:
        """Save world state to a JSON file.

        Uses the type-grouped format from SPEC.md.

        Args:
            world: The World to save.
            path: Path to write the JSON file.
            relic_name: Optional name for this relic snapshot.
        """
        path = Path(path)

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

        # Build entities section (entity_id -> metadata)
        entities_data: Dict[str, Dict[str, Any]] = {}
        for entity_id in world._entities:
            entities_data[str(entity_id)] = {
                "prefab": entity_id.prefab,
                "created_epoch": 0,  # TODO: track creation epoch
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
                # edges is now a dict: {target_id -> edge}
                for target_id, edge in edges.items():
                    relationships_data[type_name][source_key].append(
                        {
                            "target": str(target_id),
                            "edge": _component_to_dict(edge),
                        }
                    )

        # Build the full data structure
        data = {
            "metadata": metadata,
            "prefabs": prefabs_data,
            "entities": entities_data,
            "components": components_data,
            "relationships": relationships_data,
            "relics": [],  # Relics are stored separately
        }

        with path.open("w") as f:
            json.dump(data, f, indent=2)

    def load(
        self,
        world: "World",
        path: str | Path,
        component_registry: Optional[Dict[str, Type[Component]]] = None,
        edge_registry: Optional[Dict[str, Type[Edge]]] = None,
    ) -> None:
        """Load world state from a JSON file.

        Args:
            world: The World to load into (will be cleared first).
            path: Path to the JSON file.
            component_registry: Optional mapping of component names to types.
                If not provided, uses the world's registered component types.
            edge_registry: Optional mapping of edge names to types.
                If not provided, uses the world's registered edge types.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            ValueError: If a component type is not found.
        """
        path = Path(path)

        with path.open("r") as f:
            data = json.load(f)

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
                    continue  # Skip unknown components
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

            # Initialize empty component dict
            world._entities[entity_id] = {}

            # Update prefab index
            if prefab not in world._prefab_index:
                world._prefab_index[prefab] = set()
            world._prefab_index[prefab].add(entity_id)

        # Load components
        for comp_name, entities_components in components_data.items():
            if comp_name not in component_registry:
                continue  # Skip unknown components

            comp_type = component_registry[comp_name]

            for entity_id_str, comp_fields in entities_components.items():
                entity_id = EntityId.parse(entity_id_str)
                if entity_id in world._entities:
                    component = cast(
                        Component, _dict_to_component(comp_type, comp_fields)
                    )
                    world._entities[entity_id][comp_type] = component

                    # Update component index
                    if comp_type not in world._component_index:
                        world._component_index[comp_type] = set()
                    world._component_index[comp_type].add(entity_id)

        # Load relationships
        relationships_data = data.get("relationships", {})
        for edge_name, sources in relationships_data.items():
            if edge_name not in edge_registry:
                continue  # Skip unknown edge types

            edge_type = edge_registry[edge_name]

            for source_id_str, edges in sources.items():
                source_id = EntityId.parse(source_id_str)
                if source_id not in world._entities:
                    continue  # Skip if source doesn't exist

                for edge_info in edges:
                    target_id = EntityId.parse(edge_info["target"])
                    if target_id not in world._entities:
                        continue  # Skip if target doesn't exist

                    edge = cast(Edge, _dict_to_component(edge_type, edge_info["edge"]))

                    # Add to outgoing (dict-based for O(1) removal)
                    if source_id not in world._relationships:
                        world._relationships[source_id] = {}
                    if edge_type not in world._relationships[source_id]:
                        world._relationships[source_id][edge_type] = {}
                    world._relationships[source_id][edge_type][target_id] = edge

                    # Add to incoming (dict-based for O(1) removal)
                    if target_id not in world._incoming_relationships:
                        world._incoming_relationships[target_id] = {}
                    if edge_type not in world._incoming_relationships[target_id]:
                        world._incoming_relationships[target_id][edge_type] = {}
                    world._incoming_relationships[target_id][edge_type][
                        source_id
                    ] = edge

    def save_relic(
        self,
        world: "World",
        name: str,
        relics_dir: str | Path,
        overwrite: bool = False,
    ) -> None:
        """Save a named snapshot (relic) of the world.

        The relic name and metadata are stored within the JSON file itself,
        making each relic file self-contained.

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

        relic_path = relics_dir / f"{name}.json"
        if relic_path.exists() and not overwrite:
            raise FileExistsError(f"Relic '{name}' already exists")

        # Save the world state with relic name in metadata
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
        relic_path = relics_dir / f"{name}.json"

        if not relic_path.exists():
            raise FileNotFoundError(f"Relic '{name}' not found")

        self.load(world, relic_path, component_registry, edge_registry)

    def list_relics(self, relics_dir: str | Path) -> List[RelicInfo]:
        """List all available relics.

        Scans the directory for JSON files and reads metadata from each.
        Each relic file is self-contained with its name in the metadata.

        Args:
            relics_dir: Directory containing relics.

        Returns:
            List of RelicInfo objects.
        """
        relics_dir = Path(relics_dir)

        if not relics_dir.exists():
            return []

        relics: List[RelicInfo] = []

        for json_file in relics_dir.glob("*.json"):
            # Skip any legacy metadata files
            if json_file.name.startswith("_"):
                continue

            try:
                with json_file.open("r") as f:
                    data = json.load(f)

                metadata = data.get("metadata", {})
                # Use relic_name from metadata if available, otherwise derive from filename
                name = metadata.get("relic_name", json_file.stem)

                relics.append(
                    RelicInfo(
                        name=name,
                        epoch=metadata.get("epoch", 0),
                        created_at=metadata.get("created_at", ""),
                    )
                )
            except (json.JSONDecodeError, KeyError):
                # Skip invalid files
                continue

        # Sort by creation time (newest first)
        relics.sort(key=lambda r: r.created_at, reverse=True)
        return relics
