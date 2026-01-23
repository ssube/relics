"""Tests for WebSocket exceptions."""

import pytest

from relics.addons.websocket import (
    AuthorizationError,
    ConnectionError,
    HandshakeError,
    ProtocolError,
    ReconnectionError,
    SyncError,
    WebSocketError,
)


class TestWebSocketError:
    """Tests for WebSocketError base class."""

    def test_websocket_error_is_exception(self) -> None:
        """Test that WebSocketError is an Exception."""
        assert issubclass(WebSocketError, Exception)

    def test_websocket_error_with_message(self) -> None:
        """Test WebSocketError with message."""
        error = WebSocketError("Test error message")
        assert str(error) == "Test error message"

    def test_websocket_error_can_be_raised(self) -> None:
        """Test that WebSocketError can be raised and caught."""
        with pytest.raises(WebSocketError):
            raise WebSocketError("Test error")


class TestConnectionError:
    """Tests for ConnectionError class."""

    def test_connection_error_is_websocket_error(self) -> None:
        """Test that ConnectionError is a WebSocketError."""
        assert issubclass(ConnectionError, WebSocketError)

    def test_connection_error_with_message(self) -> None:
        """Test ConnectionError with message."""
        error = ConnectionError("Failed to connect")
        assert str(error) == "Failed to connect"

    def test_connection_error_can_be_caught_as_websocket_error(self) -> None:
        """Test that ConnectionError can be caught as WebSocketError."""
        with pytest.raises(WebSocketError):
            raise ConnectionError("Connection failed")


class TestHandshakeError:
    """Tests for HandshakeError class."""

    def test_handshake_error_is_websocket_error(self) -> None:
        """Test that HandshakeError is a WebSocketError."""
        assert issubclass(HandshakeError, WebSocketError)

    def test_handshake_error_with_message(self) -> None:
        """Test HandshakeError with message."""
        error = HandshakeError("Handshake failed")
        assert str(error) == "Handshake failed"


class TestAuthorizationError:
    """Tests for AuthorizationError class."""

    def test_authorization_error_is_websocket_error(self) -> None:
        """Test that AuthorizationError is a WebSocketError."""
        assert issubclass(AuthorizationError, WebSocketError)

    def test_authorization_error_with_message(self) -> None:
        """Test AuthorizationError with message."""
        error = AuthorizationError("Not authorized")
        assert str(error) == "Not authorized"


class TestProtocolError:
    """Tests for ProtocolError class."""

    def test_protocol_error_is_websocket_error(self) -> None:
        """Test that ProtocolError is a WebSocketError."""
        assert issubclass(ProtocolError, WebSocketError)

    def test_protocol_error_with_message(self) -> None:
        """Test ProtocolError with message."""
        error = ProtocolError("Invalid message format")
        assert str(error) == "Invalid message format"


class TestSyncError:
    """Tests for SyncError class."""

    def test_sync_error_is_websocket_error(self) -> None:
        """Test that SyncError is a WebSocketError."""
        assert issubclass(SyncError, WebSocketError)

    def test_sync_error_with_message(self) -> None:
        """Test SyncError with message."""
        error = SyncError("Sync failed")
        assert str(error) == "Sync failed"


class TestReconnectionError:
    """Tests for ReconnectionError class."""

    def test_reconnection_error_is_websocket_error(self) -> None:
        """Test that ReconnectionError is a WebSocketError."""
        assert issubclass(ReconnectionError, WebSocketError)

    def test_reconnection_error_with_message(self) -> None:
        """Test ReconnectionError with message."""
        error = ReconnectionError("Reconnection failed after 5 attempts")
        assert str(error) == "Reconnection failed after 5 attempts"


class TestExceptionHierarchy:
    """Tests for exception hierarchy."""

    def test_all_errors_inherit_from_websocket_error(self) -> None:
        """Test that all custom errors inherit from WebSocketError."""
        error_classes = [
            ConnectionError,
            HandshakeError,
            AuthorizationError,
            ProtocolError,
            SyncError,
            ReconnectionError,
        ]
        for error_class in error_classes:
            assert issubclass(error_class, WebSocketError)

    def test_errors_are_distinct_types(self) -> None:
        """Test that error types are distinct."""
        error_classes = [
            ConnectionError,
            HandshakeError,
            AuthorizationError,
            ProtocolError,
            SyncError,
            ReconnectionError,
        ]
        # Check that they can be caught individually
        for error_class in error_classes:
            error = error_class("test")
            assert type(error) is error_class

    def test_specific_catch_pattern(self) -> None:
        """Test catching specific exception vs base."""
        # Specific catch should work
        try:
            raise ConnectionError("specific")
        except ConnectionError as e:
            assert str(e) == "specific"

        # Generic catch should also work
        try:
            raise ConnectionError("generic")
        except WebSocketError as e:
            assert str(e) == "generic"
