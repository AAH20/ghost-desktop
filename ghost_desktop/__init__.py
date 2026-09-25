"""
Ghost-Desktop: Ephemeral, Sandboxed Virtual Desktop Environment for Full Computer-Use AI Agents.
"""

from .models import (
    DisplayConfig,
    ActionType,
    ComputerAction,
    ActionResult,
    WindowState,
    SnapshotMetadata,
)
from .display import VirtualDisplay
from .sandbox import SandboxEnvironment
from .protocol import ProtocolAdapter

__version__ = "1.0.0"
__all__ = [
    "DisplayConfig",
    "ActionType",
    "ComputerAction",
    "ActionResult",
    "WindowState",
    "SnapshotMetadata",
    "VirtualDisplay",
    "SandboxEnvironment",
    "ProtocolAdapter",
]
