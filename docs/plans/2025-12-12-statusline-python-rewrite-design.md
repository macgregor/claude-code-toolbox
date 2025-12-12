---
name: statusline-python-rewrite
description: >
  Rewrite statusline.sh to Python with tests, reusing lifecycle infrastructure
  for request scoping while keeping statusline-specific logic isolated.
created: 2025-12-12
status: design
---

# Statusline Python Rewrite Design

**Created**: 2025-12-12
**Status**: Design

---

## Problem

The current `statusline.sh` bash script duplicates request lookup logic that exists in the lifecycle system. It's untested and harder to maintain than Python. We want clean, testable code that reuses lifecycle infrastructure where appropriate.

**Discovered bug in bash script:** Dev mode detection never works in local marketplace mode. The script runs `git rev-parse HEAD` in the plugin subdirectory (`{marketplace_root}/ai-assisted-development`), but `.git` is at the marketplace root. The git command silently fails, `CURRENT_SHA` becomes empty, and dev mode check fails. The Python rewrite fixes this by tracking both `install_path` (where plugin files are) and `git_path` (where to run git commands - marketplace root in dev mode, install_path in production).

---

## Goals

1. Rewrite statusline.sh as statusline.py with identical output behavior
2. Reuse lifecycle utilities for request scoping (don't duplicate logic)
3. Keep statusline-specific concerns isolated (plugin metadata, git checking, formatting)
4. Make it fully testable
5. Follow the same interface pattern as agent-lifecycle.py

---

## Architecture

### File Structure

```
ai-assisted-development/src/
├── lifecycle/
│   ├── processing.py          # Add get_current_request_id()
│   └── ...
└── statusline.py              # New: single file (~200 lines)
```

### Shared Infrastructure Changes

Add to `lifecycle/processing.py`:

```python
def get_current_request_id(session_id: str, toolbox_root: str) -> str:
    """Get current request_id for a session from global state.

    Args:
        session_id: Session ID to lookup
        toolbox_root: Project root directory

    Returns:
        Request ID string, or empty string if not found

    Note:
        Returns empty string on any error (file missing, malformed JSON, etc).
        Does not log errors - caller decides error handling policy.
    """
    if not toolbox_root or not session_id:
        return ""

    global_state_path = Path(toolbox_root) / ".toolbox" / "events" / ".global-state.json"
    if not global_state_path.exists():
        return ""

    try:
        data = json.loads(global_state_path.read_text())
        return data.get("session_requests", {}).get(session_id, "")
    except Exception:
        # Silently fail - let caller handle errors
        return ""
```

**Why here:** Already has `get_toolbox_root()`, natural companion. Both orchestrator and statusline need this exact logic.

**Orchestrator refactor:**

Before (orchestrator.py:122-124):
```python
session_id = event_data.fields.get("session_id")
global_state = self._load_global_state(toolbox_root)
return global_state.get("session_requests", {}).get(session_id, "")
```

After:
```python
session_id = event_data.fields.get("session_id")
return get_current_request_id(session_id, toolbox_root)
```

---

## Component Design

### PluginMetadata Class

**Responsibility:** Read plugin version, SHA, and install path from Claude's plugin files.

```python
class PluginMetadata:
    """Plugin installation metadata from Claude Code."""

    def __init__(self, plugin_id: str = "ai-assisted-development@claude-code-toolbox"):
        self.plugin_id = plugin_id

        # Validate home directory
        home = Path.home()
        if not home or str(home) == "":
            raise ValueError("Path.home() returned empty path")

        self._installed_path = home / ".claude" / "plugins" / "installed_plugins.json"
        self._marketplaces_path = home / ".claude" / "plugins" / "known_marketplaces.json"
        self._load()

    def _load(self):
        """Load metadata from installed_plugins.json, fallback to marketplace."""
        self.version = "unknown"
        self.installed_sha = "unknown"
        self.install_path = ""
        self.git_path = ""  # Where to run git commands (marketplace root in dev mode)

        try:
            # Try installed plugin first
            if self._installed_path.exists():
                data = json.loads(self._installed_path.read_text())
                plugin = data.get("plugins", {}).get(self.plugin_id, {})
                self.version = plugin.get("version", "unknown")
                self.installed_sha = plugin.get("gitCommitSha", "unknown")
                self.install_path = plugin.get("installPath", "")
                # In installed mode, git and install paths are the same
                self.git_path = self.install_path

            # Fallback to dev mode (local marketplace)
            if not self.install_path and self._marketplaces_path.exists():
                data = json.loads(self._marketplaces_path.read_text())
                marketplace_root = data.get("claude-code-toolbox", {}).get("installLocation", "")
                if marketplace_root:
                    dev_path = Path(marketplace_root) / "ai-assisted-development"
                    plugin_json = dev_path / ".claude-plugin" / "plugin.json"
                    if plugin_json.exists():
                        plugin_data = json.loads(plugin_json.read_text())
                        self.version = plugin_data.get("version", "dev")
                        # In dev mode, use marketplace root for git operations
                        # (bash script bug: tried to use dev_path, but .git is at marketplace root)
                        self.git_path = marketplace_root
                        result = subprocess.run(
                            ["git", "rev-parse", "HEAD"],
                            cwd=self.git_path,
                            capture_output=True,
                            text=True,
                            timeout=1
                        )
                        self.installed_sha = result.stdout.strip() if result.returncode == 0 else "unknown"
                        self.install_path = str(dev_path)
        except Exception:
            # Fallback to defaults on any error
            pass
```

**Error handling:** All file reads in try/except, falls back to "unknown" values. Path.home() returning empty string raises ValueError with clear message.

**Dev mode detection:** The bash script has a bug - it tries to run git in the plugin install path, but .git is at the marketplace root. In local marketplace mode, we need to use marketplace root for git operations, not install_path.

**Relationship between paths:**
- `install_path`: Where plugin files exist (`~/.claude/plugins/...` or `{marketplace_root}/ai-assisted-development`)
- `git_path`: Where to run git commands (marketplace root in dev mode, install_path otherwise)
- In installed mode: both are the same
- In dev mode: install_path is subdirectory of git_path

### GitChecker Class

**Responsibility:** Compare installed SHA with current git HEAD to detect dev mode.

```python
class GitChecker:
    """Git state checker for dev mode detection."""

    def __init__(self, git_path: str):
        """Initialize with path where git commands should run.

        Args:
            git_path: Directory containing .git (marketplace root in dev mode, install_path in installed mode)
        """
        self.git_path = git_path
        self.current_sha = self._get_current_sha()

    def _get_current_sha(self) -> str:
        """Get current git HEAD SHA from git_path."""
        if not self.git_path:
            return ""

        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.git_path,
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass

        return ""

    def is_dev_mode(self, installed_sha: str) -> bool:
        """Check if current SHA differs from installed SHA.

        Returns True if:
        - We have a current SHA from git
        - Installed SHA is not "unknown" (plugin is installed)
        - SHAs don't match (we have uncommitted changes or different commit)

        Returns False if git failed, plugin not installed, or SHAs match.
        """
        return (self.current_sha != "" and
                installed_sha != "unknown" and
                self.current_sha != installed_sha)
```

**Key details:**
- Timeout on git command (2 seconds max - allows for slower git operations)
- Returns empty string on any error
- `is_dev_mode()` returns False if git fails or no mismatch
- Compares full SHAs, not just short hashes

### StatusLineFormatter Class

**Responsibility:** Build the status line output string (no I/O).

```python
class StatusLineFormatter:
    """Formats status line output."""

    def __init__(self, plugin_id: str = "ai-assisted-development@claude-code-toolbox"):
        self.plugin_id = plugin_id

    def format(self, metadata: PluginMetadata, git: GitChecker,
               request_id: str, request_dir: Path) -> str:
        """Build formatted status line string.

        Returns:
            Multi-line status string
        """
        lines = []

        # Check if plugin is installed
        if metadata.version == "unknown" or not metadata.install_path:
            lines.append(f"{self.plugin_id}: ⚠️  Plugin not installed.")
            return "\n".join(lines)

        # Plugin version line
        if git.is_dev_mode(metadata.installed_sha):
            lines.append(f"{self.plugin_id}: v{metadata.version} ⚠️")
            lines.append(f"📦 Installed: {metadata.installed_sha[:7]} | Current: {git.current_sha[:7]}")
        else:
            lines.append(f"{self.plugin_id}: v{metadata.version}")
            lines.append(f"📦 Installed: {metadata.installed_sha[:7]}")

        # Request info
        if request_id:
            lines.append(f"📁 Request: {request_id}")
            # Abbreviate home directory (prefix match only, like bash)
            display_path = str(request_dir)
            home_str = str(Path.home())
            if display_path.startswith(home_str):
                display_path = "~" + display_path[len(home_str):]
            lines.append(f"💾 {display_path}/")
        else:
            lines.append("📁 No active request")

        return "\n".join(lines)
```

**Output matches current bash script exactly.**

### Main Entry Point

**Responsibility:** Interface between Claude Code and our framework (like agent-lifecycle.py).

```python
#!/usr/bin/env python3
"""Statusline hook for Claude Code - displays plugin and request status."""

import json
import subprocess
import sys
from pathlib import Path

from lifecycle.processing import get_toolbox_root, get_current_request_id


def main():
    """Read statusline hook input, format output, print to stdout.

    Error handling policy:
    - Components (PluginMetadata, GitChecker, StatusLineFormatter) raise exceptions
    - main() catches all exceptions, prints to stderr, always exits 0
    - Never block Claude Code UI, even on catastrophic failure
    """
    try:
        # Read hook input from stdin
        hook_input = json.load(sys.stdin)
        session_id = hook_input.get("session_id", "")
        cwd = hook_input.get("cwd", "")

        # Get toolbox root and current request (shared utilities)
        toolbox_root = get_toolbox_root(hook_input)
        request_id = get_current_request_id(session_id, toolbox_root)

        # Build request directory path if we have a request
        request_dir = Path(toolbox_root) / ".toolbox" / "events" / request_id if request_id else Path()

        # Gather plugin and git information
        metadata = PluginMetadata()
        git = GitChecker(metadata.git_path)

        # Format and output
        formatter = StatusLineFormatter()
        output = formatter.format(metadata, git, request_id, request_dir)
        print(output)

    except Exception as e:
        # Print error to stderr so user sees it, but don't break UI
        print(f"Statusline error: {e}", file=sys.stderr)

    sys.exit(0)  # Always exit 0 - never block Claude Code


if __name__ == "__main__":
    main()
```

**Error handling policy:**
- All components raise exceptions on errors
- `main()` catches everything and prints to stderr
- Always exits 0 to never block Claude Code UI
- User sees errors but UI remains functional

---

## Testing Strategy

### Test Coverage

**test_lifecycle_processing.py additions:**
- `get_current_request_id()` returns request_id from global state
- Returns empty string when file missing
- Returns empty string when session not found
- Returns empty string when session_id is None
- Returns empty string when session_id is empty string
- Returns empty string when toolbox_root is None
- Returns empty string when toolbox_root is empty string
- Handles malformed JSON (returns empty string)
- Handles global state with wrong structure (not a dict, missing session_requests key)

**test_statusline.py:**

**PluginMetadata tests:**
- Reads from installed_plugins.json correctly (sets both install_path and git_path to same value)
- Falls back to marketplace when not installed
- Falls back to dev mode when in local marketplace (install_path is plugin subdir, git_path is marketplace root)
- Handles missing/malformed JSON files gracefully
- Raises ValueError when Path.home() returns empty string
- Example JSON structures embedded in tests for documentation:
  ```python
  # installed_plugins.json structure
  {
    "version": 1,
    "plugins": {
      "plugin-id@marketplace-id": {
        "version": "1.0.0",
        "installedAt": "2025-12-12T14:37:39.831Z",
        "lastUpdated": "2025-12-12T14:37:39.831Z",
        "installPath": "/path/to/plugin",
        "gitCommitSha": "abc123...",
        "isLocal": true
      }
    }
  }

  # known_marketplaces.json structure
  {
    "marketplace-id": {
      "source": {"source": "directory", "path": "/path/to/marketplace"},
      "installLocation": "/path/to/marketplace",
      "lastUpdated": "2025-12-12T14:37:34.543Z"
    }
  }
  ```

**GitChecker tests:**
- Detects git SHA correctly from git_path
- Handles non-git directories (returns empty string)
- Handles empty git_path (returns empty string)
- `is_dev_mode()` returns True when SHAs differ
- `is_dev_mode()` returns False when SHAs match
- `is_dev_mode()` returns False when installed_sha is "unknown"
- `is_dev_mode()` returns False when current_sha is empty
- Timeout behavior (mock subprocess to exceed 2 seconds)
- Git command failure (non-zero exit code)

**StatusLineFormatter tests:**
- Output format matches bash script exactly
- Dev mode warning appears correctly (version line has ⚠️, second line shows both SHAs)
- Normal mode shows single SHA line
- Request display with home directory abbreviation (prefix match only)
- Request path outside home directory (no abbreviation)
- "No active request" when request_id empty
- "No active request" when request_id is None
- Plugin not installed message (version="unknown" or no install_path)
- SHA truncation to 7 characters ([:7] slice)

**Main integration test:**
- Mock stdin with sample hook input
- Verify stdout output matches expected format
- Verify exit code is always 0
- Verify errors go to stderr

---

## Implementation Notes

### What's Reused (lifecycle module)
- `get_toolbox_root()` - existing
- `get_current_request_id()` - new shared function
- Request directory path construction pattern

### What's Statusline-Specific
- Plugin metadata reading (installed_plugins.json, known_marketplaces.json)
- Git SHA comparison for dev mode detection
- Status line formatting and output

### Migration Path
1. Add `get_current_request_id()` to lifecycle/processing.py with tests
2. Update orchestrator.py to use the new shared function
3. Implement statusline.py with full test coverage
4. Update hooks/hooks.json to use statusline.py instead of statusline.sh
5. Update project-local .claude/settings.json (or .claude/settings.local.json) for testing
6. Reinstall plugin and verify output matches bash script exactly
7. Delete statusline.sh after verification

---

## Benefits

**Maintainability:**
- Single source of truth for request lookup logic
- Testable components (no subprocess mocking in business logic)
- Clear separation: shared infrastructure vs statusline-specific

**Reliability:**
- Always exits 0 (never breaks UI)
- Graceful degradation on errors
- Errors visible to user via stderr

**Consistency:**
- Same interface pattern as agent-lifecycle.py
- Reuses established lifecycle patterns
- Request scoping logic identical to orchestrator
