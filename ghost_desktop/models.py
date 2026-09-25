"""
Data models and schemas for Ghost-Desktop Virtual Environment.
Compatible with Anthropic Computer Use API (computer_20241022) & OpenAI Operator.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import time


class ActionType(str, Enum):
    SCREENSHOT = "screenshot"
    MOUSE_MOVE = "mouse_move"
    LEFT_CLICK = "left_click"
    CLICK = "click"
    RIGHT_CLICK = "right_click"
    MIDDLE_CLICK = "middle_click"
    DOUBLE_CLICK = "double_click"
    TRIPLE_CLICK = "triple_click"
    MOUSE_DOWN = "mouse_down"
    MOUSE_UP = "mouse_up"
    MOVE_CURSOR = "move_cursor"
    TYPE = "type"
    KEY = "key"
    KEY_DOWN = "key_down"
    KEY_UP = "key_up"
    WAIT = "wait"
    HOTKEY = "hotkey"
    CURSOR_POSITION = "cursor_position"
    DRAG = "drag"
    SCROLL = "scroll"


@dataclass
class DisplayConfig:
    width: int = 1280
    height: int = 800
    dpi: int = 96
    color_depth: int = 24
    framerate: int = 30
    title: str = "Ghost-Desktop Ephemeral Workspace"


@dataclass
class ComputerAction:
    action: ActionType
    coordinate: Optional[Tuple[int, int]] = None
    text: Optional[str] = None
    key: Optional[str] = None
    duration_ms: int = 0
    delta_x: int = 0
    delta_y: int = 0
    button: str = "left"


@dataclass
class ActionResult:
    success: bool
    action: str
    output: Optional[str] = None
    error: Optional[str] = None
    screenshot_base64: Optional[str] = None
    cursor_position: Tuple[int, int] = (0, 0)
    execution_time_ms: float = 0.0
    active_window: Optional[str] = None


@dataclass
class WindowState:
    id: str
    title: str
    rect: Tuple[int, int, int, int]  # (x, y, w, h)
    is_active: bool = True
    content_lines: List[str] = field(default_factory=list)
    input_text: str = ""
    status_bar: str = "Ready"


@dataclass
class SnapshotMetadata:
    snapshot_id: str
    timestamp: float = field(default_factory=time.time)
    description: str = ""
    display_resolution: Tuple[int, int] = (1280, 800)
    active_window_count: int = 0
    memory_footprint_mb: float = 0.0
