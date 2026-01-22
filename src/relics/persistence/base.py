"""Base classes for persistence drivers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Type

from relics.types import Component, Edge

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


class PersistenceDriver(ABC):
    """Abstract base class for persistence drivers.

    Persistence drivers handle saving and loading world state to/from
    various storage backends (JSON files, SQLite databases, etc.).
    """

    @abstractmethod
    def save(
        self,
        world: "World",
        path: str | Path,
        relic_name: Optional[str] = None,
    ) -> None:
        """Save world state to the specified path.

        Args:
            world: The World to save.
            path: Path to write the data.
            relic_name: Optional name for this relic snapshot.
        """
        ...

    @abstractmethod
    def load(
        self,
        world: "World",
        path: str | Path,
        component_registry: Optional[Dict[str, Type[Component]]] = None,
        edge_registry: Optional[Dict[str, Type[Edge]]] = None,
    ) -> None:
        """Load world state from the specified path.

        Args:
            world: The World to load into (will be cleared first).
            path: Path to the data file.
            component_registry: Optional mapping of component names to types.
                If not provided, uses the world's registered component types.
            edge_registry: Optional mapping of edge names to types.
                If not provided, uses the world's registered edge types.

        Raises:
            FileNotFoundError: If the file doesn't exist.
        """
        ...

    @abstractmethod
    def save_relic(
        self,
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
        ...

    @abstractmethod
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
        ...

    @abstractmethod
    def list_relics(self, relics_dir: str | Path) -> List[RelicInfo]:
        """List all available relics.

        Args:
            relics_dir: Directory containing relics.

        Returns:
            List of RelicInfo objects.
        """
        ...
