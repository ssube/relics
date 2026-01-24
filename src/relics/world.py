"""World class - central manager for all entities, systems, and observers."""

from __future__ import annotations

import time
import uuid
from collections import deque
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple, Type, Union

from relics.entity import Entity
from relics.errors import (
    EntityNotFoundError,
    IndexNotFoundError,
    PrefabNotFoundError,
    RelationshipValidationError,
    SystemDependencyCycleError,
)
from relics.shared import copy_component
from relics.types import Component, CustomEvent, Edge, EntityId

if TYPE_CHECKING:
    from relics.index import IndexView
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

        # Observer event queue (deque for O(1) popleft)
        self._observer_queue: deque[tuple[Observer, tuple[Any, ...]]] = deque()

        # Component type registry (for persistence)
        self._component_types: Dict[str, Type[Component]] = {}

        # Relationship storage (dict-based for O(1) removal)
        # Outgoing: source_id -> {edge_type -> {target_id -> edge}}
        self._relationships: Dict[EntityId, Dict[Type[Edge], Dict[EntityId, Edge]]] = {}
        # Incoming index: target_id -> {edge_type -> {source_id -> edge}}
        self._incoming_relationships: Dict[
            EntityId, Dict[Type[Edge], Dict[EntityId, Edge]]
        ] = {}

        # Edge type registry (for persistence)
        self._edge_types: Dict[str, Type[Edge]] = {}

        # Component index: component_type -> set of entity_ids that have it
        # Enables O(1) lookup of entities by component type for query optimization
        self._component_index: Dict[Type[Component], Set[EntityId]] = {}

        # Secondary indexes
        self._indexes: Dict[str, "IndexView"] = {}

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
                # Deep copy all components by default for independence.
                # Use @shared_component to opt out of copying.
                components[comp_type] = copy_component(comp_instance)

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

        # Update component index for all components and bind monitored components
        for comp_type, comp_instance in components.items():
            if comp_type not in self._component_index:
                self._component_index[comp_type] = set()
            self._component_index[comp_type].add(entity_id)

            # Bind monitored components to this world for change tracking
            if hasattr(comp_instance, "_bind_to_world"):
                comp_instance._bind_to_world(self, entity_id)

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

        # Clean up outgoing relationships
        if entity_id in self._relationships:
            for edge_type, edges in list(self._relationships[entity_id].items()):
                for target_id in list(edges.keys()):
                    self._remove_relationship(entity_id, edge_type, target_id)
            del self._relationships[entity_id]

        # Clean up incoming relationships (where this entity is the target)
        if entity_id in self._incoming_relationships:
            for edge_type, incoming_edges in list(
                self._incoming_relationships[entity_id].items()
            ):
                for source_id in list(incoming_edges.keys()):
                    # Remove from source's outgoing relationships (O(1) dict delete)
                    if source_id in self._relationships:
                        if edge_type in self._relationships[source_id]:
                            self._relationships[source_id][edge_type].pop(
                                entity_id, None
                            )
            del self._incoming_relationships[entity_id]

        # Update component index (before removing from storage)
        for comp_type in self._entities[entity_id]:
            if comp_type in self._component_index:
                self._component_index[comp_type].discard(entity_id)

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

        # Bind monitored components to this world for change tracking
        if hasattr(component, "_bind_to_world"):
            component._bind_to_world(self, entity_id)

        # Update component index
        if component_type not in self._component_index:
            self._component_index[component_type] = set()
        self._component_index[component_type].add(entity_id)

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

        # Update component index
        if component_type in self._component_index:
            self._component_index[component_type].discard(entity_id)

        # Queue OnComponentRemoved observers
        entity = Entity(self, entity_id)
        self._queue_component_removed(entity, component)

    def _notify_component_changed(
        self,
        entity_id: EntityId,
        component: Component,
        field_name: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """Internal method to notify observers of component changes.

        Called by @monitored components when their values change.

        Args:
            entity_id: The entity's ID.
            component: The current (mutated) component instance.
            field_name: The name of the field that changed.
            old_value: The previous value of the field.
            new_value: The new value of the field.
        """
        entity = Entity(self, entity_id)
        self._queue_component_changed(
            entity, component, field_name, old_value, new_value
        )

    def register_edge_type(self, edge_type: Type[Edge]) -> None:
        """Register an edge type for persistence.

        Args:
            edge_type: The edge class to register.
        """
        self._edge_types[edge_type.__name__] = edge_type

    def _add_relationship(
        self, source_id: EntityId, edge: Edge, target_id: EntityId
    ) -> None:
        """Internal method to add a relationship between entities.

        Args:
            source_id: The source entity's ID.
            edge: The edge instance defining the relationship.
            target_id: The target entity's ID.

        Raises:
            EntityNotFoundError: If source or target doesn't exist.
            RelationshipValidationError: If edge validation fails.
        """
        # Validate entities exist
        if source_id not in self._entities:
            raise EntityNotFoundError(f"Source entity {source_id} not found")
        if target_id not in self._entities:
            raise EntityNotFoundError(f"Target entity {target_id} not found")

        # Validate the edge
        source = Entity(self, source_id)
        target = Entity(self, target_id)
        try:
            if not edge.validate(source, target):
                raise RelationshipValidationError(
                    f"Edge validation failed for {type(edge).__name__} "
                    f"from {source_id} to {target_id}"
                )
        except RelationshipValidationError:
            raise
        except Exception as e:
            raise RelationshipValidationError(
                f"Edge validation raised exception: {e}"
            ) from e

        edge_type = type(edge)
        self.register_edge_type(edge_type)

        # Initialize storage if needed
        if source_id not in self._relationships:
            self._relationships[source_id] = {}
        if edge_type not in self._relationships[source_id]:
            self._relationships[source_id][edge_type] = {}

        if target_id not in self._incoming_relationships:
            self._incoming_relationships[target_id] = {}
        if edge_type not in self._incoming_relationships[target_id]:
            self._incoming_relationships[target_id][edge_type] = {}

        # Add the relationship (O(1) dict assignment)
        self._relationships[source_id][edge_type][target_id] = edge
        self._incoming_relationships[target_id][edge_type][source_id] = edge

        # Queue observer
        self._queue_relationship_added(source, edge, target)

    def _remove_relationship(
        self, source_id: EntityId, edge_type: Type[Edge], target_id: EntityId
    ) -> None:
        """Internal method to remove a relationship between entities.

        Args:
            source_id: The source entity's ID.
            edge_type: The type of edge to remove.
            target_id: The target entity's ID.
        """
        # Find and remove the edge (O(1) dict operations)
        edge_to_remove: Optional[Edge] = None

        if source_id in self._relationships:
            if edge_type in self._relationships[source_id]:
                edges = self._relationships[source_id][edge_type]
                if target_id in edges:
                    edge_to_remove = edges[target_id]
                    del edges[target_id]

        if target_id in self._incoming_relationships:
            if edge_type in self._incoming_relationships[target_id]:
                incoming = self._incoming_relationships[target_id][edge_type]
                if source_id in incoming:
                    del incoming[source_id]

        # Queue observer if edge was found and entities still exist
        if edge_to_remove is not None:
            if source_id in self._entities and target_id in self._entities:
                source = Entity(self, source_id)
                target = Entity(self, target_id)
                self._queue_relationship_removed(source, edge_to_remove, target)

    def _get_relationships(
        self, entity_id: EntityId, edge_type: Type[Edge]
    ) -> List[Tuple[Edge, EntityId]]:
        """Internal method to get outgoing relationships.

        Args:
            entity_id: The source entity's ID.
            edge_type: The type of edge to get.

        Returns:
            List of (edge, target_id) tuples.
        """
        if entity_id not in self._relationships:
            return []
        if edge_type not in self._relationships[entity_id]:
            return []
        # Convert dict to list of tuples for API compatibility
        return [
            (edge, target_id)
            for target_id, edge in self._relationships[entity_id][edge_type].items()
        ]

    def _get_incoming_relationships(
        self, entity_id: EntityId, edge_type: Type[Edge]
    ) -> List[Tuple[EntityId, Edge]]:
        """Internal method to get incoming relationships.

        Args:
            entity_id: The target entity's ID.
            edge_type: The type of edge to get.

        Returns:
            List of (source_id, edge) tuples.
        """
        if entity_id not in self._incoming_relationships:
            return []
        if edge_type not in self._incoming_relationships[entity_id]:
            return []
        # Convert dict to list of tuples for API compatibility
        return [
            (source_id, edge)
            for source_id, edge in self._incoming_relationships[entity_id][
                edge_type
            ].items()
        ]

    def _has_relationship(
        self, entity_id: EntityId, edge_type: Type[Edge], target_id: Optional[EntityId]
    ) -> bool:
        """Check if entity has outgoing relationship of given type.

        Args:
            entity_id: The source entity's ID.
            edge_type: The type of edge to check.
            target_id: Optional specific target to check for.

        Returns:
            True if the relationship exists.
        """
        if entity_id not in self._relationships:
            return False
        if edge_type not in self._relationships[entity_id]:
            return False
        if target_id is None:
            return len(self._relationships[entity_id][edge_type]) > 0
        # O(1) dict lookup instead of linear search
        return target_id in self._relationships[entity_id][edge_type]

    def _has_incoming_relationship(
        self, entity_id: EntityId, edge_type: Type[Edge], source_id: Optional[EntityId]
    ) -> bool:
        """Check if entity has incoming relationship of given type.

        Args:
            entity_id: The target entity's ID.
            edge_type: The type of edge to check.
            source_id: Optional specific source to check for.

        Returns:
            True if the relationship exists.
        """
        if entity_id not in self._incoming_relationships:
            return False
        if edge_type not in self._incoming_relationships[entity_id]:
            return False
        if source_id is None:
            return len(self._incoming_relationships[entity_id][edge_type]) > 0
        # O(1) dict lookup instead of linear search
        return source_id in self._incoming_relationships[entity_id][edge_type]

    def emit(self, event: CustomEvent) -> None:
        """Emit a custom event.

        The event will be queued and delivered to matching OnCustomEvent
        observers at the end of the current tick.

        Args:
            event: The custom event to emit.
        """
        self._queue_custom_event(event)

    def query(self) -> "QueryBuilder":
        """Create a new query builder.

        Returns:
            A QueryBuilder instance for constructing queries.
        """
        from relics.query import QueryBuilder

        return QueryBuilder(self)

    def get_entities_with_component(
        self, component_type: Type[Component]
    ) -> Set[EntityId]:
        """Get all entity IDs that have a specific component type.

        This is an O(1) lookup using the component index.

        Args:
            component_type: The component type to search for.

        Returns:
            Set of entity IDs that have this component type.
            Returns empty set if no entities have this component.
        """
        return self._component_index.get(component_type, set())

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

    def tick(
        self,
        delta: float,
        *,
        include_groups: list[str] | None = None,
        exclude_groups: list[str] | None = None,
    ) -> None:
        """Advance epoch, run systems, process observer queue.

        Args:
            delta: Time elapsed since last tick in seconds.
            include_groups: If specified, only run systems in these groups.
            exclude_groups: If specified, skip systems in these groups.

        Note:
            Group filtering is applied in addition to the system's own
            paused state and frequency checks. If both include_groups and
            exclude_groups are specified, a system must be in include_groups
            AND not in exclude_groups to run.
        """
        self._epoch += 1

        # Ensure systems are sorted
        if not self._systems_sorted:
            self._resolve_system_order()

        # Convert to sets for O(1) lookup
        include_set = set(include_groups) if include_groups else None
        exclude_set = set(exclude_groups) if exclude_groups else None

        # Run systems in order
        for system in self._systems:
            # Check group filtering
            if include_set is not None and system.group not in include_set:
                continue
            if exclude_set is not None and system.group in exclude_set:
                continue

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
        from relics.observer import EntityObserver, OnEntityCreated

        for observer in self._observers:
            if isinstance(observer, OnEntityCreated):
                if observer.prefab is None or observer.prefab == entity.prefab:
                    self._observer_queue.append(
                        (observer, ("on_entity_created", entity))
                    )
            elif isinstance(observer, EntityObserver):
                if observer.prefab is None or observer.prefab == entity.prefab:
                    self._observer_queue.append(
                        (observer, ("on_entity_created", entity))
                    )

    def _queue_entity_destroyed(self, entity: Entity) -> None:
        """Queue OnEntityDestroyed events for observers."""
        from relics.observer import EntityObserver, OnEntityDestroyed

        for observer in self._observers:
            if isinstance(observer, OnEntityDestroyed):
                if observer.prefab is None or observer.prefab == entity.prefab:
                    self._observer_queue.append(
                        (observer, ("on_entity_destroyed", entity))
                    )
            elif isinstance(observer, EntityObserver):
                if observer.prefab is None or observer.prefab == entity.prefab:
                    self._observer_queue.append(
                        (observer, ("on_entity_destroyed", entity))
                    )

    def _queue_component_added(self, entity: Entity, component: Component) -> None:
        """Queue OnComponentAdded events for observers."""
        from relics.observer import ComponentObserver, OnComponentAdded

        component_type = type(component)
        for observer in self._observers:
            if isinstance(observer, OnComponentAdded):
                if observer.component_type is component_type:
                    self._observer_queue.append(
                        (observer, ("on_component_added", entity, component))
                    )
            elif isinstance(observer, ComponentObserver):
                if observer.component_type is component_type:
                    self._observer_queue.append(
                        (observer, ("on_component_added", entity, component))
                    )

    def _queue_component_removed(self, entity: Entity, component: Component) -> None:
        """Queue OnComponentRemoved events for observers."""
        from relics.observer import ComponentObserver, OnComponentRemoved

        component_type = type(component)
        for observer in self._observers:
            if isinstance(observer, OnComponentRemoved):
                if observer.component_type is component_type:
                    self._observer_queue.append(
                        (observer, ("on_component_removed", entity, component))
                    )
            elif isinstance(observer, ComponentObserver):
                if observer.component_type is component_type:
                    self._observer_queue.append(
                        (observer, ("on_component_removed", entity, component))
                    )

    def _queue_component_changed(
        self,
        entity: Entity,
        component: Component,
        field_name: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """Queue OnComponentChanged events for observers."""
        from relics.observer import ComponentObserver, OnComponentChanged

        component_type = type(component)
        for observer in self._observers:
            if isinstance(observer, OnComponentChanged):
                if observer.component_type is component_type:
                    self._observer_queue.append(
                        (
                            observer,
                            (
                                "on_component_changed",
                                entity,
                                component,
                                field_name,
                                old_value,
                                new_value,
                            ),
                        )
                    )
            elif isinstance(observer, ComponentObserver):
                if observer.component_type is component_type:
                    self._observer_queue.append(
                        (
                            observer,
                            (
                                "on_component_changed",
                                entity,
                                component,
                                field_name,
                                old_value,
                                new_value,
                            ),
                        )
                    )

    def _queue_relationship_added(
        self, source: Entity, edge: Edge, target: Entity
    ) -> None:
        """Queue OnRelationshipAdded events for observers."""
        from relics.observer import OnRelationshipAdded, RelationshipObserver

        edge_type = type(edge)
        for observer in self._observers:
            if isinstance(observer, OnRelationshipAdded):
                if observer.edge_type is edge_type:
                    self._observer_queue.append(
                        (observer, ("on_relationship_added", source, edge, target))
                    )
            elif isinstance(observer, RelationshipObserver):
                if observer.edge_type is edge_type:
                    self._observer_queue.append(
                        (observer, ("on_relationship_added", source, edge, target))
                    )

    def _queue_relationship_removed(
        self, source: Entity, edge: Edge, target: Entity
    ) -> None:
        """Queue OnRelationshipRemoved events for observers."""
        from relics.observer import OnRelationshipRemoved, RelationshipObserver

        edge_type = type(edge)
        for observer in self._observers:
            if isinstance(observer, OnRelationshipRemoved):
                if observer.edge_type is edge_type:
                    self._observer_queue.append(
                        (observer, ("on_relationship_removed", source, edge, target))
                    )
            elif isinstance(observer, RelationshipObserver):
                if observer.edge_type is edge_type:
                    self._observer_queue.append(
                        (observer, ("on_relationship_removed", source, edge, target))
                    )

    def _queue_custom_event(self, event: CustomEvent) -> None:
        """Queue OnCustomEvent events for observers."""
        from relics.observer import OnCustomEvent

        event_type = type(event)
        for observer in self._observers:
            if isinstance(observer, OnCustomEvent):
                if observer.event_type is event_type:
                    self._observer_queue.append((observer, ("on_event", event)))

    def _process_observer_queue(self) -> None:
        """Process all queued observer events."""
        while self._observer_queue:
            observer, args = self._observer_queue.popleft()
            method_name = args[0]
            method_args = args[1:]
            method = getattr(observer, method_name)
            method(*method_args)

    def create_index(
        self,
        name: str,
        query: "QueryBuilder",
        watches: Optional[List[Type[Component]]] = None,
        materialized: bool = False,
    ) -> "IndexView":
        """Create a secondary index for efficient querying.

        Args:
            name: Unique name for the index.
            query: The query that defines which entities are in the index.
            watches: Component types that trigger index updates (for materialized).
            materialized: If True, maintain cached set; if False, re-execute query.

        Returns:
            The created IndexView.
        """
        from relics.index import LazyIndex, MaterializedIndex

        if materialized:
            index: "IndexView" = MaterializedIndex(self, query, watches or [])
        else:
            index = LazyIndex(self, query)

        self._indexes[name] = index
        return index

    def index(self, name: str) -> "IndexView":
        """Get a secondary index by name.

        Args:
            name: The name of the index.

        Returns:
            The IndexView for the named index.

        Raises:
            IndexNotFoundError: If the index doesn't exist.
        """
        if name not in self._indexes:
            raise IndexNotFoundError(f"Index '{name}' not found")
        return self._indexes[name]

    def export_entity(self, entity_id: EntityId) -> Dict[str, Any]:
        """Export entity data in a structured format.

        Returns all components and relationships for an entity
        in a format suitable for tooling/debugging.

        Args:
            entity_id: The entity's ID.

        Returns:
            Dictionary with entity data:
            {
                "id": str(entity_id),
                "prefab": prefab_name,
                "components": {ComponentName: {field: value, ...}, ...},
                "relationships": {EdgeType: [target_ids, ...], ...},
                "incoming_relationships": {EdgeType: [source_ids, ...], ...}
            }

        Raises:
            EntityNotFoundError: If the entity doesn't exist.
        """
        if entity_id not in self._entities:
            raise EntityNotFoundError(f"Entity {entity_id} not found")

        from relics.persistence import _component_to_dict

        result: Dict[str, Any] = {
            "id": str(entity_id),
            "prefab": entity_id.prefab,
            "components": {},
            "relationships": {},
            "incoming_relationships": {},
        }

        # Export components
        for comp_type, comp in self._entities[entity_id].items():
            result["components"][comp_type.__name__] = _component_to_dict(comp)

        # Export outgoing relationships
        if entity_id in self._relationships:
            for edge_type, edges in self._relationships[entity_id].items():
                result["relationships"][edge_type.__name__] = [
                    {"edge": _component_to_dict(edge), "target": str(target_id)}
                    for target_id, edge in edges.items()
                ]

        # Export incoming relationships
        if entity_id in self._incoming_relationships:
            for edge_type, incoming in self._incoming_relationships[entity_id].items():
                result["incoming_relationships"][edge_type.__name__] = [
                    {"source": str(source_id), "edge": _component_to_dict(edge)}
                    for source_id, edge in incoming.items()
                ]

        return result
