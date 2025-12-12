"""StatusLine event handler."""

import json
import subprocess
from pathlib import Path
from typing import Optional

from ..models import RequestContext, EventData
from ..errors import NonBlockingError
from .base import EventHandler


class PluginMetadata:
    """Plugin installation metadata from Claude Code."""

    def __init__(self, plugin_id: str, marketplace_id: str):
        self.plugin_id = plugin_id
        self.marketplace_id = marketplace_id

        # Default values
        self.version = "unknown"
        self.installed_sha = "unknown"
        self.current_sha = ""
        self.install_path = ""
        self.is_dev_mode = False
        self.needs_warning = False

        self._load()

    def _load(self):
        """Load metadata from Claude's JSON files and git."""
        try:
            # Read installed_plugins.json
            installed_path = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
            if installed_path.exists():
                data = json.loads(installed_path.read_text())
                plugin = data.get("plugins", {}).get(self.plugin_id, {})
                if plugin:
                    self.version = plugin.get("version", "unknown")
                    self.installed_sha = plugin.get("gitCommitSha", "unknown")
                    self.install_path = plugin.get("installPath", "")

            # Read known_marketplaces.json for dev mode detection
            marketplaces_path = Path.home() / ".claude" / "plugins" / "known_marketplaces.json"
            if marketplaces_path.exists():
                data = json.loads(marketplaces_path.read_text())
                marketplace = data.get(self.marketplace_id, {})
                source = marketplace.get("source", {})
                self.is_dev_mode = source.get("source") == "directory"

            # Run git in dev mode
            if self.is_dev_mode and self.install_path:
                try:
                    result = subprocess.run(
                        ["git", "-C", self.install_path, "rev-parse", "HEAD"],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if result.returncode == 0:
                        self.current_sha = result.stdout.strip()
                        # Check if warning needed
                        if self.current_sha and self.installed_sha != "unknown":
                            self.needs_warning = (self.current_sha != self.installed_sha)
                except Exception:
                    # Git failed - leave current_sha empty
                    pass
        except Exception:
            # Graceful fallback on any error
            pass


class StatusLineHandler(EventHandler):
    """Handler for StatusLine hook events."""

    PLUGIN_ID = "ai-assisted-development@claude-code-toolbox"
    MARKETPLACE_ID = "claude-code-toolbox"

    def handle(self, context: RequestContext, event_data: EventData) -> RequestContext:
        """Build and print statusline (stub implementation)."""
        # Stub - will implement later
        print("StatusLine stub")
        return context
