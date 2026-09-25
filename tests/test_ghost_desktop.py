"""
Comprehensive Unit Test Suite for Ghost-Desktop.
"""

import base64
import io
import os
import unittest
from PIL import Image

from ghost_desktop.models import (
    DisplayConfig,
    ActionType,
    ComputerAction,
    ActionResult,
)
from ghost_desktop.display import VirtualDisplay
from ghost_desktop.sandbox import SandboxEnvironment
from ghost_desktop.protocol import ProtocolAdapter


class TestGhostDesktop(unittest.TestCase):

    def setUp(self):
        self.config = DisplayConfig(width=1024, height=768)
        self.display = VirtualDisplay(config=self.config)

    def test_display_initialization_and_clamping(self):
        """Test display properties and cursor coordinate clamping."""
        self.assertEqual(self.display.config.width, 1024)
        self.assertEqual(self.display.config.height, 768)

        # Move inside bounds
        pos = self.display.move_cursor(200, 300)
        self.assertEqual(pos, (200, 300))

        # Move outside bounds (should clamp)
        pos = self.display.move_cursor(2000, -50)
        self.assertEqual(pos, (1023, 0))

    def test_canvas_rendering_and_screenshot(self):
        """Test bitmap generation and base64 encoding."""
        img = self.display.render_canvas()
        self.assertIsInstance(img, Image.Image)
        self.assertEqual(img.size, (1024, 768))

        b64 = self.display.capture_base64()
        self.assertTrue(len(b64) > 100)
        raw_bytes = base64.b64decode(b64)
        # Verify valid PNG header (\x89PNG\r\n\x1a\n)
        self.assertTrue(raw_bytes.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_window_focus_and_typing(self):
        """Test clicking on windows to focus and typing into input buffer."""
        # Click terminal window
        res_click = self.display.click(100, 100)
        self.assertTrue(res_click.success)
        self.assertEqual(self.display.active_window_id, "window_terminal")

        # Type command
        res_type = self.display.type_text("ls -la")
        self.assertTrue(res_type.success)
        term_win = self.display.windows["window_terminal"]
        self.assertTrue(any("ls -la" in line for line in term_win.content_lines))

        # Press Enter
        res_key = self.display.press_key("Return")
        self.assertTrue(res_key.success)

    def test_sandbox_snapshot_and_fast_rollback(self):
        """Test ephemeral workspace dirty diffing and rollback."""
        sandbox = SandboxEnvironment()
        try:
            # 1. Take baseline checkpoint
            cp = sandbox.create_checkpoint("baseline")
            self.assertEqual(cp.snapshot_id, "baseline")

            # 2. Mutate state: write file & move cursor
            dirty_file = os.path.join(sandbox.workspace_dir, "rogue_script.py")
            with open(dirty_file, "w") as f:
                f.write("print('malicious rogue code')")
            sandbox.display.move_cursor(900, 600)
            self.assertTrue(os.path.exists(dirty_file))
            self.assertEqual(sandbox.display.cursor_pos, (900, 600))

            # 3. Restore checkpoint
            restored = sandbox.restore_checkpoint("baseline")
            self.assertTrue(restored)
            self.assertFalse(os.path.exists(dirty_file))
            self.assertNotEqual(sandbox.display.cursor_pos, (900, 600))
        finally:
            sandbox.cleanup()

    def test_protocol_adapter_anthropic(self):
        """Test Anthropic Computer Use schema generation and invocation parsing."""
        schema = ProtocolAdapter.get_anthropic_tool_schema(1920, 1080)
        self.assertEqual(schema["name"], "computer")
        self.assertEqual(schema["type"], "computer_20241022")
        self.assertEqual(schema["display_width_px"], 1920)

        # Parse screenshot call
        action = ProtocolAdapter.parse_anthropic_call({"action": "screenshot"})
        self.assertEqual(action.action, ActionType.SCREENSHOT)

        # Execute & format response
        result = self.display.execute_action(action)
        resp = ProtocolAdapter.format_anthropic_response(result)
        self.assertEqual(resp["type"], "tool_result")
        self.assertEqual(resp["content"][0]["type"], "image")

    def test_protocol_adapter_jsonrpc(self):
        """Test standard JSON-RPC 2.0 dispatching."""
        req = {
            "jsonrpc": "2.0",
            "id": 42,
            "method": "computer.action",
            "params": {"action": "mouse_move", "coordinate": [300, 400]}
        }
        resp = ProtocolAdapter.handle_jsonrpc(req, self.display)
        self.assertEqual(resp["id"], 42)
        self.assertTrue(resp["result"]["success"])
        self.assertEqual(resp["result"]["cursor"], (300, 400))


if __name__ == "__main__":
    unittest.main()
