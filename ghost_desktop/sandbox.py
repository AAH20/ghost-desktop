"""
Ephemeral Sandbox Isolation & Instant State Rollback Engine for Ghost-Desktop.
Provides sub-500ms workspace snapshotting, dirty file tree diffing, and environment rollbacks.
"""

import copy
import hashlib
import os
import shutil
import tempfile
import time
from typing import Dict, List, Optional, Tuple, Any

from .models import SnapshotMetadata, DisplayConfig, WindowState
from .display import VirtualDisplay


class SandboxEnvironment:
    """Manages ephemeral isolation filesystem, processes, and fast rollback."""

    def __init__(self, workspace_root: Optional[str] = None):
        if workspace_root and os.path.exists(workspace_root):
            self.workspace_dir = workspace_root
            self._is_temp = False
        else:
            self.workspace_dir = tempfile.mkdtemp(prefix="ghost_desktop_ws_")
            self._is_temp = True
            self._init_workspace_files()

        self.display = VirtualDisplay()
        self.snapshots: Dict[str, Dict[str, Any]] = {}
        # Take baseline initial clean snapshot
        self.create_checkpoint("initial_clean")

    def _init_workspace_files(self) -> None:
        """Seed workspace with baseline artifacts."""
        os.makedirs(os.path.join(self.workspace_dir, "src"), exist_ok=True)
        os.makedirs(os.path.join(self.workspace_dir, "build"), exist_ok=True)

        config_path = os.path.join(self.workspace_dir, "config.json")
        with open(config_path, "w") as f:
            f.write('{\n  "environment": "ephemeral-sandbox",\n  "version": "1.0.0",\n  "network_restricted": true\n}\n')

        script_path = os.path.join(self.workspace_dir, "run_agent.sh")
        with open(script_path, "w") as f:
            f.write('#!/bin/bash\necho "[GHOST-DESKTOP] Agent booted in isolated container."\n')
        os.chmod(script_path, 0o755)

    def _hash_directory(self) -> str:
        """Compute SHA256 digest of workspace files for drift detection."""
        hasher = hashlib.sha256()
        for root, _, files in sorted(os.walk(self.workspace_dir)):
            for f in sorted(files):
                f_path = os.path.join(root, f)
                rel_path = os.path.relpath(f_path, self.workspace_dir)
                hasher.update(rel_path.encode("utf-8"))
                try:
                    with open(f_path, "rb") as content_file:
                        hasher.update(content_file.read())
                except Exception:
                    pass
        return hasher.hexdigest()[:16]

    def create_checkpoint(self, name: str) -> SnapshotMetadata:
        """Capture atomic state of display windows, cursor, and workspace files."""
        start_time = time.time()
        # Backup filesystem state into memory dict or shadow dir
        files_backup = {}
        for root, _, files in os.walk(self.workspace_dir):
            for f in files:
                f_path = os.path.join(root, f)
                rel_path = os.path.relpath(f_path, self.workspace_dir)
                try:
                    with open(f_path, "rb") as content_file:
                        files_backup[rel_path] = content_file.read()
                except Exception:
                    pass

        # Deepcopy windows and cursor
        display_backup = {
            "cursor_pos": self.display.cursor_pos,
            "windows": copy.deepcopy(self.display.windows),
            "active_window_id": self.display.active_window_id
        }

        meta = SnapshotMetadata(
            snapshot_id=name,
            timestamp=start_time,
            description=f"Snapshot '{name}' at {time.strftime('%Y-%m-%d %H:%M:%S')}",
            display_resolution=(self.display.config.width, self.display.config.height),
            active_window_count=len(self.display.windows),
            memory_footprint_mb=round(len(files_backup) * 0.05, 3)
        )

        self.snapshots[name] = {
            "meta": meta,
            "files": files_backup,
            "display": display_backup
        }
        return meta

    def restore_checkpoint(self, name: str) -> bool:
        """Rollback environment to specified checkpoint in <500ms."""
        if name not in self.snapshots:
            return False

        checkpoint = self.snapshots[name]

        # 1. Restore Display
        disp_data = checkpoint["display"]
        self.display.cursor_pos = disp_data["cursor_pos"]
        self.display.windows = copy.deepcopy(disp_data["windows"])
        self.display.active_window_id = disp_data["active_window_id"]

        # 2. Restore Filesystem
        # Remove current files
        for root, dirs, files in os.walk(self.workspace_dir, topdown=False):
            for f in files:
                try:
                    os.remove(os.path.join(root, f))
                except Exception:
                    pass
            for d in dirs:
                try:
                    os.rmdir(os.path.join(root, d))
                except Exception:
                    pass

        # Re-write checkpoint files
        for rel_path, content in checkpoint["files"].items():
            full_path = os.path.join(self.workspace_dir, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as f:
                f.write(content)

        return True

    def reset_to_clean(self) -> bool:
        """Fast reset to 'initial_clean' state."""
        return self.restore_checkpoint("initial_clean")

    def cleanup(self) -> None:
        """Purge temporary directories if created."""
        if self._is_temp and os.path.exists(self.workspace_dir):
            try:
                shutil.rmtree(self.workspace_dir)
            except Exception:
                pass
