"""World class - central manager for all entities, systems, and observers."""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Any, Dict, Optional, Set, Type, Union

from relics.entity import Entity
from relics.errors import (
    EntityNotFoundError,
    PrefabNotFoundError,
    SystemDependencyCycleError,
)
from relics.types import Component, EntityId

if TYPE_CHECKING:
    from relics.observer import Observer
    from relics.query import QueryBuilder
    from relics.system import System


class SequenceGenerator:
    """Generates unique sequence numbers per prefab.

    Uses a hybrid timestamp + collision counter approach:
    - Base: milliseconds since epoch * 1000
    - If collision within same millisecond, increment counter
    """

    def __init__(self) -> None:
        """Initialize the sequence generator."""
        self._counters: Dict[str, int] = {}

    def next(self, prefab: str) -> int:
        """Generate the next sequence number for a prefab.

        Args:
            prefab: The prefab name.

        Returns:
            A unique sequence number for this prefab.
        """
        base = int(time.time() * 1000) * 1000
        last = self._counters.get(prefab, 0)
        if base <= last:
            base = last + 1
        self._counters[prefab] = base
        return base


class World:
    """Central manager for all entities, systems, and observers.

    A World is single-threaded - each instance should only be accessed
    from one thread. Multiple World instances can run in parallel threads.

    Attributes:
        id: Unique world identifier.
    """

    def __init__(self, world_id: Optional[str] = None) -> None:
        """Create a new World.

        Args:
            world_id: Optional unique identifier. Generated if not provided.
        """
        self.id: str = world_id or str(uuid.uuid4())
        self._epoch: int = 0

        # Entity storage: EntityId -> (Type[Component] -> Component)
        self._entities: Dict[EntityId, Dict[Type[Component], Component]] = {}

        # Prefab index for efficient prefab queries
        self._prefab_index: Dict[str, Set[EntityId]] = {}

        # Sequence generator for entity IDs
        self._sequence_generator = SequenceGenerator()

        # Prefab definitions: name -> (Type[Component] -> default_data)
        self._prefabs: Dict[str, Dict[Type[Component], Component]] = {}

        # Systems - order determined by DAG resolution
        self._systems: list[System] = []
        self._systems_sorted: bool = False

        # Observers
        self._observers: list[Observer] = []

        # Observer event queue
        self._observer_queue: list[tuple[Observer, tuple[Any, ...]]] = []

        # Component type registry (for persistence)
        self._component_types: Dict[str, Type[Component]] = {}

    @property
    def epoch(self) -> int:
        """Current epoch number."""
        return self._epoch

    def register_component_type(self, component_type: Type[Component]) -> None:
        """Register a component type for persistence.

        Args:
            component_type: The component class to register.
        """
        self._component_types[component_type.__name__] = component_type

    def register_prefab(
        self, name: str, components: Dict[Type[Component], Component]
    ) -> None:
        """Register a prefab programmatically.

        Args:
            name: The prefab name.
            components: Dictionary mapping component types to default instances.
        """
        self._prefabs[name] = components
        # Register component types
        for comp_type in components:
            self.register_component_type(comp_type)

    def spawn(
        self,
        prefab: str,
        overrides: Optional[Dict[Type[Component], Component]] = None,
    ) -> Entity:
        """Create an entity from a prefab with optional component overrides.

        Args:
            prefab: The prefab name to instantiate.
            overrides: Optional component overrides.

        Returns:
            A live Entity handle.

        Raises:
            PrefabNotFoundError: If the prefab doesn't exist.
        """
        if prefab not in self._prefabs:
            raise PrefabNotFoundError(f"Prefab '{prefab}' not found")

        # Generate entity ID
        sequence = self._sequence_generator.next(prefab)
        entity_id = EntityId(prefab=prefab, sequence=sequence)

        # Copy prefab components and apply overrides
        components: Dict[Type[Component], Component] = {}
        for comp_type, comp_instance in self._prefabs[prefab].items():
            if overrides and comp_type in overrides:
                components[comp_type] = overrides[comp_type]
            else:
                # Deep copy would be ideal but for now use same instance
                # This works because Pydantic dataclasses are immutable by default
                components[comp_type] = comp_instance

        # Apply any additional overrides not in prefab
        if overrides:
            for comp_type, comp_instance in overrides.items():
                if comp_type not in components:
                    components[comp_type] = comp_instance
                    self.register_component_type(comp_type)

        # Store entity
        self._entities[entity_id] = components

        # Update prefab index
        if prefab not in self._prefab_index:
            self._prefab_index[prefab] = set()
        self._prefab_index[prefab].add(entity_id)

        entity = Entity(self, entity_id)

        # Queue OnEntityCreated observers
        self._queue_entity_created(entity)

        return entity

    def get_entity(self, entity_id: EntityId) -> Entity:
        """Get a live handle to an entity.

        Args:
            entity_id: The entity's unique identifier.

        Returns:
            A live Entity handle.

        Raises:
            EntityNotFoundError: If the entity doesn't exist.
        """
        if entity_id not in self._entities:
            raise EntityNotFoundError(f"Entity {entity_id} not found")
        return Entity(self, entity_id)

    def has_entity(self, entity_id: EntityId) -> bool:
        """Check if an entity exists.

        Args:
            entity_id: The entity's unique identifier.

        Returns:
            True if the entity exists, False otherwise.
        """
        return entity_id in self._entities

    def remove(self, entity: Union[Entity, EntityId]) -> None:
        """Remove an entity from the world.

        Args:
            entity: The entity or entity ID to remove.

        Raises:
            EntityNotFoundError: If the entity doesn't exist.
        """
        entity_id = entity._id if isinstance(entity, Entity) else entity
        if entity_id not in self._entities:
            raise EntityNotFoundError(f"Entity {entity_id} not found")

        # Queue OnEntityDestroyed observers before removal
        entity_handle = (
            Entity(self, entity_id) if isinstance(entity, EntityId) else entity
        )
        self._queue_entity_destroyed(entity_handle)

        # Remove from storage
        del self._entities[entity_id]

        # Update prefab index
        prefab = entity_id.prefab
        if prefab in self._prefab_index:
            self._prefab_index[prefab].discard(entity_id)

    def _add_component(self, entity_id: EntityId, component: Component) -> None:
        """Internal method to add a component to an entity.

        Args:
            entity_id: The entity's ID.
            component: The component to add.
        """
        component_type = type(component)
        self._entities[entity_id][component_type] = component
        self.register_component_type(component_type)

        # Queue OnComponentAdded observers
        entity = Entity(self, entity_id)
        self._queue_component_added(entity, component)

    def _remove_component(
        self, entity_id: EntityId, component_type: Type[Component]
    ) -> None:
        """Internal method to remove a component from an entity.

        Args:
            entity_id: The entity's ID.
            component_type: The type of component to remove.
        """
        component = self._entities[entity_id][component_type]
        del self._entities[entity_id][component_type]

        # Queue OnComponentRemoved observers
        entity = Entity(self, entity_id)
        self._queue_component_removed(entity, component)

    def _notify_component_changed(
        self, entity_id: EntityId, old_value: Component, new_value: Component
    ) -> None:
        """Internal method to notify observers of component changes.

        Called by @monitored components when their values change.

        Args:
            entity_id: The entity's ID.
            old_value: The previous component value.
            new_value: The new component value.
        """
        entity = Entity(self, entity_id)
        self._queue_component_changed(entity, old_value, new_value)

    def query(self) -> "QueryBuilder":
        """Create a new query builder.

        Returns:
            A QueryBuilder instance for constructing queries.
        """
        from relics.query import QueryBuilder

        return QueryBuilder(self)

    def register_system(self, system: "System") -> None:
        """Register a system.

        Args:
            system: The system to register.

        Raises:
            SystemDependencyCycleError: If adding this system creates a cycle.
        """
        system.world = self
        self._systems.append(system)
        self._systems_sorted = False
        # Validate no cycle
        self._resolve_system_order()

    def observe(self, observer: "Observer") -> None:
        """Register an observer for events.

        Args:
            observer: The observer to register.
        """
        observer.world = self
        self._observers.append(observer)

    def tick(self, delta: float) -> None:
        """Advance epoch, run systems, process observer queue.

        Args:
            delta: Time elapsed since last tick in seconds.
        """
        self._epoch += 1

        # Ensure systems are sorted
        if not self._systems_sorted:
            self._resolve_system_order()

        # Run systems in order
        for system in self._systems:
            if system._should_run(self._epoch, delta):
                system._execute(delta)

        # Process observer queue
        self._process_observer_queue()

    def _resolve_system_order(self) -> None:
        """Resolve system execution order using topological sort.

        Raises:
            SystemDependencyCycleError: If dependencies form a cycle.
        """
        from relics.system import RunOrder, System

        if not self._systems:
            self._systems_sorted = True
            return

        # Build dependency graph
        # Node = system, Edge = dependency (A -> B means A runs before B)
        system_map = {type(s): s for s in self._systems}
        graph: Dict[Type[System], Set[Type[System]]] = {
            type(s): set() for s in self._systems
        }
        reverse_graph: Dict[Type[System], Set[Type[System]]] = {
            type(s): set() for s in self._systems
        }

        for system in self._systems:
            system_type = type(system)
            deps = system.deps()

            # Handle BEFORE dependencies: this system runs BEFORE others
            before_deps = deps.get(RunOrder.BEFORE, [])
            for dep_type in before_deps:
                if dep_type is System.WILDCARD:
                    # This system runs before all others
                    for other_type in graph:
                        if other_type != system_type:
                            graph[system_type].add(other_type)
                elif dep_type in system_map:
                    graph[system_type].add(dep_type)

            # Handle AFTER dependencies: this system runs AFTER others
            after_deps = deps.get(RunOrder.AFTER, [])
            for dep_type in after_deps:
                if dep_type is System.WILDCARD:
                    # This system runs after all others
                    for other_type in graph:
                        if other_type != system_type:
                            reverse_graph[system_type].add(other_type)
                elif dep_type in system_map:
                    reverse_graph[system_type].add(dep_type)

        # Merge reverse graph (B runs after A means A -> B)
        for system_type, after_set in reverse_graph.items():
            for after_type in after_set:
                graph[after_type].add(system_type)

        # Topological sort using Kahn's algorithm
        in_degree = {s: 0 for s in graph}
        for deps_set in graph.values():
            for dep in deps_set:
                if dep in in_degree:
                    in_degree[dep] += 1

        queue = [s for s, d in in_degree.items() if d == 0]
        sorted_types: list[Type[System]] = []

        while queue:
            current = queue.pop(0)
            sorted_types.append(current)

            for dep in graph[current]:
                if dep in in_degree:
                    in_degree[dep] -= 1
                    if in_degree[dep] == 0:
                        queue.append(dep)

        if len(sorted_types) != len(self._systems):
            raise SystemDependencyCycleError("System dependencies form a cycle")

        # Reorder systems
        self._systems = [system_map[t] for t in sorted_types]
        self._systems_sorted = True

    def _queue_entity_created(self, entity: Entity) -> None:
        """Queue OnEntityCreated events for observers."""
        from relics.observer import OnEntityCreated

        for observer in self._observers:
            if isinstance(observer, OnEntityCreated):
                if observer.prefab is None or observer.prefab == entity.prefab:
                    self._observer_queue.append(
                        (observer, ("on_entity_created", entity))
                    )

    def _queue_entity_destroyed(self, entity: Entity) -> None:
        """Queue OnEntityDestroyed events for observers."""
        from relics.observer import OnEntityDestroyed

        for observer in self._observers:
            if isinstance(observer, OnEntityDestroyed):
                if observer.prefab is None or observer.prefab == entity.prefab:
                    self._observer_queue.append(
                        (observer, ("on_entity_destroyed", entity))
                    )

    def _queue_component_added(self, entity: Entity, component: Component) -> None:
        """Queue OnComponentAdded events for observers."""
        from relics.observer import OnComponentAdded

        component_type = type(component)
        for observer in self._observers:
            if isinstance(observer, OnComponentAdded):
                if observer.component_type is component_type:
                    self._observer_queue.append(
                        (observer, ("on_component_added", entity, component))
                    )

    def _queue_component_removed(self, entity: Entity, component: Component) -> None:
        """Queue OnComponentRemoved events for observers."""
        from relics.observer import OnComponentRemoved

        component_type = type(component)
        for observer in self._observers:
            if isinstance(observer, OnComponentRemoved):
                if observer.component_type is component_type:
                    self._observer_queue.append(
                        (observer, ("on_component_removed", entity, component))
                    )

    def _queue_component_changed(
        self, entity: Entity, old_value: Component, new_value: Component
    ) -> None:
        """Queue OnComponentChanged events for observers."""
        from relics.observer import OnComponentChanged

        component_type = type(new_value)
        for observer in self._observers:
            if isinstance(observer, OnComponentChanged):
                if observer.component_type is component_type:
                    self._observer_queue.append(
                        (
                            observer,
                            ("on_component_changed", entity, old_value, new_value),
                        )
                    )

    def _process_observer_queue(self) -> None:
        """Process all queued observer events."""
        while self._observer_queue:
            observer, args = self._observer_queue.pop(0)
            method_name = args[0]
            method_args = args[1:]
            method = getattr(observer, method_name)
            method(*method_args)
