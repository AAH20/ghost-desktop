"""
Virtual Display & Framebuffer Engine for Ghost-Desktop.
Provides high-fidelity software rendering of a desktop workspace with active windows,
dock/taskbar, cursor positioning, and full graphic capture for Computer-Use AI agents.
"""

import base64
import io
import time
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image, ImageDraw, ImageFont

from .models import DisplayConfig, WindowState, ComputerAction, ActionResult, ActionType


class VirtualDisplay:
    """Headless virtual desktop display and event dispatcher."""

    def __init__(self, config: Optional[DisplayConfig] = None):
        self.config = config or DisplayConfig()
        self.cursor_pos: Tuple[int, int] = (self.config.width // 2, self.config.height // 2)
        self.mouse_pressed: bool = False
        self.windows: Dict[str, WindowState] = {}
        self.active_window_id: Optional[str] = None
        self._init_default_desktop()

    def _init_default_desktop(self) -> None:
        """Initialize desktop with standard operational windows."""
        # Terminal Window
        term = WindowState(
            id="window_terminal",
            title="bash - ghost-sandbox@ephemeral: ~",
            rect=(50, 60, 600, 420),
            is_active=True,
            content_lines=[
                "Ghost-Desktop v1.0.0 (x86_64-ephemeral-sandbox)",
                "Linux 6.8.0-ghost-virt #1 SMP PREEMPT_DYNAMIC",
                "Environment: ISOLATED_CONTAINER_SECURE",
                "",
                "guest@ghost-sandbox:~$ ls -la /workspace",
                "drwxr-xr-x 2 guest guest 4096 Sep 25 21:00 .",
                "-rw-r--r-- 1 guest guest 1024 Sep 25 21:00 config.json",
                "-rwxr-xr-x 1 guest guest 4096 Sep 25 21:00 run_agent.sh",
                "guest@ghost-sandbox:~$ "
            ],
            input_text="",
            status_bar="bash | UTF-8 | PID 1042"
        )
        # Web Browser Window
        browser = WindowState(
            id="window_browser",
            title="Ghost Chromium - Cloud Console & Agent Dashboard",
            rect=(500, 100, 720, 520),
            is_active=False,
            content_lines=[
                "https://console.cloud.internal/agent-cluster/status",
                "----------------------------------------------------------------",
                "[ AGENT CLUSTER HEALTH: ALL SYSTEMS OPERATIONAL ]",
                "- Active Nodes: 12",
                "- Memory Utilization: 24.3%",
                "- Workload Queue: 0 pending",
                "- Security Tripwires: ARMED",
                "",
                "Actions Available:",
                "  [1] Deploy Production Build",
                "  [2] Run Chaos Drill",
                "  [3] Flush Redis Cache"
            ],
            input_text="search query or URL...",
            status_bar="TLS 1.3 | Encrypted | Latency 2ms"
        )
        self.windows[term.id] = term
        self.windows[browser.id] = browser
        self.active_window_id = term.id

    def move_cursor(self, x: int, y: int) -> Tuple[int, int]:
        """Move cursor with boundary clamping."""
        clamped_x = max(0, min(self.config.width - 1, x))
        clamped_y = max(0, min(self.config.height - 1, y))
        self.cursor_pos = (clamped_x, clamped_y)
        return self.cursor_pos

    def click(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left") -> ActionResult:
        """Handle mouse click and window focus changes."""
        start_time = time.time()
        if x is not None and y is not None:
            self.move_cursor(x, y)
        cx, cy = self.cursor_pos

        clicked_window_id = None
        # Check window hit test in reverse order (top to bottom)
        for win_id, win in reversed(list(self.windows.items())):
            wx, wy, ww, wh = win.rect
            if wx <= cx <= wx + ww and wy <= cy <= wy + wh:
                clicked_window_id = win_id
                break

        if clicked_window_id:
            self._focus_window(clicked_window_id)
            win = self.windows[clicked_window_id]
            # Check if clicked inside titlebar close or buttons
            output = f"Clicked window '{win.title}' at ({cx}, {cy})"
        else:
            output = f"Clicked desktop background at ({cx}, {cy})"

        duration_ms = (time.time() - start_time) * 1000.0
        return ActionResult(
            success=True,
            action=f"{button}_click",
            output=output,
            cursor_position=self.cursor_pos,
            execution_time_ms=duration_ms,
            active_window=self.active_window_id
        )

    def _focus_window(self, win_id: str) -> None:
        """Bring window to front and set active."""
        if win_id in self.windows:
            for w in self.windows.values():
                w.is_active = False
            self.windows[win_id].is_active = True
            self.active_window_id = win_id
            # Move to end of dict so it renders on top
            win = self.windows.pop(win_id)
            self.windows[win_id] = win

    def type_text(self, text: str) -> ActionResult:
        """Type text into the active window."""
        start_time = time.time()
        if not self.active_window_id or self.active_window_id not in self.windows:
            return ActionResult(
                success=False,
                action="type",
                error="No active window focused to receive text input",
                cursor_position=self.cursor_pos
            )

        win = self.windows[self.active_window_id]
        if win.id == "window_terminal":
            # Append characters to current line or new line
            if "\n" in text:
                parts = text.split("\n")
                if win.content_lines:
                    win.content_lines[-1] += parts[0]
                for p in parts[1:]:
                    win.content_lines.append(f"guest@ghost-sandbox:~$ {p}")
            else:
                if win.content_lines:
                    win.content_lines[-1] += text
                else:
                    win.content_lines.append(text)
        else:
            win.input_text += text

        duration_ms = (time.time() - start_time) * 1000.0
        return ActionResult(
            success=True,
            action="type",
            output=f"Typed {len(text)} characters into '{win.title}'",
            cursor_position=self.cursor_pos,
            execution_time_ms=duration_ms,
            active_window=self.active_window_id
        )

    def press_key(self, key: str) -> ActionResult:
        """Dispatch key press (Return, Backspace, Tab, Escape, etc.)."""
        start_time = time.time()
        k = key.lower()
        if self.active_window_id and self.active_window_id in self.windows:
            win = self.windows[self.active_window_id]
            if k in ("return", "enter"):
                if win.id == "window_terminal":
                    last_line = win.content_lines[-1] if win.content_lines else ""
                    # Simple simulated command execution
                    cmd = last_line.split("$ ")[-1].strip() if "$ " in last_line else last_line.strip()
                    if cmd == "clear":
                        win.content_lines = ["guest@ghost-sandbox:~$ "]
                    elif cmd == "pwd":
                        win.content_lines.append("/workspace")
                        win.content_lines.append("guest@ghost-sandbox:~$ ")
                    elif cmd == "whoami":
                        win.content_lines.append("guest (UID 1000)")
                        win.content_lines.append("guest@ghost-sandbox:~$ ")
                    else:
                        if cmd:
                            win.content_lines.append(f"executed: {cmd} [exit: 0]")
                        win.content_lines.append("guest@ghost-sandbox:~$ ")
            elif k in ("backspace",):
                if win.id == "window_terminal" and win.content_lines:
                    if len(win.content_lines[-1]) > len("guest@ghost-sandbox:~$ "):
                        win.content_lines[-1] = win.content_lines[-1][:-1]
                elif win.input_text:
                    win.input_text = win.input_text[:-1]

        duration_ms = (time.time() - start_time) * 1000.0
        return ActionResult(
            success=True,
            action="key",
            output=f"Dispatched key '{key}'",
            cursor_position=self.cursor_pos,
            execution_time_ms=duration_ms,
            active_window=self.active_window_id
        )

    def render_canvas(self) -> Image.Image:
        """Render high-fidelity desktop workspace to PIL Image."""
        w, h = self.config.width, self.config.height
        img = Image.new("RGB", (w, h), color=(18, 22, 32))  # Dark modern desktop background
        draw = ImageDraw.Draw(img)

        # Draw Wallpaper grid / cybernetic subtle dots
        for gx in range(0, w, 40):
            for gy in range(0, h - 45, 40):
                draw.point((gx, gy), fill=(35, 42, 60))

        # Top Bar (Menu & Indicators)
        draw.rectangle([(0, 0), (w, 30)], fill=(28, 33, 48))
        draw.text((15, 8), "❖ GHOST-DESKTOP", fill=(99, 179, 237))
        draw.text((180, 8), "Workspace: isolated-sandbox-01", fill=(160, 174, 192))
        draw.text((w - 240, 8), "State: CLEAN | 1920x1080@60Hz", fill=(72, 187, 120))
        draw.text((w - 60, 8), "12:00", fill=(226, 232, 240))

        # Render open windows
        for win_id, win in self.windows.items():
            wx, wy, ww, wh = win.rect
            is_active = (win_id == self.active_window_id)

            # Window drop shadow
            shadow_offset = 6
            draw.rectangle(
                [(wx + shadow_offset, wy + shadow_offset), (wx + ww + shadow_offset, wy + wh + shadow_offset)],
                fill=(10, 12, 18)
            )

            # Window body background
            body_bg = (15, 23, 42) if win.id == "window_terminal" else (24, 30, 46)
            draw.rectangle([(wx, wy), (wx + ww, wy + wh)], fill=body_bg, outline=(59, 130, 246) if is_active else (71, 85, 105), width=2 if is_active else 1)

            # Window Title Bar
            title_bg = (30, 41, 59) if is_active else (20, 27, 45)
            draw.rectangle([(wx, wy), (wx + ww, wy + 32)], fill=title_bg)

            # Window traffic light buttons
            draw.ellipse([(wx + 10, wy + 10), (wx + 22, wy + 22)], fill=(239, 68, 68))    # Close
            draw.ellipse([(wx + 28, wy + 10), (wx + 40, wy + 22)], fill=(245, 158, 11))   # Minimize
            draw.ellipse([(wx + 46, wy + 10), (wx + 58, wy + 22)], fill=(16, 185, 129))   # Maximize

            # Title text
            title_color = (255, 255, 255) if is_active else (148, 163, 184)
            draw.text((wx + 75, wy + 9), win.title, fill=title_color)

            # Window Content
            line_y = wy + 42
            if win.id == "window_terminal":
                # Render terminal text
                for line in win.content_lines[-18:]:  # Show last 18 lines
                    color = (52, 211, 153) if "guest@" in line else (203, 213, 225)
                    if "ISOLATED" in line:
                        color = (251, 191, 36)
                    draw.text((wx + 12, line_y), line, fill=color)
                    line_y += 18
            else:
                # Browser / GUI window
                # Address bar
                draw.rectangle([(wx + 12, line_y), (wx + ww - 12, line_y + 26)], fill=(33, 41, 60), outline=(51, 65, 85))
                draw.text((wx + 20, line_y + 6), win.content_lines[0] if win.content_lines else "about:blank", fill=(147, 197, 253))
                line_y += 36

                for line in win.content_lines[1:]:
                    text_color = (226, 232, 240)
                    if "[ AGENT CLUSTER HEALTH" in line:
                        text_color = (74, 222, 128)
                    elif "[1]" in line or "[2]" in line or "[3]" in line:
                        text_color = (96, 165, 250)
                    draw.text((wx + 15, line_y), line, fill=text_color)
                    line_y += 20

            # Window Status Bar
            draw.rectangle([(wx, wy + wh - 22), (wx + ww, wy + wh)], fill=(20, 26, 40))
            draw.text((wx + 10, wy + wh - 17), win.status_bar, fill=(100, 116, 139))

        # Bottom Dock / Taskbar
        dock_h = 42
        draw.rectangle([(0, h - dock_h), (w, h)], fill=(15, 20, 32), outline=(30, 41, 59))
        draw.text((20, h - 28), "▶ Start", fill=(248, 250, 252))
        draw.rectangle([(100, h - 36), (240, h - 6)], fill=(30, 41, 59), outline=(59, 130, 246))
        draw.text((115, h - 26), "Terminal [PID 1042]", fill=(226, 232, 240))
        draw.rectangle([(250, h - 36), (390, h - 6)], fill=(24, 30, 46))
        draw.text((265, h - 26), "Chromium [PID 1098]", fill=(148, 163, 184))

        # Render Mouse Cursor (Smooth triangle pointer)
        cx, cy = self.cursor_pos
        cursor_poly = [
            (cx, cy),
            (cx, cy + 18),
            (cx + 5, cy + 14),
            (cx + 10, cy + 22),
            (cx + 13, cy + 21),
            (cx + 8, cy + 13),
            (cx + 14, cy + 13)
        ]
        draw.polygon(cursor_poly, fill=(255, 255, 255), outline=(0, 0, 0))

        return img

    def capture_base64(self, format: str = "PNG") -> str:
        """Capture screenshot as Base64 string for direct LLM multimodal ingestion."""
        img = self.render_canvas()
        buffer = io.BytesIO()
        img.save(buffer, format=format)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def execute_action(self, action: ComputerAction) -> ActionResult:
        """Dispatch computer-use action and return result with optional screenshot."""
        start_time = time.time()
        act_type = action.action

        if act_type == ActionType.SCREENSHOT:
            b64 = self.capture_base64()
            duration_ms = (time.time() - start_time) * 1000.0
            return ActionResult(
                success=True,
                action="screenshot",
                output=f"Captured {self.config.width}x{self.config.height} screenshot",
                screenshot_base64=b64,
                cursor_position=self.cursor_pos,
                execution_time_ms=duration_ms,
                active_window=self.active_window_id
            )

        elif act_type in (ActionType.MOUSE_MOVE, ActionType.MOVE_CURSOR):
            if action.coordinate:
                self.move_cursor(*action.coordinate)
            duration_ms = (time.time() - start_time) * 1000.0
            return ActionResult(
                success=True,
                action="mouse_move",
                output=f"Cursor moved to {self.cursor_pos}",
                cursor_position=self.cursor_pos,
                execution_time_ms=duration_ms,
                active_window=self.active_window_id
            )

        elif act_type in (ActionType.LEFT_CLICK, ActionType.CLICK):
            coord = action.coordinate
            return self.click(coord[0] if coord else None, coord[1] if coord else None, button="left")

        elif act_type == ActionType.RIGHT_CLICK:
            coord = action.coordinate
            return self.click(coord[0] if coord else None, coord[1] if coord else None, button="right")

        elif act_type == ActionType.TYPE:
            text = action.text or ""
            return self.type_text(text)

        elif act_type == ActionType.KEY:
            key = action.key or ""
            return self.press_key(key)

        elif act_type == ActionType.CURSOR_POSITION:
            duration_ms = (time.time() - start_time) * 1000.0
            return ActionResult(
                success=True,
                action="cursor_position",
                output=f"Current cursor position: {self.cursor_pos}",
                cursor_position=self.cursor_pos,
                execution_time_ms=duration_ms,
                active_window=self.active_window_id
            )

        else:
            return ActionResult(
                success=True,
                action=str(act_type),
                output=f"Action '{act_type}' acknowledged and executed",
                cursor_position=self.cursor_pos,
                execution_time_ms=(time.time() - start_time) * 1000.0,
                active_window=self.active_window_id
            )
