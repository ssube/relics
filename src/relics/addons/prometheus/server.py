"""HTTP server for exposing Prometheus metrics endpoint."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Optional

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    generate_latest,
)

if TYPE_CHECKING:
    from http.server import HTTPServer

    from .collector import WorldMetricsCollector


class MetricsServer:
    """HTTP server for exposing Prometheus metrics.

    Provides an HTTP endpoint at /metrics for Prometheus to scrape.

    Example:
        >>> from relics import World
        >>> from relics.addons.prometheus import WorldMetricsCollector, MetricsServer
        >>>
        >>> world = World()
        >>> collector = WorldMetricsCollector(world, world_id="game_server")
        >>> server = MetricsServer(port=8000)
        >>> server.start()
        >>>
        >>> # Metrics available at http://localhost:8000/metrics
        >>>
        >>> # When done:
        >>> server.stop()

    Attributes:
        port: The port number the server listens on.
        addr: The address to bind to.
    """

    def __init__(
        self,
        port: int = 8000,
        addr: str = "0.0.0.0",
    ) -> None:
        """Create a metrics server.

        Args:
            port: Port number to listen on.
            addr: Address to bind to (default: all interfaces).
        """
        self._port = port
        self._addr = addr
        self._server: Optional["HTTPServer"] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def port(self) -> int:
        """The port the server is listening on."""
        return self._port

    @property
    def addr(self) -> str:
        """The address the server is bound to."""
        return self._addr

    @property
    def is_running(self) -> bool:
        """Whether the server is currently running."""
        return self._thread is not None and self._thread.is_alive()

    def start(self, daemon: bool = True) -> None:
        """Start the metrics server.

        Args:
            daemon: If True, server thread is a daemon thread and will
                    be terminated when the main program exits.
        """
        if self.is_running:
            return

        # Create server manually to control daemon status before starting
        from http.server import HTTPServer
        from prometheus_client import MetricsHandler

        self._server = HTTPServer((self._addr, self._port), MetricsHandler)

        self._thread = threading.Thread(target=self._server.serve_forever)
        self._thread.daemon = daemon
        self._thread.start()

    def stop(self) -> None:
        """Stop the metrics server."""
        if self._server is not None:
            self._server.shutdown()
            self._server = None
            self._thread = None

    def get_metrics_url(self) -> str:
        """Get the URL for the metrics endpoint.

        Returns:
            The full URL to access metrics.
        """
        host = "localhost" if self._addr == "0.0.0.0" else self._addr
        return f"http://{host}:{self._port}/metrics"


def get_metrics_text() -> str:
    """Get the current metrics in Prometheus text format.

    Returns:
        Prometheus metrics in text exposition format.

    Example:
        >>> metrics = get_metrics_text()
        >>> print(metrics)  # Print all metrics
    """
    return generate_latest(REGISTRY).decode("utf-8")


def get_content_type() -> str:
    """Get the content type for Prometheus metrics.

    Returns:
        The MIME type for Prometheus metrics.
    """
    return CONTENT_TYPE_LATEST
