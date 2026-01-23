"""Tests for Prometheus metrics server."""

import time

from pydantic.dataclasses import dataclass

from relics import Component, World
from relics.addons.prometheus import (
    MetricsServer,
    WorldMetricsCollector,
    get_content_type,
    get_metrics_text,
)


@dataclass
class Position(Component):
    """Test component for position."""

    x: float
    y: float


class TestMetricsServer:
    """Tests for MetricsServer class."""

    def test_server_creation(self) -> None:
        """Test basic server creation."""
        server = MetricsServer(port=9100)

        assert server.port == 9100
        assert server.addr == "0.0.0.0"
        assert server.is_running is False

    def test_server_custom_addr(self) -> None:
        """Test server with custom address."""
        server = MetricsServer(port=9101, addr="127.0.0.1")

        assert server.addr == "127.0.0.1"

    def test_server_start_stop(self) -> None:
        """Test starting and stopping the server."""
        server = MetricsServer(port=9102)

        server.start()
        time.sleep(0.1)  # Give server time to start

        assert server.is_running is True

        server.stop()
        time.sleep(0.1)  # Give server time to stop

        assert server.is_running is False

    def test_server_start_idempotent(self) -> None:
        """Test that start is idempotent."""
        server = MetricsServer(port=9103)

        server.start()
        server.start()  # Should not raise

        assert server.is_running is True

        server.stop()

    def test_server_stop_idempotent(self) -> None:
        """Test that stop is idempotent."""
        server = MetricsServer(port=9104)

        server.start()
        server.stop()
        server.stop()  # Should not raise

        assert server.is_running is False

    def test_get_metrics_url(self) -> None:
        """Test getting the metrics URL."""
        server = MetricsServer(port=9105)

        url = server.get_metrics_url()
        assert url == "http://localhost:9105/metrics"

    def test_get_metrics_url_custom_addr(self) -> None:
        """Test getting the metrics URL with custom address."""
        server = MetricsServer(port=9106, addr="192.168.1.1")

        url = server.get_metrics_url()
        assert url == "http://192.168.1.1:9106/metrics"


class TestMetricsHelpers:
    """Tests for metrics helper functions."""

    def test_get_metrics_text(self) -> None:
        """Test getting metrics in text format."""
        # Create a world and collector to populate some metrics
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        collector = WorldMetricsCollector(world, world_id="test_text")

        world.spawn("player")
        world.tick(0)
        collector.collect()

        metrics = get_metrics_text()

        # Should be a string
        assert isinstance(metrics, str)

        # Should contain our metrics
        assert "relics_entities_total" in metrics

    def test_get_content_type(self) -> None:
        """Test getting the content type."""
        content_type = get_content_type()

        assert isinstance(content_type, str)
        assert "text/plain" in content_type or "text/openmetrics" in content_type


class TestMetricsServerIntegration:
    """Integration tests for metrics server."""

    def test_server_serves_metrics(self) -> None:
        """Test that server serves metrics via HTTP."""
        import urllib.request

        # Create world and collector
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        collector = WorldMetricsCollector(world, world_id="test_http")

        world.spawn("player")
        world.tick(0)
        collector.collect()

        # Start server
        server = MetricsServer(port=9107)
        server.start()
        time.sleep(0.2)  # Give server time to start

        try:
            # Fetch metrics
            url = server.get_metrics_url()
            with urllib.request.urlopen(url, timeout=5) as response:
                body = response.read().decode("utf-8")

            # Should contain metrics
            assert "relics_entities_total" in body

        finally:
            server.stop()

    def test_server_daemon_mode(self) -> None:
        """Test that server runs in daemon mode."""
        server = MetricsServer(port=9108)

        server.start(daemon=True)
        time.sleep(0.1)

        # Server should be running
        assert server.is_running is True

        server.stop()
