"""Custom exceptions for WebSocket synchronization."""

from __future__ import annotations


class WebSocketError(Exception):
    """Base exception for WebSocket-related errors."""

    pass


class ConnectionError(WebSocketError):
    """Error establishing or maintaining connection."""

    pass


class HandshakeError(WebSocketError):
    """Error during WebSocket handshake."""

    pass


class AuthorizationError(WebSocketError):
    """Error when client attempts unauthorized action."""

    pass


class ProtocolError(WebSocketError):
    """Error in message protocol (malformed messages, etc.)."""

    pass


class SyncError(WebSocketError):
    """Error during synchronization."""

    pass


class ReconnectionError(WebSocketError):
    """Error during reconnection attempts."""

    pass
