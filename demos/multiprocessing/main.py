#!/usr/bin/env python3
"""Main entry point for the multiprocessing demo.

Spawns two processes:
1. ECS Process: Runs the Relics World with entities and systems
2. Renderer Process: Uses pygame to render entities via IPC

Run with: python demos/multiprocessing/main.py
"""

import multiprocessing
import os
import sys

# Add src to path for running from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from demos.multiprocessing.ecs_process import run_ecs_process
from demos.multiprocessing.render_process import run_render_process


def main() -> None:
    """Main entry point - spawns ECS and renderer processes."""
    print("=" * 60)
    print("Relics ECS - Multiprocessing Demo")
    print("=" * 60)
    print()
    print("This demo shows how to use Relics ECS with multiprocessing:")
    print("  - Process 1 (ECS): Runs the simulation with entities/systems")
    print("  - Process 2 (Renderer): Renders entities via pygame")
    print()
    print("A custom ComponentObserver sends position changes via IPC.")
    print("Close the pygame window to exit.")
    print()
    print("-" * 60)
    print()

    # Create queues for IPC
    # render_queue: ECS -> Renderer (entity state changes)
    # control_queue: Renderer -> ECS (quit signals)
    render_queue: multiprocessing.Queue = multiprocessing.Queue()
    control_queue: multiprocessing.Queue = multiprocessing.Queue()

    # Spawn processes
    ecs_proc = multiprocessing.Process(
        target=run_ecs_process,
        args=(render_queue, control_queue),
        name="ECS-Process",
    )
    render_proc = multiprocessing.Process(
        target=run_render_process,
        args=(render_queue, control_queue),
        name="Render-Process",
    )

    try:
        # Start both processes
        ecs_proc.start()
        render_proc.start()

        print(f"[Main] ECS Process PID: {ecs_proc.pid}")
        print(f"[Main] Render Process PID: {render_proc.pid}")
        print()

        # Wait for renderer to exit (it controls the lifecycle)
        render_proc.join()
        print("[Main] Renderer process exited")

        # Wait for ECS process with timeout
        ecs_proc.join(timeout=2.0)
        if ecs_proc.is_alive():
            print("[Main] ECS process didn't exit cleanly, terminating...")
            ecs_proc.terminate()
            ecs_proc.join(timeout=1.0)

        print("[Main] ECS process exited")

    except KeyboardInterrupt:
        print("\n[Main] KeyboardInterrupt received, shutting down...")
        control_queue.put("quit")

        # Give processes time to exit gracefully
        render_proc.join(timeout=2.0)
        ecs_proc.join(timeout=2.0)

        # Force terminate if needed
        if render_proc.is_alive():
            render_proc.terminate()
        if ecs_proc.is_alive():
            ecs_proc.terminate()

    print()
    print("-" * 60)
    print("Demo finished!")


if __name__ == "__main__":
    # Use 'spawn' for better cross-platform compatibility with pygame
    multiprocessing.set_start_method("spawn", force=True)
    main()
