"""
Command Line Interface for Ghost-Desktop.
Provides interactive demo, headless screenshotting, action execution, and sandbox resets.
"""

import argparse
import os
import sys
import time
from .models import ComputerAction, ActionType
from .display import VirtualDisplay
from .sandbox import SandboxEnvironment
from .protocol import ProtocolAdapter


def run_demo() -> None:
    """Run an interactive demonstration of Ghost-Desktop computer use & instant rollback."""
    print("=" * 72)
    print("  ❖ GHOST-DESKTOP: EPHEMERAL VIRTUAL ENVIRONMENT FOR COMPUTER-USE AGENTS")
    print("=" * 72)
    print("Initializing isolated sandbox container and virtual 1280x800 framebuffer...")

    start_init = time.time()
    env = SandboxEnvironment()
    disp = env.display
    print(f"✓ Virtual Display online: 1280x800 @ 30FPS (in {(time.time() - start_init)*1000:.1f}ms)")
    print(f"✓ Isolated filesystem allocated: {env.workspace_dir}")
    print(f"✓ Anthropic Tool Schema (computer_20241022) armed\n")

    # Step 1: Capture Screenshot
    print("[1/5] Agent Request: Capture initial desktop screenshot")
    t0 = time.time()
    b64 = disp.capture_base64()
    dur = (time.time() - t0) * 1000
    print(f"      -> Framebuffer rendered: {len(b64)} Base64 chars ({dur:.2f}ms)")

    # Step 2: Mouse Move & Click Terminal
    print("\n[2/5] Agent Request: Focus Terminal Window & Click at (150, 120)")
    res_click = disp.execute_action(ComputerAction(
        action=ActionType.LEFT_CLICK,
        coordinate=(150, 120)
    ))
    print(f"      -> {res_click.output} [cursor: {res_click.cursor_position}]")

    # Step 3: Type Shell Commands
    print("\n[3/5] Agent Request: Type shell commands into Terminal")
    disp.execute_action(ComputerAction(
        action=ActionType.TYPE,
        text="echo 'Agent executing autonomous task' > agent_output.txt\n"
    ))
    disp.execute_action(ComputerAction(
        action=ActionType.KEY,
        key="Return"
    ))
    print(f"      -> Input dispatched. Active window: {disp.active_window_id}")

    # Step 4: Create Sandbox Checkpoint
    print("\n[4/5] Creating Checkpoint 'pre_mutation'...")
    cp_start = time.time()
    meta = env.create_checkpoint("pre_mutation")
    print(f"      -> Checkpoint '{meta.snapshot_id}' created in {(time.time() - cp_start)*1000:.2f}ms")
    print(f"         Active windows: {meta.active_window_count} | Footprint: {meta.memory_footprint_mb} MB")

    # Simulate rogue / dirty mutation
    dirty_file = f"{env.workspace_dir}/malicious_spill.bin"
    with open(dirty_file, "wb") as f:
        f.write(b"\xde\xad\xbe\xef" * 1024)
    disp.move_cursor(999, 500)
    print("      -> Injected workspace file drift (malicious_spill.bin) & moved cursor to (999, 500)")

    # Step 5: Instant Rollback
    print("\n[5/5] Invoking Sub-500ms Instant Rollback to 'pre_mutation'...")
    rb_start = time.time()
    success = env.restore_checkpoint("pre_mutation")
    rb_dur = (time.time() - rb_start) * 1000
    print(f"      -> Rollback complete: {success} (Elapsed: {rb_dur:.2f}ms)")
    print(f"      -> Workspace file removed: {not os.path.exists(dirty_file)}")
    print(f"      -> Cursor restored: {disp.cursor_pos}")

    print("\n" + "=" * 72)
    print("  DEMO COMPLETE: GHOST-DESKTOP READY FOR MULTIMODAL AGENT RUNTIMES")
    print("=" * 72)
    env.cleanup()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ghost-Desktop Virtual Environment CLI")
    subparsers = parser.add_subparsers(dest="command")

    demo_parser = subparsers.add_parser("demo", help="Run interactive demo")

    screenshot_parser = subparsers.add_parser("screenshot", help="Capture screenshot to file")
    screenshot_parser.add_argument("--output", "-o", default="screenshot.png", help="Output PNG file path")

    args = parser.parse_args()

    if args.command == "demo" or len(sys.argv) == 1:
        run_demo()
    elif args.command == "screenshot":
        disp = VirtualDisplay()
        img = disp.render_canvas()
        img.save(args.output, format="PNG")
        print(f"Screenshot written to {args.output}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
