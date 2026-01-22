"""Persistence module for saving and loading world state.

This module provides:
- Abstract PersistenceDriver interface for implementing storage backends
- JSONPersistenceDriver for JSON file storage
- SQLitePersistenceDriver for SQLite database storage
- Backwards-compatible module functions that use the JSON driver

Example usage:

    # Old usage (backwards compatible)
    from relics import save, load, save_relic, load_relic, list_relics
    save(world, "world.json")

    # New driver-based usage
    from relics.persistence import JSONPersistenceDriver, SQLitePersistenceDriver

    json_driver = JSONPersistenceDriver()
    json_driver.save(world, "world.json")

    sqlite_driver = SQLitePersistenceDriver()
    sqlite_driver.save(world, "world.db")
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Type

from relics.persistence.base import PersistenceDriver, RelicInfo
from relics.persistence.drivers.json import JSONPersistenceDriver
from relics.persistence.drivers.sqlite import SQLitePersistenceDriver
from relics.persistence.serialization import _component_to_dict, _dict_to_component
from relics.types import Component, Edge

if TYPE_CHECKING:
    from relics.world import World

# Default driver instance for backwards compatibility
_default_driver = JSONPersistenceDriver()


# Backwards-compatible module functions
def save(
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
    _default_driver.save(world, path, relic_name)


def load(
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
    _default_driver.load(world, path, component_registry, edge_registry)


def save_relic(
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
    _default_driver.save_relic(world, name, relics_dir, overwrite)


def load_relic(
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
    _default_driver.load_relic(world, name, relics_dir, component_registry, edge_registry)


def list_relics(relics_dir: str | Path) -> List[RelicInfo]:
    """List all available relics.

    Scans the directory for JSON files and reads metadata from each.
    Each relic file is self-contained with its name in the metadata.

    Args:
        relics_dir: Directory containing relics.

    Returns:
        List of RelicInfo objects.
    """
    return _default_driver.list_relics(relics_dir)


__all__ = [
    # Base classes
    "PersistenceDriver",
    "RelicInfo",
    # Drivers
    "JSONPersistenceDriver",
    "SQLitePersistenceDriver",
    # Serialization helpers (for internal use)
    "_component_to_dict",
    "_dict_to_component",
    # Backwards-compatible functions
    "save",
    "load",
    "save_relic",
    "load_relic",
    "list_relics",
]
