---
name: statusline-event-handler-design
description: >
  Design for implementing statusline as an event handler in the lifecycle system,
  reusing orchestrator infrastructure for request context and error handling.
created: 2025-12-12
status: design
---

# StatusLine Event Handler Design

**Created**: 2025-12-12
**Status**: Design

---

## Problem

The bash script `statusline.sh` operates separately from the lifecycle system, duplicating logic for request lookup and lacking tests. We want statusline to leverage the lifecycle orchestrator infrastructure while maintaining clean separation of concerns.

**Key insight**: StatusLine is just another event that needs request context and plugin state. Implementing it as an event handler lets us reuse RequestContext, error handling, and the event routing pattern.

---

## Goals

1. Implement statusline as an event handler in the lifecycle system
2. Reuse orchestrator infrastructure (RequestContext, error handling, routing)
3. Replace bash script with testable Python code
4. Maintain identical output format
5. No new entry points - use existing `agent-lifecycle.py`

---

## Architecture

### Overview

**Flow:**
1. Settings.json calls `agent-lifecycle.py` (existing entry point)
2. StatusLine hook input → orchestrator
3. Orchestrator infers event type (missing hook_event_name → "StatusLine")
4. Orchestrator builds RequestContext (existing logic)
5. Orchestrator routes to StatusLineHandler
6. Handler reads plugin metadata, checks git, formats output, prints to stdout
7. Handler raises NonBlockingError if operations fail
8. Orchestrator logs errors to stderr (existing error handling)
9. Always exits 0 (preserves Claude Code UI)

**What we get for free:**
- RequestContext (session_id, request_id, request_dir, transcript_path)
- Error handling (NonBlockingError → stderr + exit 1)
- Event routing pattern
- State management infrastructure

**What's new:**
- StatusLine event inference
- StatusLineHandler implementation
- Plugin metadata reading
- Git SHA checking
- Output formatting

### Settings Configuration

```json
{
  "statusLine": {
    "type": "command",
    "command": "python ${CLAUDE_PLUGIN_ROOT}/src/agent-lifecycle.py"
  }
}
```

Same entry point as lifecycle hooks - no separate script needed.

---

## Component Design

### File Structure

```
ai-assisted-development/src/lifecycle/
├── handlers/
│   ├── __init__.py              # Exports EventHandler, StatusLineHandler
│   ├── base.py                  # EventHandler ABC (moved from handlers.py)
│   └── statusline.py            # StatusLineHandler + helpers
└── handlers.py                  # DELETE - replaced by handlers/
```

**Pattern established:**
- Each handler in own file under `handlers/`
- Helper classes live alongside handler (statusline-specific, not shared)
- Easy to locate: "where's statusline?" → `handlers/statusline.py`

### 1. StatusLineHandler

**File:** `lifecycle/handlers/statusline.py`

**Responsibility:** Orchestrate plugin metadata, formatting, and output.

```python
class StatusLineHandler(EventHandler):
    """Handler for StatusLine hook events."""

    PLUGIN_ID = "ai-assisted-development@claude-code-toolbox"
    MARKETPLACE_ID = "claude-code-toolbox"

    def handle(self, context: RequestContext, event_data: EventData) -> RequestContext:
        """Build and print statusline.

        Args:
            context: Request context from orchestrator
            event_data: Hook input data

        Returns:
            Unchanged context

        Raises:
            NonBlockingError: On any failure (logged to stderr, exits 1)
        """
        try:
            metadata = PluginMetadata(self.PLUGIN_ID, self.MARKETPLACE_ID)
            formatter = StatusLineFormatter()
            output = formatter.format(metadata, context)
            print(output)
            return context
        except Exception as e:
            raise NonBlockingError(f"StatusLine failed: {e}")
```

**Error handling:**
- Raises NonBlockingError on any failure
- Orchestrator catches, logs to stderr, exits 1
- Claude Code continues normally (UI preserved)

**Configuration:**
- Class constants for plugin/marketplace IDs
- When copying to another repo, just change constants
- Later can add constructor params or config file if needed

### 2. PluginMetadata

**Responsibility:** Read plugin state from Claude's files and git.

```python
class PluginMetadata:
    """Plugin installation metadata from Claude Code."""

    def __init__(self, plugin_id: str, marketplace_id: str):
        self.plugin_id = plugin_id
        self.marketplace_id = marketplace_id

        # Populated by _load()
        self.version = "unknown"
        self.installed_sha = "unknown"
        self.current_sha = ""
        self.install_path = ""
        self.is_dev_mode = False
        self.needs_warning = False

        self._load()

    def _load(self):
        """Load metadata from Claude's JSON files and git."""
        # Read installed_plugins.json
        # Read known_marketplaces.json
        # Detect dev mode (source.source == "directory")
        # Run git if dev mode
        # Set needs_warning if SHAs differ
```

**Data sources:**

1. **installed_plugins.json** (`~/.claude/plugins/installed_plugins.json`):
   - `plugins[plugin_id].version` → version
   - `plugins[plugin_id].gitCommitSha` → installed_sha
   - `plugins[plugin_id].installPath` → install_path

2. **known_marketplaces.json** (`~/.claude/plugins/known_marketplaces.json`):
   - `marketplaces[marketplace_id].source.source == "directory"` → is_dev_mode
   - `marketplaces[marketplace_id].installLocation` → marketplace root

3. **Git (dev mode only)**:
   - Run: `git -C <install_path> rev-parse HEAD`
   - Timeout: 2 seconds
   - Result → current_sha

**Dev mode detection:**
- Check if marketplace `source.source == "directory"`
- Only local directory marketplaces are dev mode
- Plugins from GitHub/git URLs are not dev mode (even though isLocal=true)

**SHA comparison:**
- In dev mode: compare installed_sha with current_sha
- If different: `needs_warning = True`
- Warns developer they may need to reinstall plugin

**Error handling (graceful degradation):**
- File not found → use default "unknown" values
- JSON parse error → use default values
- Git command fails → `current_sha = ""`
- No exceptions raised (silent fallback to defaults)

### 3. StatusLineFormatter

**Responsibility:** Format output string (pure function, no I/O).

```python
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
        # Build output matching bash script format
```

**Output formats:**

**Plugin not installed:**
```
ai-assisted-development@claude-code-toolbox: ⚠️  Plugin not installed.
```

**Normal mode (SHAs match or not dev mode):**
```
ai-assisted-development@claude-code-toolbox: v1.0.0
📦 Installed: a1b2c3d
📁 Request: 2025-12-11T00-15-32_e36738f5
💾 ~/.toolbox/events/2025-12-11T00-15-32_e36738f5/
```

**Dev mode (SHAs differ):**
```
ai-assisted-development@claude-code-toolbox: v1.0.0 ⚠️
📦 Installed: a1b2c3d | Current: f8e6b21
📁 Request: 2025-12-11T00-15-32_e36738f5
💾 ~/.toolbox/events/2025-12-11T00-15-32_e36738f5/
```

**No active request:**
```
ai-assisted-development@claude-code-toolbox: v1.0.0
📦 Installed: a1b2c3d
📁 No active request
```

**Formatting details:**
- SHA truncation: Show first 7 characters (`sha[:7]`)
- Path abbreviation: Replace `Path.home()` prefix with `~`
- Request check: `context.request_id` empty → "No active request"
- Plugin check: `version == "unknown"` or no `install_path` → "Plugin not installed"

**Pure function:**
- No I/O operations
- Gets home directory internally for path abbreviation
- Deterministic output for testing

---

## Changes to Existing Code

### EventData Model Simplification

**Current:**
```python
@dataclass(frozen=True)
class EventData:
    hook_event_name: str
    raw_hook_input: str  # JSON string
    fields: Dict[str, Any]  # Duplicates raw_hook_input
```

**New:**
```python
@dataclass(frozen=True)
class EventData:
    hook_event_name: str
    raw_hook_input: Dict[str, Any]  # Keep as dict, no serialization
```

**Impact:**
- Change all `event_data.fields` → `event_data.raw_hook_input`
- Remove JSON serialization/deserialization round-trip
- Simpler API, less code

### Orchestrator Changes

**1. Event inference in `_build_event_data()`:**

```python
def _build_event_data(self, raw_hook_input: Dict[str, Any]) -> EventData:
    """Extract/validate fields, create EventData."""

    # Validate required fields
    session_id = raw_hook_input.get("session_id")
    transcript_path = raw_hook_input.get("transcript_path")
    cwd = raw_hook_input.get("cwd")

    if not session_id or not transcript_path or not cwd:
        raise NonBlockingError(
            f"Invalid hook input: missing required fields "
            f"(session_id={bool(session_id)}, "
            f"transcript_path={bool(transcript_path)}, "
            f"cwd={bool(cwd)})"
        )

    # Infer StatusLine if hook_event_name missing
    hook_event_name = raw_hook_input.get("hook_event_name", "")
    if not hook_event_name:
        hook_event_name = "StatusLine"

    return EventData(
        hook_event_name=hook_event_name,
        raw_hook_input=raw_hook_input
    )
```

**Validation strategy:**
- All hooks (lifecycle + statusline) need session_id, transcript_path, cwd
- Missing required fields → NonBlockingError (fail fast with clear message)
- Missing hook_event_name → infer "StatusLine" (statusline hook doesn't provide it)
- Explicit events (SessionStart, UserPromptSubmit, etc.) pass through unchanged

**2. Handler routing in `_get_handler()`:**

```python
def _get_handler(self, event_name: str) -> Optional[EventHandler]:
    """Route event to handler."""
    if event_name == "StatusLine":
        from .handlers.statusline import StatusLineHandler
        return StatusLineHandler()
    return None
```

**Design notes:**
- New handler instance each execution (script lifetime is single hook)
- Lazy import (only load StatusLineHandler when needed)
- Easy to add more handlers: add elif branch

### Handler Directory Structure

**Create `lifecycle/handlers/` package:**

1. Move `EventHandler` ABC from `handlers.py` to `handlers/base.py`
2. Create `handlers/statusline.py` with StatusLineHandler + helpers
3. Update `handlers/__init__.py`:
   ```python
   from .base import EventHandler
   from .statusline import StatusLineHandler

   __all__ = ["EventHandler", "StatusLineHandler"]
   ```
4. Delete `lifecycle/handlers.py` (replaced by directory)

**Import paths:**
- Orchestrator: `from .handlers import StatusLineHandler`
- Handler imports: `from ..models import RequestContext, EventData`
- Handler imports: `from ..errors import NonBlockingError`
- Handler imports: `from .base import EventHandler`

---

## Testing Strategy

### test_lifecycle_orchestrator.py additions

**EventData changes:**
- All references to `event_data.fields` → `event_data.raw_hook_input`
- EventData stores dict, not JSON string

**StatusLine event inference:**
- Missing hook_event_name → inferred as "StatusLine"
- Explicit hook_event_name → passes through unchanged

**Input validation:**
- Missing session_id → NonBlockingError
- Missing transcript_path → NonBlockingError
- Missing cwd → NonBlockingError
- Valid statusline input → routes to StatusLineHandler

**Handler routing:**
- "StatusLine" event → calls StatusLineHandler
- Other events → returns None (no handler)

### test_statusline.py (new file)

**PluginMetadata tests:**

*Reading plugin files:*
- Reads installed_plugins.json correctly
- Extracts version, gitCommitSha, installPath
- Reads known_marketplaces.json correctly
- Detects dev mode when source.source == "directory"
- Not dev mode when source is "github" or other

*Git operations:*
- Runs `git -C <path> rev-parse HEAD` in dev mode
- Compares installed_sha with current_sha
- Sets needs_warning=True when SHAs differ
- Sets needs_warning=False when SHAs match
- Does not run git when not dev mode
- Git command timeout (2 seconds)
- Git command failure → current_sha = ""

*Error handling:*
- Missing installed_plugins.json → version="unknown"
- Missing known_marketplaces.json → is_dev_mode=False
- Invalid JSON → graceful fallback to defaults
- Plugin not found in files → version="unknown"

*Example JSON structures in tests (documentation):*
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
    "source": {
      "source": "directory",
      "path": "/path/to/marketplace"
    },
    "installLocation": "/path/to/marketplace",
    "lastUpdated": "2025-12-12T14:37:34.543Z"
  }
}
```

**StatusLineFormatter tests:**

*Output formats:*
- Plugin not installed message
- Normal mode (single SHA line)
- Dev mode warning (both SHAs, ⚠️ emoji)
- Request info display
- No active request message
- SHA truncation to 7 chars

*Path handling:*
- Path abbreviation with home directory prefix
- Path outside home (no abbreviation)
- Empty request_id → "No active request"
- Empty request_dir → handled gracefully

*Edge cases:*
- version="unknown" → shows in output
- installed_sha="unknown" → shows "unknown"
- current_sha="" → shows empty (or hidden)
- request_id="" → "No active request"

**StatusLineHandler tests:**

*Integration:*
- Creates PluginMetadata with correct IDs
- Calls formatter with metadata + context
- Prints output to stdout
- Returns unchanged context

*Error handling:*
- PluginMetadata raises exception → NonBlockingError
- Formatter raises exception → NonBlockingError
- Print fails → NonBlockingError

**Testing approach:**
- Use temporary directories for JSON files
- Mock subprocess for git commands
- Mock print() to capture output
- Verify exact output format matches bash script

---

## Implementation Sequence

1. **Refactor existing code:**
   - Simplify EventData (remove .fields)
   - Update orchestrator._build_event_data() (validation + inference)
   - Update all event_data.fields → event_data.raw_hook_input
   - Create handlers/ directory structure
   - Move EventHandler ABC to handlers/base.py
   - Update orchestrator._get_handler() for StatusLine routing

2. **Implement StatusLineHandler:**
   - Create handlers/statusline.py
   - Implement PluginMetadata class
   - Implement StatusLineFormatter class
   - Implement StatusLineHandler class

3. **Add tests:**
   - Update test_lifecycle_orchestrator.py for EventData changes
   - Add StatusLine routing tests
   - Create test_statusline.py with full coverage

4. **Integration:**
   - Test with actual hook input (use statusline_input.txt)
   - Verify output matches bash script exactly
   - Delete statusline.sh after verification

**Note:** User will manually update settings.json when ready to enable statusline.

---

## Benefits

**Reuse:**
- RequestContext from orchestrator (request_id, request_dir, session_id)
- Error handling pattern (NonBlockingError → stderr + exit 1)
- Event routing infrastructure
- Single entry point for all hooks

**Testability:**
- Pure functions (PluginMetadata, StatusLineFormatter)
- No subprocess mocking in business logic (git isolated to PluginMetadata)
- Clear separation of concerns
- Easy to verify output format

**Maintainability:**
- Python instead of bash (better error handling, testing, readability)
- Established pattern for future event handlers
- Handler directory structure scales naturally
- Configuration centralized in handler class constants

**Consistency:**
- Same interface as other event handlers
- Same error handling strategy
- Same file organization pattern
- Reuses lifecycle system infrastructure

---

## Future Extensions

**Easy additions:**
- New event handlers follow same pattern (handlers/foo.py)
- Handler configuration via constructor or config file
- Shared utilities between handlers (if patterns emerge)
- Handler registry pattern (if many handlers)

**StatusLine specific:**
- Configurable output format (if users request customization)
- Additional plugin state (marketplace info, update status)
- Performance metrics (if request context expands)
