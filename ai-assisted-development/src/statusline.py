#!/usr/bin/env python3
"""Standalone statusline script for Claude Code.

Displays plugin version, installation SHA, and dev mode mismatch warnings.
Reads JSON from stdin (Claude Code statusline protocol) but only uses
filesystem metadata for display.
"""

import json
import subprocess
import sys
from pathlib import Path


PLUGIN_ID = "ai-assisted-development@claude-code-toolbox"
MARKETPLACE_ID = "claude-code-toolbox"


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
                entries = data.get("plugins", {}).get(self.plugin_id)
                # v2 format: plugins are arrays of install records
                if isinstance(entries, list) and entries:
                    plugin = entries[0]
                elif isinstance(entries, dict):
                    plugin = entries
                else:
                    plugin = None
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

            # Run git in dev mode to check for SHA mismatch
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
                        if self.current_sha and self.installed_sha != "unknown":
                            self.needs_warning = (self.current_sha != self.installed_sha)
                except Exception:
                    pass
        except Exception:
            pass


def format_statusline(metadata: PluginMetadata) -> str:
    """Build formatted status line string."""
    lines = []

    if metadata.version == "unknown" or not metadata.install_path:
        lines.append(f"{metadata.plugin_id}: Plugin not installed.")
        return "\n".join(lines)

    if metadata.needs_warning:
        lines.append(f"{metadata.plugin_id}: v{metadata.version} ⚠️")
        lines.append(
            f"📦 Installed: {metadata.installed_sha[:7]} | "
            f"Current: {metadata.current_sha[:7]}"
        )
    else:
        lines.append(f"{metadata.plugin_id}: v{metadata.version}")
        lines.append(f"📦 Installed: {metadata.installed_sha[:7]}")

    return "\n".join(lines)


def main():
    """Read statusline input from stdin and print formatted output."""
    try:
        # Consume stdin (Claude Code expects it to be read)
        json.load(sys.stdin)
    except Exception:
        pass

    try:
        metadata = PluginMetadata(PLUGIN_ID, MARKETPLACE_ID)
        output = format_statusline(metadata)
        print(output, flush=True)
    except Exception as e:
        print(f"StatusLine error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
