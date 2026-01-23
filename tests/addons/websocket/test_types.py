"""Tests for WebSocket type definitions."""

from unittest.mock import MagicMock

from relics.addons.websocket import ClientConnection, ConnectionState
from relics.types import EntityId


class TestConnectionState:
    """Tests for ConnectionState enum."""

    def test_all_states_exist(self) -> None:
        """Test that all expected connection states exist."""
        expected_states = [
            "DISCONNECTED",
            "CONNECTING",
            "CONNECTED",
            "SYNCING",
            "READY",
            "RECONNECTING",
            "CLOSING",
        ]
        for name in expected_states:
            assert hasattr(ConnectionState, name)

    def test_states_are_unique(self) -> None:
        """Test that state values are unique."""
        values = [s.value for s in ConnectionState]
        assert len(values) == len(set(values))

    def test_initial_state_is_disconnected(self) -> None:
        """Test common initial state pattern."""
        # Most common initial state should be DISCONNECTED
        assert ConnectionState.DISCONNECTED.value == 1


class TestClientConnection:
    """Tests for ClientConnection dataclass."""

    def test_client_connection_creation(self) -> None:
        """Test basic ClientConnection creation."""
        websocket = MagicMock()
        conn = ClientConnection(
            client_id="test_client",
            websocket=websocket,
        )
        assert conn.client_id == "test_client"
        assert conn.websocket == websocket
        assert conn.component_whitelist == set()
        assert conn.entity_id is None
        assert conn.subscribed_regions == set()
        assert conn.sequence == 0

    def test_client_connection_with_whitelist(self) -> None:
        """Test ClientConnection with component whitelist."""
        websocket = MagicMock()
        conn = ClientConnection(
            client_id="test_client",
            websocket=websocket,
            component_whitelist={"Position", "InputState"},
        )
        assert "Position" in conn.component_whitelist
        assert "InputState" in conn.component_whitelist

    def test_client_connection_with_entity_id(self) -> None:
        """Test ClientConnection with entity ID."""
        websocket = MagicMock()
        entity_id = EntityId(prefab="player", sequence=1)
        conn = ClientConnection(
            client_id="test_client",
            websocket=websocket,
            entity_id=entity_id,
        )
        assert conn.entity_id == entity_id

    def test_client_connection_with_regions(self) -> None:
        """Test ClientConnection with subscribed regions."""
        websocket = MagicMock()
        conn = ClientConnection(
            client_id="test_client",
            websocket=websocket,
            subscribed_regions={"region_1", "region_2"},
        )
        assert "region_1" in conn.subscribed_regions
        assert "region_2" in conn.subscribed_regions

    def test_client_connection_sequence_tracking(self) -> None:
        """Test ClientConnection sequence number."""
        websocket = MagicMock()
        conn = ClientConnection(
            client_id="test_client",
            websocket=websocket,
            sequence=42,
        )
        assert conn.sequence == 42

    def test_client_connection_multiple_instances_independent(self) -> None:
        """Test that multiple ClientConnection instances are independent."""
        websocket1 = MagicMock()
        websocket2 = MagicMock()

        conn1 = ClientConnection(
            client_id="client_1",
            websocket=websocket1,
            component_whitelist={"Position"},
        )
        conn2 = ClientConnection(
            client_id="client_2",
            websocket=websocket2,
            component_whitelist={"Velocity"},
        )

        # Verify independence
        assert conn1.client_id != conn2.client_id
        assert conn1.component_whitelist != conn2.component_whitelist

        # Modify one should not affect other
        conn1.component_whitelist.add("Health")
        assert "Health" not in conn2.component_whitelist
