"""JSON persistence backend for saving and loading world state."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

from relics.prefab import prefab_to_dict
from relics.types import Component, EntityId

if TYPE_CHECKING:
    from relics.world import World


@dataclass
class RelicInfo:
    """Information about a saved relic (snapshot).

    Attributes:
        name: The relic name.
        epoch: The epoch at which the relic was saved.
        created_at: Timestamp when the relic was created.
    """

    name: str
    epoch: int
    created_at: str


def _component_to_dict(component: Component) -> Dict[str, Any]:
    """Convert a component to a dictionary for serialization.

    Args:
        component: The component to convert.

    Returns:
        Dictionary of field values.
    """
    if hasattr(component, "__dataclass_fields__"):
        return {
            name: getattr(component, name)
            for name in component.__dataclass_fields__
            if not name.startswith("_")
        }
    elif hasattr(component, "__pydantic_fields__"):
        return {
            name: getattr(component, name)
            for name in component.__pydantic_fields__
            if not name.startswith("_")
        }
    elif hasattr(component, "model_fields"):
        return {
            name: getattr(component, name)
            for name in component.model_fields
            if not name.startswith("_")
        }
    else:
        return {k: v for k, v in component.__dict__.items() if not k.startswith("_")}


def _dict_to_component(
    comp_type: Type[Component],
    data: Dict[str, Any],
) -> Component:
    """Convert a dictionary to a component instance.

    Args:
        comp_type: The component type.
        data: The field values.

    Returns:
        A component instance.
    """
    return comp_type(**data)


def save(world: "World", path: str | Path) -> None:
    """Save world state to a JSON file.

    Uses the type-grouped format from SPEC.md.

    Args:
        world: The World to save.
        path: Path to write the JSON file.
    """
    path = Path(path)

    # Build metadata
    metadata = {
        "version": "1.0",
        "epoch": world.epoch,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "world_id": world.id,
    }

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

    # Build the full data structure
    data = {
        "metadata": metadata,
        "prefabs": prefabs_data,
        "entities": entities_data,
        "components": components_data,
        "relationships": {},  # v0.2 feature
        "relics": [],  # Relics are stored separately
    }

    with path.open("w") as f:
        json.dump(data, f, indent=2)


def load(
    world: "World",
    path: str | Path,
    component_registry: Optional[Dict[str, Type[Component]]] = None,
) -> None:
    """Load world state from a JSON file.

    Args:
        world: The World to load into (will be cleared first).
        path: Path to the JSON file.
        component_registry: Optional mapping of component names to types.
            If not provided, uses the world's registered component types.

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

    # Clear existing state
    world._entities.clear()
    world._prefab_index.clear()

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
            components[comp_type] = _dict_to_component(comp_type, comp_fields)

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
                component = _dict_to_component(comp_type, comp_fields)
                world._entities[entity_id][comp_type] = component


def save_relic(
    world: "World",
    name: str,
    relics_dir: str | Path,
    overwrite: bool = False,
) -> None:
    """Save a named snapshot (relic) of the world.

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

    # Save the world state
    save(world, relic_path)

    # Update relic metadata file
    metadata_path = relics_dir / "_relics.json"
    relics_list: List[Dict[str, Any]] = []

    if metadata_path.exists():
        with metadata_path.open("r") as f:
            relics_list = json.load(f)

    # Remove old entry if overwriting
    relics_list = [r for r in relics_list if r["name"] != name]

    # Add new entry
    relics_list.append(
        {
            "name": name,
            "epoch": world.epoch,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    with metadata_path.open("w") as f:
        json.dump(relics_list, f, indent=2)


def load_relic(
    world: "World",
    name: str,
    relics_dir: str | Path,
    component_registry: Optional[Dict[str, Type[Component]]] = None,
) -> None:
    """Load a named relic into the world.

    Args:
        world: The World to load into.
        name: The relic name.
        relics_dir: Directory containing relics.
        component_registry: Optional mapping of component names to types.

    Raises:
        FileNotFoundError: If the relic doesn't exist.
    """
    relics_dir = Path(relics_dir)
    relic_path = relics_dir / f"{name}.json"

    if not relic_path.exists():
        raise FileNotFoundError(f"Relic '{name}' not found")

    load(world, relic_path, component_registry)


def list_relics(relics_dir: str | Path) -> List[RelicInfo]:
    """List all available relics.

    Args:
        relics_dir: Directory containing relics.

    Returns:
        List of RelicInfo objects.
    """
    relics_dir = Path(relics_dir)
    metadata_path = relics_dir / "_relics.json"

    if not metadata_path.exists():
        return []

    with metadata_path.open("r") as f:
        relics_list = json.load(f)

    return [
        RelicInfo(
            name=r["name"],
            epoch=r["epoch"],
            created_at=r["created_at"],
        )
        for r in relics_list
    ]
