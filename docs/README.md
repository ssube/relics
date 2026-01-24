# Relics Documentation

Documentation for the Relics ECS framework with graph database semantics.

## Getting Started

- [Getting Started](GETTING_STARTED.md) - Installation, basic concepts, and first steps

## Core Concepts

- [World](WORLD.md) - The central container for entities, systems, and observers
- [Entities & Components](ENTITIES_COMPONENTS.md) - Data model and component patterns
- [Relationships](RELATIONSHIPS.md) - Graph-like connections between entities
- [Systems](SYSTEMS.md) - Logic that operates on entities each tick
- [Observers](OBSERVERS.md) - Event-driven reactions to world changes

## Addons

Optional extensions for specialized functionality:

- [Spatial Indexing](../src/relics/addons/spatial/README.md) - 2D/3D spatial queries with quadtree/octree
- [Tile Grid](../src/relics/addons/tilegrid/README.md) - Chunked tile-based world management
- [Procedural Prefabs](../src/relics/addons/procedural_prefabs/README.md) - Graph-based entity generation
- [Prometheus](../src/relics/addons/prometheus/README.md) - Metrics and monitoring
- [WebSocket](../src/relics/addons/websocket/README.md) - Real-time multiplayer synchronization

## Reference

- [Benchmarks](BENCHMARKS.md) - Performance characteristics and optimization guidance
- [Best Practices](BEST_PRACTICES.md) - Recommended patterns and anti-patterns
- [Agent Guide](AGENT_GUIDE.md) - Guide for AI agents working with the codebase
