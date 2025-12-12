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


class StatusLineFormatter:
    """Formats status line output."""

    def format(self, metadata: PluginMetadata, context: RequestContext) -> str:
        """Build formatted status line string.

        Args:
            metadata: Plugin state (version, SHAs, paths, dev mode)
            context: Request context (request_id, request_dir)

        Returns:
            Multi-line status string
        """
        lines = []

        # Check if plugin is installed
        if metadata.version == "unknown" or not metadata.install_path:
            lines.append(f"{metadata.plugin_id}: ⚠️  Plugin not installed.")
            return "\n".join(lines)

        # Plugin version line
        if metadata.needs_warning:
            lines.append(f"{metadata.plugin_id}: v{metadata.version} ⚠️")
            lines.append(
                f"📦 Installed: {metadata.installed_sha[:7]} | "
                f"Current: {metadata.current_sha[:7]}"
            )
        else:
            lines.append(f"{metadata.plugin_id}: v{metadata.version}")
            lines.append(f"📦 Installed: {metadata.installed_sha[:7]}")

        # Request info
        if context.request_id:
            lines.append(f"📁 Request: {context.request_id}")

            # Abbreviate home directory
            display_path = str(context.request_dir)
            home_str = str(Path.home())
            if display_path.startswith(home_str):
                display_path = "~" + display_path[len(home_str):]
            lines.append(f"💾 {display_path}/")
        else:
            lines.append("📁 No active request")

        return "\n".join(lines)


class StatusLineHandler(EventHandler):
    """Handler for StatusLine hook events."""

    PLUGIN_ID = "ai-assisted-development@claude-code-toolbox"
    MARKETPLACE_ID = "claude-code-toolbox"

    def handle(self, context: RequestContext, event_data: EventData) -> RequestContext:
        """Build and print statusline (stub implementation)."""
        # Stub - will implement later
        print("StatusLine stub")
        return context
