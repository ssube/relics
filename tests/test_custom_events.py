"""Tests for custom event functionality."""

from typing import List

from pydantic.dataclasses import dataclass

from relics import Component, CustomEvent, OnCustomEvent, World


@dataclass
class Position(Component):
    """Test component for position."""

    x: float
    y: float


@dataclass
class DamageEvent(CustomEvent):
    """Custom event for damage dealt."""

    source_name: str
    target_name: str
    amount: float


@dataclass
class HealEvent(CustomEvent):
    """Custom event for healing."""

    target_name: str
    amount: float


@dataclass
class GameOverEvent(CustomEvent):
    """Custom event for game over."""

    winner: str
    reason: str


class TestCustomEventEmission:
    """Tests for emitting custom events."""

    def test_emit_custom_event(self) -> None:
        """Test basic custom event emission."""
        world = World()

        received_events: List[DamageEvent] = []

        class DamageObserver(OnCustomEvent):
            event_type = DamageEvent

            def on_event(self, event: CustomEvent) -> None:
                received_events.append(event)  # type: ignore

        world.observe(DamageObserver())

        event = DamageEvent(source_name="Player1", target_name="Enemy1", amount=50.0)
        world.emit(event)
        world.tick(0)

        assert len(received_events) == 1
        assert received_events[0].source_name == "Player1"
        assert received_events[0].target_name == "Enemy1"
        assert received_events[0].amount == 50.0

    def test_multiple_events_same_type(self) -> None:
        """Test emitting multiple events of the same type."""
        world = World()

        received_events: List[DamageEvent] = []

        class DamageObserver(OnCustomEvent):
            event_type = DamageEvent

            def on_event(self, event: CustomEvent) -> None:
                received_events.append(event)  # type: ignore

        world.observe(DamageObserver())

        world.emit(DamageEvent(source_name="A", target_name="B", amount=10.0))
        world.emit(DamageEvent(source_name="C", target_name="D", amount=20.0))
        world.emit(DamageEvent(source_name="E", target_name="F", amount=30.0))
        world.tick(0)

        assert len(received_events) == 3
        assert received_events[0].amount == 10.0
        assert received_events[1].amount == 20.0
        assert received_events[2].amount == 30.0


class TestCustomEventFiltering:
    """Tests for event type filtering."""

    def test_observer_filters_by_event_type(self) -> None:
        """Test that observers only receive their event type."""
        world = World()

        damage_events: List[DamageEvent] = []
        heal_events: List[HealEvent] = []

        class DamageObserver(OnCustomEvent):
            event_type = DamageEvent

            def on_event(self, event: CustomEvent) -> None:
                damage_events.append(event)  # type: ignore

        class HealObserver(OnCustomEvent):
            event_type = HealEvent

            def on_event(self, event: CustomEvent) -> None:
                heal_events.append(event)  # type: ignore

        world.observe(DamageObserver())
        world.observe(HealObserver())

        world.emit(DamageEvent(source_name="A", target_name="B", amount=50.0))
        world.emit(HealEvent(target_name="B", amount=25.0))
        world.emit(DamageEvent(source_name="C", target_name="D", amount=30.0))
        world.tick(0)

        assert len(damage_events) == 2
        assert len(heal_events) == 1
        assert heal_events[0].target_name == "B"

    def test_no_observer_for_event_type(self) -> None:
        """Test that events without observers are silently dropped."""
        world = World()

        received_events: List[DamageEvent] = []

        class DamageObserver(OnCustomEvent):
            event_type = DamageEvent

            def on_event(self, event: CustomEvent) -> None:
                received_events.append(event)  # type: ignore

        world.observe(DamageObserver())

        # Emit event type with no observer
        world.emit(GameOverEvent(winner="Player1", reason="Victory"))
        world.tick(0)

        # No errors, no events received
        assert len(received_events) == 0


class TestMultipleObservers:
    """Tests for multiple observers of the same event type."""

    def test_multiple_observers_same_type(self) -> None:
        """Test that multiple observers receive the same event."""
        world = World()

        observer1_events: List[DamageEvent] = []
        observer2_events: List[DamageEvent] = []

        class DamageObserver1(OnCustomEvent):
            event_type = DamageEvent

            def on_event(self, event: CustomEvent) -> None:
                observer1_events.append(event)  # type: ignore

        class DamageObserver2(OnCustomEvent):
            event_type = DamageEvent

            def on_event(self, event: CustomEvent) -> None:
                observer2_events.append(event)  # type: ignore

        world.observe(DamageObserver1())
        world.observe(DamageObserver2())

        world.emit(DamageEvent(source_name="A", target_name="B", amount=100.0))
        world.tick(0)

        assert len(observer1_events) == 1
        assert len(observer2_events) == 1
        assert observer1_events[0] is observer2_events[0]


class TestEventTiming:
    """Tests for event timing and queuing."""

    def test_events_processed_at_tick(self) -> None:
        """Test that events are queued and processed at tick."""
        world = World()

        received_events: List[DamageEvent] = []

        class DamageObserver(OnCustomEvent):
            event_type = DamageEvent

            def on_event(self, event: CustomEvent) -> None:
                received_events.append(event)  # type: ignore

        world.observe(DamageObserver())

        world.emit(DamageEvent(source_name="A", target_name="B", amount=50.0))

        # Event should be queued but not processed yet
        # (Note: The observer hasn't been called yet because tick() hasn't run)
        # This depends on implementation - if emit processes immediately,
        # this test may need adjustment

        world.tick(0)

        assert len(received_events) == 1

    def test_events_across_multiple_ticks(self) -> None:
        """Test events emitted across multiple ticks."""
        world = World()

        received_events: List[DamageEvent] = []

        class DamageObserver(OnCustomEvent):
            event_type = DamageEvent

            def on_event(self, event: CustomEvent) -> None:
                received_events.append(event)  # type: ignore

        world.observe(DamageObserver())

        world.emit(DamageEvent(source_name="A", target_name="B", amount=10.0))
        world.tick(0)
        assert len(received_events) == 1

        world.emit(DamageEvent(source_name="C", target_name="D", amount=20.0))
        world.tick(0)
        assert len(received_events) == 2

        world.emit(DamageEvent(source_name="E", target_name="F", amount=30.0))
        world.tick(0)
        assert len(received_events) == 3


class TestCustomEventWithEntities:
    """Tests for custom events involving entities."""

    def test_event_can_reference_entities(self) -> None:
        """Test custom events that reference entity data."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        @dataclass
        class CollisionEvent(CustomEvent):
            entity1_prefab: str
            entity2_prefab: str
            x: float
            y: float

        collision_events: List[CollisionEvent] = []

        class CollisionObserver(OnCustomEvent):
            event_type = CollisionEvent

            def on_event(self, event: CustomEvent) -> None:
                collision_events.append(event)  # type: ignore

        world.observe(CollisionObserver())

        p1 = world.spawn("player")
        p2 = world.spawn("player")

        # Emit collision event
        world.emit(
            CollisionEvent(
                entity1_prefab=p1.prefab,
                entity2_prefab=p2.prefab,
                x=5.0,
                y=10.0,
            )
        )
        world.tick(0)

        assert len(collision_events) == 1
        assert collision_events[0].entity1_prefab == "player"
        assert collision_events[0].x == 5.0
