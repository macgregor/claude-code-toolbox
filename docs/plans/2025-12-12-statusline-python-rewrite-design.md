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
        return ""
```

**Why here:** Already has `get_toolbox_root()`, natural companion. Both orchestrator and statusline need this exact logic.

**Orchestrator refactor:** Replace lines 133-135 in `_get_or_create_request_id()` to use this shared function.

---

## Component Design

### PluginMetadata Class

**Responsibility:** Read plugin version, SHA, and install path from Claude's plugin files.

```python
class PluginMetadata:
    """Plugin installation metadata from Claude Code."""

    def __init__(self, plugin_id: str = "ai-assisted-development@claude-code-toolbox"):
        self.plugin_id = plugin_id
        self._installed_path = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
        self._marketplaces_path = Path.home() / ".claude" / "plugins" / "known_marketplaces.json"
        self._load()

    def _load(self):
        """Load metadata from installed_plugins.json, fallback to marketplace."""
        self.version = "unknown"
        self.installed_sha = "unknown"
        self.install_path = ""

        try:
            # Try installed plugin first
            if self._installed_path.exists():
                data = json.loads(self._installed_path.read_text())
                plugin = data.get("plugins", {}).get(self.plugin_id, {})
                self.version = plugin.get("version", "unknown")
                self.installed_sha = plugin.get("gitCommitSha", "unknown")
                self.install_path = plugin.get("installPath", "")

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
                        self.installed_sha = "dev"
                        self.install_path = str(dev_path)
        except Exception:
            # Fallback to defaults on any error
            pass
```

**Error handling:** All file reads in try/except, falls back to "unknown" values.

### GitChecker Class

**Responsibility:** Compare installed SHA with current git HEAD to detect dev mode.

```python
class GitChecker:
    """Git state checker for dev mode detection."""

    def __init__(self, install_path: str):
        self.install_path = install_path
        self.current_sha = self._get_current_sha()

    def _get_current_sha(self) -> str:
        """Get current git HEAD SHA from install path."""
        if not self.install_path:
            return ""

        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.install_path,
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass

        return ""

    def is_dev_mode(self, installed_sha: str) -> bool:
        """Check if current SHA differs from installed SHA."""
        return (self.current_sha != "" and
                installed_sha != "dev" and
                self.current_sha != installed_sha)
```

**Key details:**
- Timeout on git command (1 second max)
- Returns empty string on any error
- `is_dev_mode()` returns False if git fails or no mismatch

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
            display_path = str(request_dir).replace(str(Path.home()), "~")
            lines.append(f"💾 {display_path}/")
        else:
            lines.append("📁 No active request")

        return "\n".join(lines)
```

**Output matches current bash script exactly.**

### Main Entry Point

**Responsibility:** Interface between Claude Code and our framework (like agent-lifecycle.py).

```python
def main():
    """Read statusline hook input, format output, print to stdout."""
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
        git = GitChecker(metadata.install_path)

        # Format and output
        formatter = StatusLineFormatter()
        output = formatter.format(metadata, git, request_id, request_dir)
        print(output)

    except Exception as e:
        # Print error to stderr, don't break UI
        print(f"Statusline error: {e}", file=sys.stderr)

    sys.exit(0)  # Always exit 0


if __name__ == "__main__":
    main()
```

**Error handling:**
- Exceptions printed to stderr (user sees them)
- Always exit 0 (never block Claude Code)

---

## Testing Strategy

### Test Coverage

**test_lifecycle_processing.py additions:**
- `get_current_request_id()` returns request_id from global state
- Returns empty string when file missing
- Returns empty string when session not found
- Handles malformed JSON

**test_statusline.py:**

**PluginMetadata tests:**
- Reads from installed_plugins.json correctly
- Falls back to marketplace when not installed
- Falls back to dev mode when in local marketplace
- Handles missing/malformed JSON files gracefully

**GitChecker tests:**
- Detects git SHA correctly
- Handles non-git directories
- `is_dev_mode()` logic (matches/differs/dev mode special case)
- Timeout behavior (mock subprocess)

**StatusLineFormatter tests:**
- Output format matches bash script exactly
- Dev mode warning appears correctly
- Request display with home directory abbreviation
- "No active request" when request_id empty
- Plugin not installed message

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
1. Add `get_current_request_id()` to lifecycle/processing.py
2. Add tests for the new shared function
3. Implement statusline.py with full test coverage
4. Update .claude/settings.json to use statusline.py
5. Verify output matches bash script
6. Delete statusline.sh

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
