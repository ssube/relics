"""Registry for procedural prefabs."""

import json
import random
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union

from relics.types import Component
from relics.addons.procedural_prefabs.exceptions import (
    PrefabListNotFoundError,
    ProcPrefabNotFoundError,
)
from relics.addons.procedural_prefabs.prefab import (
    AddOperation,
    AttachmentDefinition,
    ComponentRegistry,
    ComponentVariant,
    ConditionalBlock,
    DeriveOperation,
    GraphDefinition,
    ParamDefinition,
    ProceduralPrefab,
    WhenClause,
)
from relics.addons.procedural_prefabs.spawner import PrefabSpawner

if TYPE_CHECKING:
    from relics.entity import Entity
    from relics.world import World


class ProceduralPrefabRegistry:
    """Registry for procedural prefabs.

    Manages registration, lookup, and spawning of procedural prefabs.
    Also handles JSON loading and component type registration.

    Example:
        >>> world = World()
        >>> registry = ProceduralPrefabRegistry(world, rng_seed=42)
        >>> registry.register_component_type("Health", Health)
        >>> registry.load("prefabs/character.procprefab.json")
        >>> entity = registry.spawn("character", {"race": "elf"})
    """

    def __init__(
        self,
        world: "World",
        component_registry: Optional[ComponentRegistry] = None,
        rng_seed: Optional[int] = None,
    ) -> None:
        """Initialize registry.

        Args:
            world: World to spawn entities in.
            component_registry: Optional pre-built component registry.
            rng_seed: Optional seed for deterministic spawning.
        """
        self._world = world
        self._component_registry: ComponentRegistry = component_registry or {}
        self._prefabs: Dict[str, ProceduralPrefab] = {}
        self._prefab_lists: Dict[str, List[str]] = {}

        # Initialize RNG
        self._rng = random.Random()
        if rng_seed is not None:
            self._rng.seed(rng_seed)

        # Spawner is created lazily
        self._spawner: Optional[PrefabSpawner] = None

    @property
    def spawner(self) -> PrefabSpawner:
        """Get or create the spawner instance."""
        if self._spawner is None:
            self._spawner = PrefabSpawner(
                registry=self._prefabs,
                prefab_lists=self._prefab_lists,
                world=self._world,
                component_registry=self._component_registry,
                rng=self._rng,
            )
        return self._spawner

    def register(self, prefab: ProceduralPrefab) -> None:
        """Register a procedural prefab.

        Args:
            prefab: Prefab to register.
        """
        self._prefabs[prefab.name] = prefab
        # Invalidate spawner to pick up new prefab
        self._spawner = None

    def get(self, name: str) -> ProceduralPrefab:
        """Get a prefab by name.

        Args:
            name: Prefab name.

        Returns:
            ProceduralPrefab instance.

        Raises:
            ProcPrefabNotFoundError: If prefab not found.
        """
        if name not in self._prefabs:
            raise ProcPrefabNotFoundError(name)
        return self._prefabs[name]

    def has(self, name: str) -> bool:
        """Check if a prefab exists.

        Args:
            name: Prefab name.

        Returns:
            True if prefab is registered.
        """
        return name in self._prefabs

    def list_prefabs(self) -> List[str]:
        """List all registered prefab names.

        Returns:
            List of prefab names.
        """
        return list(self._prefabs.keys())

    def register_list(self, name: str, prefab_names: List[str]) -> None:
        """Register a prefab list.

        Args:
            name: List name.
            prefab_names: List of prefab names.
        """
        self._prefab_lists[name] = list(prefab_names)
        # Invalidate spawner
        self._spawner = None

    def get_list(self, name: str) -> List[str]:
        """Get a prefab list by name.

        Args:
            name: List name.

        Returns:
            List of prefab names.

        Raises:
            PrefabListNotFoundError: If list not found.
        """
        if name not in self._prefab_lists:
            raise PrefabListNotFoundError(name)
        return list(self._prefab_lists[name])

    def has_list(self, name: str) -> bool:
        """Check if a prefab list exists.

        Args:
            name: List name.

        Returns:
            True if list is registered.
        """
        return name in self._prefab_lists

    def list_prefab_lists(self) -> List[str]:
        """List all registered prefab list names.

        Returns:
            List of prefab list names.
        """
        return list(self._prefab_lists.keys())

    def register_component_type(self, name: str, cls: Type[Component]) -> None:
        """Register a component type.

        Args:
            name: Name for the component type (used in prefab definitions).
            cls: Component class.
        """
        self._component_registry[name] = cls
        # Invalidate spawner
        self._spawner = None

    def spawn(
        self,
        prefab_name: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> "Entity":
        """Spawn an entity from a procedural prefab.

        Args:
            prefab_name: Name of the procedural prefab.
            params: Parameters to pass.

        Returns:
            Spawned entity.

        Raises:
            ProcPrefabNotFoundError: If prefab not found.
            ParamValidationError: If parameter validation fails.
        """
        return self.spawner.spawn(prefab_name, params)

    def load(self, path: Union[str, Path]) -> None:
        """Load a procedural prefab from JSON file.

        Args:
            path: Path to .procprefab.json file.

        Raises:
            FileNotFoundError: If file not found.
            json.JSONDecodeError: If JSON is invalid.
        """
        path = Path(path)
        with open(path, "r") as f:
            data = json.load(f)

        prefab = self._parse_prefab(data)
        self.register(prefab)

    def load_directory(self, directory: Union[str, Path]) -> int:
        """Load all procedural prefabs from a directory.

        Loads all files matching *.procprefab.json pattern.

        Args:
            directory: Directory path.

        Returns:
            Number of prefabs loaded.
        """
        directory = Path(directory)
        count = 0

        for path in directory.glob("*.procprefab.json"):
            self.load(path)
            count += 1

        return count

    def _parse_prefab(self, data: Dict[str, Any]) -> ProceduralPrefab:
        """Parse a prefab from JSON data.

        Args:
            data: JSON data dict.

        Returns:
            ProceduralPrefab instance.
        """
        # Parse params
        params = []
        for p in data.get("params", []):
            params.append(ParamDefinition(
                name=p["name"],
                param_type=p.get("type", "str"),
                required=p.get("required", False),
                default=p.get("default"),
                allowed_values=p.get("allowed_values"),
            ))

        # Parse graph
        graph = self._parse_graph(data.get("graph", {}))

        return ProceduralPrefab(
            name=data["name"],
            params=params,
            graph=graph,
            base_prefab=data.get("base_prefab"),
        )

    def _parse_graph(self, data: Dict[str, Any]) -> GraphDefinition:
        """Parse a graph definition from JSON data.

        Args:
            data: JSON data dict.

        Returns:
            GraphDefinition instance.
        """
        # Parse components
        components = []
        for c in data.get("components", []):
            when = None
            if "when" in c:
                when = WhenClause(conditions=c["when"])

            components.append(ComponentVariant(
                component_type=c["type"],
                fields=c.get("fields", {}),
                when=when,
            ))

        # Parse conditionals
        conditionals = None
        if "conditionals" in data:
            conditionals = []
            for cond in data["conditionals"]:
                when = WhenClause(conditions=cond["when"])

                add_ops = []
                for a in cond.get("add", []):
                    add_ops.append(AddOperation(
                        component_type=a["type"],
                        fields=a.get("fields", {}),
                    ))

                derive_ops = []
                for d in cond.get("derive", []):
                    derive_ops.append(DeriveOperation(
                        target=d["target"],
                        operation=d["operation"],
                        value=d["value"],
                    ))

                conditionals.append(ConditionalBlock(
                    when=when,
                    add=add_ops,
                    derive=derive_ops,
                ))

        # Parse attachments
        attachments = None
        if "attachments" in data:
            attachments = []
            for att in data["attachments"]:
                attachments.append(AttachmentDefinition(
                    prefab=att.get("prefab"),
                    from_list=att.get("from_list"),
                    edge_type=att.get("edge_type", "HasAttached"),
                    slot=att.get("slot", "default"),
                    inherit_params=att.get("inherit_params"),
                    override_params=att.get("override_params"),
                    optional=att.get("optional", False),
                    skip=att.get("skip", False),
                ))

        # Parse lists
        lists = data.get("lists")

        return GraphDefinition(
            components=components,
            conditionals=conditionals,
            attachments=attachments,
            lists=lists,
        )

    def set_seed(self, seed: int) -> None:
        """Set the RNG seed for deterministic spawning.

        Args:
            seed: Random seed value.
        """
        self._rng.seed(seed)
        # Invalidate spawner to use new seed
        self._spawner = None
