"""System base class and execution frequency configuration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import TYPE_CHECKING, Callable, ClassVar, Dict, List, Tuple, Type

from relics.entity import Entity
from relics.types import Component

if TYPE_CHECKING:
    from relics.query import QueryBuilder
    from relics.world import World


class RunOrder(Enum):
    """Specifies ordering relationship between systems."""

    BEFORE = auto()
    AFTER = auto()


class Frequency:
    """Execution frequency configuration for systems.

    Controls how often a system runs relative to ticks.
    """

    EVERY_TICK: ClassVar["Frequency"]

    def __init__(
        self,
        every_tick: bool = True,
        tick_interval: int = 1,
        time_interval: float = 0.0,
    ) -> None:
        """Create a frequency configuration.

        Args:
            every_tick: If True, run every tick.
            tick_interval: Run every N ticks (if every_tick is False).
            time_interval: Run at fixed time intervals in seconds.
        """
        self._every_tick = every_tick
        self._tick_interval = tick_interval
        self._time_interval = time_interval
        self._accumulated_time: float = 0.0
        self._last_tick: int = 0

    @classmethod
    def every_n_ticks(cls, n: int) -> "Frequency":
        """Create a frequency that runs every N ticks.

        Args:
            n: Number of ticks between executions.

        Returns:
            A Frequency instance.
        """
        return cls(every_tick=False, tick_interval=n)

    @classmethod
    def fixed_interval(cls, seconds: float) -> "Frequency":
        """Create a frequency that runs at fixed time intervals.

        Args:
            seconds: Time in seconds between executions.

        Returns:
            A Frequency instance.
        """
        return cls(every_tick=False, time_interval=seconds)

    def should_run(self, epoch: int, delta: float) -> bool:
        """Check if the system should run this tick.

        Args:
            epoch: Current epoch number.
            delta: Time elapsed since last tick.

        Returns:
            True if the system should run.
        """
        if self._every_tick:
            return True

        if self._time_interval > 0:
            self._accumulated_time += delta
            if self._accumulated_time >= self._time_interval:
                self._accumulated_time -= self._time_interval
                return True
            return False

        if self._tick_interval > 1:
            if epoch % self._tick_interval == 0:
                return True
            return False

        return True


# Singleton for EVERY_TICK frequency
Frequency.EVERY_TICK = Frequency(every_tick=True)  # type: ignore[misc]


class _WildcardSentinel:
    """Sentinel class for System.WILDCARD dependency."""

    pass


class System(ABC):
    """Base class for all systems.

    Systems contain game logic and process entities based on queries.
    They form a directed acyclic graph (DAG) based on dependencies.

    Subclasses must implement:
    - query(): Returns the QueryBuilder for entities to process
    - process(): Implements the system logic

    Optional overrides:
    - deps(): Declare execution order dependencies
    - frequency(): Control execution frequency
    """

    WILDCARD: ClassVar[Type["System"]] = _WildcardSentinel  # type: ignore[assignment]

    def __init__(self) -> None:
        """Initialize the system."""
        self._world: "World" | None = None
        self._frequency: Frequency | None = None

    @property
    def world(self) -> "World":
        """The World this system is registered with.

        Raises:
            RuntimeError: If the system is not registered with a world.
        """
        if self._world is None:
            raise RuntimeError("System is not registered with a world")
        return self._world

    @world.setter
    def world(self, value: "World") -> None:
        """Set the World this system is registered with."""
        self._world = value

    @property
    def q(self) -> "QueryBuilder":
        """Convenience accessor for a fresh query builder.

        Returns:
            A new QueryBuilder instance.
        """
        return self.world.query()

    @abstractmethod
    def query(self) -> "QueryBuilder":
        """Define which entities this system processes.

        Returns:
            A QueryBuilder that selects entities for this system.
        """
        pass

    def deps(self) -> Dict[RunOrder, List[Type["System"]]]:
        """Declare execution order dependencies.

        Override this method to specify that this system should run
        before or after other systems.

        Returns:
            Dictionary mapping RunOrder to list of system types.
        """
        return {}

    def frequency(self) -> Frequency:
        """Control execution frequency.

        Override this method to change how often the system runs.

        Returns:
            A Frequency instance.
        """
        return Frequency.EVERY_TICK

    def sub_systems(
        self,
    ) -> List[
        Tuple[
            "QueryBuilder",
            Callable[[List[Entity], List[List[Component]], float], None],
        ]
    ]:
        """Define sub-systems with separate queries.

        Override this method to define sub-systems that run after the main
        process() method. Each sub-system has its own query and process function.

        Returns:
            List of (QueryBuilder, process_function) tuples.
        """
        return []

    @abstractmethod
    def process(
        self,
        entities: List[Entity],
        components: List[List[Component]],
        delta: float,
    ) -> None:
        """Implement system logic.

        Args:
            entities: List of matching entities.
            components: List of component lists (from iterate()).
            delta: Time elapsed since last tick in seconds.
        """
        pass

    def _should_run(self, epoch: int, delta: float) -> bool:
        """Check if this system should run.

        Args:
            epoch: Current epoch number.
            delta: Time elapsed since last tick.

        Returns:
            True if the system should run.
        """
        if self._frequency is None:
            self._frequency = self.frequency()
        return self._frequency.should_run(epoch, delta)

    def _execute(self, delta: float) -> None:
        """Execute the system.

        Args:
            delta: Time elapsed since last tick.
        """
        query_builder = self.query()

        # Collect entities
        entities: List[Entity] = list(query_builder.execute_entities())

        # Collect components if iterate() was used
        components: List[List[Component]] = []
        if query_builder._iterate_types:
            # Group components by type
            for comp_type in query_builder._iterate_types:
                comp_list: List[Component] = []
                for entity in entities:
                    if entity.has_component(comp_type):
                        comp_list.append(entity.get_component(comp_type))
                components.append(comp_list)

        self.process(entities, components, delta)

        # Execute sub-systems
        for sub_query, sub_process in self.sub_systems():
            sub_entities: List[Entity] = list(sub_query.execute_entities())

            # Collect components if iterate() was used on sub-query
            sub_components: List[List[Component]] = []
            if sub_query._iterate_types:
                for comp_type in sub_query._iterate_types:
                    comp_list = []
                    for entity in sub_entities:
                        if entity.has_component(comp_type):
                            comp_list.append(entity.get_component(comp_type))
                    sub_components.append(comp_list)

            sub_process(sub_entities, sub_components, delta)
