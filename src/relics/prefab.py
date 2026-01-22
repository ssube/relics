"""Prefab loading and management utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Type

from relics.errors import PrefabNotFoundError
from relics.types import Component

if TYPE_CHECKING:
    from relics.world import World


def load_prefabs_from_json(
    world: "World",
    path: str | Path,
    component_registry: Dict[str, Type[Component]],
) -> None:
    """Load prefabs from a JSON file.

    The JSON file should have the format:
    {
        "prefab_name": {
            "components": {
                "ComponentName": {"field1": value1, ...}
            }
        },
        ...
    }

    Args:
        world: The World to register prefabs with.
        path: Path to the JSON file.
        component_registry: Dictionary mapping component names to types.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If a component type is not found in the registry.
    """
    path = Path(path)
    with path.open("r") as f:
        data = json.load(f)

    for prefab_name, prefab_data in data.items():
        components_data = prefab_data.get("components", {})
        components: Dict[Type[Component], Component] = {}

        for comp_name, comp_fields in components_data.items():
            if comp_name not in component_registry:
                raise ValueError(
                    f"Unknown component type '{comp_name}' in prefab '{prefab_name}'. "
                    f"Available types: {list(component_registry.keys())}"
                )

            comp_type = component_registry[comp_name]
            # Instantiate the component with the field values
            component = comp_type(**comp_fields)
            components[comp_type] = component

        world.register_prefab(prefab_name, components)


def prefab_to_dict(
    prefab_name: str,
    components: Dict[Type[Component], Component],
) -> Dict[str, Any]:
    """Convert a prefab to a dictionary for JSON serialization.

    Args:
        prefab_name: The name of the prefab.
        components: Dictionary mapping component types to instances.

    Returns:
        Dictionary representation of the prefab.
    """
    components_data: Dict[str, Dict[str, Any]] = {}

    for comp_type, comp_instance in components.items():
        # Extract field values from the component
        if hasattr(comp_instance, "__dataclass_fields__"):
            # Standard dataclass
            fields_dict = {
                name: getattr(comp_instance, name)
                for name in comp_instance.__dataclass_fields__
            }
        elif hasattr(comp_instance, "__pydantic_fields__"):
            # Pydantic model/dataclass
            fields_dict = {
                name: getattr(comp_instance, name)
                for name in comp_instance.__pydantic_fields__
            }
        elif hasattr(comp_instance, "model_fields"):
            # Pydantic v2 model
            fields_dict = {
                name: getattr(comp_instance, name)
                for name in comp_instance.model_fields
            }
        else:
            # Fall back to __dict__
            fields_dict = {
                k: v for k, v in comp_instance.__dict__.items() if not k.startswith("_")
            }

        components_data[comp_type.__name__] = fields_dict

    return {
        "components": components_data,
    }


def save_prefabs_to_json(
    world: "World",
    path: str | Path,
) -> None:
    """Save all registered prefabs to a JSON file.

    Args:
        world: The World containing prefabs.
        path: Path to write the JSON file.
    """
    path = Path(path)
    data: Dict[str, Dict[str, Any]] = {}

    for prefab_name, components in world._prefabs.items():
        data[prefab_name] = prefab_to_dict(prefab_name, components)

    with path.open("w") as f:
        json.dump(data, f, indent=2)


def get_prefab(world: "World", name: str) -> Dict[Type[Component], Component]:
    """Get a prefab's component definitions.

    Args:
        world: The World containing the prefab.
        name: The prefab name.

    Returns:
        Dictionary mapping component types to default instances.

    Raises:
        PrefabNotFoundError: If the prefab doesn't exist.
    """
    if name not in world._prefabs:
        raise PrefabNotFoundError(f"Prefab '{name}' not found")
    return world._prefabs[name]


def list_prefabs(world: "World") -> list[str]:
    """List all registered prefab names.

    Args:
        world: The World to query.

    Returns:
        List of prefab names.
    """
    return list(world._prefabs.keys())
